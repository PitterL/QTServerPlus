from kivy.uix.actionbar import ActionBar, ActionView, ActionButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import DictProperty
from kivy.clock import Clock

from ui.PageElement import PageContext
from ui.WidgetExt import ActionEvent, ActionEventWrapper

from functools import partial
#import time

class ActionEventButton(ActionButton):
    def get_op(self):
        return self.text.lower()

    def set_action(self, dt):
        assert self.parent.property('action', True)
        self.parent.action = {'op': self.get_op(), 'time': dt}

    def on_state(self, inst, value):
        print(self.__class__.__name__, inst, value)
        if value == 'normal': #un focus any other object then schedule
            Clock.schedule_once(lambda dt: self.set_action(dt))
                #self.set_action(dt)
            # if self.parent:
            #     if self.parent.property('action', True):
            #         import time
            #         dt = time.time()
            #         self.parent.action = {'op': self.get_action(), 'time': dt}
        # fn = partial(self.set_action, action)
        # Clock.schedule_once(lambda dt: fn(dt))

class ActionEventView(ActionEvent, ActionView):
    def on_action(self, inst, action):
        print(self.__class__.__name__, inst, action)

# class ActionEventView(ActionEvent, ActionView):
#
#     def on_action(self, inst, action):
#         print(self.__class__.__name__, inst, action)
#
#     def add_widget(self, widget, *args):
#         self.action_bind(widget)
#         super().add_widget(widget, *args)
#
#     def remove_widget(self, widget):
#         self.action_unbind(widget)
#         super().remove_widget(widget)
#
#     def clear_widgets(self, children=None):
#         if not children:
#             children = self.children
#
#         for child in children:
#             self.action_unbind(child)
#
#         super().clear_widgets(children)
#
#     def on_width(self, width, *args):
#         super().on_width(width, *args)

class ActionEventBar(ActionEventWrapper, ActionBar):
    pass

class UpControlBar(ActionEventBar):
    def on_action(self, inst, action):
        if inst != self:
            self.action = dict(source=self.__class__.__name__, **action)

class DownControlBar(ActionEventBar):
    pass
#
# class LeftControlBar(Button):
#     def __init__(self, **kwargs):
#         super(LeftControlBar, self).__init__(**kwargs)
#         self.text = 'Left'
#
# class RightControlBar(Button):
#     def __init__(self, **kwargs):
#         super(RightControlBar, self).__init__(**kwargs)
#         self.text = 'Right'

class CenterContentBar(PageContext):
    pass
#
# class CenterMessageBar(Button):
#     pass

if __name__ == "__main__":
    from kivy.app import App
    from kivy.lang import Builder
    import array
    import os

    from MainUi import MainUi
    from server.devinfo import Page, MemMapStructure
    from ui.WidgetExt import LayerBoxLayout

    MainUi.load_ui_kv_file(os.curdir)

    class DeviceWindowApp(App):
        def build(self):
            root = LayerBoxLayout(orientation='vertical')
            root.add_layer('up', UpControlBar())
            root.add_layer('down', DownControlBar())

            return root


    DeviceWindowApp().run()