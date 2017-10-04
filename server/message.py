import time

class MsgError(Exception):
    "Message error exception class type"
    pass

class Token(list):
    def __init__(self, arg):
        if isinstance(arg, list):
            val = arg
        else:
            val = [arg]
        super(Token, self).__init__(val)

class BaseMessage(object):
    def __init__(self, location, type, id, seq, **kwargs):
        self._location = location
        self._type = type
        self._id = id
        self._seq = seq  # may use Token as sequence
        self._kwargs = kwargs

    #def __repr__(self):
    #    return str([self.loc(), self.type(), self.id(), self.seq()]) + str(self.extra_info())

    def __str__(self):
        return str([self.loc(), self.type(), self.id(), self.seq()]) + str(self.extra_info())

    def loc(self):
        return self._location

    def type(self):
        return self._type

    def id(self):
        return self._id

    def seq(self):
        #print("Token {}".format(self._seq))
        return self._seq.copy()

    def extra_info(self):
        return self._kwargs

    def value(self):
        info = self.extra_info()
        if 'value' in info.keys():
            return info['value']

class Message(BaseMessage):
    #message name
    (DEVICE, BUS, SERVER, UI) = ('Device', 'Bus', 'Server', 'Ui')

    #message format of each byte
    (FORMAT_CMD, FORMAT_ID, FORMAT_SEQ) = range(3)

    #message type
    (MSG_DEVICE_NAK, MSG_DEVICE_ATTACH, MSG_DEVICE_BOOTLOADER, MSG_DEVICE_CONNECTED, MSG_DEVICE_PAGE_READ, MSG_DEVICE_PAGE_WRITE, MSG_DEVICE_BLOCK_READ, MSG_DEVICE_BLOCK_WRITE) = range(10, 18)

    #command
    (CMD_POLL_DEVICE, CMD_DEVICE_PAGE_READ, CMD_DEVICE_PAGE_WRITE, CMD_DEVICE_BLOCK_READ, CMD_DEVICE_BLOCK_WRITE) = range(100, 105)
    #command status
    (INIT, SEND, REPEAT) = range(3)

    #range 600 + used by USER

    @staticmethod
    def seq_root():
        return Token([])

    def __init__(self, location, type, id, seq, **kwargs):
        self._status = Message.INIT

        if 'pipe' in kwargs.keys():
            self.pipe = kwargs.pop('pipe')
        else:
            self.pipe = None

        self.__time = time.time()
        super(Message, self).__init__(location, type, id, seq, **kwargs)

    def status(self):
        return self._status

    def time(self):
        return self.__time

    def set_status(self, status):
        self._status = status
        self.__time = time.time()

    def set_pipe(self, pipe):
        self.pipe = pipe

    def ready(self):
        return self.status() == Message.INIT

    def msg_data(self):
        return BaseMessage(self.loc(), self.type(), self.id(), self.seq(), **self.extra_info())

    def send_to(self, pipe):
        if not pipe:
            MSGError("Pipe is None")

        status = self.status()

        if self.ready():
            self.set_status(Message.SEND)
            data = self.msg_data()
            print("Send Message: {}".format(data))
            pipe.send(data)
            return True

        return False

    def send(self):
        if not self.pipe:
            MsgError('No pipe set')
        else:
            return self.send_to(self.pipe)

class DeviceMessage(Message):
    def __init__(self, *args, **kwargs):
        super(DeviceMessage, self).__init__(Message.DEVICE, *args, **kwargs)

class BusMessage(Message):
    def __init__(self, *args, **kwargs):
        super(BusMessage, self).__init__(Message.BUS, *args, **kwargs)

class ServerMessage(Message):
    def __init__(self, *args, **kwargs):
        super(ServerMessage, self).__init__(Message.SERVER, *args, **kwargs)

class UiMessage(Message):
    def __init__(self, *args, **kwargs):
        super(UiMessage, self).__init__(Message.UI, *args, **kwargs)