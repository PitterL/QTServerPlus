from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.layout import Layout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.codeinput import CodeInput
from kivy.uix.togglebutton import ToggleButton, ToggleButtonBehavior
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.tabbedpanel import TabbedPanelHeader, TabbedPanelItem
from kivy.properties import ListProperty, StringProperty
import kivy.utils as utils

from tools.tree import mTree
from tools.hook import MessageHookServer, KeyboardShotcut
from tools.mem import PageElementMmap, ElementProcessor
from ui.WidgetExt import Action, PropAction, ValueAction, LayerActionWrapper, LayerBoxLayout
from ui.WidgetExt import LayerBehavior, ActionEvent,  ActionEventWrapper
from ui.TableElement import WidgetPageLayout
from ui.TableElement import WidgetPageContentRecycleElement
from ui.TableElement import WidgetPageContentTitleElement, WidgetPageContentDataElement
from ui.TableElement import WidgetRowTitleElement, WidgetRowElement, WidgetRowIndexElement, WidgetRowDataElement
from ui.TableElement import WidgetFieldElement, WidgetFieldLabelName, WidgetFieldButtonName, WidgetFieldLabelValue, WidgetFieldInputValue
from ui.TableElement import WidgetFieldIndexElement, WidgetFieldIndexName, WidgetFieldIndexButtonName, WidgetFieldTitleName
from ui.PageElement import WidgetPageMultiInstElement
from ui.PageElement import PageContext, WidgetPageMultiInstElement, WidgetPageElement, WidgetPageLayout

from collections import OrderedDict
import time
from hashlib import md5
import array, struct

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
                'class_idx_field': (WidgetFieldIndexElement, WidgetFieldIndexButtonName, None),
                'class_data_field': (WidgetFieldElement, WidgetFieldButtonName, None)}
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
        self.repo_tab = OrderedDict()
        repo_id = repo_mm.id()
        repo_range = repo_mm.report_range()
        einfo = repo_mm.extra_info()
        layout_kwargs = self.get_cls_layout_kwargs(repo_id)
        #tab_name = self.to_tab_name(repo_id, repo_range, einfo)

        tab_name = str(repo_id)
        print(self.__class__.__name__, "init_repo [repo {}{}] tab {}".format(repo_id, repo_range, tab_name))
        super(WidgetRepoElement, self).__init__(text=tab_name)

        self._content = WidgetPageLayout(repo_id, layout_kwargs)
        self.add_widget(self._content)

        #if page_mm.valid():
        self._content.create_page_content_widget(repo_mm)

        self.add_repo(repo_mm)

    def add_repo(self, new_repo_mm):
        repo_id = new_repo_mm.id()
        if not self.repo_tab:
            self.repo_tab[repo_id] = new_repo_mm
        else:
            ids = list(self.repo_tab.keys())
            rid = ids[-1]   #last one in table
            rmm = self.repo_tab[rid]
            if repo_id == rid + 1 and new_repo_mm.extra_info() == rmm.extra_info():
                self.repo_tab[repo_id] = new_repo_mm

        if repo_id in self.repo_tab.keys():
            self.text = self.to_tab_name()
            return repo_id

    def to_tab_name(self):
        ids = list(self.repo_tab.keys())
        st = ids[0]
        end = ids[-1]

        if st != end:
            name = "{}-{}".format(st, end)
        else:
            name = "{}".format(st)
        return name

    def on_action(self, inst, act):
        if inst != self:
            action = Action.parse(act, rid=tuple(self.repo_tab.keys()))
            self.action = action

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

