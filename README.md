# Hoarder
This script is made to collect the most valuable artifacts for forensics or incident response investigation rather than imaging the whole hard drive. 

## installing dependences

To install Hoarder  dependences run the following command on a privileged terminal:

`pip install -r requirment.txt` 

## Usage

Make sure that `hoarder.yml` is on the same directory as the script. `hoarder.yml` is YAML file that contains artifacts. Hoarder will read this file and generate argument at runtime (try `python hoarder.py -h`). The following is the list of argument :

```
	usage: hoarder.py [-h] [-a] [-p] [-s] [--PowerShellHistory] [--Config]
                  [--WMITraceLogs] [--Firwall] [--Events] [--usrclass] [--BMC]
                  [--Ntuser] [--ChromeData] [--SRUM] [--Recent] [--Ntfs]
                  [--FirefoxData] [--applications] [--WMI] [--scheduled_task]
                  [--IECookies] [--IEData] [--Startup] [--prefetch]
                  [--RecycleBin] [--WindowsIndexSearch]

Hoarder is a tool to collect windows artifacts.

optional arguments:
  -h, --help            show this help message and exit
  -a, --all             Get all
  -p, --processes       Collect information about the running processes.
  -s, --services        Collect information about the system services.
  --PowerShellHistory   PowerShell history for all the users
  --Config              System hives
  --WMITraceLogs        WMI Trace Logs
  --Firwall             Firewall Logs
  --Events              Windows event logs
  --usrclass            UserClass.dat file for all the users
  --BMC                 BMC files for all the users
  --Ntuser              All users hives
  --ChromeData          Chrome Data
  --SRUM                SRUM folder
  --Recent              Recently opened files
  --Ntfs                $MFT file
  --FirefoxData         Firefox Data
  --applications        Amcache files
  --WMI                 WMI OBJECTS.DATA file
  --scheduled_task      Scheduled Tasks files
  --IECookies           Internet Explorer Cookies
  --IEData              Internet Explorer Data
  --Startup             Startup info
  --prefetch            Prefetch files
  --RecycleBin          RecycleBin Files
  --WindowsIndexSearch  Windows Search artifacts
```

#### Example

Let's say you want to collect all of the artifacts specified in `hoarder.yml` then all you need to do is:

`python hoarder.py --all` or `python hoarder.py -a` 

After the script finishes it will generate a zip file called `<HOSTNAME>.zip` contains all of the artifacts in addition to `metadata.csv` which contains all selected artifacts' metadata (path,time, etc) and `hoarder.log` that contains the script debugging logs.

## Add an artifact to hoarder.yml

The following is an example for an artifact:

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
