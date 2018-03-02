# from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.label import Label
# from kivy.uix.button import Button
#from kivy.uix.behaviors import FocusBehavior
from kivy.graphics import Color, Rectangle
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
#from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton

from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataAdapter
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.properties import NumericProperty,  BooleanProperty, StringProperty, ListProperty, DictProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.animation import Animation
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem, TabbedPanelHeader
from kivy.clock import Clock

from server.devinfo import Page
from ui.WidgetExt import Action, ValueAction, PropAction, ActionEvent, ActionEventWrapper, LayerBoxLayout, LayerBoxLayoutBase

from collections import OrderedDict
import re, time


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

class WidgetFieldBehavior(object):
    #(TYPE_NAME, TYPE_VALUE) = ('NAME', 'VALUE')
    def __init__(self, row, col, v, t, **kwargs):
        self.row = row
        self.col = col
        self._val = v
        self._type = t

    def __str__(self):
        return "{} [{}-{}] [type {}]: {} ".format(self.__class__.__name__, self.row, self.col, self._type, self._val)

    def __repr__(self):
        return super(WidgetFieldBehavior, self).__repr__() + self.__str__()

    def type(self):
        return self._type

    def is_type_name(self):
        return self._type == WidgetFieldElement.TYPE_NAME

    def is_type_value(self):
        return self._type == WidgetFieldElement.TYPE_VALUE

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

    def get_value(self):
        return self._val

    def set_value(self, v):
        self._val = v
        self.fresh()

class WidgetFieldLabelBase(WidgetFieldBehavior, Label):
    border = ListProperty([1, 1, 1, 1])
    """Widget border size: It must be a list of four values: (bottom, right, top, left)."""

    border_color = ListProperty([0, 0, 0, 1])
    """Border color, in the format (r, g, b, a)."""

    background_color = ListProperty([1, 1, 1, 1])
    """Border color, in the format (r, g, b, a)."""

    def __init__(self, row, col, v, t, **kwargs):
        WidgetFieldBehavior.__init__(self, row, col, v, t)
        Label.__init__(self, text=self.covert_to_text(), **kwargs)

    # def on_size(self, *args):
    #     print(self.__class__.__name__, args)

class WidgetFieldIndexName(WidgetFieldLabelBase):
    hightlight = BooleanProperty(False)

    def __init__(self, row, col, v):
        super(WidgetFieldIndexName, self).__init__(row, col, v, WidgetFieldElement.TYPE_NAME)
        #self._type = self.TYPE_NAME
        self.adjust_font_color()

    def adjust_font_color(self):
        if self.col == 1:
            self.hightlight = True

class WidgetFieldLabelName(WidgetFieldLabelBase):
    def __init__(self, row, col, v, **kwargs):
        super(WidgetFieldLabelName, self).__init__(row, col, v, WidgetFieldElement.TYPE_NAME, **kwargs)
        #self._type = self.TYPE_NAME

class WidgetFieldTitleName(WidgetFieldLabelName):
    pass

class WidgetFieldButtonName(ActionEvent, WidgetFieldBehavior, ToggleButton):
    (UNSELECTED, SELECTED) = range(2)
    def __init__(self, row, col, n, **kwargs):
        ActionEvent.__init__(self)
        WidgetFieldBehavior.__init__(self, row, col, n, WidgetFieldElement.TYPE_NAME)
        ToggleButton.__init__(self, text=self.covert_to_text(), **kwargs)
        self.prop_value = self.UNSELECTED

    def name(self):
        return self._val

    def write(self):
        action = PropAction(col=self.col, name=self.name(), value=self.prop_value, time=time.time())
        print(self.__class__.__name__, "write", action)
        self.action = action

    def on_state(self, inst, value):
        if value == 'normal':
            self.prop_value = self.UNSELECTED
        else:
            self.prop_value = self.SELECTED
        self.write()

    # def on_size(self, *args):
    #     print(self.__class__.__name__, args)

class WidgetFieldIndexButtonName(WidgetFieldButtonName):
    disabled = BooleanProperty(False)

    def __init__(self, row, col, n, **kwargs):
        super(WidgetFieldIndexButtonName, self).__init__(row, col, n)
        self.adjust_state()

    def adjust_state(self):
        if self.col == 0:
            self.disabled = True

