import os
import json
import time
import GenertaeHashLib

class file_act:
    def __init__(self,xpath):
        # self.command= command
        self.path = xpath
        print self.path[0]


    def path_to_dict(self):

        path = os.path.abspath(self.path)
        d= {}
        d['dirs'] = []
        d['files'] = []
        # d['metadata']= []
        for f in os.listdir(path):
            fof=os.path.join(path, f)
            if os.path.isfile(fof):
                d['files'].append({'file':f, 'path':fof
                # "metadata": os.stat.st_mtime(os.path.join(path, f))
                })
            if os.path.isdir(fof):
                d['dirs'].append({'dir':f, 'path':fof})
        d['mainfolder'] = os.path.dirname(path)
        return d

    def get_file_metadata(self):
        pathz = os.path.abspath(self.path)
        print pathz
        d= {}
        d['file'] = []
        # d['metadata']= []
        # for f in os.isfile(path):
        fof=pathz
        commandcls = file_act(fof)
        hashes= commandcls.get_file_data()

        md5 = hashes[0]
        sha1 = hashes[1]
        sha256 = hashes[2]
        #print sha1
        if os.path.isfile(fof):
            d['file'].append({'created':time.ctime(os.path.getmtime(fof)), 'accessed':time.ctime(os.path.getatime(fof)),
            'modified':time.ctime(os.path.getmtime(fof)),'size':os.path.getsize(fof),'md5':md5,'sha1':sha1,
            'sha256':sha256
            # "metadata": os.stat.st_mtime(os.path.join(path, f))
            })
        else:
            print'notfile'
        print d
        return d

    def get_file_data(self):
        filePath = self.path
        fileData = ""
        try:
            # Read file complete
            with open(filePath, 'rb') as f:
                fileData = f.read()
                f.close()
        except Exception, e:
            print e
        hashes = GenertaeHashLib.generate_hash(fileData)
        return hashes





#
# commandcls = file_act("C:\hiberfil.sys")
# info= commandcls.get_file_metadata()
# # data2=pickle.dumps(info)
# print info
