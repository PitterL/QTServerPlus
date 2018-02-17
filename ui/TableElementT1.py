from ui.TableElement import WidgetRecycleDataView, SelectableRecycleBoxLayout, WidgetPageContentRecycleElement
from ui.TableElement import  WidgetRowElementBase
from ui.TableElement import LayerBoxLayout, WidgetFieldLabelValue

from collections import OrderedDict

class WidgetFieldT1IndexName(LayerBoxLayout):
    pass

class WidgetT1FieldLabelValue(WidgetFieldLabelValue):
    def to_field_value(self, value):
        def func_report_id(report_id):
            if report_id:
                st, end = report_id
                if st == end:
                    return "{}".format(st)
                else:
                    return "{st}-{end}".format(st=st, end=end)
            else:
                return '-'

        func_list = (None, hex, None, None, func_report_id)
        if self.col < len(func_list):
            func = func_list[self.col]
        else:
            func = None

        if func:
            value = func(value)

        return str(value)

class WidgetT1RowElement(WidgetRowElementBase):
    ROW_TITLE_DATA_NAME = ('TYPE', 'ADDR', 'SIZE', 'INSTANCES', 'REPORT ID')

    #def _create_view(self, rv, index, data):
    def __init__(self, **kwargs):

        #kwargs = data['view_attrs']

        v_kwargs = kwargs.get('view_kwargs')
        page_id = v_kwargs.get('page_id')
        row_id = v_kwargs.get('row_id')
        row_data = v_kwargs.get('row_data')

        c_kwargs = kwargs.get('cls_kwargs')
        l_kwargs = kwargs.get('layout_kwargs', dict())
        #self.__init2__(page_id, row_id, l_kwargs)
        super(WidgetT1RowElement, self).__init__(page_id, row_id, **l_kwargs)

        cls_row_elem, cls_row_idx, cls_row_data = c_kwargs.get('class_row_elems')
        cls_idx_field = c_kwargs.get('class_idx_field')
        cls_data_field = c_kwargs.get('class_data_field')

        idx, content = row_data
        # idx content
        if cls_row_idx:
            self.add_layout(self.CHILD_ELEM_INDEX, cls_row_idx())
            for i, (name, value) in enumerate(idx.items()):
                w_field = self.create_field_element(col_idx=i, name=name, value=value, cls_kwargs=cls_idx_field)
                self.add_children_layout([self.CHILD_ELEM_INDEX, name], w_field)

        #data content
        if cls_row_data:
            self.add_layout(self.CHILD_ELEM_DATA, cls_row_data())
            for i, (name, value) in enumerate(content.items()):
                #print(self.__class__.__name__, "create_field_element", name, value)
                layout_kwargs = {}
                kwargs = dict(col_idx=i, name=name, value=value,   #set name and value same
                              layout_kwargs=layout_kwargs, cls_kwargs=cls_data_field)
                w_field = self.create_field_element(**kwargs)
                self.add_children_layout([self.CHILD_ELEM_DATA, name], w_field)

    def do_fresh(self, **kwargs):
        #v_kwargs = kwargs.get('view_kwargs')
        #idx, content = v_kwargs.get('row_data')
        idx, content = kwargs.get('row_data')

        for name, value in content.items():
            layout = self.get_children_layout([self.CHILD_ELEM_DATA, name])
            if layout:
                layout.set_value(value)

class WidgetT1RowTitleElement(WidgetT1RowElement):
    pass

class WidgetT1RowElementPacking(object):
    TITLE = (("n",), ("object", "address", "size", "instances", "report id"))

    def build_row_data(self, values):
        raw_data=[]
        for i, name in enumerate(self.TITLE):
            if values:
                v = values[i]
            else:
                v = [None] * len(name)
            d = OrderedDict(zip(name, v))
            raw_data.append(d)

        return raw_data

class WidgetT1PageContentTitleElement(WidgetT1RowElementPacking, LayerBoxLayout):
    def __init__(self, id, row_elems, cls_kwargs, **layout_kwargs):
        super(WidgetT1PageContentTitleElement, self).__init__()

        cls_row_elem, _, _ = cls_kwargs.get('class_row_elems')
        #data = []
        values = self.TITLE
        row_data = self.build_row_data(None)
        # row_kwargs = {'view_attrs': {
        #                 'view_kwargs': {'page_id': id, 'row_id': 0, 'row_data': row_data,},
        #                 'cls_kwargs': cls_kwargs,
        #                 'layout_kwargs': layout_kwargs}}
        view_kwargs = {'page_id': id, 'row_id': 0, 'row_data': row_data, }
        widget = cls_row_elem(view_kwargs=view_kwargs, cls_kwargs=cls_kwargs, layout_kwargs=layout_kwargs)
        self.add_layout(-1, widget)
        #row_kwargs = dict(page_id=id, row_id=0, raw_data=self.TITLE, cls_kwargs=cls_kwargs, layout_kwargs=layout_kwargs)
        #data.append(row_kwargs)

        #setattr(self, 'data', data)
        #setattr(self, 'viewclass', WidgetRecycleDataView)

class WidgetT1PageContentDataElement(WidgetT1RowElementPacking, WidgetPageContentRecycleElement):
    def __init__(self, id, row_elems, cls_kwargs, **layout_kwargs):
        super(WidgetT1PageContentDataElement, self).__init__()
        self.num_report_id_table = {}

        #cls_row_elems = cls_kwargs.get('class_row_elems')
        data = []
        for i, row_elem in enumerate(row_elems):#row_elems is list store RowElementByte
            # row_elem is RowElementByte, iter() is {name: ByteField}
            rid, addr, size, instances, num_report_ids = row_elem.values()
            size = size + 1
            instances = instances + 1
            num_report_ids = num_report_ids * instances
            report_id = self.set_report_id_num(rid, num_report_ids)

            values = ((i, ), (rid, addr, size, instances, report_id))
            row_data = self.build_row_data(values)
            row_kwargs = {'view_attrs': {
                            'view_kwargs': {'page_id': id, 'row_id': i, 'row_data': row_data},
                            'cls_kwargs': cls_kwargs,
                            'layout_kwargs': layout_kwargs}}
            #row_kwargs = dict(page_id=id, row_id=i, raw_data=values, cls_kwargs=cls_kwargs, layout_kwargs=layout_kwargs)
            #print(self.__class__.__name__, row_kwargs)
            data.append(row_kwargs)

        setattr(self, 'data', data)
        setattr(self, 'viewclass', WidgetRecycleDataView)

    def set_report_id_num(self, rid, num_report_ids):
        if num_report_ids:
            report_st = 1
            for k, v in self.num_report_id_table.items():
                if k == rid:
                    break

                report_st += v

            report_end = report_st + num_report_ids - 1
            report_id = (report_st, report_end)
        else:
            report_id = None

        if id not in self.num_report_id_table.keys():
            self.num_report_id_table[rid] = num_report_ids

        return report_id

class WidgetT1PageSelectableRecycleBoxLayout(SelectableRecycleBoxLayout):
    pass
