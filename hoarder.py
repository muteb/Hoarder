
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

__version__ = "3.0"

hoarder_config = "Hoarder.yml"
# Add the static arguments.
args_set = argparse.ArgumentParser(description="Hoarder is a tool to collect windows artifacts.\n\n")

args_set.add_argument('-V', '--version', action="store_true", help='Print Hoarder version number.')
args_set.add_argument('-v', '--verbose', action="store_true", help='Print details of hoarder message in console.')
args_set.add_argument('-a', '--all', action="store_true", help='Get all (Default)')

#args_set.add_argument('-v', '--volume', help='Select a volume letter to collect artifacts from (By default hoarder will automatically look for the root volume)')

# set arguments for plugins
argsplugins = args_set.add_argument_group('Plugins')
argsplugins.add_argument('-p', '--processes', action="store_true", help='Collect information about the running processes.')
argsplugins.add_argument('-s', '--services', action="store_true", help='Collect information about the system services.')

# build the artifacts and commands options
argspartifacts  = args_set.add_argument_group('Artifacts')
argscommands    = args_set.add_argument_group('Commands')

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
    bVerboseEnabled = False
    options         = []
    plugins         = Plugins()
    def __init__(self, config_file , options=None , enabled_verbose = False , output=None, compress_level=6, compress_method = zipfile.ZIP_DEFLATED):
        
        self.options = options 
        
        self.bVerboseEnabled    = enabled_verbose
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
        
        # init. zip file
        try:
            if os.path.isfile(output ) :
                os.remove(output)
            self.zfile = zipfile.ZipFile(output, mode='w', compresslevel=compress_level , compression=compress_method)
        except Exception as e:
            self.logging("ERR" , "Failed opening output file ["+output+".zip] : " + str(e))
            sys.exit()
        
        # get yaml configuration 
        self.config = self.GetYamlConfig(config_file)
        
        
        # make sure there are a OS on the disk 
        if not self.GetWindowsPart():
            self.logging("ERR" , "No Partition with Windows OS found")
        
        # get all artifacts paths selected
        paths = self.GetPaths()
        """paths = {
            "users" : [
                '/Users/K/Desktop/test.txt',
                '/Users/K/Desktop/antest.txt'
            ],
            "program": [
                '/ProgramData/testdata.txt',
            ],
            "": [
                '/$LogFile'
            ]
        }
        """
        # extract all files and compress it
        self.ExtractFiles(paths) 
        
        # execute commands on yaml config
        self.ExecuteCommands()
        
        # run selected plugins
        self.RunPlugins()
        
        self.logging("INFO" , "Hoarder Done!")
        
        f = open('hoarder.log' , 'rb')
        self.ZipWriteFile(f.read() , 'hoarder.log')
        f.close()
        
        self.zfile.close()
    
    
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
        
    def GetPaths(self):
        # check if the config element is artifacts files and make sure whether the argument is all or the artifact selected
        enabled_artifacts = [ea for ea in self.config if 'cmd' not in self.config[ea] and (ea in self.options or len(self.options) == 0)]
        self.logging("INFO" , "Enabed Artifacts: " + str(len(enabled_artifacts)))
        
        # get paths
        paths = {}
        selected_files = 0
        for arti in enabled_artifacts:
            output_folder = self.config[arti]['output']
            
            # check Windows arch
            if _platform == "win32" and 'path32' in self.config[arti]:
                arti_paths = self.config[arti]['path32']
            elif _platform == "win64" and 'path64' in self.config[arti]:
                arti_paths = self.config[arti]['path64']
            else:
                continue
            
            # get all paths as list 
            paths_list = []
            if type(arti_paths) is not list:
                arti_paths = [arti_paths]
            for p in arti_paths:
                paths_list.append(p)
            
            
            
            # append the para (files) with paths
            if 'files' in self.config[arti]:
                files_list = []
                files = self.config[arti]['files']
                if type(self.config[arti]['files']) is not list:
                    files = [files]
                for path in paths_list:
                    for f in files:
                        files_list.append(path + f)
                paths_list = files_list
                
            # trace and replace the * to get full path
            full_paths = []
            for p in paths_list:
                for i in self.GetWildCardPaths(p):
                    full_paths.append(i)
            
            self.logging("INFO" , "Files ["+str(len(full_paths))+"] \t" + arti)
            paths[output_folder] = full_paths
            
            selected_files += len(full_paths)
            
        self.logging("INFO" , "Found "+str(selected_files)+" files to be collected")
        return paths
    
    # Gets wildcard paths and return the absulote path.
    def GetWildCardPaths(self, path):
        paths = []
        for p in glob.glob(self.disk_drive + path , recursive=True ):
            if os.path.isfile(p):
                paths.append(p.lstrip(self.disk_drive) )
            
        return paths
        
        
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
        
        
    # get all files from the disk and compress it on zip file
    def ExtractFiles(self , paths):
        collected_files = 0
        for key in paths:
            # if there is no files to be collected skip
            if len(paths[key]) == 0:
                continue
                
            self.logging("INFO" , "Start ["+key+"] collection")
            for file in paths[key]:
                try:
                    if key == "":
                        file = file.lstrip('/')
                    fdata = self.ReadFile(file)
                    if fdata:
                        self.ZipWriteFile( fdata , key + file)
                        collected_files += 1
                except Exception as e:
                    self.logging("ERR" , "Failed collecting the file ["+file+"], reason: " + str(e))
                    
        self.logging("INFO" , "Successfuly finished collecting ["+str(collected_files)+"] files")
        
    # write file to zip file
    def ZipWriteFile(self, data , path):
        self.zfile.writestr(path , data)
        
    # read file content from disk
    def ReadFile(self, path):
        try:
            f = self.filesystemObj.open(path.replace("\\" , "/"))
            fdata = f.read_random(0,f.info.meta.size)
            return fdata
        except Exception as e:
            self.logging ("ERR", "Failed reading the file: " + path + " - reason:" + str(e) )
            return False
        
    # test function
    def CopyFile(self, pathList , dir_root , curr_path = "/" ):
        #print("Current Path: " + curr_path)
        found_files  = 0 # count the number of files found on this directory
        found_dirs   = 0 # count number of dirs found
        for dir_entry in dir_root:
            # if all files found on the directory then stop
            if found_files + found_dirs >= len(pathList):
                break
            #print( dir_entry )
            entry_meta = dir_entry.info.meta
            entry_name = dir_entry.info.name
            
            # Skip ".", ".." or directory entries without a name.
            if (not hasattr(dir_entry, "info") or
                not hasattr(dir_entry.info, "name") or
                not hasattr(dir_entry.info.name, "name") or
                dir_entry.info.name.name.decode('utf-8') in [".", ".."]):
                continue
            
            #print ( curr_path + dir_entry.info.name.name.decode('utf-8'))
            temp_dir = []
            #print( pathList )
            for path in pathList:
                if any(p[0] == path for p in self.pathsfound):
                    continue
                # check if path for file or dir
                #print( curr_path + " >> " + path)
                temp_path = path[len(curr_path)::]
                #print( temp_path )
                if len(temp_path.split('/')) > 1:
                    # directory
                    #print( "dir: " + temp_path )
                    if temp_path.split('/')[0] == entry_name.name.decode('utf-8'):
                        temp_dir.append(path)
                        found_dirs += 1
                        
                else:
                    # file 
                    #print(temp_path + "=====" + entry_name.name.decode('utf-8'))
                    if temp_path == entry_name.name.decode('utf-8'):
                        #print( "=====found file: " + path )
                        f = self.filesystemObj.open_meta()
                        self.pathsfound.append([ path , f ])
                        found_files += 1 
            
            #print(temp_dir)
            if len(temp_dir):
                new_path = curr_path + entry_name.name.decode('utf-8') + "/"
                self.CopyFile(temp_dir ,  dir_entry.as_directory() , new_path)
        
    # get the partion with Windows OS 
    def GetWindowsPart(self, phyDrive = "\\\\.\\PhysicalDrive0"):
        self.filesystemObj  = None   # contain the file system object
        self.root_dir       = None   # store opened dir on root
        bWindowsFound       = False  # true if partition with windows OS found
        
        img                 = pytsk3.Img_Info(phyDrive) # open the physical drive
        volume              = pytsk3.Volume_Info(img)   # get volume information 
        block_size          = 512                       # by default block size is 512 
        for part in volume:
            try:
                self.filesystemObj = pytsk3.FS_Info(img , offset=part.start * block_size )
                
                dirs = []
                for dir_entry in self.filesystemObj.open_dir("/"):
                    dirs.append( dir_entry.info.name.name.decode("utf-8")  )
                    # print( dir_entry.info.name.name )
                
                
                if 'Windows' in dirs and 'Users' in dirs:
                    #print( "[+] Windows Partition found: addr[%d] , desc[%s] , offet[%d] , size[%d] " , part.addr, part.desc.decode('utf-8'), part.start, part.len)
                    bWindowsFound = True
                    break
            except Exception as e :
                pass
                #print( "[-] Error %s" , str(e))
        
        if bWindowsFound:
            self.root_dir = self.filesystemObj.open_dir("/")
        return bWindowsFound

    def logging(self, type , msg):
        line = str(datetime.utcnow()) + " - " + type + ":" + msg 
        if self.bVerboseEnabled:
            print(line)
        f = open("hoarder.log" , 'a' , newline = "")
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
            if a in ['all' , 'version' , 'verbose']:
                continue
            if v[a]:
                options.append(a) 
        
        # if user admin run hoarder
        if is_user_admin():
            h = Hoarder(hoarder_config , options=options , enabled_verbose=args.verbose)   
        else:
            # Re-run the program with admin rights
            ctypes.windll.shell32.ShellExecuteW(None, u"runas", sys.executable, subprocess.list2cmdline(sys.argv), "", 1)
