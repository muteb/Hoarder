import psutil
import sys

class service_act:
    def __init__(self,command):
        self.command= command


    def GetAllServices(self):
        allservices =[]
        for serv in psutil.win_service_iter():
            print serv.as_dict()
            print "\n"
            allservices.append(serv.as_dict())
            #allproesses.append("\n")
        return allservices


# commandcls = service_act('osdetails')
# info= commandcls.GetAllServices()
# # data2=pickle.dumps(info)
# print info
