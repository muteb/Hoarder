
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


__version__ = "3.1.0"

hoarder_config = "Hoarder.yml"
# Add the static arguments.
args_set = argparse.ArgumentParser(description="Hoarder is a tool to collect windows artifacts.\n\n")

args_set.add_argument('-V', '--version', action="store_true", help='Print Hoarder version number.')
args_set.add_argument('-v', '--verbose', action="store_true", help='Print details of hoarder message in console.')
args_set.add_argument('-vv', '--very_verbose', action="store_true", help='Print more details (DEBUG) of hoarder message in console.')
args_set.add_argument('-a', '--all', action="store_true", help='Get all (Default)')
args_set.add_argument('-f', '--image_file', help='Use disk image as data source instead of the live machine disk image ')



# set arguments for plugins
argsplugins = args_set.add_argument_group('Plugins')
argsplugins.add_argument('-p', '--processes', action="store_true", help='Collect information about the running processes.')
argsplugins.add_argument('-s', '--services', action="store_true", help='Collect information about the system services.')

# build the artifacts and commands options
argspartifacts  = args_set.add_argument_group('Artifacts')
argscommands    = args_set.add_argument_group('Commandss')

yaml_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), hoarder_config)
try:
    yaml_file = open(yaml_path, 'r')
    yaml_config = json.loads( json.dumps( yaml.safe_load(yaml_file.read()) ) )['all_artifacts']
    yaml_file.close()
except Exception as e:
    print("ERR" , "Could not Find Configurations File '"+yaml_path+"'! - reason: " + str(e))
    sys.exit()
                
for key,value in yaml_config.items():
    if 'cmd' in yaml_config[key]:
        argscommands.add_argument('--'+key, action="store_true", help=yaml_config[key]['description'])
    else:
        argspartifacts.add_argument('--'+key, action="store_true", help=yaml_config[key]['description'])
    
args = args_set.parse_args()



class Plugins:
    plugins_list = ['processes' , 'services']
    
    def __init__(self):
        pass
    
    
    
    # This function take's a path to a file as argument then return it's MD% hash.
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
                MD5Hash         = ""
                process_info    = process.as_dict(attrs=attr)
                process_path    = process_info.get('exe')

                date            = datetime.fromtimestamp(process.create_time())
                dateAndTime     = date.strftime('%Y-%m-%d T%H:%M:%S')
                process_info['@timestamp'] = dateAndTime

                imports         = []
                try:
                    for dll in process.memory_maps():
                        imports.append(dll.path)
                except Exception as e:
                    imports.append("AccessDenied")
                process_info['imports'] = imports


                open_files              = process_info['open_files']
                del process_info['open_files']
                fixed_open_files        = []

                if open_files:
                    for file_info in open_files:
                        fixed_open_files.append(file_info[0])
                else:
                    process_info['open_files'] = []
                    
                    
                process_info['open_files']  = fixed_open_files
                
                cmdline                     = process_info['cmdline']
                del process_info['cmdline']
                fixed_cmdline               = ""
                if  cmdline:
                    fixed_cmdline = " ".join(cmdline)
                    process_info['cmdline'] = fixed_cmdline
                else:
                    process_info['cmdline'] = ""
                
                connections         = process_info['connections']
                fixed_connections   = []
                del process_info['connections']

                if connections:
                    for connection in connections:
                        connection_ = {}
                        connection_['local_ip']     = connection.laddr.ip
                        connection_['local_port']   = connection.laddr.port
                        connection_['protocole']    = "TCP" if connection.type == 1 else "UDP"
                        if connection.raddr:
                            connection_['remote_ip']    = connection.raddr.ip
                            connection_['remote_port']  = connection.raddr.port
                        connection_['status']           = connection.status
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
            return [False , "Plugin Processes Failed, reason: " + str(e)]
            
            
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
            return [False, "Plugin Services Failed, reason: " + str(e)]
        
    
