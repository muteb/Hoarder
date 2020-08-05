
import yaml
import pytsk3
import zipfile
import os 
import json 
from sys import platform as _platform
import glob
from datetime import datetime
import subprocess
import psutil
import argparse
import hashlib
import ctypes
import sys
import fnmatch
import re
import shutil
import traceback
import ctypes

__version__ = "4.0.0"

# get working dir path:
if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'): # running from frozen exe
    hoarder_wd = sys._MEIPASS
else:
    hoarder_wd = os.path.dirname(sys.argv[0])

hoarder_config = "Hoarder.yml"

# Parses hoarder arguments
def init_hoarder():
    
    # Add the static arguments:
    args_set = argparse.ArgumentParser(description="Hoarder is a tool to collect and parse windows artifacts.\n\n")

    args_set.add_argument('-V', '--version', action="store_true", help='Print Hoarder version number.')
    args_set.add_argument('-v', '--verbose', action="store_true", help='Print details of hoarder message in console.')
    args_set.add_argument('-vv', '--very_verbose', action="store_true", help='Print more details (DEBUG) of hoarder message in console.')
    args_set.add_argument('-a', '--all', action="store_true", help='Get all (Default)')
    args_set.add_argument('-f', '--image_file', help='Use disk image as data source instead of the live machine disk image ')
    args_set.add_argument('-pa', '--parse_artifacts', action="store_true", help='Parse artifacts')
    args_set.add_argument('-n', '--no_raw_files', action="store_true", help='Only bring parsed output. Do not bring any raw evidence files')

    # set arguments for plugins:
    argsplugins = args_set.add_argument_group('Plugins')
    argsplugins.add_argument('-p', '--processes', action="store_true", help='Collect information about the running processes.')
    argsplugins.add_argument('-s', '--services', action="store_true", help='Collect information about the system services.')

    # build the artifacts and commands options:
    argspartifacts  = args_set.add_argument_group('Artifacts')
    argscommands    = args_set.add_argument_group('Commands')

    # build YAML config path:
    if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'): # running from frozen exe
        if os.path.exists(os.path.join(os.path.dirname(sys.argv[0]),hoarder_config)):
            yaml_path = os.path.join(os.path.dirname(sys.argv[0]), hoarder_config)
        else:
            yaml_path = os.path.join(hoarder_wd, hoarder_config)
    else:
        yaml_path = os.path.join(hoarder_wd, hoarder_config)
    try:
        yaml_file = open(yaml_path, 'r')
        yaml_config = json.loads( json.dumps( yaml.safe_load(yaml_file.read()) ) )['all_artifacts']
        yaml_file.close()
    except Exception as e:
        print("ERROR" , "Could not Find Configurations File '"+yaml_path+"'! - reason: " + str(e))
        sys.exit()

    available_groups = []               

    for key,value in yaml_config.items():
        if 'cmd' in yaml_config[key]:
            argscommands.add_argument('--'+key, action="store_true", help=yaml_config[key]['description'])
        else:
            argspartifacts.add_argument('--'+key, action="store_true", help=yaml_config[key]['description'])
            if 'groups' in yaml_config[key]:
                if type(yaml_config[key]['groups']) is not list:
                    available_groups.append(yaml_config[key]['groups'])
                else:
                    available_groups.extend((yaml_config[key]['groups']))

    # uniq available groups list:
    available_groups = list(set(available_groups))

    # add static argument for groups:
    args_set.add_argument('-g','--groups',nargs='*',help='Specify what to collect by group tag. takes a space seperated list of groups. e.g. -g execution user_activities. Available groups: ' + str(available_groups))
    
    # Parse arguments:
    args = args_set.parse_args()

    return args

