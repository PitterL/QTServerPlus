from kivy.lang import Builder

from multiprocessing import Pipe
from ui.app import UiApp
from server.core import QTouchserver
from bus.manage import BusManager
from bus.hid_bus import Hid_Bus

BusManager.register_bus(Hid_Bus())

Builder.load_file('ui/app.kv')
Builder.load_file('ui/element.kv')

if __name__ == '__main__':
    bus_parent_pipe, bus_client_pipe = Pipe()  #devices send message to server
    manager = BusManager(bus_parent_pipe)

    ui_parent_pipe, ui_client_pipe = Pipe() #communication between server and ui
    server = QTouchserver(bus_client_pipe, ui_client_pipe)

    ui = UiApp(ui_parent_pipe)
    ui.run()
