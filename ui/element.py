from kivy.lang import Builder
# from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.label import Label
# from kivy.uix.button import Button
from kivy.uix.behaviors import FocusBehavior
from kivy.graphics import Color, Rectangle
# from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView


from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem, TabbedPanelHeader
from server.devinfo import Page

class ElemError(Exception):
    "Message error exception class type"
    pass

class FocusWithColor(FocusBehavior):
    ''' Class that when focused, changes its background color to red.
    '''

    _color = None
    _rect1 = None


    def __init__(self, *args, **kwargs):
        super(FocusWithColor, self).__init__(*args, **kwargs)
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
        #layout.bind(minimum_height=layout.setter('height'))
        for i, row in enumerate(page_mm):
            w_row = WidgetRowElement(row_idx=i)
            for j, (name, elem) in enumerate(row):
                #w_field = WidgetFieldElement(size_hint=(WidgetPageElement.ELEMENT_SIZE_HINT_X_UNIT * elem.size_hint, 1))
                #w_field = WidgetFieldElement(size_hint=(0.2, None), width=10)
                #w_field.ids['name'].text = name
                #w_field.ids['value'].text = str(hex(elem.value))
                w_field = WidgetFieldElement(self.id(), i, j, name, elem.value)
                #print(self.__class__.__name__, name, elem.value)
                w_row.add_widget(w_field)
            self.ids['rows'].add_widget(w_row)

    def id(self):
        return self.__id

    def do_fresh(self, page_mm):
        if page_mm.id() != self.__id:
            print("{} fresh id mis-match {}, {}".format(page_mm.id(), self.id))
            return

        for w_row in self.ids['rows'].children:
            for w_field_elem in w_row.children:
                #print(self.__class__.__name__, w_field)
                w_field_value = w_field_elem.field_type(WidgetFieldElement.VALUE)
                value = page_mm.select_idx(*w_field_value.id())

                if value is not None:
                    w_field_value.text = WidgetFieldElement.to_field_value(page_mm.id(), w_field_value.row_idx(), w_field_value.col_idx(), value)
                else:
                    print("{} fresh page {}, field '{}' not found".format(self.__class__.__name__, page_mm.id(), w_field_value.id()))

    # def build_mem_map(self):
    #     mem = []
    #     for w_row in self.ids['rows']:
    #         row = []
    #         for w_field in w_row.children:
    #             name = w_field.ids['name'].text
    #             value = int(w_field.ids['value'].text)
    #             row.append((name, value),)
    #         mem.append(row)
    #
    #     return PageMem(self.id(), mem)

class WidgetRowElement(BoxLayout):
    def __init__(self, **kwargs):
        self.__row_idx = kwargs.pop('row_idx')
        super(WidgetRowElement, self).__init__(**kwargs)

    def id(self):
        return self.__row_idx

class WidgetFieldElement(BoxLayout):
    (NAME, VALUE) = range(2)

    def __init__(self, page_id, row_idx, col_idx, name, value, **kwargs):
        super(WidgetFieldElement, self).__init__(**kwargs)

        text = WidgetFieldElement.to_field_name(page_id, row_idx, col_idx, name)
        self.add_widget(WidgetFieldElementName(eid=(row_idx, col_idx), etype=WidgetFieldElement.NAME, text=text))

        text = WidgetFieldElement.to_field_value(page_id, row_idx, col_idx, value)
        self.add_widget(WidgetFieldElementValue(eid=(row_idx, col_idx), etype=WidgetFieldElement.VALUE, text=text))

    @staticmethod
    def to_field_name(page_id, row_idx, col_idx, name):
        if page_id == Page.OBJECT_TABLE:
            if row_idx > 0:
                #return None
                pass
        return name

    @staticmethod
    def to_field_value(page_id, row_idx, col_idx, value):
        func = hex
        if page_id == Page.OBJECT_TABLE:
            func_list = (None, hex, None, None, None)
            if col_idx < len(func_list):
                func = func_list[col_idx]

        if func:
            value = func(value)

        return str(value)

    def field_type(self, type):
        for field_t in self.children:
            if field_t.type() == type:
                return field_t

class WidgetFieldElementBaseLabel(FocusLabel):
    def __init__(self, **kwargs):
        self.__id = kwargs.pop('eid')
        self.__type = kwargs.pop('etype')

        super(WidgetFieldElementBaseLabel, self).__init__(**kwargs)

    def id(self):
        return self.__id

    def type(self):
        return self.__type

    def row_idx(self):
        return self.__id[0]

    def col_idx(self):
        return self.__id[1]

class WidgetFieldElementName(WidgetFieldElementBaseLabel):
    pass

class WidgetFieldElementValue(WidgetFieldElementBaseLabel):
    pass

if __name__ == '__main__':

    import array
    from kivy.app import App
    from tools.mem import ChipMemoryMap

    Builder.load_file('element.kv')

    class FocusApp(App):

        def build(self):
            root = WidgetRootElement()
            v_chip_id = array.array('B', [164, 24, 16, 170, 32, 20, 40])
            #v_chip_id = array.array('B', [164, 24, 16, 170, 32, 20, 3])
            chip = ChipMemoryMap.get_chip_mmap(v_chip_id)

            page_mmap = chip.get_mmap(Page.ID_INFORMATION)
            w_page = WidgetPageElement(page_mmap)
            root.add_element(w_page)
            #test upgrade value
            w_page_check = root.get_element(Page.ID_INFORMATION)
            page_mmap.set_values([1,2,3,4,5,6,7, 0xa1, 0xd2, 0xc3])
            w_page_check.do_fresh(page_mmap)

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

            #v_block_info = array.array('B',
            #                           [117, 250, 0, 214, 5, 0,])
            page_mmap = chip.get_mmap(Page.OBJECT_TABLE)
            page_mmap.set_values(v_block_info)
            w_page = WidgetPageElement(page_mmap)
            root.add_element(w_page)

            chip.create_default_mmap_pages()
            all_page_mmaps = chip.get_mmap()
            for mmap in all_page_mmaps.values():
                if mmap.active():
                    w_page = WidgetPageElement(mmap)
                    root.add_element(w_page)
            return root

    FocusApp().run()
