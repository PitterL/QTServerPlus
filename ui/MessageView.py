from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.bubble import Bubble

from kivy.properties import ObjectProperty, BooleanProperty, ListProperty, \
    NumericProperty, StringProperty, OptionProperty, \
    ReferenceListProperty, AliasProperty, VariableListProperty

class RepoButton(ToggleButton):
    def __init__(self, repo):
        self.idx = repo.page_id[0]
        self.text = "T" + str(self.idx)


class ReporterControl(BoxLayout):
    def __init__(self, reporter_table):
        self.repo_ctrl = {}
        for r in reporter_table:
            idx = r.page_id[0]
            if idx not in self.repo_ctrl.keys():
                self.repo_ctrl[idx] = RepoButton(r)

class MessageView(FloatLayout):
    activated = BooleanProperty(False)

    selected_command = StringProperty('')
    #history_command = ListProperty('')

    def __init__(self, msg_table, win=None):
        super(MessageView, self).__init__()
        self._layout = {}
        self._root = win

    def sub_widget(self, name):
        return self._layout.get(name, None)

    def on_select_widget(self, tree, node):
        pass

    def on_action(self, *args):
        pass

    def create_message_element(self, report_table):
        for reporter in report_table:
            self._layout['reporter']

    def handle_data(self, mmsg):
        print(mmsg)

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
        if scancode == 109 and modifiers == ['ctrl']:   #ctrl + d
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

    @staticmethod
    def register_message_view(win=None):
        from kivy.core.window import Window

        if not win:
            win = Window

        view = MessageView(win=win)
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

if __name__ == '__main__':
    from kivy.app import App
    from kivy.lang import Builder

    #from kivy.modules import inspector
    #from kivy.core.window import Window

    class MessageViewApp(App):

        def build(self):
            #root = MessageView()
            #inspector.create_inspector(Window, root)
            #return root
            return MessageView.register_message_view()

    MessageViewApp().run()