class MessageSettingContent(PageContext):
    NAME = 'Setting'

    def __init__(self, **kwargs):
        super(MessageSettingContent, self).__init__(**kwargs)

    def create_repo_element(self, repo_insts):
        assert repo_insts

        for repo_mm in repo_insts:
            repo_id = repo_mm.id()
            repo_range = repo_mm.report_range()
            page_id = repo_mm.page_id()
            print(self.__class__.__name__, "create repo element [page {}] [repo {}{}]".format(page_id, repo_id, repo_range))
            st, end = repo_range
            major, _ = page_id

            parent_widget = self.get_layer(major)
            if not parent_widget:
                parent_widget = WidgetPageMultiInstElement(major, repo_range)
                self.add_layer(major, parent_widget)

            w_repo = parent_widget.last_layer()
            if not w_repo:
                w_repo = WidgetRepoElement(repo_mm)
                parent_widget.add_page(repo_id, w_repo)
            else:
                result = w_repo.add_repo(repo_mm)
                if not result:
                    w_repo = WidgetRepoElement(repo_mm)
                    parent_widget.add_page(repo_id, w_repo)

        return w_repo

    def insert_cb(self):
        self.switch_tab()
        #
        # if len(repo_insts) == 1:
        #     widget = WidgetRepoElement(major, repo_mm)
        #     self.add_layer(major, widget)
        # else:
        #     parent_widget = self.get_element(major)
        #     if not parent_widget:
        #         parent_widget = WidgetPageMultiInstElement(major, repo_range)
        #         self.add_layer(major, parent_widget)
        #
        #
        #
        # report_id = repo_mm.id()
        # repo_range = repo_mm.report_range()
        # page_id = repo_mm.page_id()
        # print(self.__class__.__name__, "create repo element", page_id, report_id, repo_range)
        # st, end = repo_range
        # major, _ = page_id
        # num_reports = end - st + 1
        # if num_reports > 1:
        #     parent_widget = self.get_element(major)
        #     if not parent_widget:
        #         parent_widget = WidgetPageMultiInstElement(major, repo_range)
        #         self.add_layer(major, parent_widget)
        #     widget = WidgetRepoElement(report_id, repo_mm)
        #     parent_widget.add_page(report_id, widget)
        # else:
        # return widget

class MessageTextLabel(LayerActionWrapper, CodeInput):
    #default text color
    color = ListProperty([])

    #bold font
    font_name_bold = StringProperty([])

    NAME = 'Message'

    MAX_LISTED_MESSAGE = 20

    class MsgFormat(object):
        def __init__(self, msgc, **param):
            self.m = msgc
            self.param = param

        def set_decorate(self, **kwargs):
            for k, v in kwargs:
                self.param[k] = v

        def head(self):
            major = self.m.major
            minor = self.m.minor
            parent_inst = self.m.parent_inst
            if parent_inst > 1:
                text_head = '[{}-{}]'.format(major, minor)
            else:
                text_head = '[{}]'.format(major)

            param = self.param.get('head')
            text_head = self.decorate(text_head, param)

            return text_head

        def body(self):
            content = []
            param = self.param.get('body')
            if param:
                param_n, param_v, param_t = param
            else:
                param_n = param_v = param_t = None

            for k, v in self.m.data.items():
                name = self.decorate(k, param_n)
                value = self.decorate(v, param_v)
                div = self.decorate('=', param_t)
                content.append(name + div + value)

            div = self.decorate(', ', param_t)
            text_body = div.join(content)

            return text_body

        def tail(self):
            param = self.param.get('head')
            text = '<{}>'.format(self.m.rid)
            text_tail = self.decorate(text, param)
            return text_tail

        def decorate(self, v, param):
            text = str(v)
            if not param:
                return text

            st = []
            end = []
            for n, v in param.items():
                if v is not None:
                    dc_s = '[{}={}]'.format(n, v)
                else:
                    dc_s = '[{}]'.format(n)
                dc_e = '[/{}]'.format(n)
                st.append(dc_s)
                end.append(dc_e)

            return ''.join(st) + text + ''.join(end)

        def output(self):
            return ' '.join([self.head(), self.body(), self.tail()])

    def __init__(self, **kwargs):
        ##markup=True,
        super(MessageTextLabel, self).__init__(**kwargs)
        self._cached_text = []

    def max_msg_count(self):
        return self.MAX_LISTED_MESSAGE

    def render(self, msgc):
        default_color = utils.get_hex_from_color(self.color)
        message_color = utils.get_hex_from_color(msgc.color)
        # param = {'head':{ 'color': default_color},
        #          'body':({'color': message_color, 'font':self.font_name_bold}, {'color': message_color}, {'color': default_color}),
        #          'tail':{'color': self.color}}
        param = {}
        ft_msg = MessageTextLabel.MsgFormat(msgc, **param)
        text = ft_msg.output()
        if text:
            self._cached_text.append(text)
            if len(self._cached_text) > self.max_msg_count():
                self._cached_text.pop(0)    #FIXME: Any better method than pop?

    def render_end(self):
        if self._cached_text:
            self.text = '\n'.join(self._cached_text)
            #self._cached_text = []

