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
from kivy.properties import BooleanProperty, StringProperty, ListProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.animation import Animation
from kivy.uix.textinput import TextInput
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

class WidgetFieldLabelBase(Label):


    border = ListProperty([1, 1, 1, 1])
    """Widget border size: It must be a list of four values: (bottom, right, top, left)."""

    border_color =  ListProperty([1, 1, 1, 1])
    """Border color, in the format (r, g, b, a)."""
    
    background_color =  ListProperty([0, 0, 0, 1])
    """Border color, in the format (r, g, b, a)."""
    
    (TYPE_NAME, TYPE_VALUE) = ('NAME', 'VALUE')
    def __init__(self, row, col, v, t, **kwargs):
        self.row = row
        self.col = col
        self._val = v
        self._type = t
        super(WidgetFieldLabelBase, self).__init__(text=self.covert_to_text(), **kwargs)

    def __str__(self):
        return "{} row {} col {} val {} type {}".format(self.__class__.__name__, self.row, self.col, self._val, self._type)

    def type(self):
        return self._type

    def is_type_name(self):
        return self.TYPE_NAME == self._type

    def is_type_value(self):
        return self.TYPE_VALUE == self._type

    def to_field_name(self, name):
        return name

    def to_field_value(self, value):
        return "%02X" %value

    def covert_to_text(self):
        data = self._val
        if self.is_type_name():
            return self.to_field_name(data)
        elif self.is_type_value():
            return self.to_field_value(data)
        else:
            return '<%s>' % str(data)

    def get_text(self):
        pass

    def fresh(self):
        self.text = self.covert_to_text()

    def set_value(self, v):
        self._val = v
        self.fresh()

class WidgetFieldIndexName(WidgetFieldLabelBase):
    def __init__(self, row, col, v):
        super(WidgetFieldIndexName, self).__init__(row, col, v, self.TYPE_NAME)
        self._type = self.TYPE_NAME

class WidgetFieldLabelName(WidgetFieldLabelBase):
    def __init__(self, row, col, v, **kwargs):
        super(WidgetFieldLabelName, self).__init__(row, col, v, self.TYPE_NAME, **kwargs)
        self._type = self.TYPE_NAME

class WidgetFieldLabelValue(WidgetFieldLabelBase):
    def __init__(self, row, col, v):
        super(WidgetFieldLabelValue, self).__init__(row, col, v, self.TYPE_VALUE)
        self._type = self.TYPE_VALUE

from ui.DebugView import ElemValVar2, ElemValVarBase
#WidgetFieldElemBehavior

class WidgetFieldInputValue(ElemValVar2):
    (TYPE_NAME, TYPE_VALUE) = ('NAME', 'VALUE')

    def __init__(self, row, col, v):
        super(WidgetFieldInputValue, self).__init__()
        self.row = row
        self.col = col
        self.set_value(v)

    def type(self):
        return self.TYPE_VALUE

    def is_type_name(self):
        return False

    def is_type_value(self):
        return True

