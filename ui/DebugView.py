from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from kivy.uix.scatter import Scatter
from kivy.uix.treeview import TreeView, TreeViewNode
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image

from kivy.properties import ObjectProperty, BooleanProperty, ListProperty, \
    NumericProperty, StringProperty, OptionProperty, \
    ReferenceListProperty, AliasProperty, VariableListProperty
from kivy.clock import Clock

import re
from functools import partial
from collections import OrderedDict
import weakref
import array

class TreeViewProperty(BoxLayout, TreeViewNode):

    widget_ref = ObjectProperty(None, allownone=True)

    def _get_widget(self):
        wr = self.widget_ref
        if wr is None:
            return None
        wr = wr()
        if wr is None:
            self.widget_ref = None
            return None
        return wr
    widget = AliasProperty(_get_widget, None, bind=('widget_ref', ))

    key = ObjectProperty(None, allownone=True)

    #inspector = ObjectProperty(None)

    #refresh = BooleanProperty(False)

class TreeViewWidget(Label, TreeViewNode):

    widget = ObjectProperty(None)

    def __str__(self):
        return super(TreeViewWidget, self).__str__() + " " + self.text

    def name(self):
        return self.text

    def on_select_widget(self, widget):
        print(self.__class__.__name__, "on_select_widget", widget)


class TreeViewDataWidget(TreeViewWidget):

    (INIT, SEND, DONE) = range(3)
    status = NumericProperty(INIT)

    def __init__(self, **kwargs):
        self.value = kwargs.pop('value', None)
        if self.value:
            if isinstance(self.value, (tuple, array.array, list)):
                text = " ".join(map(lambda x: "{:02X}".format(x) if isinstance(x, int) else "'{}'".format(x), self.value))
            else:
                text = str(self.value)
        else:
            text = 'None'

        super().__init__(**kwargs, text=text)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.__class__.__name__ + " status={} data={}".format(self.status, self.value)

    def is_status(self, status):
        return self.status == status

class WidgetTree(TreeView):
    selected_widget = ObjectProperty(None, allownone=True)

    __events__ = ('on_select_widget',)

    def __init__(self, **kwargs):
        super(WidgetTree, self).__init__(**kwargs)
        self.update_scroll = Clock.create_trigger(self._update_scroll)

    def find_node_by_widget(self, widget):
        for node in self.iterate_all_nodes():
            if not node.parent_node:
                continue
            try:
                if node.widget == widget:
                    return node
            except ReferenceError:
                pass
        return None

    def update_selected_widget(self, widget):
        if widget:
            node = self.find_node_by_widget(widget)
            if node:
                self.select_node(node)
                while node and isinstance(node, TreeViewWidget):
                    if not node.is_open:
                        self.toggle_node(node)
                    node = node.parent_node

    def on_selected_widget(self, inst, widget):
        if widget:
            self.update_selected_widget(widget)
            self.update_scroll()

    def select_node(self, node):
        # entrance when treeview node selected
        super(WidgetTree, self).select_node(node)

        #print(self.__class__.__name__, "select_node", node)
        self.dispatch('on_select_widget', node)

    def on_select_widget(self, widget):
        pass

    def _update_scroll(self, *args):
        node = self._selected_node
        if not node:
            return

        self.parent.scroll_to(node)

