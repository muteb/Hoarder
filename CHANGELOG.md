

# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).




## [3.2.0] - 2020-01-25

### Added:
- Added handling forensics disk image `-f` switch, which collect the artifacts from disk image instead of the live disk
- Added icon for hoarder executable
- Added more artifacts to collect:
  - Bits Admin database files
  - Amcache files now collect all files in the folder, not just `Amcache.hve*`



## [3.1.0] - 2019-11-27

### Changed:
- Hoarder now does not depends on the OS to detect the Physical Drive to collect the files from, instead it will iterate over all the Phyisical Drives (\\.\PhysicalDrive0, \\.\PhysicalDrive1, etc.) and collect the files matching the configuration on `Hoarder.yml`, it is hoarder literally ;)
- Mutiple changes on `Hoarder.yml` config file


## [3.0.0] - 2019-11-18

### Changed:
- Hoarder v3 now rebuilt to work with python3 instead of python2
- All extracted files now compressed directly to the ouput zip file, instead of writing it to the disk and compress it
- Major changes on the performance enhancement
- Reading the files content from physical disk in all cases instead of using (normal copy and justCopy options)
- Mutiple changes on `Hoarder.yml` config file to be more easier to write

### Added:
- Add new object `Plugins` which contain plugins such as list processes and services

### Fixed:
- Fixed issue of compressing large files

### Removed:
- Removed the `metadata.csv` file temporarily and will be added soon
- Removed Specify the volume letter, currently it auto-detect the running system
