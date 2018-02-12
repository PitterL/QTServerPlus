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
from kivy.animation import Animation

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

        if super(FocusLabel, self).keyboard_on_key_down(window, keycode, text, modifiers):
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


class WidgetFieldIndexElement(FocusLabel):
    pass

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
        class_field_name = kwargs.pop('class_field_name')
        class_field_value = kwargs.pop('class_field_value')
        layout_kwargs = kwargs.pop('layout_kwargs', dict())

        super(WidgetFieldElement, self).__init__(**layout_kwargs)

        if not skip_name:
            text = self.to_field_name(row_idx, col_idx, name)
            self.add_layout(self.NAME, class_field_name(eid=(row_idx, col_idx), etype=self.NAME, text=text))

        if not skip_value:
            text = self.to_field_value(row_idx, col_idx, value)
            self.add_layout(self.VALUE, class_field_value(eid=(row_idx, col_idx), etype=self.VALUE, text=text))

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

class WidgetRowIndexElement(BoxLayout):
    def __init__(self, row_idx_elems, **kwargs):
        super(WidgetRowIndexElement, self).__init__(**kwargs)

        #layout = self.ids['content']
        #layout.text = str(row_idx)
        self.line_space = sum(map(lambda x: x[1] if x else 0, row_idx_elems))
        for elem in row_idx_elems:
            if elem:
                percent = elem[1] / self.line_space
                self.add_widget(WidgetFieldIndexElement(text=elem[0], size_hint_x=percent, font_size=12))

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

        #print(kwargs)
        #skip_index = kwargs.get('skip_index', True)
        layout_kwargs = kwargs.get('layout_kwargs', dict())
        for k, v in layout_kwargs:
            if hasattr(self, k):
                setattr(self, k, v)

        row_mm = kwargs.get('row_mm', None)
        if row_mm is not None:
            if row_mm.idx:
                #idx_widget = WidgetRowIndexElement(self.__row_idx + 1)
                idx_widget = WidgetRowIndexElement(row_mm.idx)
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
        class_field_elem, class_field_name, class_field_value = kwargs.pop('class_field_elem')

        #print(class_field_elem, kwargs)
        return class_field_elem(page_id=page_id, row_idx=row_idx,
                                class_field_name=class_field_name, class_field_value=class_field_value, **kwargs)

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
        skip_value = w_field_kwargs.get('skip_value')
        skip_name = w_field_kwargs.get('skip_name')
        self.__init2__(**w_row_kwargs)

        row_mm = w_row_kwargs.get('row_mm')
        line_space = sum(map(lambda v: v.width, row_mm.field_values()))
        for j, (name, elem) in enumerate(row_mm):
            percent = elem.width / line_space
            w_layout_kwargs = {'size_hint_x': percent}
            kwargs = dict(col_idx=j, layout_kwargs=w_layout_kwargs, **w_field_kwargs)
            if not skip_value:
                kwargs['value'] = elem.value

            if not skip_name:
                kwargs['name'] = name

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

class WidgetRowTitleElement(WidgetRowElement):
    pass
# class WidgetRowTitleElement(WidgetRowElement):
#
#     def refresh_view_attrs1(self, rv, index, data):
#         ''' Catch and handle the view changes '''
#         #print(self.__class__.__name__, rv, index, data)
#
#         kwargs = data
#         w_row_kwargs = kwargs.get('w_row_kwargs')
#         w_field_kwargs = kwargs.get('w_field_kwargs')
#         super(WidgetRowTitleElement, self).__init2__(**w_row_kwargs)
#
#         # page_title = w_row_kwargs.get('title')   #[:2] value index filed, [2:] value bit field
#         #
#         # for row_data in page_title:
#         #     print(self.__class__.__name__, "refresh_view_attrs", row_data)
#         #     idx = row_data.idx
#         #     if idx:
#         #         idx_widget = WidgetRowIndexElement(idx)
#         #         #self.add_layout(self.CHILD_ELEM_INDEX, idx_widget)
#         #
#         #     content_widget = WidgetRowDataElement()
#         #     self.add_layout(self.CHILD_ELEM_DATA, content_widget)
#         #     content = row_data.content
#         #     line_space = sum(map(lambda x: x[1], content))
#         #     for j, v in enumerate(content):
#         #         # if isinstance(v, int):
#         #         #     name = None
#         #         #     value = v
#         #         # else:
#         #         #     name = v
#         #         #     value = None
#         #         name, space = v
#         #         percent = space / line_space
#         #         w_layout_kwargs = {'size_hint_x': percent}
#         #
#         #         kwargs = dict(col_idx=j, name=name, layout_kwargs=w_layout_kwargs, **w_field_kwargs)
#         #         w_field = self.create_field_element(**kwargs)
#         #         #print(self.__class__.__name__, "w_field", raw_data)
#         #         self.add_children_layout(self.CHILD_ELEM_DATA, w_field)
#
#         self.index = index
#
#         #print(self.__class__.__name__, rv.data[index])
#         return super(WidgetRowElement, self).refresh_view_attrs(
#             rv, index, data)

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

