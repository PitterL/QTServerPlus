class HookServer(object):
    #WatchList = {} #defined WatchList in derived class

    @classmethod
    def register_hook(cls, watch_struct, inst, *param):
        cls.add_to_watch(watch_struct, inst, *param)

    @classmethod
    def add_to_watch(cls, watch_struct, inst, *param):
        name = str(inst)
        #(v0, v1, fn)
        assert len(watch_struct) == 2
        if name not in cls.WatchList:
            cls.WatchList[name] = (watch_struct, inst, param)

    #should re-construct this function in derived class
    def matched(self, key, mm):
        return False

    # def handle(self, msg_mm):
    #     major, _ = msg_mm.page_id()
    #     rid = msg_mm.id()
    #     for name, watch in self.WatchList.items():
    #         (mids, rids, fn), inst, param = watch
    #         if (mids is None or major in mids) and \
    #                 (rids is None or report_id in rids):
    #             fn(inst, msg_mm, *param)

    def handle(self, msg):
        for name, watch in self.WatchList.items():
            (k, fn), inst, param = watch
            if self.matched(k, msg):
                fn(inst, msg, *param)

class ConfigHookServer(HookServer):
    WatchList = {}

    def matched(self, id_key, mmap):
        majs, mins = id_key
        major, minor = mmap.id()
        if (majs is None or major in majs) and \
                (mins is None or minor in mins):
            return True

class MessageHookServer(HookServer):
    WatchList = {}

    def matched(self, id_key, mmap):
        majs, rids = id_key
        major, _ = mmap.page_id()
        rid = mmap.id()
        if (majs is None or major in majs) and \
                (rids is None or rid in rids):
            return True

class KeyboardShotcut(object):
    WatchList = []
    KeyHandle = None
    Root = None

    def __init__(self, **kwargs):
        if not KeyboardShotcut.KeyHandle:
            from kivy.core.window import Window
            KeyboardShotcut.KeyHandle = Window.bind(on_keyboard=KeyboardShotcut.keyboard_shortcut)
            KeyboardShotcut.Root = kwargs.get('win', Window)

        super(KeyboardShotcut, self).__init__()

    @staticmethod
    def content(w):
        return w[1:]

    @staticmethod
    def order(w):
        return w[0]

    @classmethod
    def max_order(cls):
        _, w = cls.WatchList[0]
        return cls.order(w)

    @classmethod
    def set_order(cls, w, i):
        w[0] = i

    @classmethod
    def sort_key(cls, b):
        _, w = b
        return cls.order(w)

    @classmethod
    def sort(cls):
        cls.WatchList.sort(key=cls.sort_key, reverse=True)


    @classmethod
    def add_to_watch(cls, key_watch_struct, inst, *param):
        name = str(inst)
        if name not in cls.WatchList:
            cls.WatchList.append([name,[0]])   #first elem is priority

        for n, row in cls.WatchList:
            if n == name:
                row.append((key_watch_struct, inst, param))
                break

    @classmethod
    def register_keyboard(cls, key_watch_struct, inst, *param):
        #(scancode, modifiers, callback)
        if len(key_watch_struct) == 3:
            #KeyboardShotcut.WatchList.[str(inst)] = [0, (key_watch_struct, param)]
            cls.add_to_watch(key_watch_struct, inst, *param)

    @staticmethod
    def set_root_window(win):
        cls.Root = win
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

    @classmethod
    def keyboard_shortcut(cls, win, scancode, *largs):
        #print(win.__class__.__name__, "keyboard", win, scancode, largs)

        modifiers = largs[-1]
        for _, watch in cls.WatchList:
            content = cls.content(watch)
            for elem in content:
                (code, mod, fn), inst, param = elem
                matched = False
                if scancode == code:
                    if len(modifiers) >= 1:  #has modifiers
                        if isinstance(mod, (list, tuple)):
                            if set(mod) == set(modifiers):
                                matched = True
                    else:
                        if not mod:    #no modifier
                            matched = True

                    if matched:
                        result = fn(KeyboardShotcut.Root, inst, *param)
                        if result is not None:
                            if result:  # stop dispatch if widget handle it
                                cls.set_order(watch,
                                          cls.max_order() + 1)  # first elem is biggest, set me first
                            else:
                                cls.set_order(watch, 0)
                            cls.sort()
                            print(win, "on_keyboard", scancode, largs, KeyboardShotcut.WatchList)
                            return True
