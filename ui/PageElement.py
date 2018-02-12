# from kivy.uix.gridlayout import GridLayout
#from kivy.uix.boxlayout import BoxLayout
#from kivy.uix.stacklayout import StackLayout
#from kivy.uix.label import Label
# from kivy.uix.button import Button
#from kivy.uix.behaviors import FocusBehavior
#from kivy.graphics import Color, Rectangle
# from kivy.uix.textinput import TextInput
#from kivy.uix.widget import Widget
#from kivy.uix.scrollview import ScrollView

#from kivy.uix.recycleview import RecycleView
#from kivy.uix.recycleview.views import RecycleDataViewBehavior
#from kivy.uix.label import Label
#from kivy.uix.recycleboxlayout import RecycleBoxLayout
#from kivy.uix.behaviors import FocusBehavior
#from kivy.uix.recycleview.layout import LayoutSelectionBehavior

from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem, TabbedPanelHeader

from collections import OrderedDict
from kivy.properties import BooleanProperty

from server.devinfo import Page
from ui.TableElement import WidgetPageBehavior
from ui.TableElement import WidgetFieldElement, WidgetFieldLabelName, WidgetFieldLabelValue
from ui.TableElement import WidgetRowTitleElement
from ui.TableElement import WidgetRowElement, WidgetRowIndexElement, WidgetFieldIndexElement

class WidgetFieldT1Element(WidgetFieldElement):
    def __init__(self, **kwargs):
        #print(self.__class__.__name__, kwargs)
        super(WidgetFieldT1Element, self).__init__(**kwargs)

    @staticmethod
    def to_field_value(row_idx, col_idx, value):

        def func_report_id(report_id):
            if report_id:
                st, end = report_id
                if st == end:
                    return "{}".format(st)
                else:
                    return "{st}-{end}".format(st=st, end=end)
            else:
                return '-'

        func_list = (None, hex, None, None, func_report_id)
        if col_idx < len(func_list):
            func = func_list[col_idx]
        else:
            func = None

        if func:
            value = func(value)

        return str(value)


class WidgetRowT1Element(WidgetRowElement):
    REPORT_ID_TABLE = OrderedDict()
    ROW_TITLE_DATA_NAME = ('TYPE', 'ADDR', 'SIZE', 'INSTANCES', 'REPORT ID')

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        #print(self.__class__.__name__, rv, index, data)

        kwargs = data
        w_row_kwargs = kwargs.get('w_row_kwargs')
        w_field_kwargs = kwargs.get('w_field_kwargs')
        skip_value = w_field_kwargs.get('skip_value')
        skip_name = w_field_kwargs.get('skip_name')
        super(WidgetRowT1Element, self).__init2__(**w_row_kwargs)

        row_mm = w_row_kwargs.get('row_mm')
        field_size = len(row_mm)

        #print(self.__class__.__name__, row_mm)
        if not skip_value:
            # pid = row_mm.get_field('type')
            # addr = row_mm.get_field('start_address')
            # size = row_mm.get_field('size_minus_one') + 1
            # instances = row_mm.get_field('instances_minus_one') + 1
            # num_report_ids = row_mm.get_field('num_report_ids') * instances
            val = row_mm.values()
            print(self.__class__.__name__, val)
            pid, addr, size, instances, num_report_ids = val
            size = size + 1
            instances = instances + 1
            num_report_ids = num_report_ids * instances

            if num_report_ids:
                report_st = 1
                for k, v in self.REPORT_ID_TABLE.items():
                    if k == pid:
                        break

                    report_st += v

                report_end = report_st + num_report_ids - 1
                report_id = (report_st, report_end)
            else:
                report_id = None

            if id not in self.REPORT_ID_TABLE.keys():
                self.REPORT_ID_TABLE[pid] = num_report_ids

            elem_values = (pid, addr, size, instances, report_id)

        for j in range(field_size):
            kwargs = dict(col_idx=j, **w_field_kwargs)
            if not skip_value:
                kwargs['value'] = elem_values[j]

            if not skip_name:
                kwargs['name'] = self.ROW_TITLE_DATA_NAME[j]

            w_field = self.create_field_element(**kwargs)
            self.add_children_layout(self.CHILD_ELEM_DATA, w_field)

        self.index = index

        #print(self.__class__.__name__, self.REPORT_ID_TABLE)

        return super(WidgetRowElement, self).refresh_view_attrs(
            rv, index, data)

