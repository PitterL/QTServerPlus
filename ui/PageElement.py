from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem, TabbedPanelHeader
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.properties import BooleanProperty

from ui.WidgetExt import LayerBehavior, ActionEvent, ActionEventWrapper
from ui.TableElement import WidgetPageLayout
from ui.TableElement import WidgetPageContentRecycleElement
from ui.TableElement import WidgetPageContentTitleElement, WidgetPageContentDataElement
from ui.TableElement import WidgetRowTitleElement, WidgetRowElement, WidgetRowIndexElement, WidgetRowDataElement
from ui.TableElement import WidgetFieldElement, WidgetFieldLabelName, WidgetFieldLabelValue, WidgetFieldInputValue
from ui.TableElement import WidgetFieldIndexElement, WidgetFieldIndexName, WidgetFieldTitleName
from ui.TableElementT1 import WidgetT1PageContentTitleElement, WidgetT1PageContentDataElement
from ui.TableElementT1 import WidgetT1RowTitleElement, WidgetT1RowElement, WidgetT1FieldLabelValue
from ui.TableElementT1 import WidgetFieldT1IndexName

from server.devinfo import Page
from collections import OrderedDict

class WidgetPageElement(ActionEventWrapper, TabbedPanelItem):
    PAGE_CLS_LAYOUT_TABLE = {
        Page.OBJECT_TABLE: {
            # 'title': ("type", "address", "size", "instances", "report id"),
            'title': {
                'class_content': WidgetT1PageContentTitleElement,
                'class_row_elems': (WidgetT1RowTitleElement, WidgetRowIndexElement, WidgetRowDataElement),
                'class_idx_field': (WidgetFieldIndexElement, WidgetFieldTitleName, None),
                'class_data_field': (WidgetFieldElement, WidgetFieldTitleName, None)},
            'data': {
                'class_content': WidgetT1PageContentDataElement,
                'class_row_elems': (WidgetT1RowElement, WidgetRowIndexElement, WidgetRowDataElement),
                'class_idx_field': (WidgetFieldIndexElement, None, WidgetT1FieldLabelValue),
                'class_data_field': (WidgetFieldElement, None, WidgetT1FieldLabelValue)}
        },
        Page.ID_INFORMATION: {
            'title': {
                'class_content': WidgetPageContentTitleElement,
                'class_row_elems': (WidgetRowTitleElement, WidgetRowIndexElement, WidgetRowDataElement),
                'class_idx_field': (WidgetFieldIndexElement, WidgetFieldTitleName, None),
                'class_data_field': (WidgetFieldElement, WidgetFieldTitleName, None)},
            'data': {
                'class_content': WidgetPageContentDataElement,
                'class_row_elems': (WidgetRowElement, WidgetRowIndexElement, WidgetRowDataElement),
                'class_idx_field': (WidgetFieldIndexElement, WidgetFieldIndexName, None),
                'class_data_field': (WidgetFieldElement, WidgetFieldLabelName, WidgetFieldLabelValue)}
        },
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
                'class_data_field': (WidgetFieldElement,
                                        (WidgetFieldLabelName, {'exclusion':('TBD','User data', '')}),
                                        WidgetFieldInputValue)}
        }
    }

    @classmethod
    def get_cls_layout_kwargs(cls, id):
        if id in cls.PAGE_CLS_LAYOUT_TABLE.keys():
            kwargs = cls.PAGE_CLS_LAYOUT_TABLE[id]
        else:
            kwargs = cls.PAGE_CLS_LAYOUT_TABLE['default']

        return kwargs

    def __init__(self, page_mm):
        page_id = self._page_id = page_mm.id()
        parent_inst = page_mm.parent_inst()
        layout_kwargs = self.get_cls_layout_kwargs(page_id)
        tab_name = self.to_tab_name(page_id, parent_inst)

        print(self.__class__.__name__, "init_page", page_id, parent_inst, tab_name)
        super(WidgetPageElement, self).__init__(text=tab_name)

        self._content = WidgetPageLayout(page_id, layout_kwargs)
        self.add_widget(self._content)

        if page_mm.valid():
            self._content.create_page_content_widget(page_mm)

    def __str__(self):
        return super(WidgetPageElement, self).__str__() + "[id{}] ".format(self.id())

    def id(self):
        return self._page_id

    # def selected_id(self):
    #     return self.id()

    def to_tab_name(self, page_id, parent_inst):
        major, minor = page_id
        if parent_inst > 1:
            name = "{}".format(minor)
        else:
            name = "{}".format(major)
        return name

    def do_fresh(self, page_mm=None):
        self._content.do_fresh(page_mm)

    # def on_state(self, widget, value):
    #     print(self.__class__.__name__, "state", value)

    def on_action(self, inst, action):
        if inst is not self:
            #value = self.page_mm.raw_values()
            self.action = dict(source=self.__class__.__name__, page_id=self.id(), **action)

