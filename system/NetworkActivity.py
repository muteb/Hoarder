import psutil
import subprocess
import os
import re
class network_acts:
    def __init__(self,command):
        self.command = command

    #get the interfaces and their usages
    def each_interface_usage(self):
        pctsfrmnetworkint= psutil.net_io_counters(pernic=True)
        values =[]
        for k, v in pctsfrmnetworkint.items():
            xx =( k , v)
            values.append(xx)
        return values

    #list all connections
    def list_connections(self):
        lst_conn = psutil.net_connections()
        x = []
        for p in lst_conn:
            x.append((p,psutil.Process(p[6]).name()))
        return x

    #Return the addresses associated to each NIC (network interface card)
    def rtn_addresses(self):
        lst_addess = psutil.net_if_addrs()
        return lst_addess

    #Return information about each NIC (network interface card);speed: the NIC speed expressed in mega bits (MB
    def lst_info_address(self):
        lst_info_add = psutil.net_if_stats()
        return lst_info_add

    #retrun dns cache from command lines
    def _list_dns_cache(self):
        values = {}
        # values['HostNames']=[]
        values['hostvalues']=[]
        cache   = os.popen2("ipconfig /displaydns")
        source  = cache[1].read()
        for row in source.split('\n'):
            if ': ' in row:
                key, value = row.split(': ')
                key1 = key.replace('.','')
                key1 = key1.replace(' ','')

                if key1 =='RecordName':
                    {
                values['hostvalues'].append({'key':key1 ,'value':value})
                }
        return values



#
# commandcls = network_acts("C:\hiberfil.sys")
# info= commandcls._list_dns_cache()
# # data2=pickle.dumps(info)
# print info
