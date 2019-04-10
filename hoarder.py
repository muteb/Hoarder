import yaml
import json
import os
import string
import platform
import sys
import shutil
import argparse
from datetime import datetime
import glob
import logging
import psutil
import pytsk3
import wmi

p = psutil.Process(os.getpid())
p.nice(0x00000040)

logging.basicConfig(filename='hoarder.log',mode='w',level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

parser = argparse.ArgumentParser(description="Hoarder is a tool to collect windows artifacts.\n\n")
parser.add_argument('-a', '--all', action="store_true", help='Get all')

global yaml_config
yaml_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "hoarder.yml")
print(yaml_path)
if os.path.exists(yaml_path):
    yaml_file = open(yaml_path, 'r')
else:
    print("[*] Could not Find Configurations File 'hoarder.yml'!")
    sys.exit()
yaml_config = json.loads( json.dumps( yaml.safe_load(yaml_file.read()) ) ) # parse the yaml_file and get the result as json format
yaml_file.close()

allArtifacts = yaml_config['all_artifacts']

for key,value in allArtifacts.items():
    parser.add_argument('--'+key, action="store_true", help=allArtifacts[key]['description'])

args = parser.parse_args()

global ou
ou = os.getenv('COMPUTERNAME')
global metadata
metadata = []

def get_vol():
    available_drives = ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
    xf = platform.architecture()[0]
    for drive in available_drives:
        dee = os.listdir(drive+"\\")
        if "Windows" in dee and "Users" in dee:
            return drive,xf

# Get the drive that contains windows installation and windows architecture. 
main_drive,arch = get_vol()

