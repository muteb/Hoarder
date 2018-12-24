from commands import cmds
import json
import os
import csv

lst = ['osdetails','processlst','servicelst','partitationslst','get_network_interfaces','get_network_conn','get_dns_cache','getallusers','current_logged_in']
main_dir = "Artifacts"
if os.path.exists(main_dir):
    os.rmdir(main_dir)
os.mkdir(main_dir)
for i in lst:
    commandcls = cmds(i)
    info= commandcls.pass_command()
    with open("Artifacts\\"+i, 'w') as outfile:
        try:
            json.dump(info, outfile,ensure_ascii=False)
        except OSError as err:
            print "the error is %s"%err
