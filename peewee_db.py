from peewee import *
import logging

"""Get vlans from db"""
def peewee_collect(Vlans_table):
    query = Vlans_table.select(Vlans_table.vlan_id, Vlans_table.name)
    vlans_db = dict(query.tuples().execute())
    return(vlans_db)
    
"""Get vlans from db"""
def peewee_revision_collect(Revision_table):
    query = Revision_table.select(Revision_table.source, Revision_table.revision_num)
    rev_dict = dict(query.tuples().execute())
    return(rev_dict)


"""
Add or replace vlans based dict
<SQLite was originally designed with a policy of avoiding arbitrary limits...> . 
So we should check vlan numbers by py3 rather than db during insert/update.
"""
def peewee_edit(Vlans_table,mod_dict):
    vlans_mod = [(k, mod_dict[k]) for k in mod_dict]
    for k in mod_dict:
        query = Vlans_table.replace(vlan_id = k, name = mod_dict[k])
        query.execute()
    #check trigger with updates
    #len(mod_dict.keys())

"""Del Vlans from db"""
def peewee_del(Vlans_table,del_dict):
    query = Vlans_table.delete().where(Vlans_table.vlan_id.in_(list(del_dict.keys())))
    query.execute()

def peewee_edit_rev(Revision_table, src, value):
    query = Revision_table.replace(source = src, revision_num = value)
    query.execute()