class MessageTextContent(ActionEventWrapper, ScrollView):
    NAME = 'Message'
    class MessagePackage(object):
        def __init__(self, *args):
            major, minor, parent_inst, rid, color, data = args
            self.major = major
            self.minor = minor
            self.parent_inst = parent_inst
            self.rid = rid
            self.color = color
            self.data = data

    def __init__(self, **kwargs):
        super(MessageTextContent, self).__init__(**kwargs)
        self.add_widget(MessageTextLabel())
#
# root = ScrollView(size_hint=(None, None), size=(500, 320),
#                 pos_hint={'center_x': .5, 'center_y': .5}, do_scroll_x=False)

    def max_msg_count(self):
        if self.children:
            layout = self.children[0]
            return layout.max_msg_count()

        return 0

    def render(self, msgc):
        if self.children:
            layout = self.children[0]
            return layout.render(msgc)

    def render_end(self):
        if self.children:
            layout = self.children[0]
            return layout.render_end()

class WidgetMsgBaseButton(ButtonBehavior, Label):
    pass

class WidgetMsgCtrlButton(ActionEvent, ToggleButtonBehavior, WidgetMsgBaseButton):
    #default border size
    border_default = ListProperty([])

    #button pressed border size
    border_active = ListProperty([])

    #default border color
    border_color_default = ListProperty([])

    #button pressed border size
    border_color_active = ListProperty([])

    def __init__(self, name):
        self._name = name
        self.border_color_active = self._hash_color()
        super(WidgetMsgCtrlButton, self).__init__(text=name)

    def _hash_color(self):
        #here general the color for the button by hash map, you could any other method
        try:
            value = int(self._name)
        except:
            value = 0

        words = array.array('b', [value])
        hash = md5()
        hash.update(words)
        value = hash.digest()
        data = struct.unpack_from('BBB', value)

        r, g, b = [ v / 255 for v in data]

        return (r, g, b, 1)

    def name(self):
        return self._name

    def write(self, value):
        action = PropAction(name=self.text, value=value, color=self.border_color_active, time=time.time())
        print(self.__class__.__name__, "write", action)
        self.action = action

    def on_state(self, inst, state):
        print(self.__class__.__name__, inst, state)
        #self.action = {'name':'ctrl', 'id': self.text, 'state':value}
        if state == 'down':
            self.border_color = self.border_color_active
            self.border = self.border_active
            val = True
        else:
            self.border_color = self.border_color_default
            self.border = self.border_default
            val = False

        self.write(val)

    def on_disposal(self, inst, disposal):
        if inst != self:
            target_name = disposal.get('target')
            widget_name = disposal.get('widget')
            name = disposal.get('name')
            value = disposal.get('value')
            v = self.property(name, True)
            if v and widget_name == self.__class__.__name__ and \
                    (target_name == self.name() or target_name == '-'):
                    v.set(self, value)
                    print(self.__class__.__name__, 'state', self.state, v)

class WidgetMsgSwitchButton(ActionEvent, WidgetMsgBaseButton):
    def __init__(self, props):
        self.props = props
        self.curr = 0
        super(WidgetMsgSwitchButton, self).__init__(text=props[0])

    def next_curr(self, curr=None):
        if curr is None:
            curr = self.curr + 1
        curr %= len(self.props)
        self.curr = curr
        return curr

    def switch(self, curr=None):
        curr = self.next_curr(curr)
        self.text = self.props[curr]

    def write(self):
        for i, s in enumerate(self.props):
            if i == self.curr:
                action = PropAction(name=s, value=True, time=time.time())
            else:
                action = PropAction(name=s, value=False, time=time.time())
            print(self.__class__.__name__, "write", action)
            self.action = action

    def on_release(self):
        self.switch()
        self.write()