class WidgetPageMultiInstElement(ActionEvent, LayerBehavior, TabbedPanelItem):

    selected = BooleanProperty(False)

    def __init__(self, major, insts, **kwargs):
        self.major = major
        self.insts = insts
        super(WidgetPageMultiInstElement, self).__init__(text=str(major), **kwargs)
        #self.__pages_tab = {}

        # ActionEvent.__init__(self)
        # LayerBehavior.__init__(self)
        # TabbedPanelItem.__init__(self, text=str(major), **kwargs)

        self._content = self.ids['content']
        #print(self.__class__.__name__, "init", self)

    def __str__(self):
        return super(WidgetPageMultiInstElement, self).__str__() + "[id{}] [insts {}]: {}".format(self.id(), self.insts, self.get_layer_names())

    def id(self):
        return self.major

    # def selected_id(self):
    #     tab = self._content.get_current_tab()
    #     print(self.__class__.__name__, "selected_id", tab)
    #     if isinstance(tab, TabbedPanelHeader):
    #         page_id = (self.id(), 0)
    #         self._content.switch_to(self.get_element(page_id))
    #         print(self.__class__.__name__, self._content.get_current_tab())
    #         return page_id
    #     else:
    #         return tab.selected_id()

    def on_state(self, widget, value):
        #print(self.__class__.__name__, "state", value)
        if value == 'down':
            self.selected = True
            self.switch_tab()
        else:
            self.selected = False
    #
    # def set_default_page(self):
    #     if len(self._content.tab_list) == 1:
    #         self._content._switch_to_first_tab()

    def switch_tab(self, level=1):
        tab = self._content.get_current_tab()
        assert isinstance(tab, TabbedPanelHeader)
        if tab.content:
            tab.dispatch('on_release')
        else:
            if level > 0:
                level -= 1
                self._content._switch_to_first_tab()
                self.switch_tab(level)

        #if tab.content:
            #tab.content.dispatch('on_press')
        # page_id = (self.major, 0)
        # print(self.__class__.__name__, "on_page_selected", self.major, ",switch to first instance ")
        # w = self.get_page(page_id)
        # if w:
        #     self._content.switch_to(w)
        #     w.dispatch('on_press')
        #     # tab = self._content.get_current_tab()
        #     # tab.dispatch('on_press')

    def get_page(self, page_id):
        #return self.__pages_tab.get(page_id, None)
        return super(WidgetPageMultiInstElement, self).get_layer(page_id)

    def add_page(self, page_id, w_page):
        #self.__pages_tab[page_id] = w_page
        super(WidgetPageMultiInstElement, self).add_layer(page_id, w_page)
        super(WidgetPageMultiInstElement, self).action_bind(w_page)
        self._content.add_widget(w_page)

    def remove_page(self, page_id):
        w = self.remove_layer(page_id)
        if w:
            super(PageContext, self).action_unbind(w)
            self.remove_widget(w)

    def clear_pages(self):
        for name in super(PageContext, self).get_layer_names():
            w = super(PageContext, self).get_layer(name)
            super(PageContext, self).action_unbind(w)

        self.clear_widgets()

    def do_fresh(self, page_mm=None):
        page_id = page_mm.id()
        w = self.get_page(page_id)
        if w:
            w.do_fresh(page_mm)