# a class for plugins (To be implemented to make hoarder moduler)
class Plugins:
    plugins_list = ['processes' , 'services']
    
    def __init__(self):
        pass
    
    
    
    # This function take's a path to a file as argument then return it's MD5 hash.
    def md5(self, fname):
        try:
            hash_md5 = hashlib.md5()
            with open(fname, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except IOError as e:
            return None


    def ProcessList(self):
        try:
            results = []
            attr = ['ppid','pid', 'name', 'username','cmdline','connections','create_time','cwd','exe','nice','open_files']
            # Removed : environ,threads,cpu_percent
            for process in psutil.process_iter():
                MD5Hash      = ""
                process_info    = process.as_dict(attrs=attr)
                process_path    = process_info.get('exe')
                date            = datetime.fromtimestamp(process.create_time())
                dateAndTime  = date.strftime('%Y-%m-%d T%H:%M:%S')
                process_info['@timestamp'] = dateAndTime
                imports      = []
                try:
                    if process.name() == "svchost.exe" and process.cmdline()[-1] == "CryptSvc":
                        imports.append("AccessDenied")
                    else:
                        for dll in process.memory_maps():
                            imports.append(dll.path)
                except:
                    imports.append("AccessDenied")
                process_info['imports'] = imports

                open_files            = process_info['open_files']
                del process_info['open_files']
                fixed_open_files        = []
                if open_files:
                    for file_info in open_files:
                        fixed_open_files.append(file_info[0])
                else:
                    process_info['open_files'] = []
                    
                process_info['open_files']  = fixed_open_files
                
                cmdline                  = process_info['cmdline']
                del process_info['cmdline']
                fixed_cmdline              = ""
                if  cmdline:
                    fixed_cmdline = " ".join(cmdline)
                    process_info['cmdline'] = fixed_cmdline
                else:
                    process_info['cmdline'] = ""
                
                connections      = process_info['connections']
                fixed_connections   = []
                del process_info['connections']

                if connections:
                    for connection in connections:
                        connection_ = {}
                        connection_['local_ip']  = connection.laddr.ip
                        connection_['local_port']   = connection.laddr.port
                        connection_['protocole']    = "TCP" if connection.type == 1 else "UDP"
                        if connection.raddr:
                            connection_['remote_ip']    = connection.raddr.ip
                            connection_['remote_port']  = connection.raddr.port
                        connection_['status']          = connection.status
                        fixed_connections.append(connection_)
                        
                    process_info['connections'] = fixed_connections
                else:
                    process_info['connections'] = []

                if process_path:
                    MD5Hash = self.md5(process_path)
                process_info['md5'] = str(MD5Hash)
                results.append(process_info)
            result = json.dumps(results)

            return [True , result]
        except Exception as e:
            raise e
            # return [False , "Plugin Processes Failed, reason: " + str(e)]
            
            
    def ServicesList(self):
        try:
            results = []
            for service in psutil.win_service_iter():
                try:
                    results.append(service.as_dict())
                except Exception as e:
                    print(str(e))
            result = json.dumps(results)
            return [True, result]
            
        except Exception as e:
            raise e
        

# Main hoarder class that handles artifact collection and parsing
class Hoarder:
    verbose      = 0
    options      = []
    plugins      = Plugins()
    parsers         = []

    FILE_TYPE_LOOKUP = {
      pytsk3.TSK_FS_NAME_TYPE_UNDEF: "-",
      pytsk3.TSK_FS_NAME_TYPE_FIFO: "p",
      pytsk3.TSK_FS_NAME_TYPE_CHR: "c",
      pytsk3.TSK_FS_NAME_TYPE_DIR: "d",
      pytsk3.TSK_FS_NAME_TYPE_BLK: "b",
      pytsk3.TSK_FS_NAME_TYPE_REG: "r",
      pytsk3.TSK_FS_NAME_TYPE_LNK: "l",
      pytsk3.TSK_FS_NAME_TYPE_SOCK: "h",
      pytsk3.TSK_FS_NAME_TYPE_SHAD: "s",
      pytsk3.TSK_FS_NAME_TYPE_WHT: "w",
      pytsk3.TSK_FS_NAME_TYPE_VIRT: "v"
      }

    # ==========
    # parameters:
    # config_file:    path to the yaml config file
    # options:        options of collected files and plugins
    # enabled_verbose   level of information to print
    # output            output file name
    # compress_level    compression level
    # compress_method   compression method
    # image_path        using disk image instead of the system disk
    # parse_level       parse level - what to parse and bring back
    # ==========
    def __init__(self, 
                config_file                             , 
                options         = None                  , 
                enabled_verbose = 0                     , 
                output          = None                  , 
                compress_level  = 6                     , 
                compress_method = zipfile.ZIP_DEFLATED  ,
                image_path      = None                  ,
                parse_level     = 0                     ,
                groups          = []
                ):
         
        self.options            = options 
        self.verbose            = enabled_verbose
        self.hostname           = os.getenv('COMPUTERNAME')
        self.output             = output
        self.compress_level     = compress_level
        self.compress_method    = compress_method
        self.disk_drive         = "C:"
        self.parse_level        = parse_level
        self.groups             = groups
        if self.output is None:
            self.output         = os.path.join(os.path.dirname(sys.argv[0]),self.hostname + ".zip")
        
        self.hoarderlog = os.path.join(os.path.dirname(sys.argv[0]),"hoarder.log")
        
        if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'): # running from frozen exe
            self.hoarderjsonlog = os.path.join(sys._MEIPASS,"hoarderlog.json")
        else:
            self.hoarderjsonlog = os.path.join(os.path.dirname(sys.argv[0]),"hoarderlog.json")

        if os.path.isfile(self.hoarderlog):
                os.remove(self.hoarderlog)
        if os.path.isfile(self.hoarderjsonlog):
                os.remove(self.hoarderjsonlog)
        
        self.logging("INFO" , "Hoarder Started...")
        self.logging("INFO" , "Output file: " + self.output)
        self.logging("INFO" , "Hostname: " + self.hostname )
        self.logging("INFO" , "Arch: " + _platform)
        
        if self.verbose == 1:
            self.logging("INFO" , "Verbose mode enabled")
        elif self.verbose == 2:
            self.logging("INFO" , "very verbose mode enabled")

        if self.parse_level == 0:
            self.logging("INFO" , "Parse level 0 - No parsing")
        if self.parse_level == 1:
            self.logging("INFO" , "Parse level 1 - parsing on")
        if self.parse_level == 2:
            self.logging("INFO" , "Parse level 2 - Parsing on - no raw files")

        # init. zip file
        try:
            if os.path.isfile(self.output) :
                os.remove(self.output)
            self.zfile = zipfile.ZipFile(self.output, mode='w' , compresslevel=self.compress_level , compression=self.compress_method , allowZip64=True)
        except Exception as e:
            self.logging("ERROR" , "Failed opening output file [" + self.output + str(e) + "traceback: " + traceback.format_exc())
            sys.exit()
        
        # get yaml configuration 
        self.config = self.GetYamlConfig(config_file)
        
        
        # make sure there is an OS on the disk 
        list_imgs = {}

        # if the collection will be from disk image,
        if image_path:
            self.logging("INFO" , "Check disk image: [" + image_path + "]"  )
            if not os.path.isfile(image_path):
                self.logging("ERR" , "Disk image not found ["+image_path+"]")

            # get all the fs_info of all volumes of the drive
            list_imgs["DISK_IMAGE"] = self.GetVolumes(image_path)

            if len(list_imgs["DISK_IMAGE"]) == 0:
                self.logging("WARNING" , "No NTFS Partition found on ["+image_path+"]")
            else:
                self.logging("INFO" , "Found ["+str(len(list_imgs["DISK_IMAGE"]))+"] NTFS partitions on ["+image_path+"]")

        # if not from disk image, then the current system disk
        else:
            count = 0
            while True:
                try:
                    
                    self.logging("INFO" , "Check drive: \\\\.\\PhysicalDrive" + str(count) )

                    # get all the fs_info of all volumes of the drive
                    list_imgs["PhysicalDrive" + str(count)] = self.GetVolumes("\\\\.\\PhysicalDrive" + str(count))

                    if len(list_imgs["PhysicalDrive" + str(count)]) == 0:
                        self.logging("WARNING" , "No NTFS Partition found on PhyisicalDrive" + str(count))
                    else:
                        self.logging("INFO" , "Found ["+str(len(list_imgs["PhysicalDrive" + str(count)]))+"] NTFS partitions on drive ["+"PhysicalDrive" + str(count)+"] ")

                except Exception as e:
                    if str(e) == "PHYSICAL_DRIVE_NOT_FOUND":
                        self.logging("WARNING" , "There is no \\\\.\\PhysicalDrive" + str(count))
                        break
                    else:
                        self.logging("ERR" , "Error found on getting NTFS parition: " + str(e))

                count += 1

        # get full paths from config for enabled artifacts
        full_paths = self.GetConfigPaths()
        for path in full_paths:
            self.logging("DEBUG" , "Artifact: "+str(path['artifact'])+ "\tPath: " + path['path'] + ", \tFiles: " + str(path['files']))
            

        # if no path exists continue to next image
        if len(full_paths) > 0:
            
            # get all artifacts paths selected from each drive
            for img_info in list_imgs:
                self.logging("INFO" , "Read drive ["+img_info+"]")
                volum_num = 0
                for fs_info in list_imgs[img_info]:

                    # get the inode of root directory
                    root_inode = self.GetInodeRoot(fs_info) 

                    # if inode identified extract the files
                    if root_inode is not None:
                        self.logging("INFO" , "Start Extracting Volume #"+str(volum_num)+" Files")
                        root_dir = fs_info.open_dir(inode=root_inode)
                        fs_info_details = {
                            'fs_info'   : fs_info,
                            'drive'  : img_info,
                            'volume'    : volum_num
                        }

                        # extract all files from the volume
                        self.ExtractFilesPhysical(fs_info_details , cur_dir_obj=root_dir , paths_list=full_paths)

                    # if inode could not identified
                    else:
                        self.logging("ERR" , "Couldn't identify the root inode")
                    
                    volum_num += 1

        # test zipfile:
        ziptest = self.zfile.testzip()
        if ziptest is None:
            # perform any parsing needed:
            self.parse_artifacts()
        else:
            self.logging("DEBUG", "zip debug: zipfile error - first bad file: " + ziptest)

        # execute commands in the YAML config
        self.ExecuteCommands()
        
        # run selected plugins
        try:
            self.RunPlugins()
        except Exception as e:
            self.logging("ERR", "Exception: RunPlugins \n" + traceback.format_exc())

        self.logging("INFO" , "Hoarder Done!")

        if os.path.isfile(self.hoarderjsonlog):
            self.zfile.write(self.hoarderjsonlog, os.path.basename(self.hoarderjsonlog))
            # f = open(self.hoarderjsonlog , 'rb')
            # self.ZipWriteFile(f.read() , self.hoarderjsonlog)
            # f.close()
            os.remove(self.hoarderjsonlog)
        
        self.zfile.close()
    
    # get list of artifacts in commandline
    def get_enabled_artifacts(self):
        # get all specified artifacts or all:
        enabled_artifacts = [ea for ea in self.config if 'cmd' not in self.config[ea] and (ea in self.options or len(self.options) == 0) and (self.groups == [] or len(self.options) > 0)]
        
        # get artifacts for specified groups:
        grps = []

        for ea in self.config:
            if 'cmd' not in self.config[ea] and 'groups' in self.config[ea]:
                if type(self.config[ea]['groups']) is not list:
                    grps = [self.config[ea]['groups']]
                else:
                    grps = self.config[ea]['groups']
                for grp in grps:
                    if grp in self.groups:
                        enabled_artifacts.append(ea)
                        break

        # unique it:
        enabled_artifacts = list(set(enabled_artifacts))
        
        self.logging("INFO" , "Enabed Artifacts: " + str(len(enabled_artifacts)))
        
        return enabled_artifacts

    # get all paths from yaml config 
    def GetConfigPaths(self):

        enabled_artifacts = self.get_enabled_artifacts()
        
        full_paths = []
        for arti in enabled_artifacts:

            # check Windows arch
            if _platform == "win32" and 'path32' in self.config[arti]:
                arti_paths = self.config[arti]['path32']
            elif _platform == "win64" and 'path64' in self.config[arti]:
                arti_paths = self.config[arti]['path64']
            else:
                continue

            # if single path selected, add it to list
            if type(arti_paths) is not list:
                arti_paths = [arti_paths]
            
            
            
            files_list = []
            for path in arti_paths:
                path    = path.replace("\\" , "/") # replace \\ with /, pytsk only deals with /
                files   = []
                # append the files field with paths
                if 'files' in self.config[arti]:
                    files = self.config[arti]['files']
                    if type(self.config[arti]['files']) is not list:
                        files = [files]
                

                full_paths.append({'path':path , 'artifact' : arti , 'files' : files})


            

        # get paths
        return full_paths
    

    # get the root inode of the file system 
    def GetInodeRoot(self , fs_info):
        if getattr(fs_info, 'info', None) is None:
            return None
        return getattr(fs_info.info, 'root_inum', None)

    # extract all the files specified on the configuration from the partition 
    def ExtractFilesPhysical(self , fs_info_details , cur_dir_obj ,  paths_list , current_path = "/" , bRecursive=False):

        # build current folder entries
        current_folders = {}
        for p in paths_list:
            cur_folder = p['path'].replace(current_path , '' , 1).split("/")[0]

            # if current folder is **, then enable recursive mode
            if cur_folder == "**":
                bRecursive = True
                self.logging("DEBUG" , "Recursive mode enabled ")

            # if current folder already exists on folder entries, then append its content, other wise create new entry
            if cur_folder in current_folders:
                current_folders[cur_folder].append(p)
            else:
                current_folders[cur_folder] = [p]
            
    
        for cur in current_folders:
            self.logging("DEBUG" , "Entries: " + str(current_folders))

        # for each entry inside the current directory object
        for entry in cur_dir_obj:

            # skip current and parent folders '.' and '..', or if it does not have name
            if (not hasattr(entry, "info") or
                not hasattr(entry.info, "name") or
                not hasattr(entry.info.name, "name") or
                entry.info.name.name.decode('utf-8') in [".", ".."]):
                continue
            
            entry_name = entry.info.name.name.decode('utf-8')      # pytsk entry name
            entry_type = entry.info.name.type                      # pytsk entry type
            
            #self.logging("DEBUG" , "Type: {0:d} \t Name:{1:s}".format( int(entry_type) , current_path + entry_name ) )

            
            # if current folder is recursive them copy the file if entry is file or recursive over the dirctory if entry is directory
            if bRecursive:
                # if entry is file, copy the file
                if entry_type not in [pytsk3.TSK_FS_NAME_TYPE_DIR]:
                    for folder in current_folders:
                        for f in current_folders[folder]:
                            # if the files not specified, then copy all files
                            if len(f['files']) == 0:
                                
                                self.logging("INFO" , "-----found file type {0:d}\t{1:s} ".format(int(entry_type) , current_path + entry_name) )

                                self.copy_file(fs_info_details , entry , self.config[f['artifact']]['output'] , current_path + entry_name )

                            # if files specified, make sure it is specified
                            else:
                                for file in f['files']:
                                    if fnmatch.fnmatch(entry_name, file):
                                        
                                        self.logging("INFO" , "-----found file type {0:d}\t{1:s} ".format(int(entry_type) , current_path + entry_name) )
                                        
                                        self.copy_file(fs_info_details , entry , self.config[f['artifact']]['output'] , current_path + entry_name )


                # for directory, go inside the recursive to extract all its files
                elif entry_type == pytsk3.TSK_FS_NAME_TYPE_DIR:
                    for folder in current_folders:
                            
                        self.logging("DEBUG" , "Recursive enabled,  jumping inside the directory '{0:s}'".format(entry_name))
                            
                        # go inside the folder
                        self.jump_to_folder(fs_info_details , current_folders , folder , entry , current_path , entry_name , bRecursive)


            # if the files on the current directory, current directory will be '', others like 'windows' means entry inside the current directory
            # and only if the current entry is not folder, if it is folder it will not collect the entry itself
            elif '' in current_folders and entry_type not in [pytsk3.TSK_FS_NAME_TYPE_DIR]:
                for f in current_folders['']:
                    for file in f['files']:
                        if fnmatch.fnmatch(entry_name, file):

                            self.logging("INFO" , "-----found file type {0:d}\t{1:s} ".format(int(entry_type) , current_path + entry_name) )

                            # copy the file
                            self.copy_file(fs_info_details , entry , self.config[f['artifact']]['output'] , current_path + entry_name )
                            


            # if current entry such as 'windows' inside the current_folders, then need to go inside this folder
            elif entry_type == pytsk3.TSK_FS_NAME_TYPE_DIR:
                for folder in current_folders:
                    if fnmatch.fnmatch(entry_name, folder):
                        
                        self.logging("DEBUG" , "Entry '{0:s}' match '{1:s}' folder, Jumping inside the directory".format(entry_name , folder))
                        
                        # go inside the folder
                        self.jump_to_folder(fs_info_details , current_folders , folder , entry , current_path , entry_name , bRecursive)





        self.logging("DEBUG" , "Folder '{0:s}' scanning done...".format(current_path))


    # this receive information related to the curent folder to jump inside it 
    def jump_to_folder(self, fs_info_details , current_folders , folder , entry , current_path , entry_name , bRecursive):
        
        new_current_path    = current_path + entry_name + "/"
        new_current_folder  = []
        for folder_entries in current_folders[folder]:
            new_current_folder.append(folder_entries.copy())
                            
            # replace first hit, replace widecard with entry name,
            new_current_folder[-1]['path'] = new_current_folder[-1]['path'].replace(current_path + folder , current_path + entry_name ) 

        # test if the directory can be opened as directory to jump inside it
        # some times pytsk detect a file as directory
        dir = None
        try:
            dir = entry.as_directory()
        except Exception as e:
            self.logging("WARNING" , "Couldn't get the directory entry for ["+entry_name+"]")
                        
        if dir is not None:
            self.ExtractFilesPhysical(fs_info_details , dir , new_current_folder , new_current_path , bRecursive=bRecursive)


    # get the entry name and details needed to copy the file from physical disk to zip file
    def copy_file(self, fs_info_details , entry , output_folder , file_path):
        # check if the file has META entry and the address is not NONE
        if not hasattr(entry.info, "meta"):
            self.logging("WARNING" , "file: {0:s} does not have META object ".format(file_path))
        elif entry.info.meta is None:
            self.logging("WARNING" , "file meta {0:s} does not have file address".format(file_path))
        else:
            # read the content
            fdata = self.ReadFile(fs_info_details['fs_info'] , addr=entry.info.meta.addr)
            if fdata:
                # write file content to the zip file 
                dest_path = "{0:s}_{1:d}\\{2:s}{3:s}".format(
                        fs_info_details['drive'].replace('\\' , '').replace('.' , '') , 
                        fs_info_details['volume'] , 
                        output_folder,
                        file_path)
                
                # write the content of the file to zip file
                self.ZipWriteFile( fdata , dest_path)  

    def delete_file(filename):
        if os.path.exists(filename):
            os.remove(filename)

    # function used to run the specified plugin functions
    def RunPlugins(self):
        try:
            enabled_plugins = [p for p in self.plugins.plugins_list if p in self.options or len(self.options) == 0]
        
            for plugin in enabled_plugins:
                self.logging("INFO" , "Plugin ["+plugin+"] Started...")
            
                # processes
                if 'processes' == plugin:
                    plugin_output = self.plugins.ProcessList()
            
                # services
                elif 'services' == plugin:
                    plugin_output = self.plugins.ServicesList()
            
                if plugin_output[0]:
                    self.logging("INFO" , "Plugin ["+plugin+"] finished successfuly")
                    self.ZipWriteFile(plugin_output[1] , plugin + ".txt")
                else:
                    self.logging("ERROR" , "Plugin ["+plugin+"] failed, reason: " + plugin_output[1])
        except Exception as e:
            raise e
        
        
    # function run the specified commands on yaml configuration
    def ExecuteCommands(self):
        # check if the config element is command and make sure whether the argument is all or the command selected
        enabled_cmd = [ea for ea in self.config if 'cmd' in self.config[ea] and (ea in self.options or len(self.options) == 0)]
        self.logging("INFO" , "Enabled Commands: " + str(len(enabled_cmd)))
        
        for i in enabled_cmd:
            command = self.config[i]['cmd']
            output  = self.config[i]['output']
            self.logging("INFO" , "Command: " + command)
            try:
                p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out,err = p.communicate()
                self.ZipWriteFile(out.decode('utf-8') , output + "\output.txt")
            except Exception as e:
                self.logging("ERR" , "Failed executing the command - reason: " + str(e))
        
    # read the configuration file
    def GetYamlConfig(self, conf_file):
        # Locate and open the configuration file.
        yaml_path = os.path.join(hoarder_wd, hoarder_config)
        if os.path.exists(yaml_path):
            yaml_file = open(yaml_path, 'r')
        else:
            self.logging("ERR" , "Could not Find Configurations File '"+yaml_path+"'!")
            sys.exit()
                
        # Load the configuration file as a dictinary.
        yaml_config = json.loads( json.dumps( yaml.safe_load(yaml_file.read()) ) )
        yaml_file.close()
        return yaml_config['all_artifacts']
        
        
    # write file to zip file
    def ZipWriteFile(self, data , path):
        self.zfile.writestr(path.replace('\\','/') , data)
        
    
    # read file content from disk
    def ReadFile(self, img_info , path = None , addr = None):
        try:
            if addr is not None:
                f = img_info.open_meta(inode=addr)
                fdata = f.read_random(0 , f.info.meta.size)
            elif path is not None:
                f = img_info.open(path)
                fdata = f.read_random(0,f.info.meta.size)
            else:
                self.logging("ERR" , "ReadFile function require either inode or path, None given")
                return False

            return fdata
        except Exception as e:
            self.logging ("ERR", "Failed reading the file: path[" + str(path) + "] or inode[" + str(addr) + "] - reason:" + str(e) )
            return False
        
    # get the partion with Windows OS 
    def GetVolumes(self, phyDrive = "\\\\.\\PhysicalDrive0"):
        list_fs_info        = []     # contain the file system object
        block_size        = 512                    # by default block size is 512 

        try:
            img              = pytsk3.Img_Info(phyDrive) # open the physical drive
            volume            = pytsk3.Volume_Info(img)   # get volume information 
        except OSError as e:
            if "file not found" in str(e):
                raise Exception("PHYSICAL_DRIVE_NOT_FOUND")
            else:
                raise Exception(str(e))

        
        # for each volume in the drive, check if it is NTFS and open object to handle it
        for part in volume:
            try:
                self.logging("INFO" , "Check partition: desc{0:s}, offset{1:d}, size:{2:d}".format( part.desc.decode('utf-8') ,part.start , part.len  ) )
                fs_info = pytsk3.FS_Info(img , offset=part.start * block_size )
                # check if file system is NTFS
                if fs_info.info.ftype in [pytsk3.TSK_FS_TYPE_NTFS, pytsk3.TSK_FS_TYPE_NTFS_DETECT]:
                    list_fs_info.append(fs_info) 

                    
            except Exception as e :
                pass
        
        return list_fs_info

    # handle parsing of artifacts:
    def parse_artifacts(self):
        
        # if no parsing needed, print DEBUG message and return:
        if self.parse_level == 0:
            self.logging("DEBUG", "No parsing specified")
            return

        # log start of parsing
        self.logging("INFO", "Started parsing...")
        # initialize tracking lists (commands and cleanup lists):
        all_commands = []
        parsers_to_delete = []
        files_to_delete = []

        # Get the list of enabled artifacts:
        enabled_artifacts = self.get_enabled_artifacts()

        # Zip ops: get parsers zip file handle and list of raw artifacts:
        if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'): # running from frozen exe
            if os.path.exists(os.path.join(os.path.dirname(sys.argv[0]),'parsers.zip')):
                parsers_zip = os.path.join(os.path.dirname(sys.argv[0]), 'parsers.zip')
            else:
                parsers_zip = os.path.join(hoarder_wd,'parsers.zip')
        else:
            parsers_zip = os.path.join(hoarder_wd,'parsers.zip')
        try:
            parsers_file = zipfile.ZipFile(parsers_zip, mode='r', allowZip64=True)
            filelist = self.zfile.namelist()
        except Exception as e:
            self.logging("ERROR", "parsing error in zipfile operations (exception: " + str(e) + " )")
            return
        
        # create working directory:
        # NOTE: '?'' works as a place holder to handle the wierd space handling in windows mpv with subprocess popen.
        if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'): # running from frozen exe
            parsing_path = os.path.join(sys._MEIPASS,'parsing_out')
        else:
            parsing_path = os.path.join(os.path.dirname(sys.argv[0]),'parsing_out')
        try:
            if not os.path.exists(parsing_path):
                os.mkdir(parsing_path) # parsing directory contains all parsers and files to parse
                ctypes.windll.kernel32.SetFileAttributesW(parsing_path, 2)
            parsing_dir = parsing_path.replace(' ','?')
        except Exception as e:
            self.logging("ERROR", "parsing error in creating parsing directories (exception: " + str(e) + " )")
            return

        #extract parsers in parsing dir:
        try:
            # extract all files in the parsing dir
            parsers_file.extractall(parsing_dir.replace('?',' '))
            # add all files to the parsers_to_delete cleanup list
            for fl in parsers_file.namelist():
                parsers_to_delete.append(os.path.join(parsing_dir.replace('?',' '),fl))
        except Exception as e:
            self.logging("ERROR", "could not extract parsers (exception: " + str(e) + " ) + \n" + traceback.format_exc())
            return

        # Main parsing block:
        try:

            # look for and handle parsers in the config
            for artifact in enabled_artifacts:
                # counter to unique filenames in handling commands' inputs and outputs (incremented everytime used):
                uniq_num = 0
                if 'parsers' in self.config[artifact]:
                    # create a folder for this artifact under parsing_out:
                    os.mkdir(os.path.join(parsing_dir.replace('?',' '),artifact))

                    # start parsing things (files are in self.zfile and parsers are in parsers_file):
                    yaml_parsers = self.config[artifact]['parsers']
                    raw_commands = []
                    if type(yaml_parsers) is list:
                        raw_commands = yaml_parsers
                    else:
                        raw_commands.append(yaml_parsers)

                    for rcmd in raw_commands:
                        # get raw parser command into a local var to be to modify it:
                        raw_command = rcmd

                        # lexical analysis of parse commands commands:
                        # extract all directives:
                        directives = re.findall("<[^>]*>", raw_command)

                        # if command has |path| directives:
                        if any(re.fullmatch("<\\|path\\|[^>]*>",directive) for directive in directives):
                            # handle <|path|> directive
                            
                            # 1- convert path config to regex:
                            arti_paths = None
                            path_re_list = []
                            # check Windows arch and get paths
                            if _platform == "win32" and 'path32' in self.config[artifact]:
                                arti_paths = self.config[artifact]['path32']
                            elif _platform == "win64" and 'path64' in self.config[artifact]:
                                arti_paths = self.config[artifact]['path64']
                            else:
                                continue

                            if arti_paths is not None:
                                if type(arti_paths) is list:
                                    for path in arti_paths:
                                        path_re_list.append(path.replace("**",".*").replace("\\*","\\[^\\]*"))
                                else:
                                    path_re_list.append(arti_paths.replace("**",".*").replace("\\*","\\[^\\]*"))
                            else:
                                # no paths found.
                                self.logging("WARNING", "There are no paths, command: " + raw_command + " with |path| directive cannot be executed.")
                                continue

                            # 2- find all matching paths:

                            # handle directive replacements in raw command:
                            for directive in directives:
                                
                                # handle |path| directive:
                                if "|path|" in directive:
                                    
                                    # check if file or directory after |path| directive
                                    if directive.endswith("\\>"): # directory after directive
                                        # NOTE: since directory parsing is usually in one volume (where the OS is or where some app logs are),
                                        # I made the decision to not handle same dir in multi volumes. If need exists in the future, here
                                        # is where the logic will need to be handled.
                                        # create the directory and add it to the cleanup list:
                                        curr_dir_name = parsing_dir + "\\" + str(uniq_num) + directive[7:-1].replace("\\","_").replace(' ','?')
                                        os.makedirs(curr_dir_name.replace('?',' '))
                                        files_to_delete.append(curr_dir_name.replace('?',' '))

                                        # replace the <|path|.*> directive with the curr_dir_name in the command:
                                        raw_command = raw_command.replace(directive,curr_dir_name)
                                        # handle |output| directives (if any):
                                        raw_command = raw_command.replace("|output|" , parsing_dir + "\\" + artifact + "\\" + "parse_out_" + str(uniq_num))
                                        uniq_num = uniq_num + 1 # increment uniq_num
                                        # cleanup any '<' or '>' left from |output| directive handling, and
                                        # add the command to the all_commands list:
                                        all_commands.append(raw_command.replace("<|parsingdir|>", parsing_dir + "\\").replace('<','').replace('>',''))

                                        # find all file paths that match one of the path RegExs and have this directory:
                                        for flp in filelist:
                                            for path_re in path_re_list:
                                                # if directive is <|path|\myApp\>, RegEx will be ".*\\artifact\\the path regex\\myApp\\.*"
                                                # directory directive ends with a \ which means it will be replicated with handling escapes
                                                # so, it \\\\ needs to be replaced with \\ in the regex to mitigate replication:
                                                _re = re.compile((".*" + artifact + path_re + directive[7:-1]).replace("\\","\\\\").replace("\\\\\\\\","\\\\").replace("$","\\$") + ".*", re.IGNORECASE)
                                                if re.fullmatch(_re, flp.replace('/','\\')):
                                                    # extract the matched file (with dir structure) in the created dir:
                                                    if not flp.endswith('/'):
                                                        f = self.zfile.open(flp)
                                                        curr_file = curr_dir_name.replace('?',' ') + "\\" + flp.replace("/","\\")
                                                        if not os.path.exists(os.path.dirname(curr_file)):
                                                            os.makedirs(os.path.dirname(curr_file))
                                                        content = f.read()
                                                        f = open(curr_file.replace('?',' '),'wb')
                                                        f.write(content)
                                                        f.close()
                                    else: # single file after directive
                                        # NOTE: the same file can be in multiple paths. so, there has to be a command for each file found.
                                        for flp in filelist:
                                            for path_re in path_re_list:
                                                # if the directive is <|path|\$MFT>, RegEx will be ".*\\artifact\\the path regex\\\$MFT"
                                                # Build the re with the path re, artifact, directive config, and take care of escapes:
                                                _re = re.compile((".*" + artifact + path_re + directive[7:-1]).replace("\\","\\\\").replace("$","\\$"), re.IGNORECASE)
                                                if re.fullmatch(_re, flp.replace('/','\\')):
                                                    # get the PhysicalDrive?_? number:
                                                    vol_str = flp.split('/',1)[0] # vol_str will be e.g. "PhysicalDrive0_1"
                                                    # make the current file name:
                                                    curr_file_name = parsing_dir + "\\" + flp.replace('/','\\').split('\\')[-1].replace('$','_').replace(' ','?') + str(uniq_num) #directive[7:-1].replace('$','_').replace(' ','?') + str(uniq_num)
                                                    # extract the file:
                                                    f = self.zfile.open(flp)
                                                    content = f.read()
                                                    f = open(curr_file_name.replace('?',' '),'wb')
                                                    f.write(content)
                                                    f.close()
                                                    files_to_delete.append(curr_file_name.replace('?',' '))
                                                    # handle replace directives in the raw_command and add it to the all_commands list:
                                                    all_commands.append(raw_command.replace(directive , curr_file_name).replace("|output|" , parsing_dir + "\\" + artifact + "\\" + vol_str + "_parse_out_" + str(uniq_num)).replace("<|parsingdir|>", parsing_dir + "\\").replace('<','').replace('>',''))
                                                    uniq_num = uniq_num + 1

                            
                        # if command has no |path| directive, but has |output| directive:
                        elif any(re.fullmatch("<\\|output\\|[^>]*>",directive) for directive in directives):
                            # handle any <|output|> directives with no |path| directive:
                            all_commands.append(raw_command.replace("|output|", parsing_dir + "\\" + artifact + "\\" + "parse_out_" + str(uniq_num)).replace("<|parsingdir|>", parsing_dir + "\\").replace('<','').replace('>',''))
                            uniq_num = uniq_num + 1
                        
                        # if command has niether |path| nor |output| directives:
                        else:
                            # handle command with no directive, just add the raw command to all_commands
                            # WARNING: there is a danger of creating an output file that has the same name as another
                            # file that was created by another command without an |output| directive in the parsing dir.
                            # to mitigate this, it is recommended to always use the |output| directive.
                            all_commands.append(raw_command.replace("<|parsingdir|>", parsing_dir + "\\"))

                        # run all commands for generated from a single command, clear them, and delete the files_to_delete to save space:
                        # run the commands:
                        for cmd in all_commands:
                            self.run_parser_command(cmd, os.path.dirname(parsing_dir))
                        # delete run commands:
                        all_commands.clear()
                        # delete files_to_delete:
                        self.delete_files(files_to_delete)
                        # clear deleted files:
                        files_to_delete.clear()

        
        except Exception as e:
            self.logging("ERROR", "Error in main parsing block. Artifact: " + artifact + " (exception: " + str(e) + ")\n" + traceback.format_exc())
            pass
        finally:
            # finally, delete all parsers, close the parsers zip handle, create the parsing_out zip file, and delete the working dir:
            try:
                # delete all extracted parsers and all left files:
                self.delete_files(parsers_to_delete)
                self.delete_files(files_to_delete)
                #close the parsing zip file
                parsers_file.close()
                
                # clear the zipfile if parsing level is 2 (no_raw_files)
                if self.parse_level == 2:
                    self.zfile.close()
                    os.remove(self.output)
                    self.zfile = zipfile.ZipFile(self.output, mode='w' , compresslevel=self.compress_level , compression=self.compress_method , allowZip64=True)

                # add parsing outputs to zip (handle empty directories if needed)
                for root, dirs, files in os.walk(parsing_dir):
                    for file in files:
                        self.zfile.write(os.path.join(root, file), root[root.rfind("parsing_out"):]+'\\'+file)
                
                # delete parsing working dir
                shutil.rmtree(parsing_dir.replace('?',' '))

                # log parsing finish:
                self.logging("INFO", "Completed Parsing.")

            except Exception as e:
                self.logging("ERROR", "Error in parsing cleanup cluase (exception: " + str(e) + ")\n" + traceback.format_exc())
                pass


    # runs a parser command
    def run_parser_command(self, command, wd):
        # to complete handling spaces, split the command by space to seperate the command and the args:
        cmd = command.split()
        for i in range(len(cmd)):
            cmd[i] = cmd[i].replace('?',' ')
        
        # run the command:
        self.logging("DEBUG", "parser: running the command '" + str(cmd) + "'...")
        p = subprocess.Popen(cmd, cwd=wd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = p.communicate()
        self.logging("DEBUG", "parser: command '" + str(cmd) + "' run. std.err:" + str(err) + ". stdout:" + str(out))
        # I chose not to log or output std.out to supress large output.
        # If std.out needed in the future, here is where it should be handled

    # deletes all files in a list:
    def delete_files(self, files_to_delete):
        try:
            for ftd in files_to_delete:
                if os.path.isdir(ftd.replace("/","\\")):
                    shutil.rmtree(os.path.abspath(ftd.replace("/","\\")))
                elif os.path.isfile(ftd.replace("/","\\")):
                    os.remove(os.path.abspath(ftd.replace("/","\\")))
                else:
                    self.logging("WARNING", "parsing: cannot delete - file " + ftd.replace("/","\\").replace(' ','?') + " is niether a file nor a directory!")
        except Exception as e:
            self.logging("ERROR", "An error occured in deleting parsing files (exception: " + str(e) + ")")
            pass

    # handle hoarder logs 
    def logging(self, type , msg):
        # Write hoarder.log
        line = str(datetime.utcnow()) + " - " + type + ":" + msg
        if self.verbose:
            if self.verbose == 1 and type != 'DEBUG':
                print(line)
            elif self.verbose == 2:
                print(line)
        f = open(self.hoarderlog , 'a', encoding="utf-8" , newline = "")
        f.write( line + "\r\n")
        f.close()

        # write json log:
        jline = {'@timestamp':str(datetime.utcnow()), 'type': type, 'msg':msg}
        f = open(self.hoarderjsonlog, 'a', encoding="utf-8", newline = "")
        json.dump(jline,f)
        f.write(os.linesep)
        f.close()


# check if admin privilage
def is_user_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        pass
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except:
        return False


# Main function
def main():
    # Set Process Priority:
    p = psutil.Process(os.getpid())
    p.nice(psutil.HIGH_PRIORITY_CLASS)

    #initialize arguments:
    args = init_hoarder()
    
    if args.version:
        print("Hoarder v" + __version__)
        
    else:
        # get argument options:
        options = []
        groups = []
        v = vars(args)
        for a in v:
            if a in ['all' , 'version' , 'verbose' , 'very_verbose' , "image_file"]:
                continue
            if v[a]:
                options.append(a) 
        
        # if user admin run hoarder:
        if is_user_admin():
            # Deduce verbose level:
            verbose = 0
            if args.very_verbose:
                verbose = 2
            elif args.verbose:
                verbose = 1
            
            # Deduce parse level:
            parse_level = 0 # no parsing
            if 'parse_artifacts' in options:
                parse_level = 1 # parse
                options.remove('parse_artifacts')
            if 'no_raw_files' in options:
                parse_level = 2 # parse (no raw files)
                options.remove('no_raw_files')

            if 'groups' in options:
                groups = args.groups
                options.remove('groups')

            image_file = args.image_file
            h = Hoarder(hoarder_config , options=options , enabled_verbose=verbose , image_path = image_file, parse_level = parse_level, groups = groups)  
            
        else:
            # Re-run the program with admin rights
            ctypes.windll.shell32.ShellExecuteW(None, u"runas", sys.executable, subprocess.list2cmdline(sys.argv), "", 1)


if __name__ == '__main__':
    main()