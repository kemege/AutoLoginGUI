# -*- encoding: utf-8 -*-
import sys
import os.path
import datetime
import requests
from netifaces import interfaces, ifaddresses, AF_INET
import wx
import wx.adv
import eventlet
from eventlet.green.urllib.request import urlopen, Request
from eventlet.timeout import Timeout

TRAY_ICON = 'login.ico'


class MyLog(wx.Log):
    def __init__(self, textCtrl, logTime=0):
        wx.Log.__init__(self)
        self.tc = textCtrl
        self.logTime = logTime

    def Log(self, message):
        if self.tc:
            timeString = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S ')
            self.tc.AppendText(timeString + message + '\n')


class TaskBarIcon(wx.adv.TaskBarIcon):
    """docstring for TaskBarIcon"""

    def __init__(self, frame):
        super(TaskBarIcon, self).__init__()
        self.frame = frame
        self.setIcon(TRAY_ICON)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.showWindow)
        self.frame.taskBarIcon(self)

    def showWindow(self, event):
        self.frame.Show()

    def setIcon(self, path):
        # Set window icon
        icon = wx.Icon()
        try:
            basePath = sys._MEIPASS
        except Exception:
            basePath = os.path.abspath('.')
        iconPath = os.path.join(basePath, path)
        icon.CopyFromBitmap(wx.Bitmap(iconPath, wx.BITMAP_TYPE_ANY))
        self.SetIcon(icon)


