from ncclient import manager
from peewee import *
import json
import logging
import os
import sys
import netconf_dev
import peewee_db


conn_proxy = DatabaseProxy()

class Vlans(Model):
    vlan_id = IntegerField(null=False, primary_key=True)
    name = CharField(max_length=20,null=True)
    description = CharField(null=True)
    class Meta:
        database = conn_proxy

class Revision(Model):
    source = CharField(max_length=100,null=False, unique = True)
    #TODO: handle int32 max value
    revision_num = IntegerField(null=False)
    class Meta:
        database = conn_proxy

def vlan_diff(old, new):
    del_dict = {k:old[k] for k in (old.keys() - new.keys())}
    mod_dict = {k:v for (k,v) in (new.items() - old.items())}
    return(mod_dict,del_dict)


def cron_check_vlans():
    maindir = ''
    if __name__ == '__main__':
        maindir = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        maindir = os.path.dirname(os.path.abspath(__file__))
    
    with open(maindir+'/devs/devs.json','r') as f:
        devs_json = json.load(f)
    
    dev_uuid = f"{devs_json['hostname']}_{devs_json['ip']}"
    
    ncc_logger = create_logger('ncclient','devs/devs_conn.log')
    sync_logger = create_logger('peewee','database/sync.log')
    
    conn = SqliteDatabase(maindir+'/database/vlan_s.db')
    conn_proxy.initialize(conn)
    #DB connection
    try:
        conn.connect()
        sync_logger.debug(conn)
        Vlans.create_table()
        Revision.create_table()
        vlans_db_dict = peewee_db.peewee_collect(Vlans)
    except Exception:
        sync_logger.exception('can not connect to database')
        return
    try:
        vlans_dev_dict = netconf_dev.netconf_collect(devs_json)
    except Exception:
        sync_logger.exception('can not connect to device')
        return
    rev_dict = peewee_db.peewee_revision_collect(Revision)
    """
    The main logic starts here:
    1) vlans from db and dev dicts are equal
        * rev is eq 
            -> return, END of check
        * rev is diff 
            -> Both revision number set to max(dev,db)
    2) vlans from db and dev dicts are different
        * rev is eq (changes from device are possible)
            -> push dev state to db, make db_rev equal 
        * rev is diff
            * db > dev (changes from DB (+ by trigger) or push to dev failed)
                -> push db state to dev, make dev_rev equal
            * dev > db (changes from dev (+ by trigger) and push to DB failed last time)
                -> push dev state to db, make db_rev equal
    """
    if vlans_db_dict == vlans_dev_dict and vlans_db_dict:
        if rev_dict['db'] == rev_dict[dev_uuid]:
            return
        else:
            eq_rev = max(rev_dict['db'], rev_dict[dev_uuid])
            with conn.atomic():
                peewee_db.peewee_edit_rev(Revision, 'db', eq_rev)
                peewee_db.peewee_edit_rev(Revision, dev_uuid, eq_rev)
                sync_logger.debug(f'Revision num for db and dev set equal')
            return

    elif vlans_db_dict != vlans_dev_dict:
        #transaction
        if rev_dict['db'] == rev_dict[dev_uuid]:
            mod_dict, del_dict = vlan_diff(vlans_db_dict, vlans_dev_dict)
            with conn.atomic() as trans:
                peewee_db.peewee_edit(Vlans,mod_dict)
                sync_logger.debug(f'DB records updated for vlans: {", ".join([str(k) for k in mod_dict])}')
                if del_dict:
                    peewee_db.peewee_del(Vlans,del_dict)
                    sync_logger.debug(f'DB records deleted for vlans: {", ".join([str(k) for k in del_dict])}')
                trans.commit()
                rev_dict = peewee_db.peewee_revision_collect(Revision)
                peewee_db.peewee_edit_rev(Revision, dev_uuid, rev_dict['db'])
                sync_logger.debug(f'Revision for {dev_uuid} updated by: {rev_dict["db"]}')
            return
        else:
            if rev_dict['db'] > rev_dict[dev_uuid]:
                mod_dict, del_dict = vlan_diff(vlans_dev_dict, vlans_db_dict)
                #transaction
                try:
                    with manager.connect(host=devs_json['ip'], port=devs_json['port'], username=devs_json['auth'][
                        'login'], password=devs_json['auth']['passwd'], hostkey_verify=False,
                         device_params=devs_json['type'], allow_agent=False, look_for_keys=False) as dev_conn:
                        sync_logger.debug(f'Netconf Connected to {devs_json["ip"]}')
                        mod_rpc = ''
                        del_rpc = ''
                        if mod_dict:
                            mod_rpc = netconf_dev.netconf_edit(mod_dict)
                        if del_dict:
                            del_rpc = netconf_dev.netconf_del(del_dict)
                        with dev_conn.locked(target='candidate'):
                            if mod_rpc:
                                netconf_dev.netconf_push(dev_conn, mod_rpc, sync_logger)
                            if del_rpc:
                                netconf_dev.netconf_push(dev_conn, del_rpc, sync_logger)
                        with conn.atomic():
                            peewee_db.peewee_edit_rev(Revision, dev_uuid, rev_dict['db'])
                            sync_logger.debug(f'Revision for {dev_uuid} updated by: {rev_dict["db"]}')
                except Exception:
                    sync_logger.exception('Push to device is failed')
                return
            elif rev_dict['db'] < rev_dict[dev_uuid]:
                mod_dict, del_dict = vlan_diff(vlans_db_dict, vlans_dev_dict)
                #transaction
                with conn.atomic():
                    if mod_dict:
                        peewee_db.peewee_edit(Vlans,mod_dict)
                    if del_dict:
                        peewee_db.peewee_del(Vlans,del_dict)
                    peewee_db.peewee_edit_rev(Revision, 'db', rev_dict[dev_uuid])
                    sync_logger.debug(f'Revision for DB updated by: {rev_dict[dev_uuid]}')
                #check state and unblock
                return


def create_logger(app,log_file):
    logger = logging.getLogger(app)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s # %(message)s')
    ch = logging.FileHandler(log_file)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.debug(f'Start logging for {app}')
    return(logger)
