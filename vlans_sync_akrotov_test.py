import unittest
import vlans_sync_akrotov
import netconf_dev

class TestVlans(unittest.TestCase):
    def test_vlan_diff(self):
      old_vlans = {2:'old_vlan_2', 20: 'old_name_20', 200: 'stay_same'}
      new_vlans = {3:'new_vlan_3', 20: 'new_name_20', 200: 'stay_same'}
      mod_dict, del_dict = vlans_sync_akrotov.vlan_diff(old_vlans, new_vlans)
      self.assertEqual(mod_dict,{3: 'new_vlan_3', 20: 'new_name_20'})
      self.assertEqual(del_dict,{2: 'old_vlan_2'})

if __name__ == '__main__':
    unittest.main()