class WidgetFieldLabelValue(WidgetFieldLabelBase):
    def __init__(self, row, col, v, max_v):
        self.max_value = max_v
        super(WidgetFieldLabelValue, self).__init__(row, col, v, WidgetFieldElement.TYPE_VALUE)
        self._type = WidgetFieldElement.TYPE_VALUE

class WidgetFieldInputValue(ActionEvent, TextInput):
    #(TYPE_NAME, TYPE_VALUE) = ('NAME', 'VALUE')
    PAT_INPUT_CHAR = re.compile("[\da-fA-FxX]")

    #action = DictProperty({})
    # PG_ERROR = StringProperty('')
    # PG_NORMAL = StringProperty('')
    # PG_ACTIVE = StringProperty('')

    def __init__(self, row, col, v, max_v=0xff):
        self.row = row
        self.col = col
        self.value = v
        self.max_value = max_v
        super(WidgetFieldInputValue, self).__init__()

        self.set_value(v)

    def __str__(self):
        text = self.__class__.__name__ + "[{}-{}] {}".format(self.row, self.col, self.value)
        return text

    def __repr__(self):
        return super(WidgetFieldInputValue, self).__repr__() + self.__str__()

    # def _get_line_options1(self):
    #     # Get or create line options, to be used for Label creation
    #     if self._line_options is None:
    #         self._line_options = kw = {
    #             'font_name': "ARIALN.ttf",
    #             'font_size': self.font_size,
    #             'font_name': self.font_name,
    #             'anchor_x': 'left',
    #             'anchor_y': 'top',
    #             'padding_x': 0,
    #             'padding_y': 0,
    #             'padding': (0, 0),
    #             'halign': 'center',
    #             'valign': 'justify',
    #             'color': (0,0,0,1),
    #             'size': self.size}
    #         self._label_cached = self._label_cls()
    #     return self._line_options

    def type(self):
        return WidgetFieldElement.TYPE_VALUE

    def is_type_name(self):
        return False

    def is_type_value(self):
        return True

    def set_value(self, val):
        if val <= self.max_value:
            self.value = val
            self.text = str(val)
        else:
            self.error = 'v'

    def set_error(self, code):
        if code:
            self.background_normal = self.pg_error
        else:
            self.background_normal = self.pg_normal

    def clr_err(self):
        self.set_error(None)

    def _get_padding_left(self, text):
        width = self.width
        text_width = self._get_text_width(text, self.tab_width, None)
        if width >= text_width:
            left = (width - text_width) / 2
        else:
            left = 0

        #print(self.__class__.__name__, width, text_width, left)
        return left

    def insert_text(self, substring, from_undo=False):
        if self.PAT_INPUT_CHAR.match(substring):
            return super().insert_text(substring, from_undo=from_undo)

        print(self.__class__.__name__, "Invalid char input:", substring)

    def _convert_text(self, text):
        t = text.strip().lower()
        if t.startswith("0x"):
            base = 16
        else:
            base = 10

        try:
            value = int(t, base)
            if value <= self.max_value:
                return value
        except:
            print("Invalid input value:", text)

    def write(self, mode):
        action = ValueAction(col=self.col, value=self.value, op=mode, time=time.time())
        print(self.__class__.__name__, "write", action)
        self.action = action

    # if enter is pressed, execute write through to device, otherwith only write back to memory
    def on_text_validate(self, mode='wt'):
        val = self._convert_text(self.text)
        if isinstance(val, int):
            if val != self.value:
                self.set_value(val)
                self.clr_err()
                self.write(mode)
        else:
            print(self.__class__.__name__, "input error:", self.text)
            self.set_error('v')

    def on_focus(self, instance, value):
        print(self.__class__.__name__, instance, "on_focus", value)
        if value:
            Clock.schedule_once(lambda dt: self.select_all())
        else:
            self.on_text_validate(False)

    def on_text(self, inst, text):
        self.padding[0] = self._get_padding_left(text)

    def on_size(self, *args):
        self.padding[0] = self._get_padding_left(self.text)

