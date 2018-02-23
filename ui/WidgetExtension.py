from kivy.uix.boxlayout import BoxLayout
from kivy.properties import DictProperty
from kivy.factory import Factory

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
            #print(self.__class__.__name__, "bind:", widget, "---", self)
            widget.bind(action=self.on_action)

    def action_unbind(self, widget):
        action = widget.property('action', True)
        if action:
            #print(self.__class__.__name__, "unbind:", widget, "---", self)
            widget.unbind(action=self.on_action)

Factory.register('ActionEvent', cls=ActionEvent)

class ActionBehavior(ActionEvent):
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

class LayerBehavior(object):
    def __init__(self):
        self.__layers = {}

    # def __iter__(self):
    #     return iter(self.__layers)
    #
    # def __len__(self):
    #     return len(self.__layers)

    def get_layer_names(self):
        return tuple(self.__layers.keys())

    def get_layers(self):
        return tuple(self.__layers.values())

    def get_layer(self, name):
        return self.__layers.get(name)

    def add_layer(self, name, widget):
        assert name not in self.__layers
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

Factory.register('LayerBehavior', cls=LayerBehavior)

class LayerBoxLayout(LayerBehavior, ActionEvent, BoxLayout):
    def __init__(self, **kwargs):
        #super(LayerBoxLayout, self).__init__(**kwargs)  #why couldn't use this?
        LayerBehavior.__init__(self)
        ActionEvent.__init__(self)
        BoxLayout.__init__(self, **kwargs)
        self.prop_set_default_minimum_height = True

    def set_default_minimum_height(self):
        shw, shh = self.size_hint
        if not shh:
            if self.children:
                if self.orientation == 'horizontal':
                    height = self.children[0].height
                else:
                    height = sum([child.height for child in self.children])
                self.minimum_height = height

    def get_layer(self, name):
        return super(LayerBoxLayout, self).get_layer(name)

    def add_layer(self, name, widget):
        super(LayerBoxLayout, self).add_layer(name, widget)
        self.action_bind(widget)
        self.add_widget(widget)

        # RecycleView has some bug for fresh height = self.minimum_height, we should adjust it may manually
        # so we should as the order, all children are created first, then added to parent widget
        if self.prop_set_default_minimum_height:
            self.set_default_minimum_height()

    def remove_layer(self, name):
        if name in super(LayerBoxLayout, self).get_layer_names():
            w = super(LayerBoxLayout, self).get_layer(name)
            self.action_unbind(w)
            self.remove_widget(w)
            super(LayerBoxLayout, self).remove_layer(name)

    def detach_layer(self):
        for n in super(LayerBoxLayout, self).get_layer_names():
            self.remove_layer(n)

    def clear_layer(self):
        for layout in super(LayerBoxLayout, self).get_layers():
            if isinstance(layout, LayerBoxLayout):
                layout.clear_layer()
            else:
                self.remove_layer(layout)

    def add_child_layer(self, child_name_nested, widget):
        assert isinstance(child_name_nested, (tuple, list))
        if len(child_name_nested) > 1:
            layout = self.get_layer(child_name_nested[0])
            assert isinstance(layout, LayerBoxLayout)
            layout.add_child_layer(child_name_nested[1:], widget)
        else:
            self.add_layer(child_name_nested[0], widget)

    def get_child_layer(self, child_name_nested):
        assert isinstance(child_name_nested, (tuple, list))
        if len(child_name_nested) > 1:
            layout = self.get_layer(child_name_nested[0])
            assert isinstance(layout, LayerBoxLayout)
            return layout.get_child_layer(child_name_nested[1:])
        else:
            return self.get_layer(child_name_nested[0])

Factory.register('LayerBoxLayout', cls=ActionEvent)