class WidgetFieldElement(BoxLayout):
    def __init__(self, **kwargs):
        #print(self.__class__.__name__, kwargs)
        self.__layout = {}
        self.row =  kwargs.get('row_idx')
        self.col = kwargs.get('col_idx')
        name = kwargs.get('name', None)
        value = kwargs.get('value', None)
        cls_field_name = kwargs.get('class_field_name')
        cls_field_value = kwargs.get('class_field_value')
        #cls_field_elem, cls_field_name, cls_field_value = kwargs.get('cls_kwargs')
        layout_kwargs = kwargs.get('layout_kwargs', dict())

        #print(self.__class__.__name__, layout_kwargs)
        super(WidgetFieldElement, self).__init__(**layout_kwargs)

        if cls_field_name:
            w = cls_field_name(self.row, self.col, name)
            self.add_layout(w.type(), w)

        if cls_field_value:
            w = cls_field_value(self.row, self.col, value)
            self.add_layout(w.type(), w)

        #print(__class__.__name__, self.children)

    def __str__(self):
        text = super(WidgetFieldElement, self).__str__()
        text += "\n".join(map(str, self.children))
        return text

    def get_layout(self, name):
        return self.__layout.get(name, None)

    def add_layout(self, name, widget):
        self.__layout[name] = widget
        self.add_widget(widget)

    def clear_layout(self):
        #print(self.__class__.__name__, "clear layout", self.__layout)
        self.__layout.clear()
        self.clear_widgets()

    # def field_type(self, type):
    #     for field_t in self.children:
    #         if field_t.is_type(type):
    #             return field_t

    def set_value(self, value):
        for child in self.children:
            if child.is_type_name():
                child.set_value(value)
                break

    def set_name(self, name):
        for child in self.children:
            if child.is_type_value():
                child.set_value(name)
                break

    from kivy.graphics import BorderImage

    border = ListProperty([4, 4, 4, 4])
    '''Border used for :class:`~kivy.graphics.vertex_instructions.BorderImage`
    graphics instruction. Used with :attr:`background_normal` and
    :attr:`background_active`. Can be used for a custom background.

    .. versionadded:: 1.4.1

    It must be a list of four values: (bottom, right, top, left). Read the
    BorderImage instruction for more information about how to use it.

    :attr:`border` is a :class:`~kivy.properties.ListProperty` and defaults
    to (4, 4, 4, 4).
    '''

    background_normal = StringProperty(
        'atlas://data/images/defaulttheme/textinput')
    '''Background image of the TextInput when it's not in focus.

    .. versionadded:: 1.4.1

    :attr:`background_normal` is a :class:`~kivy.properties.StringProperty` and
    defaults to 'atlas://data/images/defaulttheme/textinput'.
    '''

    background_disabled_normal = StringProperty(
        'atlas://data/images/defaulttheme/textinput_disabled')
    '''Background image of the TextInput when disabled.

    .. versionadded:: 1.8.0

    :attr:`background_disabled_normal` is a
    :class:`~kivy.properties.StringProperty` and
    defaults to 'atlas://data/images/defaulttheme/textinput_disabled'.
    '''

    background_active = StringProperty(
        'atlas://data/images/defaulttheme/textinput_active')
    '''Background image of the TextInput when it's in focus.

    .. versionadded:: 1.4.1

    :attr:`background_active` is a
    :class:`~kivy.properties.StringProperty` and
    defaults to 'atlas://data/images/defaulttheme/textinput_active'.
    '''

    background_color = ListProperty([1, 1, 1, 1])
    '''Current color of the background, in (r, g, b, a) format.

    .. versionadded:: 1.2.0

    :attr:`background_color` is a :class:`~kivy.properties.ListProperty`
    and defaults to [1, 1, 1, 1] (white).
    '''

    foreground_color = ListProperty([0, 0, 0, 1])
    '''Current color of the foreground, in (r, g, b, a) format.

    .. versionadded:: 1.2.0

    :attr:`foreground_color` is a :class:`~kivy.properties.ListProperty`
    and defaults to [0, 0, 0, 1] (black).
    '''

    disabled_foreground_color = ListProperty([0, 0, 0, .5])
    '''Current color of the foreground when disabled, in (r, g, b, a) format.

    .. versionadded:: 1.8.0

    :attr:`disabled_foreground_color` is a
    :class:`~kivy.properties.ListProperty` and
    defaults to [0, 0, 0, 5] (50% transparent black).
    '''

class WidgetFieldIndexElement(WidgetFieldElement):
    def __init__(self, **kwargs):
        super(WidgetFieldIndexElement, self).__init__(**kwargs)

        self.adjust_size_hint()

    def adjust_size_hint(self):
        if self.col == 0:
            self.size_hint_x = self.idx_size_hint
    #
