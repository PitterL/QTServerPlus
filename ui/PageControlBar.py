from kivy.uix.actionbar import ActionBar
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from ui.PageElement import PageElementRoot

class UpControlBar(ActionBar):
    pass

class DownControlBar(ActionBar):
    pass

class LeftControlBar(Button):
    def __init__(self, **kwargs):
        super(LeftControlBar, self).__init__(**kwargs)
        self.text = 'Left'

class RightControlBar(Button):
    def __init__(self, **kwargs):
        super(RightControlBar, self).__init__(**kwargs)
        self.text = 'Right'

class CenterContext(PageElementRoot):
    pass
