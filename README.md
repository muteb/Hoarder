# Hoarder
This script is made to collect the most valuable artifacts for forensics or incident response investigation rather than imaging the whole hard drive. 

## installing dependences

To install Hoarder  dependences run the following command on a privileged terminal:

`pip install -r requirment.txt` 

## Usage

Make sure that `hoarder.yml` is on the same directory as the script. `hoarder.yml` is YAML file that contains artifacts. Hoarder will read this file and generate argument at runtime (try `python hoarder.py -h`). The following is the list of argument :

```
usage: hoarder.py [-h] [-a] [-p] [-v VOLUME] [-s] [--PowerShellHistory]
                  [--Config] [--SystemInfo] [--CCM] [--WMITraceLogs]
                  [--Firwall] [--Events] [--usrclass] [--BMC] [--Ntuser]
                  [--WERFiles] [--SRUM] [--Jump_List] [--Recent] [--Ntfs]
                  [--applications] [--WMI] [--scheduled_task] [--Startup]
                  [--BrowserHistory] [--prefetch] [--RecycleBin]
                  [--WindowsIndexSearch] [-V]

Hoarder is a tool to collect windows artifacts.

optional arguments:
  -h, --help            show this help message and exit
  -a, --all             Get all (Default)
  -p, --processes       Collect information about the running processes.
  -v VOLUME, --volume VOLUME
                        Select a volume letter to collect artifacts from (By
                        default hoarder will automatically look for the root
                        volume)
  -s, --services        Collect information about the system services.
  --PowerShellHistory   PowerShell history for all the users
  --Config              System hives
  --SystemInfo          Get system information
  --CCM                 CCM Logs
  --WMITraceLogs        WMI Trace Logs
  --Firwall             Firewall Logs
  --Events              Windows event logs
  --usrclass            UserClass.dat file for all the users
  --BMC                 BMC files for all the users
  --Ntuser              All users hives
  --WERFiles            Windows Error Reporting Files
  --SRUM                SRUM folder
  --Jump_List           JumpList files
  --Recent              Recently opened files
  --Ntfs                $MFT file
  --applications        Amcache files
  --WMI                 WMI OBJECTS.DATA file
  --scheduled_task      Scheduled Tasks files
  --Startup             Startup info
  --BrowserHistory      BrowserHistory Data
  --prefetch            Prefetch files
  --RecycleBin          RecycleBin Files
  --WindowsIndexSearch  Windows Search artifacts
  -V, --version         Print Hoarder version number.
```

#### Example

Let's say you want to collect all of the artifacts specified in `hoarder.yml` then all you need to do is:

`python hoarder.py --all` or `python hoarder.py -a` 

After the script finishes it will generate a zip file called `<HOSTNAME>.zip` contains all of the artifacts in addition to `metadata.csv` which contains all selected artifacts' metadata (path,time, etc) and `hoarder.log` that contains the script debugging logs.

## Add an artifact to hoarder.yml

### File and Folder Artifacts

The following is an example for file or folder collection:

```yaml
applications: 
      output: 'applications'
      path32: '\Windows\AppCompat\Programs\'
      path64: '\Windows\AppCompat\Programs\'
      para: 
      - Amcache.hve*
      - RecentFileCache.bcf
      type: 'file'
      copyType: 'justCopy'
      description: 'Amcache files'
```

* applications : This is the name of the artifact. This name will be used as an argument in the hoarder command line.
* output : This is the name of the output folder for this artifact.
* path32 : The path to the artifact for 32bit systems.
* path64 : The path to the artifact for 64bit systems.
* para : The file name/s. it could be a single string or a list as the example above.
* type : The time of the artifact. is it a file or folder.
* copyType : Hoarder support two types of coping a file, normal and justCopy.
  * normal : a normal copy to the file. This type should be used if the file is not locked and it could be copied normally.
  * justCopy : This type of coping is used to copy files in use (locked) which can not be copied using the normal method such as $MFT and Amcache.hve
* description : a description  about the artifact. This key is used in hoarder command line to show some information about the artifact.

### Command Execution 

Hoarder also support the execution of system commands. The following example shows the execution of the command "systeminfo":

```yaml
SystemInfo:
    output: 'SystemInfo'
    cmd: 'systeminfo'
    type: 'run'
    description: 'Get system information'
```

* SystemInfo : This is the name of the artifact. This name will be used as an argument in the hoarder command line.

output : This is the name of the output folder for this artifact.

* cmd : The command to be executed. If you want to revere to the output file you can use the variable `{{resultsPath}}`. For example the if your cmd key value is `systeminfo > {{resultsPath}}\results.txt` it will be evaluated as:

```
systeminfo > _HoarderDirectory_\_HostName_\SystemInfo\results.txt
		    |		    |		|
		    |		    |		------------------|
		    V		    V				  V
The path of Hoarder executable	Machine Hostname	 'output' key value
```

* type : The type of the  artifact. Could be `cmd` or `run`
* description : a description  about the artifact. This key is used in hoarder command line to show some information about the artifact.
