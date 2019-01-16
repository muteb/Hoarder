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
import platform


# -------------------------- Defined functions ----------------------------
global ou
ou = 'output'

def category_lst(val):
    if "64" in val:
        dic = yaml_config['all_artifacts_64']
    elif "32" in val:
        dic = yaml_config['all_artifacts_32']
    return dic

# def get_system_live_det(out,drv,arch,target):
#     drive = drv
#     varl = category_lst(arch)
#     path = varl[target]['path']
#     para = varl[target]['para']
#     var = varl[target]['output']
#     for i in para:
#         commandcls = cmds(i)
#         info= commandcls.pass_command()
#         oux = "\\"+out+"\\"
#         with open(oux+var+i, 'w') as outfile:
#             try:
#                 json.dump(info, outfile,ensure_ascii=False)
#             except OSError as err:
#                 print "the error is %s" % err

def get_vol():
    available_drives = ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
    xf = platform.architecture()[0]
    for drive in available_drives:
        dee = os.listdir(drive+"\\")
        if "Windows" in dee and "Users" in dee:
            return drive,xf


def rawcopy_aft(input,output):
    if "$Extend" in input:
        print "Copying " + str(input)
        file_e = 'RawCopy64.exe'+' /FileNamePath:' +input+' /RawDirMode:1 /OutputPath:'+output +" /all"
        os.system(file_e)
    elif "$MFT" in input:

        inputx = input.replace("\\$MFT","")
        for i in range(3):
            val = str(i)
            print "Copying " + val
            file_e = 'RawCopy64.exe'+' /FileNamePath:' +inputx+val+' /OutputPath:'+output
            os.system(file_e)
    else:
        print "Copying " + str(input)
        file_e = 'RawCopy64.exe'+' /FileNamePath:' +input+' /OutputPath:'+output
        #print file_e
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
    src = drv+path+str(i)
    #folder = 'Artifacts\\'+i
    #os.mkdir(folder)
    oxr =output
    rawcopy_aft(src,oxr)

def collect_artfacts(out, drv,arch,target):
    drive = drv
    varl = category_lst(arch)
    path = varl[target]['path']
    para = varl[target]['para']
    var = varl[target]['output']
    output = out +"\\"+ var
    if isinstance(path, list):
        if target =='WMI':
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
        elif target =='scheduled_task':
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
        if target  == 'Config':
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
        if target  == 'Ntuser' or target == 'Recent' or target == 'usrclass':
            input = drv+ "\\Users\\"
            usr_fod = os.listdir(input)
            new_dir = output
            for x in usr_fod:
                if target == 'Recent':
                    src =  os.path.join(drive+path%x)
                    if os.path.exists(src):
                        ou= os.path.join(output+"\\"+x)
                        os.mkdir(ou)
                        copyDirectory(src, ou+"\\Recent")
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

def collect_folders(out,drv,arch,target):
    drive = drv
    varl = category_lst(arch)
    path = varl[target]['path']
    para = varl[target]['para']
    path = drv+path
    copyDirectory(path, out+'\\'+para)
    return "DONE"



def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def create_zipfile():
    zipf = zipfile.ZipFile('Arti.zip', 'w', allowZip64=True)
    zipdir(ou, zipf)
    zipf.close()

def main(argv=[]):
    #print argv

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
    parser.add_argument('-g', '--live', action="store_true", help='Get all live ex. network connection, services..etc ')
    parser.add_argument('-n', '--ntusers', action="store_true", help='Get all NTUsers and usercalss files')
    parser.add_argument('-r', '--recent', action="store_true", help='Get all recent files')
    parser.add_argument('-p', '--schudele', action="store_true", help='Get all presistances from schudele tasks and WMI')
    parser.add_argument('-w', '--wmi', action="store_true", help='Get all presistances from  WMI')
    parser.add_argument('-a', '--all', action="store_true", help='Get all')
    parser.add_argument('-y', '--yaml' , dest="yaml_config", help='Yaml file configuration')



    args = parser.parse_args(argv[1:])

    # -------------------- Parse YAML File -------------------
    global yaml_config
    yaml_config = ""
    if args.yaml_config is None:
          yaml_path = ".\\Hoarder.yml"
    else:
         yaml_path = args.yaml_config

    yaml_file = open(yaml_path, 'r')
    yaml_config = json.loads( json.dumps( yaml.load(yaml_file.read()) ) ) # parse the yaml_file and get the result as json format
    yaml_file.close()


    main_drive,arch = get_vol()

    os.mkdir(ou)
    varl = yaml_config['all_artifacts_64']

    for  key,vaues in varl.items():
        output = varl[key]['output']

        path = os.path.join(ou+"\\"+ key)
        os.mkdir(path)


    if args.events == True:
        collect_folders(ou,main_drive,arch,'Events')

    if args.schudele == True:
        collect_artfacts(ou,main_drive,arch,'scheduled_task')

    if args.wmi == True:
        collect_artfacts(ou,main_drive,arch,'WMI')

    if args.recent == True:
        collect_artfacts(ou,main_drive,arch,'Recent')

    if args.usnjrl ==True:
        collect_artfacts(ou,main_drive,arch,'Usnjrl')

    if args.mft ==True:
        collect_artfacts(ou,main_drive,arch,'Ntfs')

    if args.amcache == True:
        collect_artfacts(ou,main_drive,arch,'applications')

    if args.ntusers == True:
        collect_artfacts(ou,main_drive,arch,'Ntuser')
        collect_artfacts(ou,main_drive,arch,'usrclass')

    if args.hives == True:
        collect_artfacts(ou,main_drive,arch,'Config')

    # if args.live == True:
    #     get_system_live_det(ou,main_drive,arch,key)

    if args.all ==True:
    # if args.live == False and args.wmi == False and args.usrclass == False and args.hives == False and args.ntusers == False and args.amcache == False and args.mft ==False and args.usnjrl ==False  and args.recent == False and args.persistance == False and args.events == False:
        for key,vaues in varl.items():
            output = varl[key]['output']
            type = varl[key]['type']
            if type =='folder':
                collect_folders(ou,main_drive,arch,'Events')
            elif type =='file':
                collect_artfacts(ou,main_drive,arch,key)
            # elif type =='live':
            #     get_system_live_det(ou,main_drive,arch,key)
    #create_zipfile()



if __name__ == '__main__':
    if os.path.exists(ou):
        shutil.rmtree(ou)
    #print sys.argv
    main(sys.argv)
