from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButtonBehavior, ToggleButton
from kivy.uix.bubble import Bubble, BubbleButton
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.label import Label

from kivy.animation import Animation
from kivy.properties import ObjectProperty, BooleanProperty, ListProperty, \
    NumericProperty, StringProperty, OptionProperty, \
    ReferenceListProperty, AliasProperty, VariableListProperty


from ui.TableElement import WidgetPageBehavior
from ui.TableElement import WidgetRowTitleElement, WidgetRowElement, WidgetRowIndexElement, WidgetRowDataElement
from ui.TableElement import WidgetFieldElement, WidgetFieldLabelName, WidgetFieldLabelValue
from ui.TableElement import WidgetFieldIndexElement, WidgetFieldIndexName

class WidgetFieldToggleName(ToggleButton):
    def __init__(self, id , type, **kwargs):
        self._id = id
        self._type = type

        super(WidgetFieldToggleName, self).__init__(**kwargs)

    def __str__(self):
        return "{} id {} type {}: {} ".format(self.__class__.__name__, self.id(), self.type(), self.text)

    def id(self):
        return self._id

    def type(self):
        return self._type

    def row_idx(self):
        return self._id[0]

    def col_idx(self):
        return self._id[1]

class BubbleWidget(BoxLayout):
    pass

class WidgetBubbleElement(WidgetPageBehavior, BubbleWidget):
    PAGE_CLS_LAYOUT_TABLE = {
        'default': {
            'title': {
                'class_row_elems': (WidgetRowTitleElement, WidgetRowIndexElement, WidgetRowDataElement),
                'class_idx_elems': (WidgetFieldIndexElement, WidgetFieldIndexName, None),
                'class_data_elems': (WidgetFieldElement, WidgetFieldLabelName, None)},
            'data':{
                'class_row_elems': (WidgetRowElement,WidgetRowIndexElement, WidgetRowDataElement),
                'class_idx_elems': (WidgetFieldIndexElement, WidgetFieldIndexName, None),
                'class_data_elems': (WidgetFieldElement, WidgetFieldToggleName, None)}
        }
    }

    @classmethod
    def get_cls_layout_kwargs(cls, id):
        if id in cls.PAGE_CLS_LAYOUT_TABLE.keys():
            kwargs = cls.PAGE_CLS_LAYOUT_TABLE[id]
        else:
            kwargs = cls.PAGE_CLS_LAYOUT_TABLE['default']

        return kwargs

    def __init__(self, repo):
        repo_id = repo.id()
        BubbleWidget.__init__(self)
        #w_content = self.ids['content']
        w_content = self

        cls_kwargs = self.get_cls_layout_kwargs(repo_id)
        WidgetPageBehavior.__init__(self, w_content, repo_id, cls_kwargs)
        #if repo.valid():
        self.create_page_content_widget(repo)

    def on_focus(self, instance, value):
        print(instance,value)

class RepoButton(FocusBehavior, ToggleButton):
    def __init__(self, parent, repo):
        super(RepoButton, self).__init__()
        self._parent = parent
        self.idx = repo.page_id[0]
        self.text = "T" + str(self.idx)
        self.bubb = WidgetBubbleElement(repo)
        #self._parent.add_widget(self.bubb)

    def show_bubb(self):
        #if self._parent.hidden():
        self._parent.add_content(self.bubb)

    #def hide_bubb(self):
    #    self._parent.clear_widgets()

    def on_state(self, widget, value):
        if value == 'down':
            #self.hide_bubb()
            self.show_bubb()

    # def on_focus(self, instance, value):
    #      if not value:
    #          self.hide_bubb()

class WidgetBubbleRoot(FocusBehavior, Bubble):
    # def on_focus(self, obj, status):
    #     print(obj, status)
    #     if not status:
    #          self.clear_widgets()

    def hidden(self):
        return not self.content.children

    def add_content(self, w):
        self.clear_widgets()
        self.add_widget(w)

class MessageView(FloatLayout):
    activated = BooleanProperty(False)

    #selected_command = StringProperty('')
    #history_command = ListProperty('')

    def __init__(self, win=None):
        super(MessageView, self).__init__()
        self._layout = {}
        self._root = win

        #bubb = WidgetBubbleRoot()
        self._layout['bubb'] = self.ids['bubb']
        self._layout['ctrl'] = self.ids['control']
        self._layout['data'] = self.ids['data']
        #self.add_widget(bubb)
        height = self.height
        Animation(top=height, t='out_quad', d=.3).start(self._layout['bubb'])
        #self.add_widget(bubb)

    def on_pos(self, *args):
        print(self.__class__.__name__, args)

    def sub_widget(self, name):
        return self._layout.get(name, None)

    def create_message_element(self, repo):
        w = RepoButton(self.sub_widget('bubb'), repo)
        #w = BubbleContentElement(repo)
        self._layout['ctrl'].add_widget(w)
        #self.add_widget(w)

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
        if scancode == 109 and modifiers == ['ctrl']:   #ctrl + m
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
            report_table = chip.get_reg_reporer()
            for v in report_table.values():
                repo = chip.get_msg_map_tab(v[0])
                if repo:
                    root.create_message_element(repo)

            return root

    MessageViewApp().run()