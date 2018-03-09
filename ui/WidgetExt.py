from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.properties import DictProperty, BooleanProperty
from kivy.factory import Factory

from collections import OrderedDict

class Action(dict):
    def is_event(self, name):
        e = self.get('event')
        if e:
            return e == name

    def is_op(self, name):
        def check_op(op, name):
            if isinstance(name, (tuple, list)):
                for n in name:
                    result = check_op(op, n)
                    if result:
                        return
            else:
                return op.startswith(name)

        op = self.get('op')
        if op:
            return check_op(op, name)

    def is_id(self, name):
        id = self.get('id')
        if id:
            return id == name

    def is_name(self, name):
        n = self.get('name')
        if n:
            return n == name

    @staticmethod
    def parse(action, **kwargs):
        return Action(**action, **kwargs)

    def set(self, **kwargs):
        return Action(**self)

class ValueAction(Action):
    def __init__(self, **kwargs):
        super(ValueAction, self).__init__(event='value', **kwargs)

class PropAction(Action):
    def __init__(self, **kwargs):
        super(PropAction, self).__init__(event='prop', **kwargs)

class ActionEvent(object):
    action = DictProperty({})

    def on_action(self, inst, action):
        #override this action to process action, of call directly report action to higher level
        if inst is not self:
            print(self.__class__.__name__, "on_action", inst, action)
            self.action = action

    def action_bind(self, widget):
        action = widget.property('action', True)
        if action:
            #print(self.__class__.__name__, "actionbind:", widget, "--", self)
            widget.bind(action=self.on_action)

    def action_unbind(self, widget):
        action = widget.property('action', True)
        if action:
            #print(self.__class__.__name__, "action unbind:", widget, "--", self)
            widget.unbind(action=self.on_action)

    disposal = DictProperty({})

    def on_disposal(self, inst, disposal):
        #override this disposal to process command, of set directly property from higher level
        if inst is not self:
            print(self.__class__.__name__, "on_disposal", inst, disposal)
            self.disposal = disposal

    def disposal_bind(self, widget):
        if hasattr(widget, 'on_disposal'):
            #print(self.__class__.__name__, "disposal bind:", self, "--", widget)
            self.bind(disposal=widget.on_disposal)

    def disposal_unbind(self, widget):
        if hasattr(widget, 'on_disposal'):
            #print(self.__class__.__name__, "disposal unbind:", self, "--", widget)
            self.unbind(disposal=widget.on_disposal)

Factory.register('ActionEvent', cls=ActionEvent)

class ActionEventWrapper(ActionEvent):
    def add_widget(self, widget, *args):
        self.action_bind(widget)
        self.disposal_bind(widget)
        super(ActionEventWrapper, self).add_widget(widget, *args)

    def remove_widget(self, widget):
        self.action_unbind(widget)
        self.disposal_bind(widget)
        super(ActionEventWrapper, self).remove_widget(widget)

    def clear_widgets(self, **kwargs):
        children = kwargs.get('children', self.children)
        for child in children:
            self.action_unbind(child)
            child.disposal_unbind(self)

        super(ActionEventWrapper, self).clear_widgets(**kwargs)

Factory.register('ActionEventWrapper', cls=ActionEventWrapper)

class LayerBehavior(object):
    def __init__(self, **kwargs):
        self.__layers = OrderedDict()
        super(LayerBehavior, self).__init__(**kwargs)

    def __iter__(self):
        return iter(self.__layers.items())

    # def __len__(self):
    #     return len(self.__layers)
    def count(self):
        return len(self.__layers)

    def keys(self):
        return self.__layers.keys()

    def values(self):
        return self.__layers.values()

    def first_layer(self):
        keys = self.__layers.keys()
        if keys:
            return self.__layers[list(keys)[0]]

    def last_layer(self):
        keys  = self.__layers.keys()
        if keys:
            return self.__layers[list(keys)[-1]]

    def get_layer_names(self):
        return tuple(self.__layers.keys())

    def get_layers(self):
        return tuple(self.__layers.values())

    def get_layer(self, name):
        return self.__layers.get(name)

    def add_layer(self, name, widget):
        assert name not in self.__layers.keys()
        self.__layers[name] = widget

    def remove_layer(self, name):
        assert name in self.__layers
        if name in self.__layers.keys():
            w = self.__layers[name]
            del self.__layers[name]
            return w
    #DON'T OFFER CLEAR INTERFACE
    # def clear_layer(self):
    #     self.__layers.clear()

    def add_child_layer(self, child_name_nested, widget):
        assert isinstance(child_name_nested, (tuple, list))
        if len(child_name_nested) > 1:
            layout = self.get_layer(child_name_nested[0])
            assert isinstance(layout, LayerBehavior)
            return layout.add_child_layer(child_name_nested[1:], widget)
        else:
            self.add_layer(child_name_nested[0], widget)
            return self

    def get_child_layer(self, child_name_nested):
        assert isinstance(child_name_nested, (tuple, list))
        if len(child_name_nested) > 1:
            layout = self.get_layer(child_name_nested[0])
            #assert isinstance(layout, LayerBehavior)
            return layout.get_child_layer(child_name_nested[1:])
        else:
            return self.get_layer(child_name_nested[0])

Factory.register('LayerBehavior', cls=LayerBehavior)