class Command(object):
    """
    ======================================
    Read Register:
    CMD0	LenW	LenR	ADD_L	ADD_H
    0x51    0x2
    Response:
    TAG     LenR    [Data]
    0x0

    =============================================================
    Write Register
    CMD0	LenW	LenR	ADD_L	ADD_H	DATA0	DATA1	DATA2
    Response:
    TAG     TAG2    TAG3
    0x4     0       0
    """

    COMMAND_FORMAT_LIST = {
        "RegR": OrderedDict((('type', 0x51), ('len_w', 0x2), ('len_r', None), ('addr_l', None), ('addr_h', None),
                             ('data', {'length': {'len_r': -1}, 'size_hint_x': 1, 'disabled': True}))),
        "RegW": OrderedDict((('type', 0x51), ('len_w', None), ('len_r', 0), ('addr_l', None), ('addr_h', None),
                             ('data', {'length': {'len_w': -2}, 'size_hint_x': 1}))),
        "Raw": OrderedDict((('_len', None), ('data', {'length': {'_len': 0}, 'size_hint_x': 1}))),
        "IntR": OrderedDict((('type', 0x88), ('tag', 0x58), ('len_w', 2), ('len_r', None), ('addr_l', None), ('addr_h', None),
                             ('data', {'length': {'len_r': -1}, 'size_hint_x': 1, 'disabled': True}))),
        "Poll": OrderedDict((('type', 0x86), ('tag', 0x00))),
    }

    def __init__(self, cmd_name):
        self.cmd_name = cmd_name
        self.cmd_format = self.COMMAND_FORMAT_LIST[cmd_name].copy()

        super(Command, self).__init__()

    @classmethod
    def command_format_list(cls):
        return cls.COMMAND_FORMAT_LIST

    @classmethod
    def create(cls, cmd_name):
        if cmd_name in cls.COMMAND_FORMAT_LIST.keys():
            return Command(cmd_name)

    def name(self):
        return self.cmd_name

    def format(self):
        return self.cmd_format

class ElemNameBase(Scatter):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name', '-')
        super().__init__()

        self.ids['content'].text = self.to_widget_name(self.name)

    def to_widget_name(self, name):
        pat = re.compile('[^_]+')
        result = pat.search(self.name)
        if result:
            text = result.group().upper()
        else:
            text = '-'

        return text

class CommandElemNameWidget(ElemNameBase):
    pass

class CommandElemNameRotWidget(ElemNameBase):
    pass

class CommandElemNameWidget1(Scatter):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name', '-')
        super().__init__()

        self.ids['content'].text = self.name.upper()

class CommandElemNameRotWidget1(Scatter):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name', '-')
        super().__init__()

        self.ids['content'].text = self.name.upper()

class ElemValFixed(Label):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name', None)
        self.value = kwargs.get('value')
        super().__init__(text=format(self.value, '02X'))

class ElemValVarBase(TextInput):
    MAX_CHAR_VALUE = 0xff
    CHAR_TEXT_LENGTH = 2
    max_data_length = NumericProperty(1)
    event_data_valid = BooleanProperty(True)

    source_inst = ListProperty([])
    color_data_valid = ListProperty([])
    color_data_invalid = ListProperty([])
    #color_src_invalid = ListProperty([])

    def __init__(self, **kwargs):
        self.name = kwargs.pop('name', None)
        self.max_data_length = kwargs.pop('max_data_length', 0)
        self.pat_invalid_char = kwargs.pop('pat_invalid_char', re.compile('[^0-9a-fA-F]'))
        super().__init__(**kwargs)

    def valid_text_size(self):
        return len(self.text) < self.CHAR_TEXT_LENGTH

    def check_value(self, value, notify=True):
        fn = lambda a: a <= self.MAX_CHAR_VALUE
        result = False

        if isinstance(value, (tuple, list)):
            if len(value) == self.max_data_length:
                result = all(map(fn, value))
        else:
            result = fn(value)

        if notify:
            self.event_data_valid = result

        return result

    def insert_text(self, substring, from_undo=False):
        if self.valid_text_size():
            substring = self.pat_invalid_char.sub('', substring).upper()
            super().insert_text(substring, from_undo=from_undo)

    def on_event_data_valid(self, inst, status):
        if status:
            color = self.color_data_valid
        else:
            color = self.color_data_invalid

        self.set_background_color(color)
        #print(self.__class__.__name__, "on_event_data_valid", self.background_color, status)

    def set_source_ctrl(self, src_inst):
        if src_inst:
            self.source_inst.append(src_inst)

    def set_background_color(self, color):
        self.background_color = color
        for inst in self.source_inst:
            if hasattr(inst, 'set_background_color'):
                inst.set_background_color(color)

