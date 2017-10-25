# from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.label import Label
# from kivy.uix.button import Button
#from kivy.uix.behaviors import FocusBehavior
from kivy.graphics import Color, Rectangle
# from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
#from kivy.uix.scrollview import ScrollView

from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
#from kivy.uix.label import Label
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior

from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem, TabbedPanelHeader
from server.devinfo import Page

from collections import OrderedDict

class ElemError(Exception):
    "Message error exception class type"
    pass

class FocusWithColor(FocusBehavior):
    ''' Class that when focused, changes its background color to red.
    '''

    _color = None
    _rect1 = None


    def __init__(self, *args, **kwargs):
        super(FocusWithColor, self).__init__(*args, **kwargs)
        with self.canvas:
            self._color = Color(1, 1, 1, .2)
            self._rect1 = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        #print("update {ins} {v}".format(ins=instance, v=value))
        self._rect1.pos = instance.pos
        self._rect1.size = instance.size

    def on_focused(self, instance, value, *largs):
        #print("focus {ins} {v}".format(ins=instance, v=value))
        self._color.rgba = [1, 0, 0, .2] if value else [1, 1, 1, .2]

class FocusLabel(FocusWithColor, Label):
    '''A label, which in addition to turn red when focused, it also sets the
    keyboard input to the text of the label.
    '''

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        '''We call super before doing anything else to enable tab cycling
        by FocusBehavior. If we wanted to use tab for ourselves, we could just
        not call it, or call it if we didn't need tab.
        '''

        if super(FocusLabel, self).keyboard_on_key_down(window, keycode,
                                                         text, modifiers):
            return True

        next = None

        if keycode[1] == 'right':
            next = self.get_focus_next()
        elif keycode[1] == 'left':
            next = self.get_focus_previous()
        elif keycode[1] == 'up' or keycode[1] == 'down':
            grid = self.parent
            if hasattr(grid, 'cols'):
                cols = grid.cols
                next = self
                if keycode[1] == 'up':
                    for i in range(cols):
                        next = next.get_focus_previous()
                else:
                    for i in range(cols):
                        next = next.get_focus_next()

        if next:
            self.focused = False
            next.focused = True

        return True


class WidgetFieldLabelBase(FocusLabel):
    def __init__(self, **kwargs):
        self.__id = kwargs.pop('eid')
        self.__type = kwargs.pop('etype')

        super(WidgetFieldLabelBase, self).__init__(**kwargs)

    def __str__(self):
        return "{} id {} type {}: {} ".format(self.__class__.__name__, self.id(), self.type(), self.text)

    def id(self):
        return self.__id

    def type(self):
        return self.__type

    def row_idx(self):
        return self.__id[0]

    def col_idx(self):
        return self.__id[1]


class WidgetFieldLabelName(WidgetFieldLabelBase):
    pass

class WidgetFieldLabelValue(WidgetFieldLabelBase):
    pass

class WidgetFieldElement(BoxLayout):
    (NAME, VALUE) = range(2)

    def __init__(self, **kwargs):
        #print(self.__class__.__name__, kwargs)
        #page_id = kwargs.pop('page_id')
        self.__layout = {}
        row_idx =  kwargs.pop('row_idx')
        col_idx = kwargs.pop('col_idx')
        name = kwargs.pop('name', None)
        value = kwargs.pop('value', None)
        skip_name = kwargs.pop('skip_name', False)
        skip_value = kwargs.pop('skip_value', False)
        layout_kwargs = kwargs.pop('layout_kwargs', dict())

        super(WidgetFieldElement, self).__init__(**layout_kwargs)

        if not skip_name:
            text = self.to_field_name(row_idx, col_idx, name)
            self.add_layout(WidgetFieldElement.NAME, WidgetFieldLabelName(eid=(row_idx, col_idx), etype=WidgetFieldElement.NAME, text=text))

        if not skip_value:
            text = self.to_field_value(row_idx, col_idx, value)
            self.add_layout(WidgetFieldElement.VALUE, WidgetFieldLabelValue(eid=(row_idx, col_idx), etype=WidgetFieldElement.VALUE, text=text))

        #print(__class__.__name__, self.children)

    def __str__(self):
        text = super(WidgetFieldElement, self).__str__()
        text += "\n".join(map(str, self.children))
        return text

    @staticmethod
    def to_field_name(row_idx, col_idx, name):
        return name

    @staticmethod
    def to_field_value(row_idx, col_idx, value):
        return str(hex(value))

    def get_layout(self, name):
        return self.__layout.get(name, None)

    def add_layout(self, name, widget):
        self.__layout[name] = widget
        self.add_widget(widget)

    def clear_layout(self):
        #print(self.__class__.__name__, "clear layout", self.__layout)
        self.__layout.clear()
        self.clear_widgets()

    def field_type(self, type):
        for field_t in self.children:
            if field_t.type() == type:
                return field_t

    def set_value(self, value):
        for child in self.children:
            if child.type() == WidgetFieldElement.VALUE:
                child.text = self.to_field_value(child.row_idx(), child.col_idx(), value)
                break

    def set_name(self, name):
        for child in self.children:
            if child.type() == WidgetFieldElement.NAME:
                child.text = self.to_field_name(child.row_idx(), child.col_idx(), name)
                break

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