class PageContext(ActionEvent, LayerBehavior, TabbedPanel):
    def __init__(self, **kwargs):
        super(PageContext, self).__init__(**kwargs)
        # LayerBehavior.__init__(self)
        # ActionEvent.__init__(self)
        # TabbedPanel.__init__(self, **kwargs)
        #self.__elems_tab = {}

    def get_element(self, elem_id):
        if isinstance(elem_id, tuple):
            major, _ = elem_id
        else:
            major = elem_id

        #w = self.__elems_tab.get(major)
        w = super(PageContext, self).get_layer(major)
        if w:
            if w.id() == elem_id:
                return w
            else:
                return w.get_page(elem_id)

    def add_layer(self, major, w_page):
        #self.__elems_tab[major_id] = w_pages
        super(PageContext, self).add_layer(major, w_page)
        super(PageContext, self).action_bind(w_page)
        self.add_widget(w_page)

    def remove_layer(self, major):
        w = super(PageContext, self).get_layer(major)
        if w:
            #del self.__elems_tab[major_id]
            super(PageContext, self).remove_layer(major)
            super(PageContext, self).action_unbind(w)
            self.remove_widget(w)

    def clear_layers(self, **kwargs):
        #self.__elems_tab.clear()
        #super(PageContext, self).clear_layer()
        for name in super(PageContext, self).get_layer_names():
            w = super(PageContext, self).get_layer(name)
            super(PageContext, self).action_unbind(w)

        self.clear_widgets(**kwargs)

    def create_page_element(self, page_mm):
        parent_inst = page_mm.parent_inst()
        major, _ = page_id = page_mm.id()
        print(self.__class__.__name__, "create page element", page_id, parent_inst)
        if parent_inst > 1:
            parent_widget = self.get_element(major)
            if not parent_widget:
                parent_widget = WidgetPageMultiInstElement(major, parent_inst)
                self.add_layer(major, parent_widget)
            widget = WidgetPageElement(page_mm)
            parent_widget.add_page(page_id, widget)
        else:
            widget = WidgetPageElement(page_mm)
            self.add_layer(major, widget)

        return widget

    def get_current_page_id(self):
        w = super(PageContext, self).get_current_tab()
        if isinstance(w, WidgetPageMultiInstElement):
            w = w._content.get_current_tab()

        if isinstance(w, WidgetPageElement):
            print(self.__class__.__name__, "get_current_page_id",  w.id())
            return w.id()

    def switch_tab(self, level=1):
        tab = self.get_current_tab()
        assert isinstance(tab, TabbedPanelHeader)
        if tab.content:
            tab.dispatch('on_release')
        else:
            if level > 0:
                level -= 1
                self._switch_to_first_tab()
                self.switch_tab(level)


                        # def set_default_page(self):
    #     if len(self.tab_list) == 1:
    #         self._switch_to_first_tab()
    # def set_default_page(self, tab):
    #     tab = self.get_current_tab():
    #         self.switch_to(tab)

    # def switch_to_page(self, page_id):
    #     major, _ = page_id
    #     w = super(PageContext, self).get_layer(major)
    #     if w:
    #         self.switch_to(w)
    #         #tab = self.get_current_tab()
    #         w.dispatch('on_press')

if __name__ == '__main__':

    import array, os
    from kivy.app import App
    from tools.mem import ChipMemoryMap

    from MainUi import MainUi
    MainUi.load_ui_kv_file(os.curdir)

    class PageElementApp(App):

        def build(self):

            root = PageContext()

            v_chip_id = array.array('B', [164, 24, 16, 170, 32, 20, 40])
            chip = ChipMemoryMap.get_chip_mmap(v_chip_id)
            page_mmap = chip.get_mem_map_tab(Page.ID_INFORMATION)
            #root.create_page_element(page_mmap)

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
            #root.create_page_element(page_mmap)

            def sort_key(mm):
                major, inst = mm.id()
                if isinstance(major, str):
                    result = (ord(major) - ord('z') - 1, inst)
                else:
                    result = (major, inst)

                #print("sort_key", result)
                return result

            chip.create_chip_mmap_pages()
            page_mmaps = chip.get_mem_map_tab()
            for mmap in sorted(page_mmaps.values(), key=sort_key):
                page_id = mmap.id()
                widget = root.get_element(page_id)
                if not widget:
                    if not mmap.valid():
                        value = array.array('B', range(mmap.get_value_size()))
                        mmap.set_values(value)
                    widget = root.create_page_element(mmap)
                    widget.do_fresh(mmap)

            Clock.schedule_once(lambda dt: root.switch_tab())
            return root

    PageElementApp().run()