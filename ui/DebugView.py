from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
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
        "RegR": OrderedDict((('type', 0x51), ('len_w', 0x2), ('len_r', None), ('addr_l', None), ('addr_h', None))),
        "RegW": OrderedDict((('type', 0x51), ('len_w', None), ('len_r', 0), ('addr_l', None), ('addr_h', None), ('data', ['len_w', -2])))}

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

class CommandElemNameWidget(Label):
    def __init__(self, **kwargs):
        self.name = kwargs.pop('name', '-')
        super().__init__(**kwargs, text=self.name.upper())

class ElemValFixed(Label):
    def __init__(self, **kwargs):
        self.value = kwargs.get('value')
        super().__init__(text=format(self.value, '02x'))

class ElemValVarBase(TextInput):
    MAX_CHAR_VALUE = 0xff
    CHAR_TEXT_LENGTH = 2
    max_data_length = NumericProperty(1)
    data_valid = BooleanProperty(True)

    source_inst = ListProperty([])
    color_data_valid = ListProperty([])
    color_data_invalid = ListProperty([])
    #color_src_invalid = ListProperty([])

    def __init__(self, **kwargs):
        self.max_data_length = kwargs.pop('max_data_length', 0)
        self.pat_invalid_char = kwargs.pop('pat_invalid_char', re.compile('[^0-9a-fA-F]'))
        super().__init__(**kwargs)

    def valid_text_size(self):
        return len(self.text) < self.CHAR_TEXT_LENGTH

    def check_value(self, value, save_result=True):
        fn = lambda a: a <= self.MAX_CHAR_VALUE
        result = False

        if isinstance(value, (tuple, list)):
            if len(value) == self.max_data_length:
                result = all(map(fn, value))
        else:
            result = fn(value)

        if save_result:
            self.data_valid = result

        return result

    def insert_text(self, substring, from_undo=False):
        if self.valid_text_size():
            substring = self.pat_invalid_char.sub('', substring).upper()
            super().insert_text(substring, from_undo=from_undo)

    def on_data_valid(self, inst, status):
        if status:
            color = self.color_data_valid
        else:
            color = self.color_data_invalid

        self.set_background_color(color)
        #print(self.__class__.__name__, "on_data_valid", self.background_color, status)

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

    def get_input_data(self, text, default_val):
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

    def on_focus(self, inst, status):
        #print(self.__class__.__name__, "on_focus", status)
        if not status:
            self.value = self.get_input_data(self.text, self.value)
            self.check_value(self.value)
            if not len(self.text):
                self.on_value(self, 0)

    # def on_text_validate(self):
    #     print(self.__class__.__name__, "on_text_validate", type(self.text), self.text)
    #     if not len(self.text):
    #         self.text = '0'

    def on_value(self, inst, val):
        if self.REFRESH_TXT:
            self.text = format(val, 'X')

class ElemValVarX(ElemValVarBase):
    PAT_INVALID_CHAR = re.compile(r'[^0-9a-fA-F, \n]')
    #PAT_SPLIT_DELIMITED = re.compile('[ ,]+')
    PAT_VALID_CHAR = re.compile('[0-9a-fA-F]+')
    value = ListProperty([])

    def __init__(self, **kwargs):
        self.length_bias = kwargs.pop('bias', 0)
        self.max_data_length += self.length_bias
        super().__init__(**kwargs, pat_invalid_char=self.PAT_INVALID_CHAR)

    def valid_text_size(self):
        #return self.max_data_length > 0
        return True

    def get_input_data(self):
        data = []
        text = self.text
        try:
            if len(text):
                #result = filter(None, self.pat_split_delimited.split(text))
                result = self.PAT_VALID_CHAR.findall(text)
                if len(result):
                    data = list(map(partial(int, base=16), result))
        except Exception as e:
            print(self.__class__.__name__, "get_input_data", "switch text '{}' to int crashed, error={}".format(text, str(e)))
        finally:
            #print(self.__class__.__name__, "get_input_data", data)
            return data

    def on_focus(self, inst, status):
        #print(self.__class__.__name__, "on_focus", status)
        if not status:
            self.value = self.get_input_data()
            self.check_value(self.value)

    def set_input_size(self, inst, val):
        #print(self.__class__.__name__, "on_input_size", val)
        self.max_data_length = val + self.length_bias
        self.check_value(self.value)