class WidgetMsgRegAllButton(WidgetMsgSwitchButton):
    NAME = 'reg_all'

    selected = StringProperty('')

    def name(self):
        return self.NAME

    def on_selected(self, inst, selected):
        for i, prop in enumerate(self.props):
            if prop == selected:
                self.switch(i)
                self.write()
                break

    def on_disposal(self, inst, disposal):
        if inst != self:
            target_name = disposal.get('target')
            widget_name = disposal.get('widget')
            name = disposal.get('name')
            value = disposal.get('value')
            v = self.property(name, True)
            if v and widget_name == self.__class__.__name__ and \
                    (target_name == self.name() or target_name == '-'):
                    v.set(self, value)
                    print(self.__class__.__name__, 'state', self.state, v)

class MessageBaseControlBar(LayerBoxLayout):

    def __init__(self, name, ctrl_list, cls_btn, **kwargs):
        self._name = name
        super(MessageBaseControlBar, self).__init__(**kwargs)
        for ctrl in ctrl_list:
            self.add_layer(ctrl, cls_btn(ctrl))

    def on_action(self, inst, act):
        if inst != self:
            self.action = Action.parse(act, id=self._name)

class MessageGlobelControlBar(MessageBaseControlBar):
    NAME = 'ctrl_g'
    CTRL_LIST = (('Mark','Raw'), (MessageTextContent.NAME,MessageSettingContent.NAME))
    def __init__(self, **kwargs):
        super(MessageGlobelControlBar, self).__init__(self.NAME, self.CTRL_LIST, WidgetMsgSwitchButton, **kwargs)

class MessageRegControlBar(MessageBaseControlBar):
    NAME = 'ctrl_r'
    REG_ALL = 'All'
    REG_CLR = 'Clr'
    CTRL_LIST = ((REG_CLR, REG_ALL),)  #name, state
    def __init__(self, **kwargs):
        super(MessageRegControlBar, self).__init__(self.NAME, self.CTRL_LIST, WidgetMsgRegAllButton, **kwargs)

    def create_repo_element(self, repo_insts):
        repo_mm = repo_insts[0]
        major, _ = repo_mm.page_id()
        seq = self.count()
        self.add_layer(major, WidgetMsgCtrlButton(str(major)))

    def cast(self, **kwargs):
        disposal = ValueAction(**kwargs, time=time.time())
        print(self.__class__.__name__, "cast", disposal)
        self.disposal = disposal

    def on_action(self, inst, act):
        if inst != self:
            print(self.__class__.__name__, inst, act)
            action = Action.parse(act, id=self._name)
            if action.is_event('prop'):
                if isinstance(inst, WidgetMsgRegAllButton):
                    name = action.get('name')
                    value = action.get('value')
                    if value:
                        if name == MessageRegControlBar.REG_ALL:
                            kwargs = dict(name='state', value='down', target='-', widget='WidgetMsgCtrlButton')
                            self.cast(**kwargs)
                        elif name == MessageRegControlBar.REG_CLR:
                            kwargs = dict(name='state', value='normal', target='-', widget='WidgetMsgCtrlButton')
                            self.cast(**kwargs)
                else:
                    self.action = action