class MainFrame(wx.Frame):
    """docstring for MainFrame"""

    def __init__(self, parent, id, title):
        super(MainFrame, self).__init__(parent, id, title)
        self.setIcon(TRAY_ICON)

        self.pool = eventlet.GreenPool()
        self.panel = wx.Panel(self, -1)
        self.usernameControl = wx.TextCtrl(self.panel, -1)
        self.passwordControl = wx.TextCtrl(self.panel, -1, style=wx.TE_PASSWORD)
        self.start = wx.Button(self.panel, -1, 'Start')
        self.stop = wx.Button(self.panel, -1, 'Stop')
        self.loggerText = wx.TextCtrl(self.panel, -1, size=(-1, 300), style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.logger = MyLog(self.loggerText)

        self.start.Bind(wx.EVT_BUTTON, self.startLogin)
        self.stop.Bind(wx.EVT_BUTTON, self.stopLogin)
        self.Bind(wx.EVT_CLOSE, self.exit)
        self.Bind(wx.EVT_ICONIZE, self.hideWindow)

        flag = wx.EXPAND | wx.ALL
        self.grid = wx.GridBagSizer(5, 5)
        self.grid.Add(wx.StaticText(self.panel, -1, "UIS ID"), (0, 0), flag=flag)
        self.grid.Add(self.usernameControl, (0, 1), flag=flag)
        self.grid.Add(wx.StaticText(self.panel, -1, "UIS Password"), (1, 0), flag=flag)
        self.grid.Add(self.passwordControl, (1, 1), flag=flag)
        self.grid.Add(self.start, (2, 0), flag=flag)
        self.grid.Add(self.stop, (2, 1), flag=flag)
        self.grid.Add(self.loggerText, (3, 0), (1, 2), flag=flag)
        self.grid.AddGrowableCol(0, 1)
        self.grid.AddGrowableCol(1, 1)
        self.grid.AddGrowableRow(3, 1)

        sizer = wx.BoxSizer()
        sizer.Add(self.grid, 5, wx.ALL | wx.EXPAND, 5)
        self.panel.SetSizer(sizer)
        self.SetClientSize(self.panel.GetBestSize())

        # Flag for controlling auto login
        self.startFlag = False
        self.stop.Enable(False)
        # Timer for automatic login
        self.interval = 600
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.autoLogin, self.timer)

        # Constants for login status
        self.SUCCESS = 0
        self.NEED_LOGIN = 1
        self.NO_NEED_LOGIN = 2
        self.TIMED_OUT = 3
        self.OTHER = 4

        # URL constants
        self.testURL = 'http://119.10.39.100/Upload/20170509133345.jpg'
        self.ipURL = 'http://10.158.181.55/tools/ip.php?raw'

    def autoLogin(self, event):
        # Function for automatic login
        if self.startFlag is False:
            return

        status = self.checkLogin()
        if status['reason'] == self.NO_NEED_LOGIN:
            self.logger.Log('No need to login')
            return
        elif status['reason'] == self.NEED_LOGIN:
            self.logger.Log('Login needed')
            # Start loggin in
            result = self.doLogin()
            if result['result']:
                self.logger.Log('Login successful')
            else:
                self.logger.Log('Login Failed')
                if result['reason'] == self.NO_IP:
                    self.logger.Log('Cannot get intranet IP')
                else:
                    self.logger.Log(result['detail'])
        elif status['reason'] == self.TIMED_OUT:
            self.logger.Log('Fail to fetch data... will try later')
            return
        elif status['reason'] == self.OTHER:
            self.logger.Log('Connection error: ' + status['detail'])
            return

    def startLogin(self, event):
        self.startFlag = True
        self.start.Enable(False)
        self.stop.Enable(True)
        self.usernameControl.Enable(False)
        self.passwordControl.Enable(False)
        self.logger.Log('Automatic login started')

        self.autoLogin(event)
        self.timer.Start(self.interval * 1000)

    def stopLogin(self, event):
        self.startFlag = False
        self.start.Enable(True)
        self.stop.Enable(False)
        self.usernameControl.Enable(True)
        self.passwordControl.Enable(True)
        self.logger.Log('Automatic login stopped')

        self.timer.Stop()

    def getIP(self):
        # Get local IP address
        result = None
        for ifaceName in interfaces():
            addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
            for address in addresses:
                if address[:3] == '10.':
                    result = address
        if result is not None:
            self.logger.Log('Got intranet IP: %s' % result)
        return result

    def getIPRemote(self):
        # Get IP address from server
        try:
            thread = self.pool.spawn(self.fetch, self.ipURL, {})
            content = thread.wait()
            if content is None:
                return None
            else:
                self.logger.Log('Got intranet IP: %s' % content)
                return content
        except Exception as e:
            return None

    def fetch(self, url, header):
        # Fetch HTTP page with eventlet pool
        response = ''
        with Timeout(60, False):
            req = Request(url, None, header)
            response = urlopen(req).read()
            response = response.decode()
        return response

    def checkLogin(self):
        # Check whether it's necessary to login
        try:
            thread = self.pool.spawn(self.fetch, self.testURL, {})
            content = thread.wait()
            if (not content):
                return {'result': False, 'reason': self.TIMED_OUT}
            if '10.108.255.249' in content or 'wlrz.fudan.edu.cn' in content:
                return {'result': False, 'reason': self.NEED_LOGIN}
            else:
                return {'result': True, 'reason': self.NO_NEED_LOGIN}
        except Exception as e:
            return {'result': False, 'reason': self.OTHER, 'detail': str(e)}

    def doLogin(self):
        # Perform login action
        username = self.usernameControl.GetLineText(0)
        password = self.passwordControl.GetLineText(0)
        loginURL1 = 'http://10.108.255.249/include/auth_action.php'
        loginURL2 = 'http://10.108.255.249/get_permits.php'
        ip = self.getIPRemote()

        if ip is None:
            return {'result': False, 'reason': self.NO_IP}
        data1 = {
            'username': username,
            'password': password,
            'action': 'login',
            'ac_id': '1',
            'ajax': '1',
            'save_me': '0',
            'user_ip': ip
        }

        data2 = {
            'username': data1['username']
        }
        try:
            requests.post(loginURL2, data=data2)
            requests.post(loginURL1, data=data1)
        except:
            return {'result': False, 'reason': self.OTHER, 'detail': str(e)}
        return {'result': True, 'reason': self.SUCCESS}

    def setIcon(self, path):
        # Set window icon
        icon = wx.Icon()
        try:
            basePath = sys._MEIPASS
        except Exception:
            basePath = os.path.abspath('.')
        iconPath = os.path.join(basePath, path)
        icon.CopyFromBitmap(wx.Bitmap(iconPath, wx.BITMAP_TYPE_ANY))
        self.SetIcon(icon)

    def hideWindow(self, event):
        self.Hide()
        self.Iconize(False)

    def showWindow(self, event):
        self.Show()
        self.Iconize(False)
        self.Raise()

    def taskBarIcon(self, taskBarIcon):
        self.taskBarIcon = taskBarIcon

    def exit(self, event):
        self.taskBarIcon.Destroy()
        event.Skip()


class MainApp(wx.App):
    def OnInit(self):
        frame = MainFrame(None, -1, u"Auto Login")
        self.SetTopWindow(frame)
        frame.Show(True)
        TaskBarIcon(frame)
        return True

if __name__ == '__main__':
    app = MainApp(0)
    app.MainLoop()