class CommandElemValueWidget():

    def __new__(cls, **kwargs):
        value = kwargs.pop('value', None)
        if isinstance(value, int):
            base_cls = ElemValFixed
            kwargs = dict(**kwargs, value=value)
        elif isinstance(value, (list, tuple)):
            base_cls = ElemValVarX
            kwargs = {'bias': sum(value[1:])}
        else:   #None
            base_cls = ElemValVar2

        inst = base_cls.__new__(base_cls)
        inst.__init__(**kwargs)
        return inst

class CommandElementWidget(BoxLayout):
    def __init__(self, **kwargs):
        n = kwargs.pop('name', '-')
        v = kwargs.pop('value', None)
        super().__init__()

        self._name = n
        self._layout = {}
        self._layout['name'] = widget_n = CommandElemNameWidget(name=n)
        self._layout['value'] = widget_v = CommandElemValueWidget(value=v)

        for n, v in self._layout.items():
            self.add_widget(v)

        #print(self.__class__.__name__, "__init__", self.name())
    def name(self):
        return self._name

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

class ElemInfoWidget(Label):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', '')
        super().__init__()

    def on_value_input(self, inst, val):
        if isinstance(val, (tuple, list)):
            count = len(val)
            if not count:
                self.text = ''
            else:
                self.text = "%s %d (0x%X)" %(self.name, count, count)

class CommandDataElementWidget(CommandElementWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._layout['info'] = widget_i = ElemInfoWidget(name='Count')

        widget_v = self._layout['value']
        if hasattr(widget_v, 'value'):
            widget_v.bind(value=widget_i.on_value_input)

        self.add_widget(widget_i)

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

class CommandActionWidget(BoxLayout):
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
                self.ids['cmd'].add_widget(elem)
                #self.add_widget(elem)

        elem=CommandActionWidget()
        elem.bind(on_action=self.on_action)
        self.ids['cmd'].add_widget(elem)

        #command data
        for n, v in cmd_format.items():
            if isinstance(v, (tuple, list)):
                elem = CommandDataElementWidget(name=n, value=v)
                for child in reversed(self.ids['cmd'].children):
                #for child in reversed(self.children):
                    if child.name() in v:
                        source = child.sub_widget('value')
                        if hasattr(source, 'value'):
                            elem.set_source_inst(source)
                            source.bind(value=elem.sub_widget('value').set_input_size)
                            self.ids['data'].add_widget(elem)
                            #self.add_widget(elem)
                        break

    def get_data(self):
        data_format = self.cmd.format()

        data = {}
        value = []
        for child in self.ids['cmd'].children:
            if isinstance(child, CommandElementWidget):
                n_widget, v_widget = reversed(child.children)
                # if hasattr(v_widget, "focus"):
                #     setattr(v_widget, "focus", False)
                data[n_widget.name] = v_widget.value

        for child in self.ids['data'].children:
            if isinstance(child, CommandDataElementWidget):
                n_widget, v_widget, i_widget = reversed(child.children)
                # if hasattr(v_widget, "focus"):
                #     setattr(v_widget, "focus", False)
                #print(n_widget.name, v_widget.value)
                data[n_widget.name] = v_widget.value

        if not (set(data.keys()) ^ set(data_format.keys())):
            for n, v in data_format.items():
                val = data[n]
                if isinstance(val, (tuple, list)):
                    value.extend(val)
                else:
                    value.append(val)

        print(self.__class__.__name__, "get_data", value)
        return value

    def on_action(self, *args):
        #print(self.__class__.__name__, "on_action", *args)
        if len(args) == 2 and isinstance(args[0], CommandActionWidget):
            self.dispatch('on_action', args[1])

class CommandContentArea(BoxLayout):
    pass

class CommandResultArea(BoxLayout):

    def on_command_send(self, *args):
        print(self.__class__.__name__, "on_command_send", args)

class DebugView(FloatLayout):

    selected_command = StringProperty('')
    #history_command = ListProperty('')

    def __init__(self, *args, **kwargs):
        super(DebugView, self).__init__(*args, **kwargs)
        self._layout = {}

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
        print(self.__class__.__name__, "on_action", args)
        if len(args) == 2 and isinstance(args[0], CommandRowWidget):
            inst = args[0]
            action = args[1]
            if action == CommandActionWidget.ACTION_SEND:
                value = inst.get_data()
                if value:
                    self.send_data(value)
            elif action == CommandActionWidget.ACTION_CLEAR:
                #print(self.__class__.__name__, "")
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
        name = " ".join(map(lambda x: "{:02X}".format(x), val))
        widget = TreeViewWidget(text=name)
        result_tree = self.w_cmd_result.ids['commandhistroy']
        result_tree.add_node(widget)

    def send_data(self, val):
        if len(val):
            #send the data
            self.append_command_log(val)

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