class WidgetPageElement(WidgetPageBehavior, TabbedPanelItem):
    PAGE_LAYOUT_TABLE = {
        Page.OBJECT_TABLE: {
            #'title': ("type", "address", "size", "instances", "report id"),
            'default': {'class_row_title_elem': WidgetRowTitleElement,
                'class_row_elem': WidgetRowT1Element,
                'class_field_elem': (WidgetFieldT1Element,WidgetFieldLabelName, WidgetFieldLabelValue),
                'class_index_elem': (WidgetRowIndexElement, WidgetFieldIndexElement)},
            'title': {'skip_value': True},
            'content': {'skip_name':True}
        },

        'default': {
            'default':{'class_row_title_elem': WidgetRowTitleElement,
                'class_row_elem': WidgetRowElement,
                'class_field_elem': (WidgetFieldElement, WidgetFieldLabelName, WidgetFieldLabelValue),
                'class_index_elem': (WidgetRowIndexElement, WidgetFieldIndexElement)},
            'title':{ 'skip_value': True},
            'content': {}
        }
    }

    @classmethod
    def get_page_layout_kwargs(cls, id):
        if id in cls.PAGE_LAYOUT_TABLE.keys():
            kwargs = cls.PAGE_LAYOUT_TABLE[id]
        else:
            kwargs = cls.PAGE_LAYOUT_TABLE['default']

        kwargs_t = kwargs['default'].copy()
        kwargs_t.update(kwargs['title'])
        kwargs_c = kwargs['default'].copy()
        kwargs_c.update(kwargs['content'])

        return kwargs_t, kwargs_c

    def __init__(self, page_mm):
        page_id = page_mm.id()
        parent_inst = page_mm.parent_inst()
        tab_name = self.to_tab_name(page_id, parent_inst)
        TabbedPanelItem.__init__(self, text=tab_name)
        w_content = self.ids['content']

        widget_kwargs = self.get_page_layout_kwargs(page_id)
        WidgetPageBehavior.__init__(self, w_content, page_id, widget_kwargs)
        if page_mm.valid():
            self.create_page_content_widget(page_mm)

    def to_tab_name(self, page_id, parent_inst):
        major, minor = page_id
        if parent_inst > 1:
            name = "{}".format(minor)
        else:
            name = "{}".format(major)
        return name

class WidgetPageMultiInstElement(TabbedPanelItem):

    selected = BooleanProperty(False)

    def __init__(self, major, parent_insts, **kwargs):
        self.__major = major
        self.__parent_insts = parent_insts
        self.__elems_tab = {}

        super(WidgetPageMultiInstElement, self).__init__(text=str(major), **kwargs)
        self._content = self.ids['content']

        #print(self.__class__.__name__, "init", self)

    def __str__(self):
        return super(WidgetPageMultiInstElement, self).__str__() + "{} {} {}".format(self.id(), self.parent_insts(), self.__elems_tab.keys())

    def id(self):
        return self.__major

    def parent_insts(self):
        return self.__parent_insts

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
            self.set_default_tab()
        else:
            self.selected = False

    def set_default_tab(self):
        tab = self._content.get_current_tab()
        if isinstance(tab, TabbedPanelHeader):
            page_id = (self.id(), 0)
            print(self.__class__.__name__, "on_page_selected", "switch to default page ", page_id)
            self._content.switch_to(self.get_element(page_id))
            tab = self._content.get_current_tab()
            tab.dispatch('on_press')

    def get_element(self, page_id):
        return self.__elems_tab.get(page_id, None)

    def add_element(self, page_id, w_page):
        self.__elems_tab[page_id] = w_page
        self._content.add_widget(w_page)

    def remove_element(self, page_id):
        widget = self.get_element(page_id)
        if widget:
            widget.clear_widgets()
            del self.__elems_tab[page_id]

    def clear_elements(self):
        self.__elems_tab.clear()
        super(WidgetPageMultiInstElement, self).clear_widgets()

    def do_fresh(self, page_mm):
        page_id = page_mm.id()
        widget = self.get_element(page_id)
        if widget:
            widget.do_fresh(page_mm)

