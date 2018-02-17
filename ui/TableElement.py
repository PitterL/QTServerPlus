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
from kivy.uix.recycleview.views import RecycleDataAdapter
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.properties import BooleanProperty, StringProperty, ListProperty
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

    border_color =  ListProperty([0, 0, 0, 1])
    """Border color, in the format (r, g, b, a)."""
    
    background_color =  ListProperty([1, 1, 1, 1])
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
        self._val = v
        self.set_value(self._val)

    def type(self):
        return self.TYPE_VALUE

    def is_type_name(self):
        return False

    def is_type_value(self):
        return True


class LayerBoxLayout(BoxLayout):
    def __init__(self, *args, **kwargs):
        super(LayerBoxLayout, self).__init__(*args, **kwargs)
        self.__layout = {}

    def __iter__(self):
        return iter(self.__layout)

    def __len__(self):
        return len(self.__layout)

    def get_layout(self, name):
        return self.__layout.get(name, None)

    def add_layout(self, name, widget):
        self.__layout[name] = widget
        self.add_widget(widget)

    def remove_layout(self, name):
        if name in self.__layout.keys():
            w = self.__layout[name]
            self.remove_widget(w)
            del self.__layout[name]

    def detach_layout(self):
        for n in list(self.__layout.keys()):
            self.remove_layout(n)

    def clear_layout(self):
        for layout in self.__layout.values():
            if isinstance(layout, LayerBoxLayout):
                layout.clear_layout()
        self.clear_widgets()
        self.__layout.clear()

    def add_children_layout(self, child_name_nested, widget):
        assert isinstance(child_name_nested, (tuple, list))
        if len(child_name_nested) > 1:
            layout = self.get_layout(child_name_nested[0])
            assert isinstance(layout, LayerBoxLayout)
            layout.add_children_layout(child_name_nested[1:], widget)
        else:
            self.add_layout(child_name_nested[0], widget)

    def get_children_layout(self, child_name_nested):
        assert isinstance(child_name_nested, (tuple, list))
        if len(child_name_nested) > 1:
            layout = self.get_layout(child_name_nested[0])
            assert isinstance(layout, LayerBoxLayout)
            return layout.get_children_layout(child_name_nested[1:])
        else:
            return self.get_layout(child_name_nested[0])

class WidgetFieldElement(LayerBoxLayout):
    def __init__(self, **kwargs):
        #print(self.__class__.__name__, kwargs)
        #self.__layout = {}
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
    #
    # def get_layout(self, name):
    #     return self.__layout.get(name, None)
    #
    # def add_layout(self, name, widget):
    #     self.__layout[name] = widget
    #     self.add_widget(widget)
    #
    # def clear_layout(self):
    #     #print(self.__class__.__name__, "clear layout", self.__layout)
    #     self.__layout.clear()
    #     self.clear_widgets()

    # def field_type(self, type):
    #     for field_t in self.children:
    #         if field_t.is_type(type):
    #             return field_t

    def set_value(self, value):
        for child in self.children:
            if child.is_type_value():
                child.set_value(value)
                break

    def set_name(self, name):
        for child in self.children:
            if child.is_type_name():
                child.set_value(name)
                break

class WidgetFieldIndexElement(WidgetFieldElement):
    def __init__(self, **kwargs):
        super(WidgetFieldIndexElement, self).__init__(**kwargs)

        self.adjust_size_hint()

    def adjust_size_hint(self):
        if self.col == 0:
            self.size_hint_x = self.idx_size_hint
    #

class WidgetRowIndexElement(LayerBoxLayout):
    pass

class WidgetRowDataElement(LayerBoxLayout):
    pass