class ElemValVar2(ElemValVarBase):
    PAT_INVALID_CHAR = re.compile('[^0-9a-fA-F]')
    value = NumericProperty(0)
    REFRESH_TXT = False

    def __init__(self, **kwargs):
        super().__init__(pat_invalid_char=self.PAT_INVALID_CHAR,
                         **kwargs)

    # def check_input_data(self, new_char):
    #     text = self.text + new_char
    #     substring = self.pat_invalid_char.sub('', text)

    def get_data(self, text, default_val):
        value = default_val
        try:
            if len(text):
                value = int(text, 16)
            else:
                value = 0
        except Exception as e:
            print(self.__class__.__name__, "on_focus",
                  "switch text '{}' to int crashed, error={}".format(text, str(e)))

        return value

    def clear_data(self):
        self.text = ''
        self.value = 0

    def on_focus(self, inst, status):
        #print(self.__class__.__name__, "on_focus", status)
        if not status:
            self.value = self.get_data(self.text, self.value)
            self.check_value(self.value)
            if not len(self.text):
                self.on_value(self, 0)

    def on_value(self, inst, val):
        if self.REFRESH_TXT:
            self.text = format(val, 'X')

    # def on_text_validate(self):
    #     print(self.__class__.__name__, "on_text_validate", type(self.text), self.text)
    #     self.on_focus(self, False)

class ElemValVarX(ElemValVarBase):
    PAT_INVALID_CHAR = re.compile(r'[^0-9a-fA-F, \n]')
    #PAT_SPLIT_DELIMITED = re.compile('[ ,]+')
    PAT_VALID_CHAR = re.compile('[0-9a-fA-F]+')
    value = ListProperty([])

    def __init__(self, **kwargs):
        self.length_bias = kwargs.pop('length', {})
        self.size_hint_x_bias = kwargs.pop('size_hint_x', None)
        self.max_data_length = sum(self.length_bias.values())
        super().__init__(**kwargs, pat_invalid_char=self.PAT_INVALID_CHAR)

    def valid_text_size(self):
        #return self.max_data_length > 0
        return True

    def get_data(self):
        data = []
        text = self.text
        try:
            if len(text):
                #result = filter(None, self.pat_split_delimited.split(text))
                result = self.PAT_VALID_CHAR.findall(text)
                if len(result):
                    data = list(map(partial(int, base=16), result))
        except Exception as e:
            print(self.__class__.__name__, "get_data", "switch text '{}' to int crashed, error={}".format(text, str(e)))
        finally:
            #print(self.__class__.__name__, "get_data", data)
            return data

    def clear_data(self):
        self.text = ''
        self.value = []

    def on_focus(self, inst, status):
        #print(self.__class__.__name__, "on_focus", status)
        if not status:
            self.value = self.get_data()
            self.check_value(self.value)

    # def on_text_validate(self):
    #     print(self.__class__.__name__, "on_text_validate", type(self.text), self.text)
    #     self.on_focus(self, False)

    def set_input_size(self, inst, val):
        print(self.__class__.__name__, "on_input_size", val)
        if hasattr(inst, 'name'):
            size = sum(self.length_bias.values())
            if inst.name in self.length_bias.keys():
                size += val
            self.max_data_length = size
            if not self.disabled:
                self.check_value(self.value)

    def set_width_callback(self, dt):
        inst = self.root_ref()
        if inst:
            #print(self.__class__.__name__, "set_width_callback", inst.width, inst.minimum_width, self.width)
            self.width = (inst.width - (inst.minimum_width - self.width)) * self.size_hint_x_bias

    def set_widget_width(self, inst, width):
        self.root_ref = weakref.ref(inst)
        if isinstance(self.size_hint_x_bias, (int, float)):
            Clock.schedule_once(self.set_width_callback, -1)

class CommandElemValueWidget():

    def __new__(cls, **kwargs):
        value = kwargs.pop('value', None)
        if isinstance(value, int):
            base_cls = ElemValFixed
            kwargs = dict(**kwargs, value=value)
        elif isinstance(value, (dict,)):
            base_cls = ElemValVarX
            kwargs = dict(**kwargs, **value)
        else:   #None
            base_cls = ElemValVar2

        inst = base_cls.__new__(base_cls)
        inst.__init__(**kwargs)
        return inst

class ElementWidgetBase(BoxLayout):

    def sub_widget(self, name):
        return self._layout.get(name, None)

    def set_source_inst(self, src_inst):
        for child in self.children:
            if hasattr(child, 'set_source_ctrl'):
                child.set_source_ctrl(src_inst)

    def set_background_color(self, color):
        for child in self.children:
            if hasattr(child, 'set_background_color'):
                child.set_background_color(color)