class WidgetRowIndexElement(BoxLayout):
    def __init__(self, row_idx, **kwargs):
        super(WidgetRowIndexElement, self).__init__(**kwargs)

        layout = self.ids['content']
        layout.text = str(row_idx)

class WidgetRowDataElement(BoxLayout):
    pass

class WidgetRowElement(RecycleDataViewBehavior, BoxLayout):
    (CHILD_ELEM_INDEX, CHILD_ELEM_DATA) = range(2)
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def __init__(self, **kwargs):
        #print(self.__class__.__name__, kwargs)
        self.__page_id = None
        self.__row_idx = None
        self.__layout = {}

        super(WidgetRowElement, self).__init__()

    def __init2__(self, **kwargs):
        #print(self.__class__.__name__, "__init2__", kwargs)
        if len(self.__layout):
            self.clear_layout()

        self.__page_id = kwargs.get('page_id')
        self.__row_idx = kwargs.get('row_idx')

        skip_index = kwargs.get('skip_index', True)
        layout_kwargs = kwargs.get('layout_kwargs', dict())
        for k, v in layout_kwargs:
            if hasattr(self, k):
                setattr(self, k, v)

        if not skip_index:
            idx_widget = WidgetRowIndexElement(self.__row_idx + 1)
            self.add_layout(self.CHILD_ELEM_INDEX, idx_widget)

        data_widget = WidgetRowDataElement()
        self.add_layout(self.CHILD_ELEM_DATA, data_widget)

    def inited(self):
        return len(self.__layout) > 0

    def page_id(self):
        return self.__page_id

    def row_id(self):
        return self.__row_idx

    def get_layout(self, name):
        return self.__layout.get(name, None)

    def add_layout(self, name, widget):
        self.__layout[name] = widget
        self.add_widget(widget)

    def clear_layout(self):
        #print(self.__class__.__name__, "clear layout", self.__layout)
        self.__layout.clear()
        self.clear_widgets()

    def add_children_layout(self, name, widget):
        layout = self.get_layout(name)
        if layout:
            layout.add_widget(widget)

    def get_children_layout(self, name):
        layout = self.get_layout(name)
        if layout:
            return layout.children

    def create_field_element(self, **kwargs):
        #print(self.__class__.__name__, kwargs)
        page_id = self.page_id()
        row_idx = self.row_id()
        class_field_elem = kwargs.pop('class_field_elem', WidgetFieldElement)

        #print(class_field_elem, kwargs)
        return class_field_elem(page_id=page_id, row_idx=row_idx, **kwargs)

    def refresh_data(self, data):
        kwargs = data
        w_row_kwargs = kwargs.get('w_row_kwargs')
        row_mm = w_row_kwargs.get('row_mm')
        layout = self.get_layout(self.CHILD_ELEM_DATA)
        for child in layout.children:
            child_v = child.get_layout(WidgetFieldElement.VALUE)
            value = row_mm.get_field_by_idx(child_v.col_idx())
            child.set_value(value)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        #print(self.__class__.__name__, rv, index, data)
        #
        # if self.inited():
        #     self.refresh_data(data)
        #     return

        kwargs = data
        w_row_kwargs = kwargs.get('w_row_kwargs')
        w_field_kwargs = kwargs.get('w_field_kwargs')
        self.__init2__(**w_row_kwargs)

        row_mm = w_row_kwargs.get('row_mm')
        for j, (name, elem) in enumerate(row_mm):
            kwargs = dict(col_idx=j, name=name, value=elem.value, **w_field_kwargs)
            w_field = self.create_field_element(**kwargs)
            self.add_children_layout(self.CHILD_ELEM_DATA, w_field)

        self.index = index

        #print(self.__class__.__name__, rv.data[index])
        return super(WidgetRowElement, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(WidgetRowElement, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        # if is_selected:
        #     print("selection changed to {0}".format(rv.data[index]))
        # else:
        #     print("selection removed for {0}".format(rv.data[index]))

class WidgetRowT1Element(WidgetRowElement):
    REPORT_ID_TABLE = OrderedDict()

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        #print(self.__class__.__name__, rv, index, data)

        kwargs = data
        w_row_kwargs = kwargs.get('w_row_kwargs')
        w_field_kwargs = kwargs.get('w_field_kwargs')
        super(WidgetRowT1Element, self).__init2__(**w_row_kwargs)

        row_mm = w_row_kwargs.get('row_mm')
        #print(self.__class__.__name__, row_mm)

        pid = row_mm.get_field('type')
        addr = row_mm.get_field('start_address')
        size = row_mm.get_field('size_minus_one') + 1
        instances = row_mm.get_field('instances_minus_one') + 1
        num_report_ids = row_mm.get_field('num_report_ids') * instances

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
        for j, value in enumerate(elem_values):
            kwargs = dict(col_idx=j, value=value, **w_field_kwargs)
            w_field = self.create_field_element(**kwargs)
            self.add_children_layout(self.CHILD_ELEM_DATA, w_field)

        self.index = index

        #print(self.__class__.__name__, self.REPORT_ID_TABLE)

        return super(WidgetRowElement, self).refresh_view_attrs(
            rv, index, data)

class WidgetRowTitleElement(WidgetRowElement):

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        #print(self.__class__.__name__, rv, index, data)

        kwargs = data
        w_row_kwargs = kwargs.get('w_row_kwargs')
        w_field_kwargs = kwargs.get('w_field_kwargs')
        super(WidgetRowTitleElement, self).__init2__(**w_row_kwargs)

        raw_data = w_row_kwargs.get('raw_data')
        #print(self.__class__.__name__, "refresh_view_attrs", raw_data)

        for j, v in enumerate(raw_data):
            if isinstance(v, int):
                name = None
                value = v
            else:
                name = v
                value = None

            kwargs = dict(col_idx=j, name=name, value=value, **w_field_kwargs)
            w_field = self.create_field_element(**kwargs)
            #print(self.__class__.__name__, "w_field", raw_data)
            self.add_children_layout(self.CHILD_ELEM_DATA, w_field)

        self.index = index

        #print(self.__class__.__name__, rv.data[index])
        return super(WidgetRowElement, self).refresh_view_attrs(
            rv, index, data)

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

class WidgetPageContentBaseElement(RecycleView):
    pass

class WidgetPageTitleElement(WidgetPageContentBaseElement):
    pass

class WidgetPageRowsElement(WidgetPageContentBaseElement):
    pass

class WidgetPageElement(TabbedPanelItem):
    PAGE_LAYOUT_TABLE = {
        Page.OBJECT_TABLE: {
            'title': ("type", "address", "size", "instances", "report id"),
            'class_row_elem': WidgetRowT1Element,
            'class_field_elem': WidgetFieldT1Element,
            'skip_name': True,
            'skip_index': False,
        },
        'default': {
            'class_row_elem': WidgetRowElement,
            'class_field_elem': WidgetFieldElement,
        }
    }

    (PAGE_CHILD_ELEM_TITLE, PAGE_CHILD_ELEM_CONTENT) = ('Title', 'Content')

    selected = BooleanProperty(False)

    def __init__(self, page_mm, **kwargs):
        self.__id = page_mm.id()
        self.__parent_instance = page_mm.parent_inst()
        self.__layout = {}

        self.create_page_tab_widget(page_mm, **kwargs)
        if page_mm.valid():
            self.create_page_content_widget(page_mm)

    def __str__(self):
        return "{}, page {} inited={}".format(super(WidgetPageElement, self).__str__(), self.id(), self.inited())

    def inited(self):
        return self.PAGE_CHILD_ELEM_CONTENT in self.__layout.keys()

    def id(self):
        return self.__id

    def selected_id(self):
        return self.id()

    def on_state(self, widget, value):
        #print(self.__class__.__name__, "state", value)

        if value == 'down':
            self.selected = True
        else:
            self.selected = False

    # def on_page_unselected(self, instance):
    #     print(self.__class__.__name__, "unselected")
    #     self.selected = False

    def parent_inst(self):
        return self.__parent_inst

    @classmethod
    def layout_kwargs(cls, id, name=None):
        if id in cls.PAGE_LAYOUT_TABLE.keys():
            layout_kwargs = cls.PAGE_LAYOUT_TABLE[id]
        else:
            layout_kwargs = cls.PAGE_LAYOUT_TABLE['default']

        if name is not None:
            return layout_kwargs.get(name, None)
        else:
            return layout_kwargs

    # def layout(self, name):
    #     if name in self.__layout.keys():
    #         return self.__layout[name]

    def add_layout(self, name, layout):
        self.__layout[name] = layout
        self.ids['content'].add_widget(layout)
        #super(WidgetPageElement, self).add_widget(layout)

    def get_layout(self, name):
        return self.__layout[name]

    def create_page_tab_widget(self, page_mm, **kwargs):
        # def to_tab_name(page_mm):
        #     if page_mm.parent_inst():
        #         major, minor = page_mm.id()
        #         name = "T{}".format(major)
        #         if page_mm.parent_inst() > 1:
        #             name += "-{}".format(minor)
        #     else:
        #         id = page_mm.id()
        #         name = "T{}".format(id)
        #
        #     return name
        def to_tab_name(page_mm):
             major, minor = page_mm.id()
             parent_insts = page_mm.parent_inst()

             if parent_insts > 1:
                name = "{}".format(minor)
             else:
                name = "{}".format(major)
             return name

        text = to_tab_name(page_mm)
        #print(self.__class__.__name__, "to_tab_name", text)
        super(WidgetPageElement, self).__init__(text=text)

    def create_rows_title_widget(self, page_mm, **kwargs):
        rows_title_name = kwargs.get('name')

        #row_mm = page_mm.row(0) #title use first row as element
        row_kwargs = {'w_row_kwargs': dict(page_id=self.id(), row_idx=-1, raw_data=rows_title_name),
                        'w_field_kwargs': dict(skip_value=True)}

        root = WidgetPageTitleElement()
        setattr(root, 'data', [row_kwargs])
        setattr(root, 'viewclass', WidgetRowTitleElement)
        self.add_layout(self.PAGE_CHILD_ELEM_TITLE, root)

    def create_rows_widget(self, page_mm, layout_kwargs):

        skip_index = layout_kwargs.get('skip_index', True)
        skip_name = layout_kwargs.get('skip_name', False)
        class_row_elem = layout_kwargs.get('class_row_elem')
        class_field_elem = layout_kwargs.get('class_field_elem')

        data = []
        for i, row_mm in enumerate(page_mm):
            row_kwargs = {'w_row_kwargs': dict(page_id=self.id(), row_idx=i, skip_index=skip_index, row_mm=row_mm, layout_kwargs=dict()),
                            'w_field_kwargs': dict(skip_name=skip_name, class_field_elem=class_field_elem)}
            #print(self.__class__.__name__, row_kwargs)
            data.append(row_kwargs)

        root = WidgetPageRowsElement()
        setattr(root, 'data', data)
        setattr(root, 'viewclass', class_row_elem)
        self.add_layout(self.PAGE_CHILD_ELEM_CONTENT, root)

    def create_page_content_widget(self, page_mm):
        title = WidgetPageElement.layout_kwargs(self.id(), 'title')
        if title:
            #print(self.__class__.__name__, "create_page_content_widget", title)
            widget = self.create_rows_title_widget(page_mm, name=title)

        layout_kwargs = WidgetPageElement.layout_kwargs(self.id())
        self.create_rows_widget(page_mm, layout_kwargs=layout_kwargs)

    def do_fresh(self, page_mm):

        if not page_mm.valid():
            print("{} data invalid, {}".format(page_mm.id(), page_mm))
            return

        if self.inited():
            layout = self.get_layout(self.PAGE_CHILD_ELEM_CONTENT)
            for i, data in enumerate(layout.data):
                w_row_kwargs = data.get('w_row_kwargs')
                if 'row_mm' in w_row_kwargs.keys():
                    w_row_kwargs['row_mm'] = page_mm.row(i)
                elif 'raw_data' in w_row_kwargs.keys():
                    w_row_kwargs['row_mm'] = page_mm.row(i).get_value()
                else:
                    print(self.__class__.__name__, "Not support value fresh: ", w_row_kwargs)
        else:
            self.create_page_content_widget(page_mm)

        #layout = self.layout('Rows')
        # if layout:
        #     for w_row in layout.ids['content'].children:    #WidgetRowElement
        #         for w_field_elem in w_row.children_layout(w_row.CHILD_ELEM_DATA):     #WidgetFieldElement
        #             #print(self.__class__.__name__, w_field_elem)
        #             w_field_value = w_field_elem.field_type(WidgetFieldElement.VALUE)   #WidgetFieldElementValue
        #
        #             if w_field_value:
        #                 value = page_mm.select_idx(*w_field_value.id()) #(row_idx, col_idx)
        #                 if value is not None:   #could be zero for value, but not None
        #                     w_field_value.text = w_field_elem.to_field_value(w_field_value.row_idx(), w_field_value.col_idx(), value)
        #                 else:
        #                     print("{} fresh page {}, field '{}' not found".format(self.__class__.__name__, page_mm.id(), w_field_value.id()))

class WidgetPageMultiInstElement(TabbedPanelItem):

    selected = BooleanProperty(False)

    def __init__(self, major, parent_insts, **kwargs):
        self.__major = major
        self.__parent_insts = parent_insts
        self.__elems_tab = {}

        super(WidgetPageMultiInstElement, self).__init__(text=str(major), **kwargs)
        self._content = self.ids['content']

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

        #print(self.__class__.__name__, "add_element", len(self.__elems_tab))
        # if len(self.__elems_tab) == 1:  # first element
        #     self._content.switch_to(w_page)

    def remove_element(self, page_id):
        widget = self.get_element(page_id)
        if widget:
            widget.clear_widgets()
            del self.__elems_tab[page_id]

    def clear_elements(self):
        self.__elems_tab.clear()
        super(PageElementRoot, self).clear_widgets()

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

    # def set_default_element(self, element_id=Page.ID_INFORMATION):
    #     major, inst = element_id
    #     widget = self.__elems_tab.get(major, None)
    #     if widget:
    #         self.switch_to(widget)
    #         if widget.parent_inst() > 1:
    #             sub_widget = widget.get_element(element_id)
    #             if sub_widget:
    #                 widget.switch_to(sub_widget)

if __name__ == '__main__':

    import array
    from kivy.app import App
    from tools.mem import ChipMemoryMap

    class PageElementApp(App):

        def build(self):

            root = PageElementRoot()

            v_chip_id = array.array('B', [164, 24, 16, 170, 32, 20, 40])
            chip = ChipMemoryMap.get_chip_mmap(v_chip_id)
            page_mmap = chip.get_mmap(Page.ID_INFORMATION)
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

            page_mmap = chip.get_mmap(Page.OBJECT_TABLE)
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

            chip.create_default_mmap_pages()
            all_page_mmaps = chip.get_mmap()
            for mmap in sorted(all_page_mmaps.values(), key=sort_key):
                page_id = mmap.id()
                widget = root.get_element(page_id)
                if not widget:
                    widget = root.create_page_element(mmap)

            return root

    PageElementApp().run()