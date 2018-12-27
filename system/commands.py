
from SystemActivity import sys_act
from ProcessActivity import process_act
from UserActivity import user_act
from ServicesActivity import service_act
from NetworkActivity import  network_acts
from FileActivity import file_act


class cmds:
    def __init__(self,command):
        if type(command) is list:
            self.appcomand = command[1]
            self.command = command[0]
        else:
            self.command= command


    def pass_command(self):
        if self.command== 'osdetails':

            xx = sys_act(self.command)
            values = xx.SysInfo()
            return values

        if self.command== 'processlst':

            xx = process_act(self.command)
            values = xx.GetAllProcesses()
            return values

        if self.command== 'servicelst':

            xx = service_act(self.command)
            values = xx.GetAllServices()
            return values

        if self.command== 'partitationslst':

            xx = sys_act(self.command)
            values = xx.diskvolumes()
            return values

        if self.command == 'get_network_interfaces':
            x = network_acts(self.command)
            values = x.each_interface_usage()
            return values

        if self.command == 'get_network_conn':
            xx = network_acts(self.command)
            values = xx.list_connections()
            return values

        if self.command== 'get_installed_software':

            xx = sys_act(self.command)
            values = xx.installed_software()
            return values


        # if self.command== 'win_cmd':
        #     cmd = sys_act(self.appcomand)
        #     values = cmd.command_line()
        #     return values

        if self.command== 'get_dns_cache':
            cmd = network_acts(self.command)
            values = cmd._list_dns_cache()
            return values

        # if self.command== 'pwoershell_cmd':
        #     cmd = sys_act(self.appcomand)
        #     values = cmd.powershell_cmd()
        #     return values

        #if self.command== 'get_users_info':
        if self.command == 'getallusers':
            cmd = user_act(self.command)
            values = cmd.allusers()

            # if self.appcomand == 'create_local_user':
            #     cmd =user_act(self.appcomand)
            #     values =cmd.userloggedin()

        if self.command == 'current_logged_in':
            cmd =user_act(self.command)
            values =cmd.userloggedin()
        return values