def GetMetaDataForFile(path,artType):
    if os.path.isfile(path):
        status = os.stat(path)
        ctime = datetime.utcfromtimestamp(status.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        mtime = datetime.utcfromtimestamp(status.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        atime = datetime.utcfromtimestamp(status.st_atime).strftime('%Y-%m-%d %H:%M:%S')
        pathMetadata = "\""+path+"\","+str(status.st_size)+","+ctime+","+mtime+","+atime+","+artType
        metadata.append(pathMetadata)
    else:
        return ""

def GetMetaData(path,artType):
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                GetMetaDataForFile(os.path.join(root, name),artType)
    else:
        GetMetaDataForFile(path,artType)

def copyDirectory(src, dest):
    try:
        if os.path.exists(src):
            logging.info("[+] Copying the folder {} ".format(src))
            shutil.copytree(src, dest)
            logging.info("[+] Successfully copied the folder '{}' !".format(src))
    # Directories are the same
    except:
        logging.warning("[!] Unable to copy the Directory : "+src)

def getPaths(path):
    results = []
    foldernames = []
    paths = []
    if "*" in path or "?" in path:
        for absPath in glob.glob(path):
            foldernames.append(absPath[path.find("*"):absPath.find("\\",path.find("*"))])
            paths.append(absPath)
    else:
        foldernames.append(path[path.rindex("\\")+1::])
        paths.append(path)
    results.append(foldernames)
    results.append(paths)
    return results

def GetPhysicalDisk(driveLetter):
	for physical_disk in wmi.WMI().Win32_DiskDrive():
		logical_disks = []
		for partition in physical_disk.associators ("Win32_DiskDriveToDiskPartition"):
			for logical_disk in partition.associators ("Win32_LogicalDiskToPartition"):
				if driveLetter.lower() == str(logical_disk.DeviceID).lower():
					return physical_disk.DeviceID

def justCopy(srcPath,dstPath):
    # Modified version of : https://gist.github.com/glassdfir/7f2a2d381dc17a6a4637
    driveLetter = srcPath.split("\\")[0]
    imagefile = GetPhysicalDisk(driveLetter)
    imagehandle = pytsk3.Img_Info(imagefile)
    partitionTable = pytsk3.Volume_Info(imagehandle)

    for partition in partitionTable:
        try:
            filesystemObject = pytsk3.FS_Info(imagehandle, offset=(partition.start*512))
            parsedname = os.path.abspath(srcPath).replace(driveLetter,"").replace("\\","/")
            fileobject = filesystemObject.open(parsedname)
            OutFileName = fileobject.info.name.name
            FinalOutDir = dstPath
            if not os.path.exists(FinalOutDir):
                os.makedirs(FinalOutDir)
            FinalFilePath = os.path.join(FinalOutDir, OutFileName)
            OutFile = open(FinalFilePath, 'w')
            if fileobject.info.meta.size > 0:
                logging.info("[+] Copying the file {} ".format(srcPath))
                filedata = fileobject.read_random(0,fileobject.info.meta.size)
                logging.info("[+] Successfully copied the file '{}' !".format(srcPath))
            else:
                logging.warning("[!] Unable to copy the file {} . The file is Empty!".format(srcPath))
            OutFile.write(filedata)
            OutFile.close

            return True
        except:
            pass
    logging.warning("[!] Unable to copy the file '{}' ".format(srcPath))
    return False

def CopyFile(src,dest):
    try:
        if os.path.exists(src):
            if not os.path.exists(dest):
                os.makedirs(dest)
            logging.info("[+] Copying the file {} ".format(src))
            shutil.copy(src,dest)
            logging.info("[+] Successfully copied the file '{}' !".format(src))
    except:
        logging.warning("[!] Unable to copy the file {} ".format(src))

def collect_artfacts(out, drive,arch,target):
    allArtifacts = yaml_config['all_artifacts']
    typeOfArt = allArtifacts[target]['type']
    if arch == "32":
        paths = allArtifacts[target]['path32']
    else:
        paths = allArtifacts[target]['path64']

    paras = allArtifacts[target]['para']
    destFolder = allArtifacts[target]['output']
    copyType = allArtifacts[target]['copyType']
    output = os.path.abspath(os.path.join(out,destFolder))
    srcs = []
    
    if isinstance(paths,list):
        for path in paths:
            if isinstance(paras,list):
                for para in paras: 
                    srcs.append(os.path.join(drive,path,para))
            else:
                srcs.append(os.path.join(drive,path,paras))
    else:
        if isinstance(paras,list):
            for para in paras: 
                srcs.append(os.path.join(drive,paths,para))
        else:
            srcs.append(os.path.join(drive,paths,paras))

    for src in srcs:
        if typeOfArt == "file":
            if "*" in src or "?" in src:
                allPaths = getPaths(src)
                foldernames = allPaths[0]
                paths = allPaths[1]
                for i in range(len(foldernames)):
                    foldername = foldernames[i]
                    path = paths[i]
                    GetMetaData(path,target)
                    if copyType == 'justCopy':
                        justCopy(path,os.path.join(output,foldername))           
                    elif copyType == 'normal':
                        CopyFile(path,os.path.join(output,foldername))
            else:
                GetMetaData(src,target)
                if copyType == 'justCopy':
                    justCopy(src,output)
                elif copyType == 'normal':
                    CopyFile(src,output)
        elif typeOfArt == "folder" or typeOfArt == "dir":
            if os.path.exists(src):
                GetMetaData(src,target)
                if not len(os.listdir(src)) == 0:
                    if copyType == 'normal':
                        copyDirectory(src,output)
                    elif copyType == 'justCopy':
                        #justCopy(src,output,True)
                        raise ValueError("justCopy for folders is not supported yet (Sorry !)")
        else:
            raise ValueError("YAML formate Error. 'type' should be only file,folder or dir")

def main():
    varl = yaml_config['all_artifacts']
    if args.all ==True:
        logging.info("[+] Collecting all the artifact specifided in the YAML File.")
        for  key,vaues in varl.items():
            logging.info("[+] Collecting the artifact '{}' ".format(key))
            collect_artfacts(ou,main_drive,arch,key)

    else:
        for  key,vaues in varl.items():
            if getattr(args,key) == True:
                logging.info("[+] Collecting the artifact '{}' ".format(key))
                collect_artfacts(ou,main_drive,arch,key)
    
    with open(os.path.join(ou,"metadata.csv"),"w") as output:
        logging.info("[+] Writing artifacts metadata to 'metadata.csv' ")
        for line in metadata:
            if line is not "":
                output.write(line+"\n")


if __name__ == '__main__':
    logging.info("[+] Hoarder Started!")
    if os.path.exists(ou):
        shutil.rmtree(ou)
    os.mkdir(ou)
    main()  
    logging.info("[+] Collecting artifacts finished!")
    logging.info("[+] Adding the output folder to archive.")
    logging.shutdown()
    shutil.move("hoarder.log",ou)
    shutil.make_archive(ou, 'zip', ou)    
    if os.path.exists(ou):
        shutil.rmtree(ou)