class WidgetFieldElement(LayerBoxLayout):
    (TYPE_NAME, TYPE_VALUE) = ('NAME', 'VALUE')
    def __init__(self, **kwargs):
        #print(self.__class__.__name__, kwargs)
        self.row =  kwargs.get('row_idx')
        self.col = kwargs.get('col_idx')
        name = kwargs.get('name')
        value = kwargs.get('value')
        max_value = kwargs.get('max_value')
        cls_field_name = kwargs.get('class_field_name')
        cls_field_value = kwargs.get('class_field_value')
        layout_kwargs = kwargs.get('layout_kwargs', dict())
        super(WidgetFieldElement, self).__init__(**layout_kwargs)

        cls_field = self.inspect_cls(cls_field_name, self.row, self.col, name)
        if cls_field:
            w = cls_field(self.row, self.col, name)
            self.add_layer(w.type(), w)

        if cls_field_value:
            w = cls_field_value(self.row, self.col, value, max_value)
            self.add_layer(w.type(), w)

    def __str__(self):
        text = self.__class__.__name__ + "[row {}] [col {}]".format(self.row, self.col)
        # if self.children:
        #     text += "\n\t"
        #     text += "\n\t".join(map(str, self.children))
        return text

    def __repr__(self):
        return super(WidgetFieldElement, self).__repr__() + self.__str__()

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

    def inspect_cls(self, cls_field, row, col, v):
        if cls_field:
            if not isinstance(cls_field, (tuple, list)):    #simple structure
                return cls_field
            else:
                cls_name, param = cls_field
                exclusion = param.get('exclusion')
                if exclusion:
                    if v in exclusion:
                        return None
                return cls_name

    # def get_prop(self):
    #     w = self.get_layer(WidgetFieldElement.TYPE_NAME)
    #     if w:
    #         return {w.get_value(): w.prop_value}

class WidgetFieldIndexElement(WidgetFieldElement):
    def __init__(self, **kwargs):
        super(WidgetFieldIndexElement, self).__init__(**kwargs)

        self.adjust_size_hint()

    def adjust_size_hint(self):
        if self.col == 0:
            self.size_hint_x = self.idx_size_hint

class WidgetRowIndexElement(LayerBoxLayout):
    # def get_prop(self):
    #     properties = {}
    #     for layer in self:
    #         prop = layer.get_prop()
    #         properties.update(prop)
    #
    #     return properties

    def on_action(self, inst, act):
        if inst != self:
            action = Action.parse(act, zone='idx')
            self.action = action

