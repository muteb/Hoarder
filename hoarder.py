import os
import sys
import shutil
import zipfile
import subprocess
import os
import string
import argparse
import platform
from system.commands import cmds
import json
import csv
import yaml


# ----------------------------- check the existence of ymal config and rawcopy46.exe--------------------
if os.path.isfile("Hoarder.yml") == False:
    print "*"*80
    print "please copy the ymal configuration into the same folder as Horader.exe"
    print "*"*80
    sys.exit()
if os.path.isfile("RawCopy64.exe") == False:
    print "*"*80
    print "please copy the RawCopy64.exe configuration into the same folder as Horader.exe"
    print "*"*80
    sys.exit()
# ------------------------- Arguments Parsing ------------------------------


parser = argparse.ArgumentParser(description="Hashes check with common NSLR library and virustotal\n\n")
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-e', '--events', action="store_true", help='Get all windows events')
parser.add_argument('-c', '--amcache', action="store_true", help='Get amcache or recentfile')
parser.add_argument('-m', '--mft', action="store_true", help='Get $MFT file')
parser.add_argument('-u', '--usnjrl', action="store_true", help='Get all usnjrl files')
parser.add_argument('-i', '--hives', action="store_true", help='Get all config hives')
parser.add_argument('-n', '--ntusers', action="store_true", help='Get all NTUsers files')
parser.add_argument('-r', '--recent', action="store_true", help='Get all recent files')
parser.add_argument('-p', '--persistance', action="store_true", help='Get all presistances from schudele tasks and WMI')
parser.add_argument('-l', '--lightweight', action="store_true", help='Get all and execulde the UsnJrl due to the size')
parser.add_argument('-y', '--yaml' , dest="yaml_config", help='Yaml file configuration')

args = parser.parse_args(sys.argv[1:])

# -------------------- Parse YAML File -------------------
yaml_config = ""
if args.yaml_config is None:
  	yaml_path = ".\\Hoarder.yml"
else:
 	yaml_path = args.yaml_config

yaml_file = open(yaml_path, 'r')
yaml_config = json.loads( json.dumps( yaml.load(yaml_file.read()) ) ) # parse the yaml_file and get the result as json format
yaml_file.close()

# -------------------------- Defined functions ----------------------------


def category_lst(val):
    if "64" in val:
        dic = yaml_config['all_artifacts_64']
    elif "32" in val:
        dic = yaml_config['all_artifacts_32']
    return dic

def get_system_live_det():
    lst = ['osdetails','processlst','servicelst','partitationslst','get_network_interfaces','get_network_conn','get_dns_cache','getallusers','current_logged_in']
    # main_dir = "Artifacts"
    # if os.path.exists(main_dir):
    #     os.rmdir(main_dir)
    # os.mkdir(main_dir)
    for i in lst:
        commandcls = cmds(i)
        info= commandcls.pass_command()
        with open("Artifacts\\system_live\\"+i, 'w') as outfile:
            try:
                json.dump(info, outfile,ensure_ascii=False)
            except OSError as err:
                print "the error is %s" % err

def get_vol():
    available_drives = ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
    xf = platform.architecture()[0]
    for drive in available_drives:
        dee = os.listdir(drive+"\\")
        if "Windows" in dee and "Users" in dee:
            return drive,xf


def rawcopy_aft(input,output):
    file_e = 'RawCopy64.exe'+' /FileNamePath:' +input+' /OutputPath:'+output
    print file_e
    os.system(file_e)

def rawcopy_filter(e,path):
    xe = str(e)
    xxe = xe.split()
    if "Ntuser" in path:
        input = xxe[3].replace("'","").replace("\\\\","\\")
        output = path
        rawcopy_aft(input,output)

    lst=[]
    lst3 =[]
    for f in xxe:
        xf =  " ".join(f.split("denied:")[0].split("),"))
        for xnf in xf:

             if "('C:" in xf:
                 lst.append(xf.split("('")[1].replace("',",""))
    lst2 = list(set(lst))
    for sl in lst2:
        sl = sl.replace("\\\\","\\")
        lst3.append(sl)
    for xnn in lst3:
        rawcopy_aft(xnn,path)


def perfom_actoin(drv,path,i,output):
    src = drv+path+i
    #folder = 'Artifacts\\'+i
    #os.mkdir(folder)
    oxr =output
    rawcopy_aft(src,oxr)

