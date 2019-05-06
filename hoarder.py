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
import hashlib
import io

# Set Process Priority to LOW.
p = psutil.Process(os.getpid())
p.nice(0x00000040)
# Initilize Logging.
logging.basicConfig(filename='hoarder.log',mode='w',level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
# Add the static arguments.
parser = argparse.ArgumentParser(description="Hoarder is a tool to collect windows artifacts.\n\n")
parser.add_argument('-a', '--all', action="store_true", help='Get all')
parser.add_argument('-p', '--processes', action="store_true", help='Collect information about the running processes.')
parser.add_argument('-s', '--services', action="store_true", help='Collect information about the system services.')

global yaml_config
# Locate and open the configuration file.
yaml_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "hoarder.yml")
if os.path.exists(yaml_path):
    yaml_file = open(yaml_path, 'r')
else:
    print("[*] Could not Find Configurations File 'hoarder.yml'!")
    sys.exit()
# Load the configuration file as a dictinary.
yaml_config = json.loads( json.dumps( yaml.safe_load(yaml_file.read()) ) )
yaml_file.close()

allArtifacts = yaml_config['all_artifacts']
# Dynamically load all of the artifacts from teh configuration file. 
for key,value in allArtifacts.items():
    parser.add_argument('--'+key, action="store_true", help=allArtifacts[key]['description'])

args = parser.parse_args()

global ou
ou = os.getenv('COMPUTERNAME')
global metadata
metadata = []

# This function take's a path to a file as argument then return it's MD% hash.
def md5(fname):
    try:
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except IOError as e:
        logging.error(e)
        return "File Not Found"

# Get information about the running processes then write the JSON formated output to a file called "processes.json"
def GetProcesses():
    results = []
    attr = ['ppid','pid', 'name', 'username','cmdline','connections','create_time','cwd','exe','nice','open_files']
    # Removed : environ,threads,cpu_percent
    for process in psutil.process_iter():
        MD5Hash = ""
        process_info = process.as_dict(attrs=attr)
        process_path = process_info.get('exe')

        date = datetime.fromtimestamp(process.create_time())
        dateAndTime = date.strftime('%Y-%m-%d T%H:%M:%S')
        process_info['@timestamp'] = dateAndTime

        imports = []
        try:
            for dll in process.memory_maps():
                imports.append(dll.path)
        except Exception as e:
            logging.error(e)
            imports.append("AccessDenied")
        process_info['imports'] = imports

        open_files = process_info['open_files']
        del process_info['open_files']
        fixed_open_files = []

        if open_files:
            for file_info in open_files:
                fixed_open_files.append(file_info[0])
        else:
            process_info['open_files'] = []
            
            
        process_info['open_files'] = fixed_open_files
        
        cmdline = process_info['cmdline']
        del process_info['cmdline']
        fixed_cmdline = ""
        if  cmdline:
            fixed_cmdline = " ".join(cmdline)
            process_info['cmdline'] = fixed_cmdline
        else:
            process_info['cmdline'] = ""
        
        connections = process_info['connections']
        fixed_connections = []
        del process_info['connections']

        if connections:
            for connection in connections:
                connection_ = {}
                connection_['local_ip'] = connection.laddr.ip
                connection_['local_port'] = connection.laddr.port
                connection_['protocole'] = "TCP" if connection.type == 1 else "UDP"
                if connection.raddr:
                    connection_['remote_ip'] = connection.raddr.ip
                    connection_['remote_port'] = connection.raddr.port
                connection_['status'] = connection.status
                fixed_connections.append(connection_)
                
            process_info['connections'] = fixed_connections
        else:
            process_info['connections'] = []

        if process_path:
            MD5Hash = md5(process_path)
        process_info['md5'] = MD5Hash
        results.append(process_info)

    result = json.dumps(results)

    with open(os.path.join(ou,"processes.json"),"w") as out:
        out.write(result)

# Write JSON formated output to a file called "services.json"
def GetServices():
    results = []
    for service in psutil.win_service_iter():
        try:
            encoded_dict = {}
            for key,value in service.as_dict().iteritems():
                if value and isinstance(value,str) and isinstance(key,str):
                    encoded_dict[unicode(key,"utf-8",errors="ignore")] = unicode(value,"utf-8",errors="ignore")
            results.append(encoded_dict)
        except Exception as e:
            logging.error(e)
    result = json.dumps(results)
    with open(os.path.join(ou,"services.json"),"w") as out:
        out.write(result)

