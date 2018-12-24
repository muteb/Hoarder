import os, re, sys
import psutil, time
from uptime import boottime , uptime
import subprocess
import FileSize
import installed_software

class sys_act:
    def __init__(self,command):
        self.command= command


    def SysInfo(self):
        values  = {}
        cache   = os.popen2("SYSTEMINFO")
        source  = cache[1].read()
        sysOpts = ["Host Name", "OS Name", "OS Version", "Product ID", "System Manufacturer", "System Model", "System type", "BIOS Version", "Domain", "Windows Directory", "Total Physical Memory", "Available Physical Memory", "Logon Server"]

        for opt in sysOpts:
            values[opt] = [item.strip() for item in re.findall("%s:\w*(.*?)\n" % (opt), source, re.IGNORECASE)][0]
        return values

    def Uptime(self):
        p = boottime()
        x = uptime()
        rtntime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(x))
        return 'BootTime: %s, UpTime:%s'% (p,rtntime )

    def command_line(self):
        if len(self.command) > 0:
            cmd = subprocess.Popen(self.command[:].decode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            output_bytes = cmd.stdout.read() + cmd.stderr.read()
            output_str = str(output_bytes)
            #print output_str
            return output_str

    def powershell_cmd(self):
        if len(self.command) > 0:
            cmd = ["powershell","-ExecutionPolicy", "Bypass", self.command[:].decode("utf-8")]
            p = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            out,err = p.communicate()
            output_bytes = out + err
            output_str = str(output_bytes)
            return output_str

    def diskspace(self):
        x= psutil.disk_usage('D:\\')
        dissp = []
        for xx in x:
            dissp.append(FileSize.convert_size(xx))
        return dissp

    def diskvolumes(self):
        vol = psutil.disk_partitions()
        return vol

    def installed_software(self):
        apps=installed_software.get_installed_products()
        productlst = []
        for app in apps:
            productlst.append(app.InstalledProductName())
        print productlst
        return productlst


# commandcls = sys_act('osdetails')
# info= commandcls.installed_software()
# # data2=pickle.dumps(info)
# print info