class LayerActionWrapper(LayerBehavior, ActionEvent):
    def add_layer(self, name, widget):
        super(LayerActionWrapper, self).add_layer(name, widget)
        super(LayerActionWrapper, self).action_bind(widget)
        super(LayerActionWrapper, self).disposal_bind(widget)
        super(LayerActionWrapper, self).add_widget(widget)

    def remove_layer(self, name):
        w = super(LayerActionWrapper, self).remove_layer(name)
        if w:
            super(LayerActionWrapper, self).action_unbind(w)
            super(LayerActionWrapper, self).disposal_unbind(w)
            super(LayerActionWrapper, self).remove_widget(w)

    def clear_layer(self):
        for layout in super(LayerActionWrapper, self).get_layers():
            if isinstance(layout, LayerActionWrapper):
                layout.clear_layer()
            else:
                super(LayerActionWrapper, self).remove_layer(layout)

Factory.register('LayerActionWrapper', cls=LayerActionWrapper)

class LayerBoxLayoutBase(LayerBehavior, ActionEvent, BoxLayout):

    def __init__(self, **kwargs):
        #self.prop_set_default_minimum_height = kwargs.pop('set_minimum_height', True)
        super(LayerBoxLayoutBase, self).__init__(**kwargs)  #why couldn't use this?

    def add_layer(self, name, widget):
        super(LayerBoxLayoutBase, self).add_layer(name, widget)
        self.action_bind(widget)
        self.disposal_bind(widget)
        self.add_widget(widget)

    def remove_layer(self, name):
        if name in super(LayerBoxLayoutBase, self).get_layer_names():
            w = super(LayerBoxLayoutBase, self).get_layer(name)
            self.action_unbind(w)
            self.disposal_unbind(w)
            self.remove_widget(w)
            super(LayerBoxLayoutBase, self).remove_layer(name)

    def detach_layer(self):
        for n in super(LayerBoxLayoutBase, self).get_layer_names():
            self.remove_layer(n)

    def clear_layer(self):
        for layout in super(LayerBoxLayoutBase, self).get_layers():
            if isinstance(layout, LayerBoxLayoutBase):
                layout.clear_layer()
            else:
                self.remove_layer(layout)

class LayerBoxLayout(LayerBoxLayoutBase):
    set_minimum_height = BooleanProperty(True)

    def set_default_minimum_height(self):
        shw, shh = self.size_hint
        if not shh:
            if self.children:
                if self.orientation == 'horizontal':
                    height = self.children[-1].height
                else:
                    height = sum([child.height for child in self.children])
                #print(self.__class__.__name__, "set default height", self.height, self.minimum_height, height)
                self.height = self.minimum_height = height
        #self.height = self.minimum_height

    def on_children(self, *args):
        # RecycleView has some bug for fresh height = self.minimum_height, we should adjust it may manually
        # so we should as the order, all children are created first, then added to parent widget
        if self.set_minimum_height:
            self.set_default_minimum_height()

Factory.register('LayerBoxLayout', cls=LayerBoxLayout)

class KeyboardShotcut(object):
    WatchLists = {}
    KeyHandle = None

    def __init__(self, **kwargs):
        if not KeyboardShotcut.KeyHandle:
            from kivy.core.window import Window
            KeyboardShotcut.KeyHandle = Window.bind(on_keyboard=KeyboardShotcut.keyboard_shortcut)

        super(KeyboardShotcut, self).__init__(**kwargs)

    @staticmethod
    def register_keyboard(key_watch_struct, inst, *param):
        #(scancode, modifiers, callback)
        if len(key_watch_struct) == 3:
            KeyboardShotcut.WatchLists[key_watch_struct] = (inst, param)
    #
    # def request_keyboard(self, win):
    #     from kivy.core.window import Window
    #
    #     if not win:
    #         win = Window
    #
    #     self._keyboard = win.request_keyboard(
    #         self._keyboard_closed, self, 'text')
    #     if self._keyboard.widget:
    #         # If it exists, this widget is a VKeyboard object which you can, !use
    #         # to change the keyboard layout.
    #         pass
    #     self._keyboard.bind(on_key_down=self.on_keyboard_down)
    #
    # def _keyboard_closed(self):
    #     print('My keyboard have been closed!')
    #     # self._keyboard.unbind(on_key_down=self._on_keyboard_down)
    #     # self._keyboard = None
    #
    # def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
    #     # print('The key', keycode, 'have been pressed')
    #     # print(' - text is %r' % text)
    #     # print(' - modifiers are %r' % modifiers)
    #     # Keycode is composed of an integer + a string
    #     # If we hit escape, release the keyboard
    #     if keycode[1] == 'escape':
    #         keyboard.release()
    #         #
    #
    # def keyboard_shortcut1(self, win, scancode, *largs):
    #     #print(self.__class__.__name__, win, scancode, largs)
    #     modifiers = largs[-1]
    #     if scancode == 100 and modifiers == ['ctrl']:
    #         print(self.__class__.__name__, self.activated)
    #         self.activated = not self.activated
    #         return True
    #     elif scancode == 27:
    #         if self.activated:
    #             self.activated = False
    #             return True

    @staticmethod
    def keyboard_shortcut(win, scancode, *largs):
        #print(self.__class__.__name__, win, scancode, largs)
        modifiers = largs[-1]
        for watch in KeyboardShotcut.WatchLists.items():
            (code, mod, fn), (inst, param) = watch
            if scancode == code:
                if isinstance(mod, (list, tuple)):
                    if tuple(mod) != tuple(modifiers):
                        continue
                else:
                    if len(modifiers) != 1 or modifiers[0] != mod:
                        continue

                fn(win, inst, *param)

        return True