# Return two things:
# 1. The root volume which contains the windows installation.
# 2. The OS version (64 or 32).
def get_vol():
    available_drives = ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
    xf = platform.architecture()[0]
    for drive in available_drives:
        dee = os.listdir(drive+"\\")
        if "Windows" in dee and "Users" in dee:
            return drive,xf

# Get the drive that contains windows installation and windows architecture. 
main_drive,arch = get_vol()
# Get's a path for a file as input to get it's metadata and save it to the global list metadata to be writen to a file later. 
def GetMetaDataForFile(path,artType):
    try:
        if os.path.isfile(path):
            status = os.stat(path)
            ctime = datetime.utcfromtimestamp(status.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            mtime = datetime.utcfromtimestamp(status.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            atime = datetime.utcfromtimestamp(status.st_atime).strftime('%Y-%m-%d %H:%M:%S')
            pathMetadata = "\""+path+"\","+str(status.st_size)+","+ctime+","+mtime+","+atime+","+artType
            metadata.append(pathMetadata)
        else:
            return ""
    except Exception as e:
        logging.error(e)
    return ""
# Go through a folder recursevlly and calls the function GetMetaDataForFile() for each file it finds.
def GetMetaData(path,artType):
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                GetMetaDataForFile(os.path.join(root, name),artType)
    else:
        GetMetaDataForFile(path,artType)
# Copy a directory
def copyDirectory(src, dest):
    try:
        if os.path.exists(src):
            logging.info("[+] Copying the folder {} ".format(src))
            shutil.copytree(src, dest)
            logging.info("[+] Successfully copied the folder '{}' !".format(src))
    except Exception as e:
        logging.error(e)
        logging.warning("[!] Unable to copy the Directory : "+src)

# Gets wildcard paths and return the absulote path.
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

# Get's drive litter as input and return it's physical drive.
def GetPhysicalDisk(driveLetter):
	for physical_disk in wmi.WMI().Win32_DiskDrive():
		logical_disks = []
		for partition in physical_disk.associators ("Win32_DiskDriveToDiskPartition"):
			for logical_disk in partition.associators ("Win32_LogicalDiskToPartition"):
				if driveLetter.lower() == str(logical_disk.DeviceID).lower():
					return physical_disk.DeviceID
# Copy any file even if it is locked.
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
            OutFile = open(FinalFilePath, 'wb')
            if fileobject.info.meta.size > 0:
                logging.info("[+] Copying the file {} ".format(srcPath))
                filedata = fileobject.read_random(0,fileobject.info.meta.size)
                logging.info("[+] Successfully copied the file '{}' !".format(srcPath))
            else:
                filedata=b""
                logging.warning("[!] Unable to copy the file {} . The file is Empty!".format(srcPath))
            OutFile.write(filedata)
            OutFile.close

            return True
        except Exception as e:
            logging.error(e)
    logging.warning("[!] Unable to copy the file '{}' ".format(srcPath))
    return False
# Copy a file.
def CopyFile(src,dest):
    try:
        if os.path.exists(src):
            if not os.path.exists(dest):
                os.makedirs(dest)
            logging.info("[+] Copying the file {} ".format(src))
            shutil.copy(src,dest)
            logging.info("[+] Successfully copied the file '{}' !".format(src))
    except Exception as e:
        logging.warning("[!] Unable to copy the file {} ".format(src))
        logging.error(e)
# The main function responsable for collecting the artifacts.
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

    if args.processes:
        logging.info("[+] Collecting Processes.")
        GetProcesses()
    if args.services:
        logging.info("[+] Collecting Services.")
        GetServices()
    if args.all ==True:
        logging.info("[+] Collecting Processes.")
        GetProcesses()
        logging.info("[+] Collecting Services.")
        GetServices()
        logging.info("[+] Collecting all the artifact specifided in the YAML File.")
        for  key,vaues in varl.items():
            logging.info("[+] Collecting the artifact '{}' ".format(key))
            collect_artfacts(ou,main_drive,arch,key)
        

    else:
        for  key,vaues in varl.items():
            if getattr(args,key) == True:
                logging.info("[+] Collecting the artifact '{}' ".format(key))
                collect_artfacts(ou,main_drive,arch,key)
    
    with io.open(os.path.join(ou,"metadata.csv"),"w",encoding='utf8') as output:
        logging.info("[+] Writing artifacts metadata to 'metadata.csv'")
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
        try:
            shutil.rmtree(ou)
        except Exception as e:
            logging.error(e)