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
    CMD_STACK_DEPTH = 1000
    INTERVAL_POLL_DEVICE = None  #seconds
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

    def next_seq(self, t):
        self.cmd_seq += 1
        token = t.copy()
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
    def handle_attached_msg(self, seq, data):
        val = data.get('value', None)
        if val:
            kwargs = {'repeat': LogicDevice.INTERVAL_POLL_DEVICE}
            command = ServerMessage(Message.CMD_POLL_DEVICE, self.id(), self.next_seq(Message.seq_root()), **kwargs)
            self.prepare_command(command)
        else:
            message = ServerMessage(Message.MSG_DEVICE_ATTACH, self.id(), seq, value=None)
            self.prepare_message(message)

    def handle_connected_msg(self, seq, data):
        #print("handle_connected_msg")
        if LogicDevice.PAGE_ID_INFORMATION_QUERY_CONNECTED:
            page_id = Page.ID_INFORMATION
            if not self.page_valid(page_id):
                self.page_read(page_id, discard=True)

        address = 0x01  #FIXME: need report device Phy I2C Address

        message = ServerMessage(Message.MSG_DEVICE_CONNECTED, self.id(), seq, value=address)
        self.prepare_message(message)

    def handle_page_read_msg(self, seq, cmd, data):
        type = cmd.type()
        cmd_info = cmd.extra_info()
        cmd_addr = cmd_info['addr']
        cmd_size = cmd_info['size'] # how many data is left
        cmd_page_id = cmd_info['page_id']

        #print(self.__class__.__name__, "handle_page_read_msg", cmd, data)

        data_size = len(data['value'])  #current readout data size
        if data_size == 0 or data_size > cmd_size:  #something error
            self.handle_nak_msg(seq, cmd, "data_size is invalid data_size {} cmd_size {}".format(data_size, cmd_size))
            return

        page = self.get_page(cmd_page_id)
        start = cmd_addr - page.addr()
        result = page.save_to_buffer(start, data['value'])
        if not result:
            self.handle_nak_msg(seq, cmd, "save_to_buffer error start {} data {}".format(start, data['value']))
            return

        if data_size == cmd_size: # no data left
            result = self.page_parse(cmd_page_id)
            if result:
                message = ServerMessage(Message.MSG_DEVICE_PAGE_READ, self.id(), seq, value=page)
                self.prepare_message(message)
            else:   #failed
                page.clear_buffer()
                self.handle_nak_msg(seq, cmd)
        else:
            command = ServerMessage(Message.CMD_DEVICE_PAGE_READ, self.id(), self.next_seq(seq),
                                    addr=cmd_addr + data_size, size=cmd_size - data_size, page_id=cmd_page_id)
            self.prepare_command(command)

    def handle_page_write_msg(self, seq, cmd, data):
        type = cmd.type()
        cmd_info = cmd.extra_info()
        cmd_addr = cmd_info['addr']
        cmd_value = cmd_info['value']   # store how many data will be sent
        cmd_group = cmd_info.pop('group', None)
        cmd_size = len(cmd_value)
        cmd_page_id = cmd_info['page_id']

        #print(self.__class__.__name__, "handle_page_write_msg", cmd, data)

        data_size = data['value']
        if data_size == 0 or data_size > cmd_size:  #something error
            self.handle_nak_msg(seq, cmd, "data_size is invalid data_size {} cmd_size {}".format(data_size, cmd_size))
            return

        page = self.get_page(cmd_page_id)
        start = cmd_addr - page.addr()
        result = page.save_to_buffer(start, cmd_value[:data_size])
        if not result:
            self.handle_nak_msg(seq, cmd, "save_to_buffer error start {} data {}".format(start, data['value']))
            return

        if data_size == len(cmd_value):
            if not cmd_group:
                message = ServerMessage(Message.MSG_DEVICE_PAGE_WRITE, self.id(), seq, value=page)
                self.prepare_message(message)
            else:
                self.prepare_command(cmd_group)
        else:
            #size = cmd_size - data_size
            value = cmd_value[data_size:]
            command = ServerMessage(Message.CMD_DEVICE_PAGE_WRITE, self.id(), self.next_seq(seq),
                                    addr=cmd_addr + data_size, value=value, page_id=cmd_page_id)
            self.prepare_command(command)

    def handle_raw_data_msg(self, seq, cmd, data):
        message = ServerMessage(Message.MSG_DEVICE_RAW_DATA, self.id(), seq, value=data['value'])
        self.prepare_message(message)

    def handle_interrupt_data_msg(self, seq, data):
        message = ServerMessage(Message.MSG_DEVICE_INTERRUPT_DATA, self.id(), seq, value=data['value'])
        self.prepare_message(message)

    def handle_nak_msg(self, seq, error=None):
        print(self.__class__.__name__, "Send NAK message:", seq, error)
        message = ServerMessage(Message.MSG_DEVICE_NAK, self.id(), seq, error=error)
        self.prepare_message(message)

    def prepare_message(self, message):
        self.msg_list.append(message)

    def messages_pop(self):
        while len(self.msg_list):
            yield self.msg_list.pop()

    def handle_message(self, msg):
        type = msg.type()
        seq = msg.seq()

        if type == Message.MSG_DEVICE_ATTACH:
            self.handle_attached_msg(seq, msg.extra_info())  # only status of attached, since detach will Logici device is removed
        elif type == Message.MSG_DEVICE_INTERRUPT_DATA:
            self.handle_interrupt_data_msg(seq, msg.extra_info())
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
                    elif type == Message.CMD_DEVICE_PAGE_WRITE:
                        self.handle_page_write_msg(seq, cmd, msg.extra_info())
                    elif type == Message.CMD_DEVICE_RAW_DATA:
                        self.handle_raw_data_msg(seq, cmd, msg.extra_info())
                    elif type == Message.MSG_DEVICE_NAK:
                        self.handle_nak_msg(seq, error=msg)
                    else:
                        raise ServerError("Logic device id '{}' msg {} seq not match".format(id, msg))
                        self.handle_nak_msg(seq, error="Unknow msg type {}".format(type))

                    del self.cmd_list[i]
                    break

    def group_command(self, cmd_list):
        command = cmd_list[0]
        if len(cmd_list) > 1:
            command.set_extra_info(group=cmd_list[1:])

        return command

    def prepare_command(self, command):
        if len(self.cmd_list) > self.CMD_STACK_DEPTH:   #command may have two in stack, one in prepare, one will be processing and done
            raise ServerError("command still in process {}", self.cmd_list)
            self.cmd_list.pop()

        if isinstance(command, (tuple, list)):
            command = self.group_command(command)

        #self.cmd_list.append(Message(type, self.id(), self.next_seq(seq), **kwargs, pipe=self.pipe()))
        command.set_pipe(self.pipe())
        self.cmd_list.append(command)

    def send_command(self):
        for cmd in self.cmd_list:
            cmd.send()
        #FIXME: when remove the command from list?

    def handle_device_page_read(self, type, seq, kwargs):
        page_id = kwargs.get('page_id')
        discard = kwargs.get('discard', True)

        if self.has_page(page_id):
            page = self.get_page(page_id)
            if discard:
                page.clear_buffer()

            if page.buffer_data_valid():
                message = ServerMessage(Message.MSG_DEVICE_PAGE_READ, self.id(), seq, value=page)
                self.prepare_message(message)
            else:
                kwargs = {'page_id': page_id}
                command = ServerMessage(Message.CMD_DEVICE_PAGE_READ, self.id(), self.next_seq(seq),
                                        addr=page.addr(), size=page.size(), page_id=page_id)
                self.prepare_command(command)
        else:
            ServerError("Unknown page read {} requested".format(page_id))
            self.nak_command(seq)

    def handle_device_page_write(self,type, seq, kwargs):
        page_id = kwargs.get('page_id')
        offset = kwargs.get('offset', 0)
        value = kwargs.get('value')
        assert isinstance(value, (tuple, list, array.array))

        if self.has_page(page_id):
            page = self.get_page(page_id)
            page_size = page.size()
            buf_size = page.data_length()
            buf = page.buf()

            st = None
            cmd_list = []
            val = value[:page_size - offset]
            for i, v in enumerate(val):
                if i >= buf_size:   #buf data is not enough
                    if st is None:
                        st = i
                        break

                if v != buf[offset + i]:
                    if st is None:
                        st = i
                else:
                    if st is not None:
                        cmd = ServerMessage(Message.CMD_DEVICE_PAGE_WRITE, self.id(), self.next_seq(seq),
                            addr=page.addr() + st + offset, size=i - st, value=val[st: i], page_id=page_id)
                        cmd_list.append(cmd)    #build group command
                        st = None
            if st:  #last trunk
                cmd = ServerMessage(Message.CMD_DEVICE_PAGE_WRITE, self.id(), self.next_seq(seq),
                                    addr=page.addr() + st + offset, size=len(val) - st, value=val[st: ], page_id=page_id)
                cmd_list.append(cmd)
            if cmd_list:
                self.prepare_command(cmd_list)
            else:
                self.handle_nak_msg(seq, error="Not data changed")
        else:
            ServerError("Unknown page write {} requested".format(page_id))
            self.nak_command(seq)

    def handle_device_raw_send(self, type, seq, kwargs):
        command = ServerMessage(Message.CMD_DEVICE_RAW_DATA, self.id(), self.next_seq(seq), **kwargs)
        self.prepare_command(command)

    def nak_command(self, seq):
        message = ServerMessage(Message.MSG_DEVICE_NAK, self.id(), seq)
        self.prepare_message(message)

    def handle_command(self, msg):
        type = msg.type()
        seq = msg.seq()

        #print(self.__class__.__name__, "handle_command", msg)

        if type == Message.CMD_DEVICE_PAGE_READ:
            self.handle_device_page_read(type, seq, msg.extra_info())
        elif type == Message.CMD_DEVICE_PAGE_WRITE:
            self.handle_device_page_write(type, seq, msg.extra_info())
        elif type == Message.CMD_DEVICE_RAW_DATA:
            self.handle_device_raw_send(type, seq, msg.extra_info())
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

                #   logice device is removed, so there should send message to UI individually
                ServerMessage(Message.MSG_DEVICE_ATTACH, id, seq, value=None, pipe=self.ui_pipe).send()
        else:
            if logic_pipe:
                dev = LogicDevice(id, logic_pipe)   #each logic device will communicate to a physical device
                self.devices[id] = dev



    def dispatch_msg(self, id, msg):
        if id in self.devices.keys():
            self.devices[id].handle_message(msg)

    def handle_bus_message(self, msg):
        type = msg.type()
        id = msg.id()
        seq = msg.seq()

        #print("handle_bus_message")

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
        self.ui_pipe = pipe_to_ui

        close_handle = False
        while not close_handle:  #FIXME: there is somd end command
            all_pipes = self.get_bus_devices_pipe_line()
            all_pipes.append(pipe_to_bus)
            all_pipes.append(pipe_to_ui)
            for r in wait(all_pipes[:]):
                #try:
                msg = r.recv()
                print("Process<{}> get: {}".format(self.__class__.__name__, msg))

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