class Hoarder:
    verbose         = 0
    options         = []
    plugins         = Plugins()

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
    # config_file:      path to the yaml config file
    # options:          options of collected files and plugins
    # enabled_verbose   level of information to print
    # output            output file name
    # compress_level    compression level
    # compress_method   compression method
    # image_path        using disk image instead of the system disk
    # ==========
    def __init__(self, 
                config_file, 
                options         = None, 
                enabled_verbose = 0, 
                output          = None, 
                compress_level  = 6, 
                compress_method = zipfile.ZIP_DEFLATED,
                image_path      = None):
         
        self.options            = options 
        self.verbose            = enabled_verbose
        self.hostname           = os.getenv('COMPUTERNAME')
        self.disk_drive         = "C:"
        
        if os.path.isfile("hoarder.log" ) :
                os.remove("hoarder.log")
            
        if output is None:
            output = self.hostname + ".zip"
        self.logging("INFO" , "Hoarder Started...")
        self.logging("INFO" , "Output file: " + output)
        self.logging("INFO" , "Hostname: " + self.hostname )
        self.logging("INFO" , "Arch: " + _platform)
        
        if self.verbose == 1:
            self.logging("INFO" , "Verbose mode enabled")
        elif self.verbose == 2:
            self.logging("INFO" , "very verbose mode enabled")

        # init. zip file
        try:
            if os.path.isfile(output ) :
                os.remove(output)
            self.zfile = zipfile.ZipFile(output, mode='w' , compresslevel=compress_level , compression=compress_method , allowZip64=True)
        except Exception as e:
            self.logging("ERR" , "Failed opening output file ["+output+".zip] : " + str(e))
            sys.exit()
        
        # get yaml configuration 
        self.config = self.GetYamlConfig(config_file)
        
        
        # make sure there are a OS on the disk 
        list_imgs = {}

        # if the collection will be from disk image,
        if image_path:
            self.logging("INFO" , "Check disk image: [" + image_path + "]"  )
            if not os.path.isfile(image_path):
                self.logging("ERR" , "Disk image not found ["+image_path+"]")

            # get all the fs_info of all volumes of the drive
            list_imgs["DISK_IMAGE"] = self.GetVolumes(image_path)

            if len(list_imgs["DISK_IMAGE"]) == 0:
                self.logging("WORNING" , "No NTFS Partition found on ["+image_path+"]")
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
                        self.logging("WORNING" , "No NTFS Partition found on PhyisicalDrive" + str(count))
                    else:
                        self.logging("INFO" , "Found ["+str(len(list_imgs["PhysicalDrive" + str(count)]))+"] NTFS partitions on drive ["+"PhysicalDrive" + str(count)+"] ")

                except Exception as e:
                    if str(e) == "PHYSICAL_DRIVE_NOT_FOUND":
                        self.logging("WORNING" , "There is no \\\\.\\PhysicalDrive" + str(count))
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
                            'drive'     : img_info,
                            'volume'    : volum_num
                        }

                        # extract all files from the volume
                        self.ExtractFilesPhysical(fs_info_details , cur_dir_obj=root_dir , paths_list=full_paths)

                    # if inode could not identified
                    else:
                        self.logging("ERR" , "Couldn't identify the root inode")
                    
                    volum_num += 1
 
        
        # execute commands on yaml config
        self.ExecuteCommands()
        
        # run selected plugins
        self.RunPlugins()
        
        self.logging("INFO" , "Hoarder Done!")
        
        f = open('hoarder.log' , 'rb')
        self.ZipWriteFile(f.read() , 'hoarder.log')
        f.close()
        


        self.zfile.close()
    
    # get all paths from yaml config 
    def GetConfigPaths(self):
        # check if the config element is artifacts files and make sure whether the argument is all or the artifact selected
        enabled_artifacts = [ea for ea in self.config if 'cmd' not in self.config[ea] and (ea in self.options or len(self.options) == 0)]
        self.logging("INFO" , "Enabed Artifacts: " + str(len(enabled_artifacts)))
        
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
            
            entry_name = entry.info.name.name.decode('utf-8')       # pytsk entry name
            entry_type = entry.info.name.type                       # pytsk entry type
            
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
            self.logging("WORNING" , "Couldn't get the directory entry for ["+entry_name+"]")
                        
        if dir is not None:
            self.ExtractFilesPhysical(fs_info_details , dir , new_current_folder , new_current_path , bRecursive=bRecursive)


    # get the entry name and details needed to copy the file from physical disk to zip file
    def copy_file(self, fs_info_details , entry , output_folder , file_path):
        # check if the file has META entry and the address is not NONE
        if not hasattr(entry.info, "meta"):
            self.logging("WORNING" , "file: {0:s} does not have META object ".format(file_path))
        elif entry.info.meta is None:
            self.logging("WORNING" , "file meta {0:s} does not have file address".format(file_path))
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

    # function used to run the specified plugin functions
    def RunPlugins(self):
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
                self.logging("ERR" , "Plugin ["+plugin+"] failed, reason: " + plugin_output[1])
        
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
        yaml_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), conf_file)
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
        self.zfile.writestr(path , data)
        
    
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
        block_size          = 512                       # by default block size is 512 

        try:
            img                 = pytsk3.Img_Info(phyDrive) # open the physical drive
            volume              = pytsk3.Volume_Info(img)   # get volume information 
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

    # handle hoarder logs 
    def logging(self, type , msg):
        line = str(datetime.utcnow()) + " - " + type + ":" + msg 
        if self.verbose:
            if self.verbose == 1 and type != 'DEBUG':
                print(line)
            elif self.verbose == 2:
                print(line)
        f = open("hoarder.log" , 'a', encoding="utf-8" , newline = "")
        f.write( line + "\r\n")
        f.close()





# check if user running the script admin or not
def is_user_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        pass
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except:
        return False






if __name__ == '__main__':
    # Set Process Priority to LOW.
    p = psutil.Process(os.getpid())
    p.nice(psutil.HIGH_PRIORITY_CLASS)
    
    if args.version:
        print("Hoarder v" + __version__)
        
    else:
        # get argument options
        options = []
        v = vars(args)
        for a in v:
            if a in ['all' , 'version' , 'verbose' , 'very_verbose' , "image_file"]:
                continue
            if v[a]:
                options.append(a) 
        
        # if user admin run hoarder
        if is_user_admin():
            verbose = 0
            if args.very_verbose:
                verbose = 2
            elif args.verbose:
                verbose = 1
            
            image_file = args.image_file
            h = Hoarder(hoarder_config , options=options , enabled_verbose=verbose , image_path = image_file)  
            
        else:
            # Re-run the program with admin rights
            ctypes.windll.shell32.ShellExecuteW(None, u"runas", sys.executable, subprocess.list2cmdline(sys.argv), "", 1)