from kivy.uix.floatlayout import FloatLayout
from kivy.uix.layout import Layout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton

from ui.WidgetExt import ActionEvent, LayerActionWrapper, LayerBoxLayout

class WidgetMsgCtrlButton(ActionEvent, ToggleButton):
    def __init__(self, name):
        super(WidgetMsgCtrlButton, self).__init__()
        self.text = name

    def on_state(self, inst, value):
        print(self.__class__.__name__, inst, value)
        self.action = {'name':'ctrl', 'id': self.text, 'state':value}

    def on_focus(self, inst, value):
        print(self.__class__.__name__, inst, value)

class MessageSettingBar(LayerBoxLayout):
    CTRL_LIST = ("Setting", "Raw")
    def __init__(self, name):
        super(MessageSettingBar, self).__init__()
        for name in self.CTRL_LIST:
            self.add_layer(name, WidgetMsgCtrlButton(name))

class MessageContentElement(LayerActionWrapper, Label):

    def __init__(self):
        super(MessageContentElement, self).__init__()

# class MessageView(LayerBoxLayout):
#     def __init__(self):
#         super(MessageView, self).__init__()
#         self.add_layer('setting', MessageSettingBar())
        self.add_layer('setting', MessageContentElement())

from ui.PageElement import PageContext
class MessageView(object):
    @staticmethod
    def register_message_view():
        return PageContext()

if __name__ == '__main__':
    import array, os
    from kivy.app import App
    from kivy.lang import Builder
    from tools.mem import ChipMemoryMap, Page

    #from kivy.modules import inspector
    #from kivy.core.window import Window

    from MainUi import MainUi
    MainUi.load_ui_kv_file(os.curdir)

    class MessageViewApp(App):

        def build(self):
            #root = MessageView()
            #inspector.create_inspector(Window, root)
            #return root

            root = MessageView.register_message_view()
            v_chip_id = array.array('B', [164, 24, 16, 170, 32, 20, 40])
            chip = ChipMemoryMap.get_chip_mmap(v_chip_id)
            # page_mmap = chip.get_mem_map_tab(Page.ID_INFORMATION)
            # root.create_page_element(page_mmap)

            v_block_info = array.array('B',
                  [117, 250, 0, 214, 5, 0, 37, 4, 6, 129, 0, 0, 44, 134, 6, 0, 0, 0, 5, 135, 6, 10, 0, 0, 6, 146, 6, 6,
                   0, 1, 68, 153, 6, 72, 0, 1, 38, 226, 6, 63, 0, 0, 71, 34, 7, 199, 0, 0, 110, 234, 7, 39, 8, 0, 118,
                   82, 9, 2, 0, 1, 7, 85, 9, 4, 0, 0, 8, 90, 9, 14, 0, 0, 15, 105, 9, 10, 1, 1, 18, 127, 9, 1, 0, 0, 19,
                   129, 9, 15, 0, 1, 24, 145, 9, 18, 0, 4, 25, 164, 9, 21, 0, 1, 27, 186, 9, 6, 0, 1, 40, 193, 9, 4, 0,
                   0, 42, 198, 9, 12, 0, 0, 46, 211, 9, 11, 0, 1, 47, 223, 9, 45, 0, 0, 56, 13, 10, 35, 0, 1, 61, 49,
                   10, 4, 5, 1, 65, 79, 10, 22, 2, 1, 70, 148, 10, 9, 19, 1, 72, 92, 11, 84, 0, 1, 77, 177, 11, 1, 0, 0,
                   78, 179, 11, 11, 0, 0, 79, 191, 11, 3, 2, 0, 80, 203, 11, 11, 0, 1, 84, 215, 11, 3, 0, 1, 100, 219,
                   11, 59, 0, 18, 101, 23, 12, 29, 0, 0, 104, 53, 12, 10, 0, 0, 108, 64, 12, 74, 0, 1, 109, 139, 12, 8,
                   0, 1, 111, 148, 12, 26, 2, 0, 112, 229, 12, 4, 1, 1, 113, 239, 12, 2, 0, 0])

            page_mmap = chip.get_mem_map_tab(Page.OBJECT_TABLE)
            page_mmap.set_values(v_block_info)
            chip.create_chip_mmap_pages()
            #root.create_page_element(page_mmap)
            report_table = chip.get_reg_reporer()
            for v in report_table.values():
                repo = chip.get_msg_map_tab(v[0])
                if repo:
                    root.create_page_element(repo)

            return root


    MessageViewApp().run()