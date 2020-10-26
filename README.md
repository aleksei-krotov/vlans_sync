## Vlans sync (homework)
### Description
This repo was created to complete post-interview homework.  
The task was to create a small tool that syncs the VLAN’s on any given machine with database table:
* any update of DB vlans-table reflects to network device config;
* any update of network device vlans-config reflects to DB vlans-table;
* Vlan-id and vlan-name matters. No SVI/BDI dependencies;
* Optional description for each vlan is available at DB;
* No Reserved vlans(like #1 or vDC mapping). Update/delete any vlan.

The easiest way to archive that is to partially repeat VTP-protocol logic.  
But network device will never hold Revision Number for us, it is just out of our App. Flash-storage reading is not affordable and reliable.   

### Assumptions
**Besides of homework:  
Please avoid uncontrollable changes on device at production environment when you have tools for config provisioning.  
use "Device CLI" OR use "Automated orchestration". But never use both.**  

Tool does not support sync of DB with several devices.  
To archive that we need to add: read-only mode, merge multiple updates from single source, queues.  
Like any IGP and BGP does with prefixes. 

Also it is easy to add event-based sync but it engages multiple services:
* Device change triggers snmp/syslog message to the server to init sync; 
* DB changes trigger sync;  
> IOS-XE has no commit_db to push config-change notification by Model-driven Telemetry.

> Be careful with vlan.dat on Catalyst platforms.  
> So as running, netconf-datastore and vlan.dat are different storages. You need a sync control between them.

### Stack
* Python 3.8.2
    * "peewee" ORM for DB operations
    * "ncclient" to collect and push config
    * logging, json, os, sys libs
* Sqlite DB 3.16.2
* Target Device with Cisco IOS-XE 16.12.4. 16.[3-12].* are compatible but never tested


### Design and methods
##### Tools
* SQL DB is not mandatory for this task. But it is useful when you need locks and transactions;
* Netconf from provisioning perspective gives: running-config lock, config validation and commits;
* Use IOS-XE native vlans-config capability: "http://cisco.com/ns/yang/Cisco-IOS-XE-native"

> It is possible to use json-file instead of DB but we need to write additional code for locks and transactions.  
> Restconf is awesome when we need a dict-like data structures. But it does not allow us to lock running-config. As well as CLI.

##### Sync logic
Script starts by cron schedule or manually:
* Start "vlans_sync_akrotov.cron_check_vlans"
* Compare vlans records between DB and device running-config;
* Compare revision numbers at DB storage. Two rows: for the DB and for the device;
* When vlans records are equal: just verify that revision nums are equal too. Or make them equal(max);
* When vlans records are different - check revision nums and start sync. 
    * revision nums equal -> push device running to DB (device is isolated from DB Revision table, so it has priority)
    * revision num of DB is bigger -> push db state to device running (DB changes happend before check)
    * revision num of device is bigger -> push device running to DB (manually change of dev revision, no normal)
* Every update of Vlan table calls SQL trigger which increments Revision number at DB row.  

> More detailed description is available at code comments

#### Device Netconf configuration
Basic ssh-transport and netconf config for IOS-XE:
```Handlebars
hostname {{ hostname }}
ip domain-name {{ domain }}
crypto key generate rsa
ip ssh version 2

username {{ username }} privilege 15 secret {{ password }}

netconf-yang
netconf-yang feature candidate-datastore 
```