class PageElementRoot(TabbedPanel):
    def __init__(self, **kwargs):
        self.__elems_tab = {}
        super(PageElementRoot, self).__init__(**kwargs)

    def get_element(self, elem_id):
        if isinstance(elem_id, tuple):
            major, inst = elem_id
        else:
            major = elem_id

        widget = self.__elems_tab.get(major, None)
        if widget:
            if widget.id() == elem_id:
                return widget
            elif hasattr(widget, 'get_element'):
                return widget.get_element(elem_id)

    def add_element(self, major_id, w_pages):
        self.__elems_tab[major_id] = w_pages
        super(PageElementRoot, self).add_widget(w_pages)

    def create_page_element(self, page_mm):
        parent_inst = page_mm.parent_inst()
        major, inst = page_mm.id()
        if parent_inst > 1:
            parent_widget = self.get_element(major)
            if not parent_widget:
                parent_widget = WidgetPageMultiInstElement(major, parent_inst)
                self.add_element(major, parent_widget)
            widget = WidgetPageElement(page_mm)
            parent_widget.add_element((major, inst), widget)
        else:
            widget = WidgetPageElement(page_mm)
            self.add_element(major, widget)

        return widget

    def remove_element(self, major_id):
        widget = self.get_element(major_id)
        if widget:
            del self.__elems_tab[major_id]
            super(PageElementRoot, self).remove_widget(widget)

    def clear_elements(self, **kwargs):
        self.__elems_tab.clear()
        super(PageElementRoot, self).clear_widgets(**kwargs)

    def set_default_element(self, element_id):
        major, inst = element_id
        widget = self.__elems_tab.get(major, None)
        self.switch_to(widget)
        if widget:
            tab = self.get_current_tab()
            #print(self.__class__.__name__, "set_default_element", tab)
            if isinstance(tab, TabbedPanelHeader):
                self.switch_to(widget)
                tab = self.get_current_tab()
                tab.dispatch('on_press')

if __name__ == '__main__':

    import array, os
    from kivy.app import App
    from tools.mem import ChipMemoryMap

    from MainUi import MainUi
    MainUi.load_ui_kv_file(os.curdir)

    class PageElementApp(App):

        def build(self):

            root = PageElementRoot()

            v_chip_id = array.array('B', [164, 24, 16, 170, 32, 20, 40])
            chip = ChipMemoryMap.get_chip_mmap(v_chip_id)
            page_mmap = chip.get_mem_map_tab(Page.ID_INFORMATION)
            root.create_page_element(page_mmap)

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
            root.create_page_element(page_mmap)

            def sort_key(mm):
                major, inst = mm.id()
                if isinstance(major, str):
                    result = (ord(major) - ord('z') - 1, inst)
                else:
                    result = (major, inst)

                #print("sort_key", result)
                return result

            chip.create_chip_mmap_pages()
            all_page_mmaps = chip.get_mem_map_tab()
            for mmap in sorted(all_page_mmaps.values(), key=sort_key):
                page_id = mmap.id()
                widget = root.get_element(page_id)
                if not widget:
                    value = array.array('B', range(mmap.get_value_size()))
                    mmap.set_values(value)
                    widget = root.create_page_element(mmap)
                    widget.do_fresh(mmap)

            return root

    PageElementApp().run()