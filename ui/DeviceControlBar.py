from kivy.uix.actionbar import ActionBar, ActionView, ActionButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import DictProperty
from ui.PageElement import PageContext

from ui.WidgetExtension import ActionEvent, ActionBehavior

class ActionEventButton(ActionButton):
    def get_action(self):
        return self.text.lower()

    def on_state(self, inst, value):
        print(self.__class__.__name__, inst, value)
        if self.parent:
            action = self.parent.property('action', True)
            if action:
                self.parent.action = {'op': self.get_action()}

class ActionEventView(ActionEvent, ActionView):

    def on_action(self, inst, action):
        print(self.__class__.__name__, inst, action)

    def add_widget(self, widget, *args):
        self.action_bind(widget)
        super().add_widget(widget, *args)

    def remove_widget(self, widget):
        self.action_unbind(widget)
        super().remove_widget(widget)

    def clear_widgets(self, children=None):
        if not children:
            children = self.children

        for child in children:
            self.action_unbind(child)

        super().clear_widgets(children)

    def on_width(self, width, *args):
        super().on_width(width, *args)

class ActionEventBar(ActionBehavior, ActionBar):
    pass

class UpControlBar(ActionEventBar):
    def on_action(self, inst, action):
        if inst != self:
            self.action = dict(source=self.__class__.__name__, **action)

class DownControlBar(ActionEventBar):
    pass

class LeftControlBar(Button):
    def __init__(self, **kwargs):
        super(LeftControlBar, self).__init__(**kwargs)
        self.text = 'Left'

class RightControlBar(Button):
    def __init__(self, **kwargs):
        super(RightControlBar, self).__init__(**kwargs)
        self.text = 'Right'

class CenterContentBar(PageContext):
    pass

class CenterMessageBar(Button):
    pass