class MessageContent(LayerBehavior, ActionEventWrapper, BoxLayout):
    NAME = 'Content'
    def __init__(self, **kwargs):
        super(MessageContent, self).__init__(**kwargs)
        self._cls_bar_list = {MessageGlobelControlBar: True,
                        MessageRegControlBar: True,
                        MessageSettingContent: False,
                        MessageTextContent: True}

        for cls, state in self._cls_bar_list.items():
            w = cls()
            self.add_layer(cls.NAME, w)
            if state:
                self.insert(cls.NAME)

        self.repo_mmap = {}
        self.raw_data = []
        self.filter = dict(reg=dict(), rid=dict())
        self._elemproc = ElementProcessor()
        self._hook_server = MessageHookServer()

    def create_repo_element(self, repo_insts):
        for layer in self.get_layers():
            if hasattr(layer, 'create_repo_element'):
                layer.create_repo_element(repo_insts)

    def set_repo_mmap_tab(self, mmap):
        self.repo_mmap.update(mmap)

    def get_repo_mmap_tab(self, rid=None):
        if rid is not None:
            if rid in self.repo_mmap.keys():
                return self.repo_mmap[rid]
        else:
            return self.repo_mmap

    def change_bar_status(self, name):
        if name in self._cls_bar_list.keys():
            status = self._cls_bar_list[name]
            self._cls_bar_list[name] = not status
            return status

    def insert(self, name):
        layer = self.get_layer(name)
        if layer:
            if not layer.parent:
                self.add_widget(layer)
                if hasattr(layer, 'insert_cb'):
                    layer.insert_cb()

    def remove(self, name):
        layer = self.get_layer(name)
        if layer:
            if layer in self.children:
                self.remove_widget(layer)

    def _save_data(self, data):
        self.raw_data.append(data)

    def _parse_data(self, data):
        #print(self.__class__.__name__, "parse data", data)

        rid = data[0]
        msg_mm = self.get_repo_mmap_tab(rid)
        if not msg_mm:
            print(self.__class__.__name__, "Unknown data", data)
            return

        size = msg_mm.get_value_size()
        msg_mm.set_values(data[1: size + 1])

        self._hook_server.handle(msg_mm)
        self._elemproc.clear()
        #print(self.__class__.__name__, "parse data", major, minor, data)

        # reg control bar is enabled
        # branch = ('all', str(major))
        # data = mTree.get_nested_leaf_value(self.filter, ('reg', branch))
        # if data:
        #     enabled, color = data
        #     for i, row_elem in enumerate(msg_mm):
        #         idx_name = row_elem.desc.name()
        #         # rid row disable bit if off
        #         if not mTree.get_leaf_value(
        #                 self.filter, ('rid', rid, WidgetRowIndexElement.NAME, i, idx_name)):
        #
        #             for name, field in row_elem:
        #                 # rid field disable bit is off
        #                 if name.startswith(PageElementMmap.RowDesc.RSV_DATA_NAME):
        #                     continue
        #
        #                 if not mTree.get_leaf_value(
        #                         self.filter, ('rid', rid, WidgetRowDataElement.NAME, i, field.value)):
        #                     p.push(name, field, idx_name, len(row_elem))


        major, minor = msg_mm.page_id()
        parent_inst = msg_mm.parent_inst()
        branch = ('all', str(major))
        config = mTree.get_nested_leaf_value(self.filter, ('reg', branch))
        if config:
            enabled, color = config
            if enabled:
                for row_elem in msg_mm:
                    row_name = row_elem.desc.name()
                    # rid row disable bit if off
                    row_fields_num = len(row_elem)
                    for name, field in row_elem:
                        # rid field disable bit is off
                        if not name.startswith(PageElementMmap.RowDesc.RSV_DATA_NAME) and \
                            not mTree.get_leaf_value(
                                self.filter, ('rid', rid, name)):
                            self._elemproc.push(name, field, row_name, row_fields_num)

                msg_out = self._elemproc.output()
                return MessageTextContent.MessagePackage(major, minor, parent_inst, rid, color, msg_out)

    def render(self, data):
        layer = self.get_layer(MessageTextContent.NAME)
        assert layer

        # for data in self.raw_data[-layer.max_msg_count():]:
        #     msgc = self._parse_data(data)
        #     if msgc:
        #         layer.render(msgc)
        msgc = self._parse_data(data)
        if msgc:
            layer.render(msgc)

        layer.render_end()

    def handle_data(self, data):
        self._save_data(data)
        self.render(data)

    def set_reg_filter(self, kwargs):
        #reg_filter = self.filter['reg']

        name = kwargs.get('name')
        value = kwargs.get('value')
        color = kwargs.get('color')

        mTree.build(self.filter, ('reg', name, (value, color)))

    def set_rid_filter(self, kwargs):
        #rid_filter = self.filter['rid']

        rid = kwargs.get('rid')
        zone = kwargs.get('zone')
        #row = kwargs.get('row')
        #col = kwargs.get('col')
        name = kwargs.get('name')
        value = kwargs.get('value')

        if zone == WidgetRowDataElement.NAME:
            mTree.build(self.filter, ('rid', rid, name, value))

    def on_event_control_bar(self, event):
        name = event.get('name')
        value = event.get('value')

        if name in self.get_layer_names():
            if value:
                self.insert(name)
            else:
                self.remove(name)

    def on_event_reg_bar(self, event):
        self.set_reg_filter(event)

    def on_event_setting_content(self, event):
        self.set_rid_filter(event)

    def on_action(self, inst, act):
        if inst != self:
            print(self.__class__.__name__, inst, act)
            action = Action.parse(act)
            if action.is_event('prop'):
                if action.is_id(MessageGlobelControlBar.NAME):
                    self.on_event_control_bar(action)
                elif action.is_id(MessageRegControlBar.NAME):
                    self.on_event_reg_bar(action)
                elif action.is_id(MessageSettingContent.NAME):
                    self.on_event_setting_content(action)
            #self.action = action

