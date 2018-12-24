import psutil

class services_act:
    def __init__(self,command):
        self.command= command


    def Services(self):
        #get windows services
        winservices= list(psutil.win_service_iter())
        return winservices


commandcls = services_act('osdetails')
info= commandcls.Services()
# data2=pickle.dumps(info)
print info