def collect_artfacts(drv,arch,target):
    drive = drv
    varl = category_lst(arch)
    path = varl[target]['path']
    para = varl[target]['para']
    output = varl[target]['output']
    if isinstance(path, list):
        if target =='wmi_per':
            i = 0
            for x in path:
                input = drv+ x
                i = i+1
                src =  os.path.join(drive+x +para)
                file_ex = os.path.isfile(src)
                if file_ex == True:
                    dst = output+"\\"+str(i)+para
                    os.mkdir(dst)
                    rawcopy_aft(src,dst)
        elif target =='task_per':
            i = 0
            for x in path:
                input = drv+ x
                i = i+1
                src =  os.path.join(drive+x +para)
                file_ex = os.path.isdir(src)
                if file_ex == True:
                    if '32' in x:
                        dst = output+"\\system32"
                        copyDirectory(src,dst)
                    if '64' in x:
                        dst = output+"\\SysWOW64"
                        copyDirectory(src,dst)
    elif isinstance(para, list):
        if target  == 'sys_hiv':
            input = drv+ path
            #os.mkdir(new_dir)
            for x in para:
                try:
                    src =  os.path.join(drive+path +x)
                    file_ex = os.path.isfile(src)
                    if file_ex == True:
                        dst = output
                        rawcopy_aft(src,dst)
                except IOError as e:
                    print e
        else:
            for i in para:
                perfom_actoin(drive,path,i,output)
    else:
        if target  == 'user_pro' or target == 'rcent_jmplst' or target == 'usrclass':
            input = drv+ "\\Users\\"
            usr_fod = os.listdir(input)
            new_dir = output
            for x in usr_fod:
                if target == 'rcent_jmplst':
                    src =  os.path.join(drive+path%x)
                    if os.path.exists(src):
                        ou= os.path.join(output+"\\"+x)
                        os.mkdir(ou)
                        copyDirectory(src, ou+"\\recent")
                    else:
                        pass
                elif target =='usrclass':
                    usr= output+"\\"+x
                    os.mkdir(usr)
                    src =  os.path.join(drive+path%x+para)
                    #print src
                    file_ex = os.path.isfile(src)
                    if file_ex == True:
                        dst = usr
                        rawcopy_aft(src,dst)
                    else:
                        pass
                else:
                    try:
                        oxr = os.path.join(new_dir +"\\" + x)
                        os.mkdir(oxr)
                        src =  os.path.join(drive+path +x +"\\"+ para)
                        file_ex = os.path.isfile(src)
                        if file_ex == True:
                            dst = oxr
                            rawcopy_aft(src,dst)
                    except IOError as e:
                        print e

        else:
            perfom_actoin(drive,path,para,output)
    return "DONE"


def copyDirectory(src, dest):
    try:

        shutil.copytree(src, dest)
    # Directories are the same
    except shutil.Error as e:
        rawcopy_filter(e,"config")

    except OSError as e:
        print e

def collect_folders(drv,arch,target):
    drive = drv
    varl = category_lst(arch)
    path = varl[target]['path']
    para = varl[target]['para']
    path = drv+path
    copyDirectory(path, 'Artifacts\\'+para)
    return "DONE"



def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def create_zipfile():
    zipf = zipfile.ZipFile('Arti.zip', 'w', allowZip64=True)
    zipdir('Artifacts', zipf)
    zipf.close()

def main(argv=[]):



    main_drive,arch = get_vol()

    os.mkdir("Artifacts")
    folders= ['Artifacts\\Recent','Artifacts\\Config','Artifacts\\Events','Artifacts\\Ntuser','Artifacts\\applications','Artifacts\\Usnjrl',\
    'Artifacts\\Ntfs','Artifacts\\Persistence','Artifacts\\Persistence\\WMI','Artifacts\\Persistence\\scheduled_task','Artifacts\\usrclass','Artifacts\\RecycleBin','Artifacts\\system_live']
    for f in folders:
        os.mkdir(f)

    if args.events == True:
        collect_folders(main_drive,arch,'evt_logs')
        get_system_live_det()
        create_zipfile()
    elif args.persistance == True:
        collect_artfacts(main_drive,arch,'task_per')
        collect_artfacts(main_drive,arch,'wmi_per')
        get_system_live_det()
        create_zipfile()
    elif args.recent == True:
        collect_artfacts(main_drive,arch,'rcent_jmplst')
        get_system_live_det()
        create_zipfile()
    elif args.usnjrl ==True:
        collect_artfacts(main_drive,arch,'UsnJrnl')
        get_system_live_det()
        create_zipfile()
    elif args.mft ==True:
        collect_artfacts(main_drive,arch,'ntfs')
        get_system_live_det()
        create_zipfile()
    elif args.amcache == True:
        collect_artfacts(main_drive,arch,'app_lst')
        get_system_live_det()
        create_zipfile()
    elif args.ntusers == True:
        collect_artfacts(main_drive,arch,'user_pro')
        collect_artfacts(main_drive,arch,'usrclass')
        get_system_live_det()
        create_zipfile()
    elif args.hives == True:
        collect_artfacts(main_drive,arch,'sys_hiv')
        get_system_live_det()
        create_zipfile()
    else:

        collect_artfacts(main_drive,arch,'task_per')
        collect_artfacts(main_drive,arch,'rcent_jmplst')
        collect_artfacts(main_drive,arch,'UsnJrnl')
        collect_artfacts(main_drive,arch,'ntfs')
        collect_artfacts(main_drive,arch,'app_lst')
        collect_artfacts(main_drive,arch,'user_pro')
        collect_folders(main_drive,arch,'evt_logs')
        collect_artfacts(main_drive,arch,'sys_hiv')
        collect_artfacts(main_drive,arch,'wmi_per')
        collect_artfacts(main_drive,arch,'usrclass')
        get_system_live_det()
        create_zipfile()


    # if args.events == False and args.mft == False and  args.amcache == False and args.usnjrl == False and  args.hives== False and  args.ntusers==False and  args.persistance==False  and  args.recent==False :
    #     collect_artfacts(main_drive,arch,'task_per')
    #     collect_artfacts(main_drive,arch,'rcent_jmplst')
    #     collect_artfacts(main_drive,arch,'UsnJrnl')
    #     collect_artfacts(main_drive,arch,'ntfs')
    #     collect_artfacts(main_drive,arch,'app_lst')
    #     collect_artfacts(main_drive,arch,'user_pro')
    #     collect_folders(main_drive,arch,'evt_logs')
    #     collect_artfacts(main_drive,arch,'sys_hiv')
    #     collect_artfacts(main_drive,arch,'wmi_per')
    #     collect_artfacts(main_drive,arch,'usrclass')
    #     get_system_live_det()
    #     # if eve == "DONE" and nt == "DONE" and hv=="DONE" and rc=="DONE":
    #     create_zipfile()


if __name__ == '__main__':
    if os.path.exists("Artifacts"):
        shutil.rmtree("Artifacts")
    main(sys.argv)
