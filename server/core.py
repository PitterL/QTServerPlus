from multiprocessing import Process, Pipe
from multiprocessing.connection import wait
import array
import sys

from server.message import Message, ServerMessage
from server.devinfo import Page, MemMapStructure as Mm

class ServerError(Exception):
    "Main Bus error exception class type"
    pass

class LogicDevice(Mm):
    CMD_STACK_DEPTH = 1
    INTERVAL_POLL_DEVICE = 0.2  #seconds
    PAGE_ID_INFORMATION_QUERY_CONNECTED = False #test purpose

    def __init__(self, id, logic_pipe):
        self.__id = id
        self.logic_pipe = logic_pipe
        self.cmd_seq = 0    #if command finished, seq plus one
        #self.status = Message.MSG_DEVICE_DETACH
        self.cmd_list = []
        self.msg_list = []
        self.addr = 0
        super(LogicDevice, self).__init__()

    def id(self):
        return self.__id

    def match_seq(self, seq):
        return self.cmd_seq == cmd_seq

    def next_seq(self, token):
        self.cmd_seq += 1
        token.append(self.cmd_seq)
        return token

    def pipe(self):
        return self.logic_pipe

    """
    def set_status(self, status):
        self.status = status

    def set_addr(self, addr):
        self.addr = addr
    """
    def handle_attached_msg(self):
        kwargs = {'delay':LogicDevice.INTERVAL_POLL_DEVICE, 'repeat':True}
        command = ServerMessage(Message.CMD_POLL_DEVICE, self.id(), self.next_seq(Message.seq_root()), **kwargs)
        self.prepare_command(command)

    def handle_connected_msg(self, seq, data):
        #print("handle_connected_msg")

        if LogicDevice.PAGE_ID_INFORMATION_QUERY_CONNECTED:
            page_id = Page.ID_INFORMATION
            if not self.page_valid(page_id):
                self.page_read(page_id, discard=True)

        address = 0x01  #FIXME: need report device Phy I2C Address
        message = ServerMessage(Message.MSG_DEVICE_CONNECTED, self.id(), self.next_seq(seq), value=address)
        self.prepare_message(message)

    def handle_page_read_msg(self, seq, cmd, data):
        type = cmd.type()
        cmd_info = cmd.extra_info()
        cmd_addr = cmd_info['addr']
        cmd_size = cmd_info['size']
        cmd_page_id = cmd_info['page_id']

        data_size = len(data['value'])
        page = self.get_page(cmd_page_id)
        start = cmd_addr - page.addr()
        page.save_to_buffer(start, data['value'])

        if data_size == cmd_size:
            #self.prepare_message(Message.MSG_DEVICE_PAGE_READ, self.id(), seq, data)
            result = self.page_parse(cmd_page_id)
            if result:
                message = ServerMessage(Message.MSG_DEVICE_PAGE_READ, self.id(), self.next_seq(seq), value=page)
            else:
                page.clear_buffer()
                message = ServerMessage(Message.MSG_DEVICE_PAGE_READ, self.id(), self.next_seq(seq), value=None)

            self.prepare_message(message)

        else:
            command = ServerMessage(Message.CMD_DEVICE_BLOCK_READ, self.next_seq(Message.seq_root()),
                                    start=cmd_addr + data_size, length=cmd_size - data_size)
            self.prepare_command(command)

    def handle_nak_msg(self, seq, data=None):
        #self.prepare_message(Message.MSG_DEVICE_NAK, self.id(), seq, data)
        print("NAK")

    def prepare_message(self, message):
        self.msg_list.append(message)

    def messages_pop(self):
        while len(self.msg_list):
            yield self.msg_list.pop()

    def handle_message(self, msg):
        type = msg.type()
        seq = msg.seq()

        if type == Message.MSG_DEVICE_ATTACH:
            self.handle_attached_msg()  # only status of attached, since detach will Logici device is removed
        else:
            for i, cmd in enumerate(self.cmd_list[:]):
                #print("handle_message: seq msg={} cmd={}".format(seq, cmd.seq()))
                if cmd.seq() == seq:
                    seq.pop()
                    if type == Message.MSG_DEVICE_CONNECTED:
                        self.handle_connected_msg(seq, msg.extra_info())
                    elif type == Message.CMD_DEVICE_PAGE_READ:
                        self.handle_page_read_msg(seq, cmd, msg.extra_info())
                    elif type == Message.MSG_DEVICE_BLOCK_READ:
                        self.handle_block_read_msg(seq, cmd, msg.extra_info())
                    elif type == Message.MSG_DEVICE_NAK:
                        self.handle_nak_msg(seq, msg.extra_info())
                    else:
                        raise ServerError("Logic device id '{}' msg {} seq not match".format(id, msg))
                        self.handle_nak_msg(seq)

                    del self.cmd_list[i]
                    break

    def prepare_command(self, command):
        if len(self.cmd_list) > self.CMD_STACK_DEPTH:   #command may have two in stack, one in prepare, one will be processing and done
            ServerError("command still in process {}", self.cmd_list)
            self.cmd_list.pop()

        #self.cmd_list.append(Message(type, self.id(), self.next_seq(seq), **kwargs, pipe=self.pipe()))
        command.set_pipe(self.pipe())
        self.cmd_list.append(command)

    def send_command(self):
        for cmd in self.cmd_list:
            cmd.send()

        #FIXME: when remove the command from list?

    def page_read(self, page_id, discard=False):
        if self.has_page(page_id):
            page = self.get_page(page_id)
            if discard:
                page.clear_buffer()

            if page.buffer_data_valid():
                return page
            else:
                kwargs = {'page_id': page_id}
                command = ServerMessage(Message.CMD_DEVICE_PAGE_READ, self.id(), self.next_seq(Message.seq_root()),
                                     addr=page.addr(), size=page.size(), page_id=page_id)
                self.prepare_command(command)
        else:
            ServerError("Unknown page {} requested".format(page_id))

    def handle_device_page_read(self, seq, kwargs):
        page_id = kwargs['page_id']
        discard = kwargs['discard'] if 'discard' in kwargs else False

        if self.has_page(page_id):
            page = self.get_page(page_id)
            valid_size = 0
            if discard:
                page.clear_buffer()

            if page.buffer_data_valid():
                message = ServerMessage(Message.MSG_DEVICE_PAGE_READ, self.id(), seq, value=page)
                self.prepare_message(message)
            else:
                self.page_read(page_id, discard)
        else:
            ServerError("Unknown page {} requested".format(page_id))
            self.nak_command(seq)

    def handle_device_page_write(self, id, seq, data):
        pass

    def nak_command(self, seq):
        message = ServerMessage(Message.MSG_DEVICE_NAK, self.id(), seq)
        self.prepare_message(message)

    def handle_command(self, msg):
        type = msg.type()
        seq = msg.seq()

        print("handle_command")

        if type == Message.CMD_DEVICE_PAGE_READ:
            self.handle_device_page_read(seq, msg.extra_info())
        elif type == Message.CMD_DEVICE_PAGE_WRITE:
            self.handle_device_page_write(seq, msg.extra_info())
        else:
            ServerError("cmd {} not support".format(msg))