class WidgetRowElementBase(RecycleDataViewBehavior, LayerBoxLayout):
    (CHILD_ELEM_INDEX, CHILD_ELEM_DATA) = range(2)
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def __init__(self, page_id, row_id, **kwargs):
        self.__page_id = page_id
        self.__row_idx = row_id
        super(WidgetRowElementBase, self).__init__(**kwargs)

    # def __init2__(self, page_id, row_id, layout_kwargs=None):
    #     #print(self.__class__.__name__, "__init2__", layout_kwargs)
    #     #assert not self.inited()
    #
    #     self.__page_id = page_id
    #     self.__row_idx = row_id
    #
    #     if layout_kwargs:
    #         for k, v in layout_kwargs:
    #             setattr(self, k, v)
    #
    # def _create_view(self, rv, index, data):
    #     pass

    def __repr__(self):
        return super(WidgetRowElementBase, self).__repr__() + "{} {}".format(self.__page_id, self.__row_idx)

    def inited(self):
        return len(self) > 0

    def page_id(self):
        return self.__page_id

    def row_id(self):
        return self.__row_idx

    def create_field_element(self, **kwargs):
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

    def do_fresh(self, kwargs):
        pass

    # def on_touch_down(self, touch):
    #     ''' Add selection on touch down '''
    #     if super(WidgetRowElement, self).on_touch_down(touch):
    #         return True
    #     if self.collide_point(*touch.pos) and self.selectable:
    #         return self.parent.select_with_touch(self.index, touch)

    def apply_selection1(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        # if is_selected:
        #     print("selection changed to {0}".format(rv.data[index]))
        # else:
        #     print("selection removed for {0}".format(rv.data[index]))

class WidgetRowElement(WidgetRowElementBase):

    #def _create_view(self, rv, index, data):
    def __init__(self, rv, index, data):

        kwargs = data['view_attrs']

        v_kwargs = kwargs.get('view_kwargs')
        page_id = v_kwargs.get('page_id')
        row_id = v_kwargs.get('row_id')
        row_elem = v_kwargs.get('row_elem')

        c_kwargs = kwargs.get('cls_kwargs')
        l_kwargs =  kwargs.get('layout_kwargs', dict())

        #self.__init2__(page_id, row_id, l_kwargs)
        super(WidgetRowElement, self).__init__(page_id, row_id, **l_kwargs)

        cls_row_elem, cls_row_idx, cls_row_data = c_kwargs.get('class_row_elems')
        cls_idx_field = c_kwargs.get('class_idx_field')
        cls_data_field = c_kwargs.get('class_data_field')

        # idx content
        if cls_row_idx:
            if row_elem.idx_desc:
                self.add_layout(self.CHILD_ELEM_INDEX, cls_row_idx())
                for j, desc in enumerate(row_elem.idx_desc):
                    if desc:
                        name, _= desc
                        w_field = self.create_field_element(col_idx=j, name=name, cls_kwargs=cls_idx_field)
                        self.add_children_layout([self.CHILD_ELEM_INDEX, name], w_field)

        # data content
        if cls_row_data:
            self.add_layout(self.CHILD_ELEM_DATA, cls_row_data())
            line_space = sum(map(lambda v: v.width, row_elem.field_values()))
            for j, (name, field) in enumerate(row_elem):   #row_elem is RowElement, iter() is {name: BitField}
                percent = field.width / line_space
                layout_kwargs = {'size_hint_x': percent}
                kwargs = dict(col_idx=j, name=name, value=field.value,
                              layout_kwargs=layout_kwargs, cls_kwargs=cls_data_field)
                w_field = self.create_field_element(**kwargs)
                self.add_children_layout([self.CHILD_ELEM_DATA, name], w_field)

    def do_fresh(self, kwargs):
        #page_id = kwargs.get('page_id')
        #row_id = kwargs.get('row_id')
        v_kwargs = kwargs.get('view_kwargs')
        row_elem = v_kwargs.get('row_elem')

        # if row_mm.idx_elems:
        #     layout = self.get_layout(self.CHILD_ELEM_INDEX)
        #     if layout:
        #         for j, elem in enumerate(row_mm.idx_elems):
        #             if elem:
        #                 layout.do_refresh(col_idx=j)

        for j, (name, field) in enumerate(row_elem):
            layout = self.get_children_layout([self.CHILD_ELEM_DATA, name])
            if layout:
                layout.set_value(field.value)

class WidgetRowTitleElement(WidgetRowElement):
    pass

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''
    def on_size(self, *args):
        #print(self.__class__.__name__, "on_size", args)
        pass
#class RecycleDataAdapter2(RecycleDataAdapter):

class WidgetPageContentRecycleElement(RecycleView):
    minimum_size_a = ListProperty([0, 0])

    def __init__(self, **kwargs):
        super(WidgetPageContentRecycleElement, self).__init__(**kwargs)
        self.__cache = {}

    def get_view(self, name):
        return self.__cache.get(name, None)

    def save(self, name, widget):
        self.__cache[name] = widget

    def remove(self, name):
        if name in self.__cache.keys():
            w = self.__cache[name]
            del self.__cache[name]
            return w

    def update_size(self, inst, size):
        #print(self.__class__.__name__, "update_size", inst, "child:", size, "self", self.size)
        self.minimum_size_a = size
        w, h = size
        if self.height > h:
            self.height = h
        if self.width > w:
            self.width = w

    def add_widget(self, widget, index=0):
        widget.bind(size=self.update_size)
        super().add_widget(widget, index)

class WidgetRecycleDataView(RecycleDataViewBehavior, LayerBoxLayout):

    def refresh_view_attrs(self, rv, index, data):
        #print(self.__class__.__name__, index, kwargs)
        kwargs = data['view_attrs']

        v_kwargs = kwargs.get('view_kwargs')
        page_id = v_kwargs.get('page_id')
        row_id = v_kwargs.get('row_id')

        c_kwargs = kwargs.get('cls_kwargs')
        cls_row_elem, _, _ = c_kwargs.get('class_row_elems')

        wid = (page_id, row_id)
        w = self.get_layout(wid)
        if w:
            w.do_fresh(kwargs)
        else:
            self.detach_layout()
            w = rv.get_view(wid)
            if w:
                w.do_fresh(kwargs)
                if w.parent:
                    w.parent.remove_layout(wid)
            else:
                w = cls_row_elem(rv, index, data)
                #w._create_view(rv, index, data)
                rv.save(wid, w)

            self.add_layout(wid, w)

        self.index = index
        return super(WidgetRecycleDataView, self).refresh_view_attrs(rv, index, data)

    def refresh_view_layout(self, rv, index, layout, viewport):
        return super(WidgetRecycleDataView, self).refresh_view_layout(rv, index, layout, viewport)

class WidgetPageContentBaseElement(WidgetPageContentRecycleElement):
    def __init__(self, id, row_elems, cls_kwargs, **layout_kwargs):
        super(WidgetPageContentBaseElement, self).__init__()

        cls_row_elems = cls_kwargs.get('class_row_elems')
        data = []
        for i, row_elem in enumerate(row_elems):    #row_elems is list store RowElement
            row_kwargs = {'view_attrs': {
                                'view_kwargs':{'page_id':id, 'row_id':i, 'row_elem':row_elem},
                                'cls_kwargs':cls_kwargs,
                                'layout_kwargs':layout_kwargs}}
            #print(self.__class__.__name__, row_kwargs)
            #row_kwargs=cls_row_elems[0](page_id, i, row_elem, cls_kwargs, layout_kwargs)
            data.append(row_kwargs)

        setattr(self, 'data', data)
        setattr(self, 'viewclass', WidgetRecycleDataView)

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

    def create_page_content_widget(self, page_mm):
         #create title layout
         if page_mm.title:
             cls_kwargs = self._c_kwargs['title']
             cls_content = cls_kwargs['class_content']
             widget = cls_content(self.id(), page_mm.title, cls_kwargs)
             self.add_layout(self.PAGE_CHILD_ELEM_TITLE, widget)

         # create title layout
         cls_kwargs = self._c_kwargs['data']
         cls_content = cls_kwargs['class_content']
         widget = cls_content(self.id(), page_mm, cls_kwargs)
         self.add_layout(self.PAGE_CHILD_ELEM_TITLE, widget)

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
