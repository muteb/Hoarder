# Hoarder
This script is made to collect the most valuable artifacts for forensics or incident response investigation rather than imaging the whole hard drive.

## Executable Releases:
You may find the executable binaries for x86 and x64 on 
>> will be added soon

## installing dependences

To install Hoarder  dependences run the following command on a privileged terminal:

`pip install -r requirment.txt` 

## Usage

Make sure that `Hoarder.yml` is on the same directory as the script. `Hoarder.yml` is YAML file that contains artifacts. Hoarder will read this file and generate argument at runtime (try `python hoarder.py -h`). The following is the list of argument :

```
usage: hoarder.py [-h] [-V] [-v] [-a] [-p] [-s] [--Ntfs]
                   [--PowerShellHistory] [--scheduled_task] [--applications]
                   [--WindowsIndexSearch] [--prefetch] [--usrclass] [--Config]
                   [--WERFiles] [--Jump_List] [--BrowserHistory]
                   [--RecycleBin] [--WMITraceLogs] [--Recent] [--Ntuser]
                   [--CCM] [--Startup] [--Events] [--WMI] [--SRUM]
                   [--SystemInfo] [--BMC] [--Firwall]

Hoarder is a tool to collect windows artifacts.

optional arguments:
  -h, --help            show this help message and exit
  -V, --version         Print Hoarder version number.
  -v, --verbose         Print details of hoarder message in console.
  -a, --all             Get all (Default)

Plugins:
  -p, --processes       Collect information about the running processes.
  -s, --services        Collect information about the system services.

Artifacts:
  --Ntfs                $MFT file
  --PowerShellHistory   PowerShell history for all the users
  --scheduled_task      Scheduled Tasks files
  --applications        Amcache files
  --WindowsIndexSearch  Windows Search artifacts
  --prefetch            Prefetch files
  --usrclass            UserClass.dat file for all the users
  --Config              System hives
  --WERFiles            Windows Error Reporting Files
  --Jump_List           JumpList files
  --BrowserHistory      BrowserHistory Data
  --RecycleBin          RecycleBin Files
  --WMITraceLogs        WMI Trace Logs
  --Recent              Recently opened files
  --Ntuser              All users hives
  --CCM                 CCM Logs
  --Startup             Startup info
  --Events              Windows event logs
  --WMI                 WMI OBJECTS.DATA file
  --SRUM                SRUM folder
  --BMC                 BMC files for all the users
  --Firwall             Firewall Logs

Commands:
  --SystemInfo          Get system information

```

#### Example

Let's say you want to collect all of the artifacts specified in `Hoarder.yml` then all you need to do is:

`python hoarder.py --all` or `python hoarder.py -a` 

After the script finishes it will generate a zip file called `<HOSTNAME>.zip` contains all of the artifacts in addition to  `hoarder.log` that contains the script debugging logs.


## Add an artifact to hoarder.yml

### File and Folder Artifacts

The following is an example for file or folder collection:

```yaml
  applications: 
      output: 'applications'
      path32: '\Windows\AppCompat\Programs\'
      path64: '\Windows\AppCompat\Programs\'
      files:  
      - Amcache.hve*
      - RecentFileCache.bcf
      description: 'Amcache files'
```

* applications : This is the name of the artifact. This name will be used as an argument in the hoarder command line.
* output : This is the name of the output folder for this artifact.
* path32 : The path to the artifact for 32bit systems, you can use * as widecard, and ** as recursive.
* path64 : The path to the artifact for 64bit systems, you can use * as widecard, and ** as recursive.
* files : The file name/s. it could be a single string or a list as the example above, also you can use * as widecard.
* description : a description about the artifact. This key is used in hoarder command line to show some information about the artifact.

### Command Execution 

Hoarder also support the execution of system commands. The following example shows the execution of the command "systeminfo":

```yaml
  SystemInfo:
    output: 'SystemInfo'
    cmd: 'systeminfo'
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

* description : a description  about the artifact. This key is used in hoarder command line to show some information about the artifact.

## Contributors:
Big thanks to [AbdulRhman Alfaifi](https://github.com/AbdulRhmanAlfaifi) and [Saleh Bin Muhaysin](https://github.com/salehmuhaysin) for their tremendous effrot in rewriting this project in a proper way and his ideas.  