class QTouchserver(object):
    INTERVAL_RESCAN = 2     #second

    def __init__(self, pipe_to_bus, pipe_to_ui):
        #self.server_to_bus_pipe = server_to_bus_pipe    #get message from devices of bus
        #self.ui_pipe = ui_pipe  #communication with up layer (UI)
        self.devices = {}
        self.ui_command = []
        #super(QTouchserver, self).__init__()

        self.p = Process(target=self.process, args=(pipe_to_bus, pipe_to_ui))
        self.p.start()
        #server_to_bus_pipe.close() #fork in process
        #ui_pipe.close()

    """
    def dev_seq_match(self, id, seq):
        if id in self.devices.keys():
            dev = self.devices[id]
            return dev.match_seq(seq)

        raise ServerError("Logic device id '{}' not exist".format(id))
    
    def next_dev_seq(self, id):
        if id in self.devices.keys():
            dev = self.devices[id]
            return dev.next_seq()

        raise ServerError("Logic device id '{}' not exist".format(id))
    

    def set_dev_attr(self, id, var_name, var_value):
        if id in self.devices.keys():
            dev = self.devices[id]
            if dev.hasattr(var_name):
                dev.setattr(var_name, var_value)
    """
    def report_ui_message(self, pipe):
        "Report message to up layer"
        for dev in self.devices.values():
            for msg in dev.messages_pop():
                msg.send_to(pipe)

    def handle_attach_msg(self, id, seq, ext_info):
        logic_pipe = ext_info['value']

        #remove device
        if id in self.devices.keys():
            if not logic_pipe:
                dev = self.devices[id]
                del self.devices[id]
                del dev
        else:
            if logic_pipe:
                dev = LogicDevice(id, logic_pipe)   #each logic device will communicate to a physical device
                self.devices[id] = dev

        #Message(Message.MSG_DEVICE_ATTACH, id, seq, value=True if value else False, pipe=self.ui_pipe).send()

    def dispatch_msg(self, id, msg):
        if id in self.devices.keys():
            self.devices[id].handle_message(msg)

    def handle_bus_message(self, msg):
        type = msg.type()
        id = msg.id()
        seq = msg.seq()

        print("handle_bus_message")

        #default bus pipe
        if type == Message.MSG_DEVICE_ATTACH:
            self.handle_attach_msg(id, seq, msg.extra_info())

        #logic pipe
        self.dispatch_msg(id, msg)

    def handle_poll_device_cmd(self, id, seq):
        self.devices[id].prepare_command(Message.CMD_POLL_DEVICE, seq)

    def dispatch_cmd(self, id, msg):
        if id in self.devices.keys():
            self.devices[id].handle_command(msg)

    def handle_ui_command(self, msg):
        type = msg.type()
        id = msg.id()
        seq = msg.seq()

        #print("handle_ui_command")

        if id in self.devices.keys():
            if type == Message.CMD_POLL_DEVICE:
                self.handle_poll_device_cmd(id, seq)
            else:
                self.dispatch_cmd(id, msg)
        else:
            ServerError("cmd {} id {} not exist".format(msg, id))

    def get_bus_devices_pipe_line(self):
        pipe_line =[]
        for dev in self.devices.values():
            pipe_line.append(dev.pipe())

        return pipe_line

    def process_bus_command(self):
        for dev in self.devices.values():
            dev.send_command()

    def process(self, pipe_to_bus, pipe_to_ui):
        print("process<{}> run".format(self.__class__.__name__))
        #self.bus_pipe = bus_pipe
        #self.ui_pipe = ui_pipe

        close_handle = False
        while not close_handle:  #FIXME: there is somd end command
            all_pipes = self.get_bus_devices_pipe_line()
            all_pipes.append(pipe_to_bus)
            all_pipes.append(pipe_to_ui)
            for r in wait(all_pipes[:]):
                #try:
                msg = r.recv()
                print("Process<{}> get message: {}".format(self.__class__.__name__, msg))

                location = msg.loc()
                if location == Message.BUS or location == Message.DEVICE:
                    self.handle_bus_message(msg)
                elif location == Message.UI:
                    self.handle_ui_command(msg)
                else:
                    pass
                """
                except EOFError:
                    #readers.remove(r)
                    ServerError("Pipe {} report EOFError", r) #FIXME: should process the ERROR?
                    if r == server_to_bus_pipe:
                        close_handle = True
                        break
                else:
                    print("Unexpected error: {}".format(self.__class__.__name__))
                """
            self.process_bus_command()
            self.report_ui_message(pipe_to_ui)

        pipe_to_bus.close()
        pipe_to_ui.close()



