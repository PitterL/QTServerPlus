import kivy
kivy.require('1.1.10') # replace with your current kivy version !
#from kivy.core.window import Window
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, FallOutTransition
from kivy.properties import NumericProperty, DictProperty, ListProperty
from kivy.clock import Clock
#from kivy.modules import inspector
#from kivy.core.window import Window

import os
from random import random
from multiprocessing import Pipe

from server.message import Message
from ui.DeviceWindow import DeviceWindow
from ui.DebugView import DebugView

class UiError(Exception):
    "Message error exception class type"
    pass

class MainScreen(Screen):
    "Main Screen"
    hue = NumericProperty(0)
    windows = DictProperty({})

    def __init__(self, pipe_ui_with_server, **kwargs):
        self.pipe_ui_with_server = pipe_ui_with_server
        super(MainScreen, self).__init__(**kwargs)

    def add_or_remove_window(self, id, attached):
        print("add_or_remove_window++", id, attached)
        # remove device
        if id in self.windows.keys():
            if not attached:
                win = self.windows[id]
                self.remove_widget(win)
                del self.windows[id]
                del win
        else:
            if attached:
                new_win = DeviceWindow(id)
                self.add_widget(new_win)
                self.windows[id] = new_win

        print("add_or_remove_window--")

    def dispatch_msg(self, id, msg):
        if id in self.windows.keys():
            self.windows[id].handle_message(msg)

    def recv(self):
        has_msg = self.pipe_ui_with_server.poll(0)
        if has_msg:
            msg = self.pipe_ui_with_server.recv()
            type = msg.type()
            id = msg.id()
            #print("Process<{}> recv message: {}".format(self.__class__.__name__, msg))
            #create or remove device window, root window only process this message
            if type == Message.MSG_DEVICE_ATTACH:
                self.add_or_remove_window(id, msg.value())  # detach
            elif type == Message.MSG_DEVICE_CONNECTED:
                self.add_or_remove_window(id, msg.value())  # attach

            # process message in window
            self.dispatch_msg(id, msg)

    def send(self):
        for id, win in self.windows.items():
            win.process_command(self.pipe_ui_with_server)

    def update(self, dt):
        self.hue += 0.001
        self.recv()
        self.send()

class MainUi(App):
    "Main Ui"

    def __init__(self, pipe_ui_with_server, **kwargs):
        self.pipe_ui_with_server = pipe_ui_with_server
        super(MainUi, self).__init__(**kwargs)

    @staticmethod
    def load_ui_kv_file(path):
        # print(path)
        for root, dirs, files in os.walk(path, topdown=True):
            for name in files:
                if name.endswith('.py'):
                    raw = name.split('.')[:-1]
                    raw.append('kv')
                    kv_file = ".".join(raw)
                    current_kv_file = root + "\\" + kv_file
                    try:
                        if os.path.exists(current_kv_file):
                            print(current_kv_file)
                            Builder.load_file(current_kv_file)
                    except Exception as e:
                        print('Parse failed: {:s}'.format(str(e)))

    def build(self):
        self.load_ui_kv_file(os.curdir)

        root = ScreenManager(transition=FallOutTransition())
        scr = MainScreen(self.pipe_ui_with_server, name='Main Screen')
        root.add_widget(scr)
        Clock.schedule_interval(scr.update, 1.0 / 60.0)
        return root

if __name__ == '__main__':
    parent, client = Pipe()
    MainUi(parent).run()