class CommandElementWidget(ElementWidgetBase):
    def __init__(self, **kwargs):
        n = kwargs.pop('name', '-')
        v = kwargs.pop('value', None)
        super().__init__()

        self.name = n
        self._layout = OrderedDict()
        self._layout['name'] = widget_n = CommandElemNameWidget(name=n)
        self._layout['value'] = widget_v = CommandElemValueWidget(name=n, value=v)

        for n, v in self._layout.items():
            self.add_widget(v)

class ElemInfoWidget(Scatter):
    def __init__(self, **kwargs):
        super().__init__()
        self.name = kwargs.get('name', '')

        self._layout = {}

    def on_value_input(self, inst, val):
        if isinstance(val, (tuple, list)):
            count = len(val)
            widget = self.ids['content']
            if widget:
                if not count:
                    widget.text = ''
                else:
                    widget.text = "[color=e0e0e0]({:02X}h)[/color]".format(count)

            #print(self.__class__.__name__, widget.text)

    def sub_widget(self, name):
        return self._layout.get(name, None)

class CommandDataElementWidget(ElementWidgetBase):

    def __init__(self, **kwargs):
        n = kwargs.pop('name', '-')
        v = kwargs.pop('value', None)
        i = kwargs.pop('info', '')
        super().__init__()

        self.name = n
        self._layout = OrderedDict()
        self._layout['name'] = widget_n = CommandElemNameRotWidget(name=n)
        self._layout['value'] = widget_v = CommandElemValueWidget(name=n, value=v)
        self._layout['info'] = widget_i = ElemInfoWidget(name=i)

        if hasattr(widget_v, 'value'):
            widget_v.bind(value=widget_i.on_value_input)

        for n, v in self._layout.items():
            self.add_widget(v)

class ElemActionWidget(Button):

    def __init__(self, **kwargs):
        self._name = kwargs.get('name', None)
        text = kwargs.get('text', '-').upper()
        super().__init__(text=text)

        #self.disabled = True

    def name(self):
        return self._name

    # def on_press(self, *args):
    #     print(self.__class__.__name__, "on_press")

class CommandActionWidget(GridLayout):
    (ACTION_SEND, ACTION_CLEAR) = ('SEND', 'CLEAR')
    COMMAND_ACTION_LIST = {ACTION_CLEAR: 'C', ACTION_SEND: 'S'}

    def __init__(self, **kwargs):
        super().__init__()

        self._layout = {}
        for n, v in self.COMMAND_ACTION_LIST.items():
            self._layout[n] = w = ElemActionWidget(name=n, text=v)
            self.add_widget(w)
            w.bind(on_release=self.on_action)

        self.register_event_type("on_action")
        #print(self.__class__.__name__, "__init__", self.name())

    def sub_widget(self, name):
        return self._layout.get(name, None)

    def on_action(self, *args):
        #print(self.__class__.__name__, "on_action", *args)
        if len(args) and isinstance(args[0], ElemActionWidget):
            self.dispatch('on_action', args[0].name())