class MessageView(LayerActionWrapper, FloatLayout):
    NAME = 'w_msg'
    KeyEvent = {
        'ctrl_m': (109, ('ctrl',)),  # ctrl + d
        'esc': (27, None)}  # esc

    def __init__(self, **kwargs):
        super(MessageView, self).__init__(**kwargs)
        self.add_layer(MessageContent.NAME, MessageContent())

    @staticmethod
    def register_message_view():
        view = MessageView()
        for name, key in MessageView.KeyEvent.items():
            watch = key + (MessageView._on_keyboard_down,)
            KeyboardShotcut.register_keyboard(watch, view, name)

        return view

    @staticmethod
    def _on_keyboard_down(root, inst, event):
        if event == 'ctrl_m':
            activated = inst not in root.children
        elif event == 'esc':
            activated = False
        else:
            return

        if activated:
            if inst not in root.children:
                root.add_widget(inst)
                return True
        else:
            if inst in root.children:
                root.remove_widget(inst)
                return False

    def create_repo_element(self, repo_insts):
        assert repo_insts

        # for layer in self.get_layers():
        #     if hasattr(layer, 'create_repo_element'):
        #         layer.create_repo_element(repo_insts)
        layer = self.get_layer(MessageContent.NAME)
        if layer:
            layer.create_repo_element(repo_insts)

    def set_repo_mmap_tab(self, mmap):
        layer = self.get_layer(MessageContent.NAME)
        if layer:
            layer.set_repo_mmap_tab(mmap)

    def get_repo_mmap_tab(self, rid):
        layer = self.get_layer(MessageContent.NAME)
        if layer:
            return layer.get_repo_mmap_tab(rid)

    def handle_data(self, data):
        assert(data)

        #print(self.__class__.__name__, 'data', "array.{},".format(data))

        # rid = data[0]
        # msg_mm = self.get_repo_mmap_tab(rid)
        # if msg_mm:
        #     major, minor = msg_mm.page_id()
        #     report_range = msg_mm.report_range()
        #     self._hook_msg.handle(major, minor, rid, report_range, data)
        #
        #     layer = self.get_layer(MessageContent.NAME)
        #     if layer:
        #         layer.handle_data(data)
        # else:
        #     print(self.__class__.__name__, "Unknown data", data)
        layer = self.get_layer(MessageContent.NAME)
        if layer:
            layer.handle_data(data)

    def cast(self, **kwargs):
        disposal = ValueAction(**kwargs, time=time.time())
        print(self.__class__.__name__, "cast", disposal)
        self.disposal = disposal

    def write(self, op, value):
        action = PropAction(name=self.NAME, value=value, op=op, time=time.time())
        print(self.__class__.__name__, "write", action)
        self.action = action

    def enable_irq(self):
        self.write('irq', True)

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

            KeyboardShotcut()
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

            def sort_key(repo):
                (major, minor), (st, end) = repo
                if isinstance(major, str):
                    result = (ord(major) - ord('z') - 1, inst)
                else:
                    result = (major, minor, st, end)

                #print("sort_key", result)
                return result

            report_table = chip.get_reg_reporer()
            for page_id, repo_range in sorted(report_table.items(), key=sort_key):
                major, minor = page_id
                st, end = repo_range
                if minor == 0:  #only need inst 0 report list
                    repo_insts = []
                    for repo_id in range(st, end + 1):
                        repo_mm = chip.get_msg_map_tab(repo_id)
                        if repo_mm:
                            repo_insts.append(repo_mm)
                    root.create_repo_element(repo_insts)
            #Clock.schedule_once(lambda dt: root.switch_tab())
            return root

    MessageViewApp().run()