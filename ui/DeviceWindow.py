import kivy
kivy.require('1.0.6') # replace with your current kivy version !

#from kivy.lang import Builder

from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock

from server.message import Message, UiMessage, Token
from server.devinfo import Page

from tools.mem import ChipMemoryMap
#from ui.PageElement import PageContext, WidgetPageElement
#from ui.PageElement import WidgetPageElement
#from ui.PageControlBar import UpControlBar, DownControlBar, LeftControlBar, RightControlBar, CenterContentBar
#from ui.DeviceControlBar import UpControlBar, DownControlBar

from ui.DebugView import DebugView
from ui.MessageView import MessageView
from ui.WidgetExt import Action, ActionEventWrapper
from ui.WidgetExt import KeyboardShotcut

class WinError(Exception):
    "Message error exception class type"
    pass

class DeviceWindow(ActionEventWrapper, RelativeLayout):
    CMD_STACK_DEPTH = 10
    (UP_CONTROL_BAR, DOWN_CONTROL_BAR, LEFT_CONTROL_BAR, right_CONTROL_BAR, CENTER_CONTENT_BAR) = ("up", 'down', 'left', 'right', 'center')
    DEFAULT_MESSAGE_SIZE = 11

    def __init__(self, id, *args, **kwargs):
        self.__id = id
        self.cmd_seq = 0
        self.cmd_list = []
        self.object_table = {}
        self.chip = None
        #self.__layout = {}
        self.message_size = self.DEFAULT_MESSAGE_SIZE

        super(DeviceWindow, self).__init__(*args, **kwargs)

        self._keyboard = KeyboardShotcut(win=self)
        self._center = self.ids[DeviceWindow.CENTER_CONTENT_BAR]
        self._center.bind(action=self.on_action)
        self._dbg_view = DebugView.register_debug_view()
        self._msg_view = MessageView.register_message_view()

    def __str__(self):
        return super(DeviceWindow, self).__str__() + '(' + self.id() + ')'

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

        #print(self.__class__.__name__, msg, self.cmd_list)
        self.cmd_list.append(msg)

    def prepare_debug_command(self):
        if self._dbg_view:
            value = self._dbg_view.pop_data()
            if value:
                kwargs = {'value': value}
                command = UiMessage(Message.CMD_DEVICE_RAW_DATA, self.id(), self.next_seq(), **kwargs)
                self.prepare_command(command)

    def send_command_to(self, pipe):
        if len(self.cmd_list):
            busy = any([cmd.is_status(cmd.SEND) for cmd in self.cmd_list])
            print(self.__class__.__name__,self.cmd_list, busy)
            if busy:
                print(self.__class__.__name__,"send_command busy", self.cmd_list)
            else:
                self.cmd_list[0].send_to(pipe)

    def process_command(self, pipe):
        self.prepare_debug_command()
        self.send_command_to(pipe)

    def create_chip(self, page_cache):
        page_id = page_cache.id()
        if page_id == Page.ID_INFORMATION:
            self.chip = ChipMemoryMap.get_chip_mmap(page_cache.buf())

    def get_element(self, elem_id):
        return self._center.get_element(elem_id)

    def create_page_element(self, page_id):
        if not self.chip:
            return

        #print(self.__class__.__name__, self.chip, "create page {}".format(page_id))

        page_mm = self.chip.get_mem_map_tab(page_id)
        if page_mm:
            widget = self._center.create_page_element(page_mm)
            widget.bind(on_press=self.on_page_selected)
            return widget

    def create_msg_view_element(self):
        def sort_key(repo):
            (major, minor), (st, end) = repo
            if isinstance(major, str):
                result = (ord(major) - ord('z') - 1, inst)
            else:
                result = (major, minor, st, end)

            # print("sort_key", result)
            return result

        report_table = self.chip.get_reg_reporer()
        for page_id, repo_range in sorted(report_table.items(), key=sort_key):
            major, minor = page_id
            st, end = repo_range
            if minor == 0:  # only need inst 0 report list
                repo_insts = []
                for repo_id in range(st, end + 1):
                    repo_mm = self.chip.get_msg_map_tab(repo_id)
                    if repo_mm:
                        repo_insts.append(repo_mm)
                self._msg_view.create_repo_element(repo_insts)

        mmap = self.chip.get_msg_map_tab()
        self._msg_view.set_repo_mmap_tab(mmap)

    def create_chip_pages_element(self):
        def sort_key(mm):
            major, inst = mm.id()
            if isinstance(major, str):
                result = (ord(major) - ord('z') - 1, inst)
            else:
                result = (major, inst)

            return result

        if not self.chip:
            return

        self.chip.create_chip_mmap_pages()
        page_mmaps = self.chip.get_mem_map_tab()
        # first_page_id = None
        for mmap in sorted(page_mmaps.values(), key=sort_key):
            page_id = mmap.id()
            # if not first_page_id:
            #     first_page_id = page_id
            widget = self.get_element(page_id)
            if not widget:
                self.create_page_element(page_id)
                #print(self.__class__.__name__, "create_page_element", widget)

        #get T5 message size
        mmap = self.chip.get_msg_map_tab((5, 0))
        if mmap:
            self.message_size = len(mmap)

        #self._center.switch_to_page(Page.ID_INFORMATION)
        #self._center.set_default_page()
        Clock.schedule_once(lambda dt: self._center.switch_tab())

    def distory_page_element(self):
        self.clear_elements()

    def update_page_value(self):
        page_mm = self.chip.get_mem_map_tab(page_id)
        if page_mm:
            page_mm.set_values(page_cache.buf())

    def update_page_element(self, page_cache):
        if not self.chip:
            return

        page_id = page_cache.id()
        # if not self.chip and page_id == Page.ID_INFORMATION:
        #     self.create_chip(page_cache)
        if page_id == (Page.OBJECT_TABLE):
            print(self.__class__.__name__, "OBJECT_TABLE", page_cache.buf())

        page_mm = self.chip.get_mem_map_tab(page_id)
        if page_mm:
            page_mm.set_values(page_cache.buf())
            w = self.get_element(page_id)
            if w:
                w.do_fresh(page_mm)

        #widget = self.get_element(page_id)
        # if not widget:
        #     widget = self.create_page_element(page_id)

        #if widget:
            #print(self.__class__.__name__, "update", widget, page_cache.buf())

    def on_page_selected(self, instance):
        print(self.__class__.__name__, "on_page_selected", instance)

        page_id = instance.id()
        page_mm = self.chip.get_mem_map_tab(page_id)
        if not page_mm:
            return

        if not page_mm.valid():
            kwargs = {'page_id': page_id, 'discard': True}
            command = UiMessage(Message.CMD_DEVICE_PAGE_READ, self.id(), self.next_seq(), **kwargs)
            self.prepare_command(command)

    def on_action(self, inst, act):
        print(self.__class__.__name__, inst, act)

        action = Action.parse(act)
        if action.is_event('value'):
            page_id = action.get('page_id')
            if not page_id:
                #page_id = self._center.tab = self._center.get_current_page_id()
                page_id = self._center.get_current_page_id()

            if page_id:
                page_mm = self.chip.get_mem_map_tab(page_id)
                if page_mm:
                    if action.is_op('w'):
                        t = Message.CMD_DEVICE_PAGE_WRITE
                        value = page_mm.raw_values()
                        kwargs = {'page_id': page_id, 'value': value}
                    else:
                        t = Message.CMD_DEVICE_PAGE_READ
                        kwargs = {'page_id': page_id}
                    command = UiMessage(t, self.id(), self.next_seq(), **kwargs)
                    self.prepare_command(command)
        elif action.is_event('prop'):
            pass

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

    def handle_page_read_msg(self, page_cache):
        if not page_cache:
            return

        self.update_page_element(page_cache)

        page_id = page_cache.id()
        if page_id == Page.ID_INFORMATION:
            self.create_chip(page_cache)
            kwargs = {'page_id': Page.OBJECT_TABLE, 'discard': False}
            command = UiMessage(Message.CMD_DEVICE_PAGE_READ, self.id(), self.next_seq(), **kwargs)
            self.prepare_command(command)
        elif page_id == Page.OBJECT_TABLE:
            self.create_chip_pages_element()
            self.create_msg_view_element()

    def handle_page_write_msg(self, page):
        #self.ids["message"] == "Page write: {}".format(data)
        print(self.__class__.__name__, "page write done", page.id())

    def handle_dbg_msg(self, data):
        if self._dbg_view:
            self._dbg_view.handle_data(data)

    def handle_raw_data_msg(self, data):
        self.handle_dbg_msg(data)

    def handle_interrupt_data_msg(self, data):
        if not self.chip:
            print(self.__class__.__name__, "chip is removed with interrupt data:", data)
            return

        if self._msg_view:
            self._msg_view.handle_data(data[:self.message_size])

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
        elif type == Message.MSG_DEVICE_RAW_DATA:
            self.handle_raw_data_msg(val)
        elif type == Message.MSG_DEVICE_INTERRUPT_DATA:
            self.handle_interrupt_data_msg(val)
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
    from kivy.app import App
    from kivy.lang import Builder
    import array
    import os

    from MainUi import MainUi
    from server.devinfo import Page, MemMapStructure
    from ui.WidgetExt import KeyboardShotcut

    MainUi.load_ui_kv_file(os.curdir)
    KeyboardShotcut()

    class DeviceWindowApp(App):

        def __init__(self, root_widget=None):
            super(DeviceWindowApp, self).__init__()
            if root_widget:
                self.root = root_widget

    #1066T2
    #v_chip_id = array.array('B', [164, 24, 16, 170, 32, 20, 40])
    # v_block_info = array.array('B',
    #                   [117, 250, 0, 214, 5, 0, 37, 4, 6, 129, 0, 0, 44, 134, 6, 0, 0, 0, 5, 135, 6, 10, 0, 0, 6, 146, 6, 6,
    #                    0, 1, 68, 153, 6, 72, 0, 1, 38, 226, 6, 63, 0, 0, 71, 34, 7, 199, 0, 0, 110, 234, 7, 39, 8, 0, 118,
    #                    82, 9, 2, 0, 1, 7, 85, 9, 4, 0, 0, 8, 90, 9, 14, 0, 0, 15, 105, 9, 10, 1, 1, 18, 127, 9, 1, 0, 0, 19,
    #                    129, 9, 15, 0, 1, 24, 145, 9, 18, 0, 4, 25, 164, 9, 21, 0, 1, 27, 186, 9, 6, 0, 1, 40, 193, 9, 4, 0,
    #                    0, 42, 198, 9, 12, 0, 0, 46, 211, 9, 11, 0, 1, 47, 223, 9, 45, 0, 0, 56, 13, 10, 35, 0, 1, 61, 49,
    #                    10, 4, 5, 1, 65, 79, 10, 22, 2, 1, 70, 148, 10, 9, 19, 1, 72, 92, 11, 84, 0, 1, 77, 177, 11, 1, 0, 0,
    #                    78, 179, 11, 11, 0, 0, 79, 191, 11, 3, 2, 0, 80, 203, 11, 11, 0, 1, 84, 215, 11, 3, 0, 1, 100, 219,
    #                    11, 59, 0, 18, 101, 23, 12, 29, 0, 0, 104, 53, 12, 10, 0, 0, 108, 64, 12, 74, 0, 1, 109, 139, 12, 8,
    #                    0, 1, 111, 148, 12, 26, 2, 0, 112, 229, 12, 4, 1, 1, 113, 239, 12, 2, 0, 0])
    #641T-AT
    #v_chip_id = array.array('B', [164, 17, 32, 170, 24, 14, 31])
    # v_block_info = array.array('B',
    #       [37, 196, 0, 129, 0, 0, 44, 70, 1, 0, 0, 0, 5, 71, 1, 10, 0, 0, 6, 82, 1, 6, 0, 1, 38, 89, 1, 63, 0, 0, 71,
    #        153, 1, 199, 0, 0, 110, 97, 2, 27, 8, 0, 7, 93, 3, 4, 0, 0, 8, 98, 3, 14, 0, 0, 15, 113, 3, 10, 0, 1, 18,
    #        124, 3, 1, 0, 0, 19, 126, 3, 5, 0, 1, 25, 132, 3, 14, 0, 1, 42, 147, 3, 12, 0, 0, 46, 160, 3, 11, 0, 1, 47,
    #        172, 3, 46, 0, 0, 56, 219, 3, 27, 0, 1, 61, 247, 3, 4, 5, 1, 65, 21, 4, 22, 2, 1, 70, 90, 4, 9, 19, 1, 72,
    #        34, 5, 88, 0, 1, 77, 123, 5, 1, 0, 0, 78, 125, 5, 11, 0, 0, 80, 137, 5, 13, 0, 1, 100, 151, 5, 61, 0, 12,
    #        101, 213, 5, 31, 0, 0, 104, 245, 5, 10, 0, 0, 108, 0, 6, 74, 0, 1, 109, 75, 6, 8, 0, 1, 111, 84, 6, 29, 2, 0,
    #        113, 174, 6, 2, 0, 0])
    #449T-AT
    v_chip_id = array.array('B', [164, 25, 16, 170, 32, 20, 40])
    v_block_info = array.array('B',
          [117, 250, 0, 214, 5, 0, 37, 4, 6, 129, 0, 0, 44, 134, 6, 0, 0, 0, 5, 135, 6, 10, 0, 0, 6, 146, 6, 6, 0, 1,
           68, 153, 6, 72, 0, 1, 38, 226, 6, 63, 0, 0, 71, 34, 7, 199, 0, 0, 110, 234, 7, 39, 8, 0, 118, 82, 9, 2, 0, 1,
           7, 85, 9, 4, 0, 0, 8, 90, 9, 14, 0, 0, 15, 105, 9, 10, 1, 1, 18, 127, 9, 1, 0, 0, 19, 129, 9, 15, 0, 1, 24,
           145, 9, 18, 0, 4, 25, 164, 9, 21, 0, 1, 27, 186, 9, 6, 0, 1, 40, 193, 9, 4, 0, 0, 42, 198, 9, 12, 0, 0, 46,
           211, 9, 11, 0, 1, 47, 223, 9, 45, 0, 0, 56, 13, 10, 35, 0, 1, 61, 49, 10, 4, 5, 1, 65, 79, 10, 22, 2, 1, 70,
           148, 10, 9, 19, 1, 72, 92, 11, 84, 0, 1, 77, 177, 11, 1, 0, 0, 78, 179, 11, 11, 0, 0, 79, 191, 11, 3, 2, 0,
           80, 203, 11, 11, 0, 1, 84, 215, 11, 3, 0, 1, 100, 219, 11, 59, 0, 18, 101, 23, 12, 29, 0, 0, 104, 53, 12, 10,
           0, 0, 108, 64, 12, 74, 0, 1, 109, 139, 12, 8, 0, 1, 111, 148, 12, 26, 2, 0, 112, 229, 12, 4, 1, 1, 113, 239,
           12, 2, 0, 0])

    #root window
    root = DeviceWindow('test window')

    #data cache
    mm =  MemMapStructure()

    #page 0
    page_cache = mm.get_page(Page.ID_INFORMATION)
    page_cache.save_to_buffer(0, v_chip_id)
    mm.page_parse(page_cache.id())

    #page 1
    page_cache = mm.get_page(Page.OBJECT_TABLE)
    page_cache.save_to_buffer(0, v_block_info)
    mm.page_parse(page_cache.id())

    msg_list = [Message('local', Message.MSG_DEVICE_PAGE_READ, Page.ID_INFORMATION, root.next_seq(),
                      value=mm.get_page(Page.ID_INFORMATION)),
                Message('local', Message.MSG_DEVICE_PAGE_READ, Page.OBJECT_TABLE, root.next_seq(),
                        value=mm.get_page(Page.OBJECT_TABLE))]
    #page x
    page_id_list = [(7,0), (6,0), (37,0),(38, 0), (8,0), (15,0), (15, 1), (100, 0)]
    #page_id_list = []
    for page_id in page_id_list:
        page_cache = mm.get_page(page_id)
        if page_cache:
            cache = array.array('B', range(page_cache.length))
            page_cache.save_to_buffer(0, cache)

            #enumulate message
            msg_list.append(Message('local', Message.MSG_DEVICE_PAGE_READ, page_id, root.next_seq(),
                                value=mm.get_page(page_id)))
    #enumulate message
    for msg in msg_list:
        root.handle_message(msg)

    cmd_list = [dict(name = 'selected', value = 'All', target = 'reg_all', widget = 'WidgetMsgRegAllButton')]

    for cmd in cmd_list:
        root._msg_view.cast(**cmd)

    report_list =  [
                    # Message('msg', Message.MSG_DEVICE_INTERRUPT_DATA, 'dev', root.next_seq(),
                    #     value=array.array('B', [36, 16, 2, 2, 1, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0,])),
                    # Message('msg', Message.MSG_DEVICE_INTERRUPT_DATA, 'dev', root.next_seq(),
                    #     value=array.array('B', [50, 16, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ])),
                    # Message('msg', Message.MSG_DEVICE_INTERRUPT_DATA, 'dev', root.next_seq(),
                    #     value=array.array('B', [49, 21, 230, 1, 40, 1, 129, 0, 0, 0])),
                    # Message('msg', Message.MSG_DEVICE_INTERRUPT_DATA, 'dev', root.next_seq(),
                    #     value=array.array('B', [49, 145, 230, 1, 40, 1, 129, 0, 0, 0])),
                    Message('msg', Message.MSG_DEVICE_INTERRUPT_DATA, 'dev', root.next_seq(),
                        value=array.array('B', [12, 32, 26, 17, 53, 243, 179,1, 0, 0, 0]))]
    for msg in report_list:
        root.handle_message(msg)


    #start ui
    app = DeviceWindowApp(root)
    app.run()