class CommandRowWidget(BoxLayout):
    def __init__(self, cmd_name):
        super().__init__()

        self.cmd = Command.create(cmd_name)
        format = self.cmd.format()
        if format:
            self.build_widget(format)

        self.register_event_type("on_action")

    def build_widget(self, cmd_format):
        print(self.__class__.__name__, "build_widget", cmd_format)
        #command formant
        for n, v in cmd_format.items():
            if isinstance(v, (type(None), int)):
                elem = CommandElementWidget(name=n, value=v)
                target = elem.sub_widget('value')
                if target:
                    if hasattr(target, 'on_text_validate'):
                        target.bind(on_text_validate=self.on_enter)
                self.ids['cmd'].add_widget(elem)

        #command data
        for n, v in cmd_format.items():
            if isinstance(v, dict):
                elem = CommandDataElementWidget(name=n, value=v)
                for child in reversed(self.ids['cmd'].children):
                    if child.name in v['length'].keys():
                        source = child.sub_widget('value')
                        if hasattr(source, 'value'):
                            elem.set_source_inst(source)
                            target = elem.sub_widget('value')
                            if target:
                                if hasattr(target, 'set_input_size') and hasattr(source, 'on_value'):
                                    source.bind(value=target.set_input_size)

                                if hasattr(target, 'on_text_validate'):
                                    target.bind(on_text_validate=self.on_enter)

                                if 'size_hint_x' in v.keys():
                                    self.bind(width=target.set_widget_width)

                            self.ids['data'].add_widget(elem)
                        break
        #control bar
        elem = CommandActionWidget()
        elem.bind(on_action=self.on_action)
        self.ids['set'].add_widget(elem)

    def get_data(self):
        data_format = self.cmd.format()

        data = {}
        value = []
        for child in self.ids['cmd'].children:
            if isinstance(child, CommandElementWidget):
                n_widget, v_widget = reversed(child.children)
                if not n_widget.name.startswith('-'):
                    data[n_widget.name] = v_widget.value

        for child in self.ids['data'].children:
            if isinstance(child, CommandDataElementWidget):
                n_widget, v_widget, i_widget = reversed(child.children)
                if not n_widget.name.startswith('-'):
                    data[n_widget.name] = v_widget.value

        a = set(data_format.keys()) ^ set(data.keys())
        if not len(a) or all(map(lambda x: x.startswith('_'), a)):
            for n, v in data_format.items():
                if not n.startswith('_'):
                    val = data[n]
                    if isinstance(val, (tuple, list)):
                        value.extend(val)
                    else:
                        value.append(val)

        print(self.__class__.__name__, "get_data", value)
        return value

    def clear_data(self):
        data_format = self.cmd.format()
        for child in self.ids['cmd'].children:
            if isinstance(child, CommandElementWidget):
                v_widget = child.sub_widget('value')
                if hasattr(v_widget, 'clear_data'):
                    v_widget.clear_data()

        for child in self.ids['data'].children:
            if isinstance(child, CommandDataElementWidget):
                v_widget = child.sub_widget('value')
                if hasattr(v_widget, 'clear_data'):
                    v_widget.clear_data()

    def on_enter(self, inst):
        if isinstance(inst, (ElemValVar2, ElemValVarX)):
            Clock.schedule_once(lambda dt: self.dispatch('on_action', CommandActionWidget.ACTION_SEND), 0)

    def on_action(self, *args):
        #print(self.__class__.__name__, "on_action", *args)
        if len(args) == 2 and isinstance(args[0], CommandActionWidget):
            self.dispatch('on_action', args[1])

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True

        #not dispatch touch if in self area
        if self.collide_point(*touch.pos):
            return True

class CommandContentArea(BoxLayout):
    pass

class CommandResultArea(BoxLayout):

    def on_command_send(self, *args):
        print(self.__class__.__name__, "on_command_send", args)