class WidgetRowDataElement(LayerBoxLayout):
    # def get_prop(self):
    #     properties = {}
    #     for layer in self:
    #         prop = layer.get_prop()
    #         properties.update(prop)
    #
    #     return properties
    def on_action(self, inst, act):
        if inst != self:
            action = Action.parse(act, zone='data')
            self.action = action

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

    def __str__(self):
        text = self.__class__.__name__
        text += "[page{}] [row {}]".format(self.__page_id, self.__row_idx)
        # if self.children:
        #     text += "\n\t"
        #     text += "\n\t".join(map(str, self.children))
        return text

    def __repr__(self):
        return super(WidgetRowElementBase, self).__repr__() + self.__str__()

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

    # def refresh_data(self, data):
    #     kwargs = data
    #     w_row_kwargs = kwargs.get('w_row_kwargs')
    #     row_mm = w_row_kwargs.get('row_mm')
    #     layout = self.get_layer(self.CHILD_ELEM_DATA)
    #     for child in layout.children:
    #         child_v = child.get_layoer(WidgetFieldElement.VALUE)
    #         value = row_mm.get_field_by_idx(child_v.col_idx())
    #         child.set_value(value)

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

    def __init__(self, **kwargs):

        v_kwargs = kwargs.get('view_kwargs')
        page_id = v_kwargs.get('page_id')
        self.row = row_id = v_kwargs.get('row_id')
        row_elem = v_kwargs.get('row_elem')
        self.row_elem = row_elem

        c_kwargs = kwargs.get('cls_kwargs')
        l_kwargs =  kwargs.get('layout_kwargs', dict())

        super(WidgetRowElement, self).__init__(page_id, row_id, **l_kwargs)

        cls_row_elem, cls_row_idx, cls_row_data = c_kwargs.get('class_row_elems')
        cls_idx_field = c_kwargs.get('class_idx_field')
        cls_data_field = c_kwargs.get('class_data_field')

        # idx content
        if cls_row_idx:
            if row_elem.idx_desc:
                #self.add_layer(self.CHILD_ELEM_INDEX, cls_row_idx())
                parent = cls_row_idx()
                for j, desc in enumerate(row_elem.idx_desc):
                    if desc:
                        name, _= desc
                        w_field = self.create_field_element(col_idx=j, name=name, cls_kwargs=cls_idx_field)
                        #self.add_child_layer([self.CHILD_ELEM_INDEX, name], w_field)
                        parent.add_layer(name, w_field)
                self.add_layer(self.CHILD_ELEM_INDEX,parent)
        # data content
        if cls_row_data:
            parent = cls_row_data()
            line_space = sum(map(lambda v: v.width, row_elem.field_values()))
            for j, (name, field) in enumerate(row_elem):   #row_elem is RowElement, iter() is {name: BitField}
                percent = field.width / line_space
                layout_kwargs = {'size_hint_x': percent}
                kwargs = dict(col_idx=j, name=name, value=field.value, max_value=field.max_value,
                              layout_kwargs=layout_kwargs, cls_kwargs=cls_data_field)
                w_field = self.create_field_element(**kwargs)
                #self.add_child_layer([self.CHILD_ELEM_DATA, name], w_field)
                parent.add_layer(name, w_field)
            self.add_layer(self.CHILD_ELEM_DATA, parent)

        self._uniform_idx_height_to_data_row(row_id)

    def _uniform_idx_height_to_data_row(self, row_id):
        elem_data_row = self.get_layer(self.CHILD_ELEM_DATA)
        elem_idx_row = self.get_layer(self.CHILD_ELEM_INDEX)
        if elem_data_row and elem_idx_row:
            for _, layout in elem_idx_row:
                for _, elem in layout:
                    if elem_data_row.minimum_height:
                        elem.height = elem_data_row.minimum_height
                        elem_data_row.bind(minimum_height=elem.setter('height'))
                        #print(self.__class__.__name__, "uniform height [Row {}] height {} {}".format(row_id, elem.height, elem))

    # def get_prop(self):
    #     prop = {}
    #     w = self.get_layer(self.CHILD_ELEM_INDEX)
    #     prop['idx'] = w.get_prop()
    #     w = self.get_layer(self.CHILD_ELEM_DATA)
    #     prop['data'] = w.get_prop()

    #    return prop

    def do_fresh(self, **kwargs):
        row_elem = kwargs.get('row_elem')
        for j, (name, field) in enumerate(row_elem):
            layout = self.get_child_layer([self.CHILD_ELEM_DATA, name])
            if layout:
                layout.set_value(field.value)

    def __writeback_cache(self, **kwargs):
        col = kwargs['col']
        val = kwargs['value']
        for j, (name, field) in enumerate(self.row_elem):
            if j == col:
                field.set_value(val)
                break

    def on_action(self, inst, act):
        if inst != self:
            action = Action.parse(act, row=self.row)
            if action.is_event('value'):
                if action.is_op('w'):
                    self.__writeback_cache(**action)
                    if action.is_op('wt'):  #only write through will report to hight layer
                        self.action = action
            else:
                self.action = action

class WidgetRowTitleElement(WidgetRowElement):
    pass

class WidgetRecycleDataView(RecycleDataViewBehavior, LayerBoxLayout):
    def __str__(self):
        text = self.__class__.__name__
        # if self.children:
        #     text += "\n\t"
        #     text += "\n\t".join(map(str, self.children))
        return text

    def __repr__(self):
        return super(WidgetRecycleDataView, self).__repr__() + self.__str__()

    """cache each item"""
    def refresh_view_attrs(self, rv, index, data):
        #print(self.__class__.__name__, index, data)
        kwargs = data['view_attrs']

        v_kwargs = kwargs.get('view_kwargs')
        page_id = v_kwargs.get('page_id')
        row_id = v_kwargs.get('row_id')

        c_kwargs = kwargs.get('cls_kwargs')
        cls_row_elem, _, _ = c_kwargs.get('class_row_elems')

        wid = (page_id, row_id)
        w = self.get_layer(wid)
        if w:
            w.do_fresh(**v_kwargs)
        else:
            self.detach_layer()
            w = rv.get_view(wid)
            if w:
                w.do_fresh(**v_kwargs)
                if w.parent:
                    w.parent.remove_layer(wid)
            else:
                w = cls_row_elem(**kwargs)
                rv.save(wid, w)

            self.add_layer(wid, w)

        data.update(height=w.height)
        self.index = index
        return super(WidgetRecycleDataView, self).refresh_view_attrs(rv, index, data)

    def refresh_view_layout(self, rv, index, layout, viewport):
        layer = self.first_layer()
        #layout.update(size = layer.minimum_size)
        size = layout.get('size')
        if not size or size[1] != layer.height:
            print(self.__class__.__name__, "[IDX {}] height mismatch {} {}, refresh data", index, layer.size, layer.minimum_size)
            #self.refresh_from_data()
            rv.refresh_from_data()
        return super(WidgetRecycleDataView, self).refresh_view_layout(rv, index, layout, viewport)

