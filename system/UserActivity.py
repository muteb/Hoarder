import os
import win32api
import win32net
import win32netcon
import ctypes


class user_act:
    def __init__(self,command):
        self.command= command


    def userloggedin(self):

        values = win32api.GetUserName()

        return values

    def allusers(self):
        filter = win32netcon.FILTER_NORMAL_ACCOUNT
        values =win32net.NetUserEnum(None, 0, filter, 0)
        lstpri = []
        for x in values[0]:
            member= x['name']
            group ='Administrators'
            members = win32net.NetLocalGroupGetMembers(None, group, 1)
            xval =(member, member.lower() in list(map(lambda d: d['name'].lower(), members[0])))
            lstpri.append(xval)
        return lstpri

    def create_local_user(self):
        user_info = dict (name = 'test',password = "Passw0rd",priv = win32netcon.USER_PRIV_USER, home_dir = None,comment = None,flags = win32netcon.UF_SCRIPT,script_path = None)
        test1 = win32net.NetUserAdd(None,1, user_info)
        return test1








# # Function usage
# if_user_in_group()
