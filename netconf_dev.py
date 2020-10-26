from ncclient import manager
import logging
import xml.dom.minidom
import xmltodict

def netconf_collect(dev):
    with manager.connect(host=dev['ip'], port=dev['port'], username=dev['auth']['login'],
                     password=dev['auth']['passwd'], hostkey_verify=False,
                     device_params=dev['type'],
                     allow_agent=False, look_for_keys=False) as m:
        vlan_filter = '''
            <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                <vlan>
                    <vlan-list xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-vlan">
                    </vlan-list>
                </vlan>
            </native>
            '''
        result = m.get_config('running', filter=('subtree', vlan_filter))
        if xmltodict.parse(result.xml)['rpc-reply'].get('data'):
            vlan_prep = xmltodict.parse(result.xml)['rpc-reply']['data']['native']['vlan']['vlan-list']
            vlans_dict = {int(vlan.get('id')): vlan.get('name') for vlan in vlan_prep}
            return(vlans_dict)
        else:
            return({})

        
def netconf_edit(vlans_add_dict):
    vlans_params = ''
    for k in vlans_add_dict:
        id = f'<id>{k}</id>'
        if vlans_add_dict[k]:
            name = f'<name>{vlans_add_dict[k]}</name>'
        else:
            name = ''
        vlans_params += f'''
                <vlan-list xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-vlan" operation="replace">
                    {id}{name}
                </vlan-list>'''
    vlan_add_rpc = f'''
        <config>
            <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                <vlan>
                    {vlans_params}
                </vlan>
            </native>
        </config>
        '''
    return(vlan_add_rpc)
    """
    reply = dev_conn.edit_config(vlan_add_rpc, target='running')
    print(reply)
    """


def netconf_del(vlans_del_dict):
    vlans_params = ''
    for k in vlans_del_dict:
        id = f'<id>{k}</id>'
        vlans_params += f'''
                <vlan-list xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-vlan" operation="delete">
                    {id}
                </vlan-list>'''
    vlan_del_rpc = f'''
        <config>
            <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                <vlan>
                    {vlans_params}
                </vlan>
            </native>
        </config>
        '''
    return(vlan_del_rpc)
    """
    reply = dev_conn.edit_config(vlan_del_rpc, target='running')
    print(reply)
    """

def netconf_push(dev_conn, rpc, dev_logger):
    dev_logger.debug('Netconf Locking config')
    dev_conn.discard_changes()
    dev_logger.debug('Netconf Got RPCs')
    send_config = dev_conn.edit_config(target='candidate', config=rpc)
    dev_logger.debug(send_config)
    check_config = dev_conn.validate()
    dev_logger.debug(check_config)
    commit_config = dev_conn.commit()
    dev_logger.debug(commit_config)
    dev_logger.debug('Netconf Unlocking config')