class SelectableRecycleBoxLayout(ActionEventWrapper, FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):

    ''' Adds selection and focus behaviour to the view. '''
    # def on_size(self, *args):
    #     print(self.__class__.__name__, args)

    # def compute_visible_views(self, data, viewport):
    #     return super().compute_visible_views(data, viewport)
    #
    # def add_widget(self, widget, index=0):
    #     self.action_bind(widget)
    #     super().add_widget(widget, index)
    #
    # def remove_widget(self, widget):
    #     self.action_unbind(widget)
    #     super().remove_widget(widget)
    #
    # def clear_widgets(self, children=None):
    #     if not children:
    #         children = self.children
    #
    #     for child in children:
    #         self.action_unbind(child)
    #
    #     super().clear_widgets(children)

class WidgetPageContentRecycleElement(ActionEventWrapper, RecycleView):

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

    # def add_widget(self, widget, *largs):
    #     self.action_bind(widget)
    #     super(WidgetPageContentRecycleElement, self).add_widget(widget, *largs)
    #
    # def remove_widget(self, widget, *largs):
    #     self.action_unbind(widget)
    #     super(WidgetPageContentRecycleElement, self).remove_widget(widget, *largs)

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
            data.append(row_kwargs)

        setattr(self, 'data', data)
        setattr(self, 'viewclass', WidgetRecycleDataView)

class WidgetPageContentTitleElement(LayerBoxLayout):
    def __init__(self, id, row_elems, cls_kwargs, **layout_kwargs):
        super(WidgetPageContentTitleElement, self).__init__()

        cls_row_elem, _, _ = cls_kwargs.get('class_row_elems')
        for i, row_elem in enumerate(row_elems):
            view_kwargs = {'page_id': id, 'row_id': i, 'row_elem': row_elem}
            widget = cls_row_elem(view_kwargs=view_kwargs, cls_kwargs=cls_kwargs, layout_kwargs=layout_kwargs)
            self.add_layer(i, widget)

class WidgetPageContentDataElement(WidgetPageContentBaseElement):
    pass


class WidgetPageLayout(LayerBoxLayoutBase):
    (PAGE_CONTENT_TITLE, PAGE_CONTENT_DATA) = ('Title', 'Content')
    (W_TITLE, W_CONTENT) = range(2)

    selected = BooleanProperty(False)

    def __init__(self, id, cls_kwargs, **layout_kwargs):
        self._id = id
        self._c_kwargs = cls_kwargs
        super(WidgetPageLayout, self).__init__(**layout_kwargs)

    def inited(self):
        #return self.PAGE_CONTENT_DATA in self.__layout.keys()
        return self.get_layer(self.PAGE_CONTENT_DATA)

    def id(self):
        return self._id

    # def on_size(self, inst, value):
    #     print(self.__class__.__name__, inst, value)

    def to_tab_name(self):
        return str(self.id())

    def create_page_content_widget(self, page_mm):
         #create title layout
         if page_mm.title:
             cls_kwargs = self._c_kwargs['title']
             cls_content = cls_kwargs['class_content']
             widget = cls_content(self.id(), page_mm.title, cls_kwargs)
             self.add_layer(self.PAGE_CONTENT_TITLE, widget)

         # create data layout
         cls_kwargs = self._c_kwargs['data']
         cls_content = cls_kwargs['class_content']
         widget = cls_content(self.id(), page_mm, cls_kwargs)
         self.add_layer(self.PAGE_CONTENT_DATA, widget)

    def do_fresh(self, page_mm=None):
        if self.inited():
            #FIXME: here row_mm may be same as page_mm.row()
            layout = self.get_layer(self.PAGE_CONTENT_DATA)
            #default_size
            layout.refresh_from_data()
        else:
            if page_mm:
                print(self.__class__.__name__, "do_fresh", "create_page_content_widget", page_mm.id())
                self.create_page_content_widget(page_mm)
