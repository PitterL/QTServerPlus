from kivy.uix.floatlayout import FloatLayout
from kivy.uix.layout import Layout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.tabbedpanel import TabbedPanelHeader, TabbedPanelItem

from ui.WidgetExt import ActionEvent, LayerActionWrapper, LayerBoxLayout
from ui.WidgetExt import LayerBehavior, ActionEvent, ActionEventWrapper
from ui.TableElement import WidgetPageLayout
from ui.TableElement import WidgetPageContentRecycleElement
from ui.TableElement import WidgetPageContentTitleElement, WidgetPageContentDataElement
from ui.TableElement import WidgetRowTitleElement, WidgetRowElement, WidgetRowIndexElement, WidgetRowDataElement
from ui.TableElement import WidgetFieldElement, WidgetFieldLabelName, WidgetFieldLabelValue, WidgetFieldInputValue
from ui.TableElement import WidgetFieldIndexElement, WidgetFieldIndexName, WidgetFieldTitleName
from ui.PageElement import WidgetPageMultiInstElement

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

from ui.PageElement import PageContext, WidgetPageMultiInstElement, WidgetPageElement, WidgetPageLayout
class WidgetRepoElement(ActionEventWrapper, TabbedPanelItem):
    PAGE_CLS_LAYOUT_TABLE = {
        'default': {
            'title': {
                'class_content': WidgetPageContentTitleElement,
                'class_row_elems': (WidgetRowTitleElement, WidgetRowIndexElement, WidgetRowDataElement),
                'class_idx_field': (WidgetFieldIndexElement, WidgetFieldTitleName, None),
                'class_data_field': (WidgetFieldElement, WidgetFieldTitleName, None)},
            'data': {
                'class_content': WidgetPageContentDataElement,
                'class_row_elems': (WidgetRowElement, WidgetRowIndexElement, WidgetRowDataElement),
                'class_idx_field': (WidgetFieldIndexElement, WidgetFieldIndexName, None),
                'class_data_field': (WidgetFieldElement, WidgetFieldLabelName, None)}
        }
    }

    @classmethod
    def get_cls_layout_kwargs(cls, id):
        if id in cls.PAGE_CLS_LAYOUT_TABLE.keys():
            kwargs = cls.PAGE_CLS_LAYOUT_TABLE[id]
        else:
            kwargs = cls.PAGE_CLS_LAYOUT_TABLE['default']

        return kwargs

    def __init__(self, repo_mm):
        repo_id = repo_mm.id()
        repo_range = repo_mm.report_range()
        einfo = repo_mm.extra_info()
        layout_kwargs = self.get_cls_layout_kwargs(repo_id)
        tab_name = self.to_tab_name(repo_id, repo_range, einfo)

        print(self.__class__.__name__, "init_repo", repo_id, repo_range, tab_name)
        super(WidgetRepoElement, self).__init__(text=tab_name)

        self._content = WidgetPageLayout(repo_id, layout_kwargs)
        self.add_widget(self._content)

        #if page_mm.valid():
        self._content.create_page_content_widget(repo_mm)

    def to_tab_name(self, repo_id, repo_range, einfo):
        if einfo:
            return str(repo_id)
        else:
            st, end = repo_range
            if st != end:
                name = "{}-{}".format(st, end)
            else:
                name = "{}".format(st)
            return name


class WidgetRepoMultiInstElement(WidgetPageMultiInstElement):
    def switch_tab(self):
        tab = self._content.get_current_tab()
        if isinstance(tab, TabbedPanelHeader):
            page_id = (self.major, 0)
            print(self.__class__.__name__, "on_page_selected", self.major, ",switch to first instance ")
            w = self.get_page(page_id)
            if w:
                self._content.switch_to(w)
                w.dispatch('on_press')
                # tab = self._content.get_current_tab()
                # tab.dispatch('on_press')

class MessageView(PageContext):
    @staticmethod
    def register_message_view():
        return MessageView()

    def create_repo_element(self, repo_mm):
        report_id = repo_mm.id()
        repo_range = repo_mm.report_range()
        page_id = repo_mm.page_id()
        print(self.__class__.__name__, "create repo element", page_id, report_id, repo_range)
        st, end = repo_range
        major, _ = page_id
        num_reports = end - st + 1
        if num_reports > 1:
            parent_widget = self.get_element(major)
            if not parent_widget:
                parent_widget = WidgetPageMultiInstElement(major, repo_range)
                self.add_layer(major, parent_widget)
            widget = WidgetRepoElement(repo_mm)
            parent_widget.add_page(report_id, widget)
        else:
            widget = WidgetRepoElement(repo_mm)
            self.add_layer('R'+ str(report_id), widget)

        return widget

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
            for page_id, repo_range in report_table.items():
                major, minor = page_id
                st, end = repo_range
                if minor == 0:  #only need inst 0 report list
                    for repo_id in range(st, end + 1):
                        repo_mm = chip.get_msg_map_tab(repo_id)
                        if repo_mm:
                            einfo = repo_mm.extra_info()
                            if st == repo_id or einfo:
                                root.create_repo_element(repo_mm)
            return root


    MessageViewApp().run()