class WidgetPageContentBaseElement(RecycleView):
    pass

class WidgetPageContentTitleElement(WidgetPageContentBaseElement):
    pass

class WidgetPageContentDataElement(WidgetPageContentBaseElement):
    pass

class WidgetPageBehavior(object):
    (PAGE_CHILD_ELEM_TITLE, PAGE_CHILD_ELEM_CONTENT) = ('Title', 'Content')
    (W_TITLE, W_CONTENT) = range(2)

    selected = BooleanProperty(False)

    def __init__(self, parent_widget, id, table_widget_kwargs):
        self._parent = parent_widget
        self._id = id
        self._w_kwargs = table_widget_kwargs
        self.__layout = {}

    def inited(self):
        return self.PAGE_CHILD_ELEM_CONTENT in self.__layout.keys()

    def id(self):
        return self._id

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

    def add_layout(self, name, layout):
        self.__layout[name] = layout
        self._parent.add_widget(layout)

    def get_layout(self, name):
        return self.__layout[name]

    def to_tab_name(self):
        return str(self.id())

    # def create_page_tab_widget(self, cls_base):
    #     text = self.to_tab_name()
    #     #super(WidgetPageElement, self).__init__(text=text)
    #     self.cls_base = cls_base.__init__(text=text)

    def create_page_content_title_widget(self, title_mm, layout_kwargs):
        class_row_title_elem = layout_kwargs.get('class_row_title_elem')
        class_field_elem = layout_kwargs.get('class_field_elem')

        data = []
        for i, row_mm in enumerate(title_mm):
            row_kwargs = {'w_row_kwargs': dict(page_id=self.id(), row_idx=-1, row_mm=row_mm),
                          'w_field_kwargs': dict(skip_value=True, class_field_elem=class_field_elem)}
            # print(self.__class__.__name__, row_kwargs)
            data.append(row_kwargs)

        root = WidgetPageContentTitleElement()
        setattr(root, 'data', data)
        setattr(root, 'viewclass', class_row_title_elem)

        return root

    def create_page_content_data_widget(self, page_mm, layout_kwargs):
        skip_value = layout_kwargs.get('skip_value', False)
        skip_name = layout_kwargs.get('skip_name', False)
        class_row_elem = layout_kwargs.get('class_row_elem')
        class_field_elem = layout_kwargs.get('class_field_elem')

        data = []
        for i, row_mm in enumerate(page_mm):
            row_kwargs = {'w_row_kwargs': dict(page_id=self.id(), row_idx=i, row_mm=row_mm, layout_kwargs=dict()),
                            'w_field_kwargs': dict(skip_name=skip_name, skip_value=skip_value, class_field_elem=class_field_elem)}
            #print(self.__class__.__name__, row_kwargs)
            data.append(row_kwargs)

        root = WidgetPageContentDataElement()
        setattr(root, 'data', data)
        setattr(root, 'viewclass', class_row_elem)

        return root

    def create_page_content_widget(self, page_mm):
         title_kwargs, content_kwargs = self._w_kwargs

         if page_mm.title:
             widget = self.create_page_content_title_widget(page_mm.title, layout_kwargs=title_kwargs)
             self.add_layout(self.PAGE_CHILD_ELEM_TITLE, widget)

         widget = self.create_page_content_data_widget(page_mm, layout_kwargs=content_kwargs)
         self.add_layout(self.PAGE_CHILD_ELEM_CONTENT, widget)

    def do_fresh(self, page_mm):

        if not page_mm.valid():
            print("{} data invalid, {}".format(page_mm.id(), page_mm))
            return

        if self.inited():
            #FIXME: here row_mm may be same as page_mm.row()
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