class DebugView(FloatLayout):
    activated = BooleanProperty(False)

    selected_command = StringProperty('')
    #history_command = ListProperty('')

    def __init__(self, win=None):
        super(DebugView, self).__init__()
        self._layout = {}
        self._root = win

        command_list = Command.command_format_list()
        self.w_cmd_tree = self.ids['commandtree']
        for cmd in command_list:
            name = str(cmd)
            widget = TreeViewWidget(text=name)
            cnode = self.w_cmd_tree.add_node(widget)
            self._layout[name] = w_cmd = CommandRowWidget(name)
            w_cmd.bind(on_action=self.on_action)

        self.w_cmd_tree.bind(on_select_widget=self.on_select_widget)

        self.w_cmd_content = self.ids['commandcontent']
        self.w_cmd_result = self.ids['commandresult']

    def sub_widget(self, name):
        return self._layout.get(name, None)

    def on_select_widget(self, tree, node):
        #print(self.__class__.__name__, "on_select_widget", node)
        cmd_name = node.name()
        current_cmd = self.selected_command
        if cmd_name != current_cmd:
            widget = self.sub_widget(cmd_name)
            self.w_cmd_content.clear_widgets()
            self.w_cmd_content.add_widget(widget)
            self.selected_command = cmd_name

    def on_selected_command(self, instance, cmd):
        #print(self.__class__.__name__, "on_selected_command", cmd)
        pass

    def on_action(self, *args):
        #print(self.__class__.__name__, "on_action", args)
        if len(args) == 2 and isinstance(args[0], CommandRowWidget):
            inst = args[0]
            action = args[1]
            if action == CommandActionWidget.ACTION_SEND:
                value = inst.get_data()
                if value:
                    self.send_data(value)
            elif action == CommandActionWidget.ACTION_CLEAR:
                #print(self.__class__.__name__, "")
                inst.clear_data()
                pass
            else:
                print(self.__class__.__name__, "on_action {} Not support".format(args))

    # def on_history_command(self, inst, cmd_list):
    #     print(self.__class__.__name__, "on_history_command", args)

        # name = str(cmd)
        # widget = TreeViewWidget(text=name)
        # cnode = self.w_cmd_tree.add_node(widget)

    def append_command_log(self, val):
        #self.history_command.append(val)
        widget = TreeViewDataWidget(value=val)
        tree = self.w_cmd_result.ids['commandhistroy']
        tree.add_node(widget)
        if isinstance(tree.parent, ScrollView):
            tree.parent.scroll_to(widget)

    def send_data(self, val):
        if len(val):
            #send the data
            self.append_command_log(val)

    def pop_data(self):
        tree = self.w_cmd_result.ids['commandhistroy']
        nodes = tree.root.nodes

        for node in nodes:
            if node.is_status(TreeViewDataWidget.INIT):
                node.status = TreeViewDataWidget.SEND
                # print(self.__class__.__name__, "pop_data", node)
                return node.value

    def append_msg_log(self, value):
        widget = TreeViewDataWidget(value=value)
        tree = self.w_cmd_result.ids['commandresponse']
        tree.add_node(widget)
        if isinstance(tree.parent, ScrollView):
            tree.parent.scroll_to(widget)

    def handle_data(self, value):
        tree = self.w_cmd_result.ids['commandhistroy']
        nodes = tree.root.nodes

        for node in nodes:
            if node.is_status(TreeViewDataWidget.SEND):
                node.status = TreeViewDataWidget.DONE
                break

        self.append_msg_log(value)

    def on_activated(self, inst, status):
        print(self.__class__.__name__, inst, status)
        if self._root:
            if status:
                self._root.add_widget(self)
            else:
                self._root.remove_widget(self)

    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        scancode= keycode[0]
        print('The key', scancode, 'have been pressed')
        print(' - text is %r' % text)
        print(' - modifiers are %r' % modifiers)
        if scancode == 100 and modifiers == ['ctrl']:
            print(self.__class__.__name__, self.activated)
            self.activated = not self.activated
            return True
        elif scancode == 27:
            if self.activated:
                self.activated = False
                return True
        elif scancode == 13:
            if self.activated:
                pass

    def keyboard_shortcut1(self, win, scancode, *largs):
        print(self.__class__.__name__, win, scancode, largs)
        modifiers = largs[-1]
        if scancode == 100 and modifiers == ['ctrl']:
            print(self.__class__.__name__, self.activated)
            self.activated = not self.activated
            return True
        elif scancode == 27:
            if self.activated:
                self.activated = False
                return True

    @staticmethod
    def register_debug_view(win=None):
        from kivy.core.window import Window

        if not win:
            win = Window

        view = DebugView(win=win)
        view._keyboard = Window.request_keyboard(
            view._keyboard_closed, view, 'text')
        if view._keyboard.widget:
            # If it exists, this widget is a VKeyboard object which you can, !use
            # to change the keyboard layout.
            pass
        view._keyboard.bind(on_key_down=view.on_keyboard_down)
        return view

    def _keyboard_closed(self):
        print('My keyboard have been closed!')
        #self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        #self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        print('The key', keycode, 'have been pressed')
        print(' - text is %r' % text)
        print(' - modifiers are %r' % modifiers)
        # Keycode is composed of an integer + a string
        # If we hit escape, release the keyboard
        if keycode[1] == 'escape':
            keyboard.release()
        #

if __name__ == '__main__':
    from kivy.app import App
    from kivy.lang import Builder

    from kivy.modules import inspector
    from kivy.core.window import Window

    class DebugViewApp(App):

        def build(self):
            root = DebugView()
            inspector.create_inspector(Window, root)
            return root

    DebugViewApp().run()