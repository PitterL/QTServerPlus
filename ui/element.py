from kivy.lang import Builder
# from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.label import Label
# from kivy.uix.button import Button
from kivy.uix.behaviors import FocusBehavior
# from kivy.graphics import Color, Rectangle
# from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem, TabbedPanelHeader
from server.devinfo import Page
from tools.mem import ChipMemoryMap, PageMem

class ElemError(Exception):
    "Message error exception class type"
    pass

class FocusWithColor(FocusBehavior):
    ''' Class that when focused, changes its background color to red.
    '''

    _color = None
    _rect1 = None


    def __init__(self, **kwargs):
        super(FocusWithColor, self).__init__(**kwargs)
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

        if super(FocusLabel, self).keyboard_on_key_down(window, keycode,
                                                         text, modifiers):
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

class WidgetRootElement(TabbedPanel):
    def __init__(self, **kwargs):
        self.__elems_tab = {}
        super(WidgetRootElement, self).__init__(**kwargs)

    def add_element(self, element):
        super(WidgetRootElement, self).add_widget(element)
        if element.id() == Page.ID_INFORMATION:
            self.switch_to(element)

        self.__elems_tab[element.id()] = element

    def remove_element(self, element_id):
        widget = self.get_element(element_id)
        if widget:
            del self.__elems_tab[element_id]
            super(WidgetRootElement, self).remove_widget(widget)

    def clear_elements(self, **kwargs):
        self.__elems_tab.clear()
        super(WidgetRootElement, self).clear_widgets(**kwargs)

    def get_element(self, element_id):
        if element_id in self.__elems_tab.keys():
            return self.__elems_tab[element_id]

class WidgetPageElement(TabbedPanelItem):
    ELEMENT_SIZE_HINT_X_UNIT = 0.125

    def __init__(self, page_mm, **kwargs):
        super(WidgetPageElement, self).__init__(**kwargs)
        self.__id = page_mm.id()

        #print(self.ids)
        #self.ids['page'].text = "T{}".format(page_mm.id())
        self.text = "T{}".format(page_mm.id())
        layout = self.ids['rows']
        for i, row in enumerate(page_mm):
            w_row = WidgetRowElement(i)
            for name, elem in row:
                w_field = WidgetFieldElement(size_hint=(WidgetPageElement.ELEMENT_SIZE_HINT_X_UNIT * elem.width, 1))
                w_field.ids['name'].text = name
                w_field.ids['value'].text = str(hex(elem.value))
                #print(self.__class__.__name__, w_field.ids['name'].text, w_field.ids['value'].text)
                w_row.add_widget(w_field)
            self.ids['rows'].add_widget(w_row)

    def id(self):
        return self.__id

    def do_fresh(self, page_mm):
        if page_mm.id() != self.__id:
            print("{} fresh id mis-match {}, {}".format(page_mm.id(), self.id))
            return

        for w_row in self.ids['rows'].children:
            for w_field in w_row.children:
                name = w_field.ids['name'].text
                value = value = page_mm.select(w_row.id(), name)

                if value is not None:
                    w_field.ids['value'].text = str(hex(value))
                else:
                    print("{} fresh page {}, name '{}' not found".format(self.__class__.__name__, page_mm.id(), name))

    def build_mem_map(self):
        mem = []
        for w_row in self.ids['rows']:
            row = []
            for w_field in w_row.children:
                name = w_field.ids['name'].text
                value = int(w_field.ids['value'].text)
                row.append((name, value),)
            mem.append(row)

        return PageMem(self.id(), mem)

class WidgetRowElement(StackLayout):
    def __init__(self, row_idx, **kwargs):
        super(WidgetRowElement, self).__init__(**kwargs)
        self.__row_idx = row_idx

    def id(self):
        return self.__row_idx

class WidgetFieldElement(BoxLayout):
    pass

class WidgetFieldElementLabel(Label):
    pass


if __name__ == '__main__':

    from kivy.app import App

    Builder.load_file('element.kv')

    class FocusApp(App):

        def build(self):
            chip_id = (0xa4, 0x16, 1, 2, 3, 4, 5)
            chip_mmap = ChipMemoryMap.get_chip_mmap(chip_id)
            page_mmap = chip_mmap.get_mmap(Page.ID_INFORMATION)

            root = WidgetRootElement()
            w_page = WidgetPageElement(page_mmap)
            root.add_element(w_page)
            #test upgrade value
            w_page_check = root.get_element(Page.ID_INFORMATION)
            page_mmap.set_values([1,2,3,4,5,6,7, 0xa1, 0xd2, 0xc3])
            w_page_check.do_fresh(page_mmap)
            return root

    FocusApp().run()
