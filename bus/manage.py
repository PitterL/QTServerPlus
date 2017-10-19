from abc import abstractmethod
from multiprocessing import Process, Pipe
import time

from server.message import Message, BusMessage, Token

class PhyDevice(object):
    "Each Device is a Hardware device, will running in a individual process()"
    def __init__(self, physical):
        self.phy = physical
        #self.cmd_pipe = None
        self.pipe_device_to_logic = None
        self.cmd_seq = 0
        self.p = Process(target=self.process)

    def start(self, default_pipe):
        # send the parent_pipe to server, then server will connect this pipe to send command

        parent_pipe, client_pipe = Pipe(duplex=True) #only use server send message to device. The opposite direction is transfer by default pipe.
        self.pipe_device_to_logic = parent_pipe
        #self.p = Process(target=self.process, args=())
        #self.p.setDaemon(True)
        self.p.start()
        BusMessage(Message.MSG_DEVICE_ATTACH, self.id(), Token(self.cmd_seq),
                value=client_pipe, pipe=default_pipe).send()
        #parent.close()

    def stop(self, default_pipe):
        print("dev {} call stop".format(self.phy.instance_id))
        BusMessage(Message.MSG_DEVICE_ATTACH, self.id(), Token(self.cmd_seq),
                value=None, pipe=default_pipe).send()
        self.pipe_device_to_logic.close()
        self.p.join()
        print("stop exit")

    def id(self):
        if not self.phy:
            raise BusError("Dev not exist")

        return self.phy.instance_id

    def next_seq(self, token):
        self.cmd_seq += 1
        token.append(self.cmd_seq)
        print(self.__class__.__name__, "next seq {}".format(token))
        return token

    def logic_pipe(self):
        return self.pipe_device_to_logic

    def process(self):
        # core process to communicate with higher layer with data transfer
        # each attached device will have a individual process
        print("process<{}> run".format(self.__class__.__name__))

class Bus(object):
    def __init__(self):
        self.devices = {}

    @abstractmethod
    def create_new_device(self, *args, **kwargs):
        print("create new device: {}".format(args, kwargs))

    @abstractmethod
    def refresh(self):
        #refesh the bus to check whether any new device attached
        #  return class Device() list object
        pass

    def add_or_remove_phy_devices(self, phys, bus_to_server_pipe):

        #print("add_or_remove_phy_devices++")
        #remove unexist device first
        for id, dev in self.devices.copy().items():
            if dev.id() not in map(lambda phy: phy.instance_id, phys):
                dev.stop(bus_to_server_pipe)
                del self.devices[id]
                del dev

        #add new device
        for phy in phys:
            if phy.instance_id not in self.devices.keys():
                new_dev = self.create_new_device(phy)
                new_dev.start(bus_to_server_pipe)
                self.devices[new_dev.id()] = new_dev

        #print("add_or_remove_phy_devices--")

class BusManager(object):
    """Daemon process to watch any device insert into bus, and share message pipe to the device.
       The other end of the message pipe is connected to server process"""
    BUS_TABLE = []
    BUS_REFRESH_TIME = 2 #second

    def __init__(self, bus_to_server_pipe):
        "bus_to_server_pipe as a default pipe which communicate with the server"
        self.refresh = BusManager.BUS_REFRESH_TIME
        self.p = Process(target=self.process, args=(bus_to_server_pipe,))
        #self.p.daemon = True
        self.p.start()
        #bus_to_server_pipe.close() #fork in process

    def process(self, pipe):
        "watch new devices, if found, create a Device() and send the communication pipe to up level"
        #TODO how to exit the process
        print("process<{}> run".format(self.__class__.__name__))
        while len(self.BUS_TABLE) > 0:
            for bus in self.BUS_TABLE:
                phys = bus.refresh()    #TODO: use RegisterDeviceNotification to watch device change
                bus.add_or_remove_phy_devices(phys, pipe)

            time.sleep(self.refresh)

        pipe.close()

    @staticmethod
    def register_bus(bus):
        if bus in BusManager.BUS_TABLE:
            raise BusError("Bus {} has been registered Already".format(bus))
        BusManager.BUS_TABLE.append(bus)