class WidgetRowIndexElement(BoxLayout):
    pass

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
        #cls_row, cls_row_idx, cls_row_data = kwargs.get('cls_kwargs')

        layout_kwargs = kwargs.get('layout_kwargs', dict())
        for k, v in layout_kwargs:
            if hasattr(self, k):
                setattr(self, k, v)

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
        cls_field_elem, cls_field_name, cls_field_value = kwargs.get('cls_kwargs')

        #print(class_field_elem, kwargs)
        return cls_field_elem(page_id=page_id, row_idx=row_idx,
                                class_field_name=cls_field_name, class_field_value=cls_field_value, **kwargs)

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
        row_kwargs = kwargs.get('w_row_kwargs')
        #w_field_kwargs = kwargs.get('w_field_kwargs')
        c_kwargs = kwargs.get('cls_kwargs')
        cls_row_elem, cls_row_idx, cls_row_data = c_kwargs.get('class_row_elems')
        cls_idx_elems = c_kwargs.get('class_idx_elems')
        cls_data_elems = c_kwargs.get('class_data_elems')

        # skip_value = w_field_kwargs.get('skip_value')
        # skip_name = w_field_kwargs.get('skip_name')

        self.__init2__(**row_kwargs)

        # if cls_row_idx:
        #     self.add_layout(self.CHILD_ELEM_INDEX, cls_row_idx())
        #
        # if cls_row_data:
        #     self.add_layout(self.CHILD_ELEM_DATA, cls_row_data())

        #index content
        row_mm = row_kwargs.get('row_mm', None)
        if row_mm is not None:
            # idx content
            if cls_row_idx:
                if row_mm.idx_elems:
                    self.add_layout(self.CHILD_ELEM_INDEX, cls_row_idx())
                    #line_space = sum(map(lambda x: x[1] if x else 0, row_mm.idx_elems))
                    for j, elem in enumerate(row_mm.idx_elems):
                        if elem:
                            #percent = elem[1] / line_space
                            #layout_kwargs = dict(size_hint_x=percent)
                            w_field = self.create_field_element(col_idx=j, name=elem[0], cls_kwargs=cls_idx_elems)
                            #w_field = WidgetFieldIndexElement(text=elem[0], size_hint_x=percent, font_size=12)
                            self.add_children_layout(self.CHILD_ELEM_INDEX, w_field)

            #data content
            if cls_row_data:
                self.add_layout(self.CHILD_ELEM_DATA, cls_row_data())
                line_space = sum(map(lambda v: v.width, row_mm.field_values()))
                for j, (name, elem) in enumerate(row_mm):
                    percent = elem.width / line_space
                    layout_kwargs = {'size_hint_x': percent}
                    kwargs = dict(col_idx=j, name=name, value=elem.value,
                                  layout_kwargs=layout_kwargs, cls_kwargs=cls_data_elems)
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

    def apply_selection1(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        # if is_selected:
        #     print("selection changed to {0}".format(rv.data[index]))
        # else:
        #     print("selection removed for {0}".format(rv.data[index]))

class WidgetRowTitleElement(WidgetRowElement):
    pass

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

class WidgetPageContentRecycleElement(RecycleView):
    pass

class WidgetPageContentBaseElement(WidgetPageContentRecycleElement):
    def __init__(self, id, row_elems, cls_kwargs, **layout_kwargs):
        super(WidgetPageContentBaseElement, self).__init__()

        cls_row_elems = cls_kwargs.get('class_row_elems')
        data = []
        for i, row_mm in enumerate(row_elems):
            row_kwargs = {'w_row_kwargs': dict(page_id=id, row_idx=i, row_mm=row_mm, layout_kwargs=layout_kwargs),
                        #'w_field_kwargs': dict(skip_name=skip_name, skip_value=skip_value),
                        'cls_kwargs': cls_kwargs}
            #print(self.__class__.__name__, row_kwargs)
            data.append(row_kwargs)

        #root = WidgetPageContentDataElement()
        setattr(self, 'data', data)
        setattr(self, 'viewclass', cls_row_elems[0])

class WidgetPageContentTitleElement(WidgetPageContentBaseElement):
    pass

class WidgetPageContentDataElement(WidgetPageContentBaseElement):
    pass

class WidgetPageBehavior(object):
    (PAGE_CHILD_ELEM_TITLE, PAGE_CHILD_ELEM_CONTENT) = ('Title', 'Content')
    (W_TITLE, W_CONTENT) = range(2)

    selected = BooleanProperty(False)

    def __init__(self, parent_widget, id, cls_kwargs):
        self._parent = parent_widget
        self._id = id
        self._c_kwargs = cls_kwargs
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

    # def create_page_content_title_widget1(self, title_mm, cls_kwargs):
    #     cls_row_elems = cls_kwargs.get('class_row_elems')
    #
    #     data = []
    #     for i, row_mm in enumerate(title_mm):
    #         row_kwargs = {'w_row_kwargs': dict(page_id=self.id(), row_idx=i, row_mm=row_mm),
    #                       #'w_field_kwargs': dict(skip_value=True,),
    #                       'cls_kwargs': cls_kwargs}
    #         # print(self.__class__.__name__, row_kwargs)
    #         data.append(row_kwargs)
    #
    #     root = WidgetPageContentTitleElement()
    #     setattr(root, 'data', data)
    #     setattr(root, 'viewclass', cls_row_elems[0])
    #
    #     return root
    #
    # def create_page_content_data_widget1(self, page_mm, cls_kwargs):
    #     cls_row_elems = cls_kwargs.get('class_row_elems')
    #
    #     data = []
    #     for i, row_mm in enumerate(page_mm):
    #         row_kwargs = {'w_row_kwargs': dict(page_id=self.id(), row_idx=i, row_mm=row_mm, layout_kwargs=dict()),
    #                     #'w_field_kwargs': dict(skip_name=skip_name, skip_value=skip_value),
    #                     'cls_kwargs': cls_kwargs}
    #         #print(self.__class__.__name__, row_kwargs)
    #         data.append(row_kwargs)
    #
    #     root = WidgetPageContentDataElement()
    #     setattr(root, 'data', data)
    #     setattr(root, 'viewclass', cls_row_elems[0])
    #
    #     return root

    def create_page_content_widget(self, page_mm):
         #create title layout
         if page_mm.title:
             cls_kwargs = self._c_kwargs['title']
             cls_content = cls_kwargs['class_content']
             widget = cls_content(self.id(), page_mm.title, cls_kwargs)
             self.add_layout(self.PAGE_CHILD_ELEM_TITLE, widget)

         # create data layout
         # cls_kwargs = self._c_kwargs['data']
         # cls_content = cls_kwargs['class_content']
         # widget = cls_content(self.id(), page_mm, cls_kwargs)
         # self.add_layout(self.PAGE_CHILD_ELEM_CONTENT, widget)

    def do_fresh(self, page_mm):

        if not page_mm.valid():
            print("{} data invalid, {}".format(page_mm.id(), page_mm))
            return

        if self.inited():
            #FIXME: here row_mm may be same as page_mm.row()
            layout = self.get_layout(self.PAGE_CHILD_ELEM_CONTENT)
            # for i, data in enumerate(layout.data):
            #     w_row_kwargs = data.get('w_row_kwargs')
            #     if 'row_mm' in w_row_kwargs.keys():
            #         w_row_kwargs['row_mm'] = page_mm.row(i)
            #     # elif 'raw_data' in w_row_kwargs.keys():
            #     #     w_row_kwargs['row_mm'] = page_mm.row(i).get_value()
            #     else:
            #         print(self.__class__.__name__, "Not support value fresh: ", w_row_kwargs)
            layout.refresh_from_data()
        else:
            print(self.__class__.__name__, "do_fresh", "create_page_content_widget", page_mm.id())
            self.create_page_content_widget(page_mm)
