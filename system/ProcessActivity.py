import psutil
import sys
import GenertaeHashLib

class process_act:
    def __init__(self,command):
        self.command= command


    def GetAllProcesses(self):
        allproesses =[]
        allprocesshashed=[]
        for proc in psutil.process_iter():
            allproesses.append(proc.as_dict(attrs=['status','cpu_percent','cpu_times','cwd','environ','ppid','exe','username','create_time','cmdline','name','pid']))
        for x in allproesses:
            if x['exe'] !=None:
                hashes = GenertaeHashLib.generate_hash(x['exe'])
                x['md5']= hashes[0]
                x['sha1']=hashes[1]
                x['sha256']=hashes[2]
            allprocesshashed.append(x)

        return allprocesshashed

        #return allproesses

# commandcls = process_act('osdetails')
# info= commandcls.GetAllProcesses()
# for x in info:
# 	print x
#print info
# siz = sys.getsizeof(info)
# print info
