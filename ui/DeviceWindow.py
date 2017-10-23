import kivy
kivy.require('1.0.6') # replace with your current kivy version !

#from kivy.lang import Builder

from kivy.uix.boxlayout import BoxLayout

from server.message import Message, UiMessage, Token
from server.devinfo import Page

from tools.mem import ChipMemoryMap
#from ui.PageElement import PageElementRoot, WidgetPageElement
from ui.PageElement import WidgetPageElement

class WinError(Exception):
    "Message error exception class type"
    pass

class DeviceWindow(BoxLayout):
    CMD_STACK_DEPTH = 1
    (UP_CONTROL_BAR, DOWN_CONTROL_BAR, LEFT_CONTROL_BAR, right_CONTROL_BAR, PAGE_ELEMENT) = ("up", 'down', 'left', 'right', 'center')

    def __init__(self, id, *args, **kwargs):
        self.__id = id
        self.cmd_seq = 0
        self.cmd_list = []
        self.object_table = {}
        self.chip = None
        self.__layout = {}

        super(DeviceWindow, self).__init__(*args, **kwargs)

    def __str__(self):
        return super(DeviceWindow, self).__str__() + '(' + self.id() + ')'

    def get_layout(self, name):
        return self.__layout.get(name, None)

    def add_layout(self, name, widget):
        self.__layout[name] = widget
        self.add_widget(widget)

    def clear_layout(self):
        #print(self.__class__.__name__, "clear layout", self.__layout)
        self.__layout.clear()
        self.clear_widgets()

    def get_element(self, element_id):
        return self.ids[DeviceWindow.PAGE_ELEMENT].get_element(element_id)

    def add_element(self, widget):
        self.ids[DeviceWindow.PAGE_ELEMENT].add_element(widget)

    def clear_elements(self):
        self.ids[DeviceWindow.PAGE_ELEMENT].clear_elements

    def set_default_element(self, widget):
        self.ids[DeviceWindow.PAGE_ELEMENT].set_default_element(widget)

    def id(self):
        return self.__id

    def match_seq(self, token):
        return self.cmd_seq == token[-1]

    def next_seq(self):
        self.cmd_seq += 1
        return Token(self.cmd_seq)

    def prepare_command(self, msg):
        if len(self.cmd_list) >= self.CMD_STACK_DEPTH:
            WinError("command still in process {}", self.cmd_list)
            self.cmd_list.pop()

        self.cmd_list.append(msg)

    def send_command_to(self, pipe):
        for cmd in self.cmd_list:
            cmd.send_to(pipe)

    def create_page_element(self, page):
        if not self.chip:
            chip_id = page.buf()
            self.chip = ChipMemoryMap.get_chip_mmap(chip_id)

        print(self.__class__.__name__, self.chip, "create page <{}>".format(page))

        if not self.chip:
            return

        #print(self.__class__.__name__, self.chip.get_mmap())

        page_mm = self.chip.get_mmap(page.id())
        w_page = WidgetPageElement(page_mm)
        w_page.bind(on_press=self.on_page_selected)
        self.add_element(w_page)
        return w_page

    def create_default_pages_element(self):
        if not self.chip:
            return

        def sort_key(mm):
            major, inst = mm.id()
            if isinstance(major, str):
                result = (ord(major) - ord('z') - 1, inst)
            else:
                result = (major, inst)

            return result

        self.chip.create_default_mmap_pages()
        all_page_mmaps = self.chip.get_mmap()
        for mmap in sorted(all_page_mmaps.values(), key=sort_key):
            #if mmap.parent_inst():
            if mmap.instance_id() == 0:
                widget = self.get_element(mmap.id())
                if not widget:
                    w_page = WidgetPageElement(mmap)
                    w_page.bind(on_press=self.on_page_selected)
                    self.add_element(w_page)

        self.set_default_element(Page.ID_INFORMATION)

    def distory_page_element(self):
        self.clear_elements()

    def update_page_element(self, page):
        page_id = page.id()
        widget = self.get_element(page_id)
        if not widget:
            widget = self.create_page_element(page)

        if widget:
            page_mm = self.chip.get_mmap(page.id())
            if page_mm:
                page_mm.set_values(page.buf())
                widget.do_fresh(page_mm)

    def on_page_selected(self, instance):
        print(instance)
        page_id = instance.id()
        page_mm = self.chip.get_mmap(page_id)
        if not page_mm.valid():
            kwargs = {'page_id': page_id, 'discard': True}
            command = UiMessage(Message.CMD_DEVICE_PAGE_READ, self.id(), self.next_seq(), **kwargs)
            self.prepare_command(command)

    def handle_attach_msg(self, data):
        #self.prepare_command(Message(Message.CMD_POLL_DEVICE_DEVICE, self.id(), self.next_seq()))
        pass

    def handle_connected_msg(self, attached):
        print("{} connect {}".format(self.__class__.__name__, attached))

        if attached:
            kwargs = {'page_id': Page.ID_INFORMATION, 'discard': False}
            command = UiMessage(Message.CMD_DEVICE_PAGE_READ, self.id(), self.next_seq(), **kwargs)
            self.prepare_command(command)
        else:
            self.chip = None

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
            self.create_default_pages_element()
        #if page_id not in self.page_tabs.keys():
        #    tab = PageTab(page)
        #    self.page_tabs[page_id] = tab
        #    self.add_widget(tab)


        #self.ids["message"] == "Page {} read: {}".format(page.id(), str(page))
        #self.ids.message.text = str(page)

    def handle_page_write_msg(self, data):
        self.ids["message"] == "Page write: {}".format(data)

    def hand_nak_msg(self, msg):
        print(self.__class__.__name__, "NAK: ", msg)

    def handle_message(self, msg):
        type = msg.type()
        seq = msg.seq()
        val = msg.value()

        print("Process<{}> get message: {}".format(self.__class__.__name__, msg))

        if type == Message.MSG_DEVICE_ATTACH:
            self.handle_attach_msg(val)
        elif type == Message.MSG_DEVICE_CONNECTED:
            self.handle_connected_msg(val)
        elif type == Message.MSG_DEVICE_PAGE_READ:
            self.handle_page_read_msg(val)
        elif type == Message.MSG_DEVICE_PAGE_WRITE:
            self.handle_page_write_msg(val)
        elif type == Message.MSG_DEVICE_NAK:
            self.hand_nak_msg(msg)
        else:
            UiError("Unknow Message")

        for i, cmd in enumerate(self.cmd_list[:]):
            if cmd.seq() == seq:
                print("Cmd completed. {}".format(cmd))
                self.cmd_list.pop(i)
                break

if __name__ == '__main__':
    import array
    from kivy.app import App
    from tools.mem import ChipMemoryMap
    #from ui.PageElement import PageElementApp

    class DeviceWindowApp(App):

        def build(self):
            root = DeviceWindow("test")
            return root

    DeviceWindowApp().run()