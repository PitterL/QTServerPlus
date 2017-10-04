import kivy
kivy.require('1.0.6') # replace with your current kivy version !

from kivy.lang import Builder

from server.message import Message, UiMessage, Token
from server.devinfo import Page

from tools.mem import ChipMemoryMap
from ui.element import WidgetRootElement, WidgetPageElement

class WinError(Exception):
    "Message error exception class type"
    pass

class DeviceWindow(WidgetRootElement):
    CMD_STACK_DEPTH = 1

    def __init__(self, id, *args, **kwargs):
        super(DeviceWindow, self).__init__(*args, **kwargs)
        self.__id = id
        self.cmd_seq = 0
        self.cmd_list = []
        self.object_table = {}
        #self.widget_root = WidgetRootElement()
        #self.page_widgets = {}
        self.pages_mmap = None
        #self.object_buf = {}
        print("create {} {} id {}".format(self.__class__.__name__, self.__init__.__name__, self.id()))

    #def __str__(self):
    #    return super(DeviceWindow, self).__str__() + '(' + self.id() + ')'

    def id(self):
        return self.__id

    def match_seq(self, token):
        return self.cmd_seq == token[-1]

    def next_seq(self):
        self.cmd_seq += 1
        return Token(self.cmd_seq)

    # def parse_id_infomation(self, page):
    #     self.id_infomation = Mm.IdInformation(struct.unpack("B"*ctypes.sizeof(Mm.IdInformation), data))

    # def parse_object_table(self, data):
    #     e_size = ctype.sizof(Mm.ObjectTableElement)
    #     for n in range(self.id_infomation.object_num):
    #         element = Mm.ObjectTableElement(struct.unpack_from("<BHBBB", data[n * esize: (n + 1) * esize]))
    #         self.object_table[element.type] = element

    # def parse_object_type(self, type, data):
    #     if type in self.object_table.keys():
    #         #element = self.object_table[type]
    #         pass
    #
    # def parse_page(self, page):
    #     page_id = page.id()
    #     if page_id == Page.ID_INFORMATION:
    #         self.parse_id_infomation(page)

    def prepare_command(self, msg):
        if len(self.cmd_list) >= self.CMD_STACK_DEPTH:
            WinError("command still in process {}", self.cmd_list)
            self.cmd_list.pop()

        self.cmd_list.append(msg)

    def send_command_to(self, pipe):
        for cmd in self.cmd_list:
            cmd.send_to(pipe)

    def handle_attach_msg(self, data):
        #self.prepare_command(Message(Message.CMD_POLL_DEVICE_DEVICE, self.id(), self.next_seq()))
        pass

    def handle_connected_msg(self, attached):
        #addr = data['value']
        #self.ids.status.text = "Connected to {}".format(hex(attached))
        print("{} connect {}".format(self.__class__.__name__, attached))

        if attached:
            kwargs = {'page_id': Page.ID_INFORMATION, 'discard': False}
            command = UiMessage(Message.CMD_DEVICE_PAGE_READ, self.id(), self.next_seq(), **kwargs)
            self.prepare_command(command)
        else:
            self.pages_mmap = None

    def create_page_element(self, page):
        if not self.pages_mmap:
            chip_id = page.buf()
            self.pages_mmap = ChipMemoryMap.get_chip_mmap(chip_id)

        print(self.__class__.__name__, self.create_page_element.__name__, self.pages_mmap)

        if self.pages_mmap:
            page_mm = self.pages_mmap.get_mmap(page.id())
            w_page = WidgetPageElement(page_mm)
            self.add_element(w_page)
            return w_page

    def distory_page_element(self):
        self.clear_elements()

    def update_page_element(self, page):
        page_id = page.id()
        widget = self.get_element(page_id)
        if not widget:
            widget = self.create_page_element(page)

        if widget:
            page_mm = self.pages_mmap.get_mmap(page.id())
            if page_mm:
                page_mm.set_values(page.buf())
                widget.do_fresh(page_mm)

    def handle_page_read_msg(self, page):

        if not page:
            return

        self.update_page_element(page)

        page_id = page.id()
        if page_id == Page.ID_INFORMATION:
            kwargs = {'page_id': Page.OBJECT_TABLE, 'discard': False}
            command = UiMessage(Message.CMD_DEVICE_PAGE_READ, self.id(), self.next_seq(), **kwargs)
            self.prepare_command(command)
        elif page_id == Page.OBJECT_TABLE:
            pass
        #if page_id not in self.page_tabs.keys():
        #    tab = PageTab(page)
        #    self.page_tabs[page_id] = tab
        #    self.add_widget(tab)


        #self.ids["message"] == "Page {} read: {}".format(page.id(), str(page))
        #self.ids.message.text = str(page)

    def handle_page_write_msg(self, data):
        self.ids["message"] == "Page write: {}".format(data)

    def hand_nak_msg(self):
        pass

    def handle_message(self, msg):
        type = msg.type()
        seq = msg.seq()
        val = msg.value()

        print("Process<{}> handle message: {}".format(self.__class__.__name__, msg))

        if type == Message.MSG_DEVICE_ATTACH:
            self.handle_attach_msg(val)
        elif type == Message.MSG_DEVICE_CONNECTED:
            self.handle_connected_msg(val)
        elif type == Message.MSG_DEVICE_PAGE_READ:
            self.handle_page_read_msg(val)
        elif type == Message.MSG_DEVICE_PAGE_WRITE:
            self.handle_page_write_msg(val)
        elif type == Message.MSG_DEVICE_NAK:
            self.hand_nak_msg(seq, val)
        else:
            UiError("Unknow Message")

        for i, cmd in enumerate(self.cmd_list[:]):
            if cmd.seq() == seq:
                print("Cmd completed. {}".format(cmd))
                self.cmd_list.pop(i)
                break