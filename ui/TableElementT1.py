from ui.TableElement import WidgetPageContentRecycleElement
from ui.TableElement import  WidgetRowElement
from ui.TableElement import WidgetFieldLabelValue

class WidgetT1PageContentTitleElement(WidgetPageContentRecycleElement):
    TITLE = ("type", "address", "size", "instances", "report id")
    def __init__(self, id, page_mm, cls_kwargs, **layout_kwargs):
        super(WidgetT1PageContentTitleElement, self).__init__()

        cls_row_elems = cls_kwargs.get('class_row_elems')
        data = []
        row_kwargs = {'w_row_kwargs': dict(page_id=id, row_idx=0, row_data=self.TITLE, layout_kwargs=layout_kwargs),
                      'cls_kwargs': cls_kwargs}
        data.append(row_kwargs)

        setattr(self, 'data', data)
        setattr(self, 'viewclass', cls_row_elems[0])

class WidgetT1PageContentDataElement(WidgetPageContentRecycleElement):
    def __init__(self, id, page_mm, cls_kwargs, **layout_kwargs):
        super(WidgetT1PageContentDataElement, self).__init__()
        self.num_report_id_table = {}

        cls_row_elems = cls_kwargs.get('class_row_elems')
        data = []
        for i, row_mm in enumerate(page_mm):
            rid, addr, size, instances, num_report_ids = row_mm.values()
            size = size + 1
            instances = instances + 1
            num_report_ids = num_report_ids * instances
            report_id = self.set_report_id_num(rid, num_report_ids)

            values = (rid, addr, size, instances, report_id)
            row_kwargs = {'w_row_kwargs': dict(page_id=id, row_idx=i, row_data=values, layout_kwargs=layout_kwargs),
                        #'w_field_kwargs': dict(skip_name=skip_name, skip_value=skip_value),
                        'cls_kwargs': cls_kwargs}
            #print(self.__class__.__name__, row_kwargs)
            data.append(row_kwargs)

        #root = WidgetPageContentDataElement()
        setattr(self, 'data', data)
        setattr(self, 'viewclass', cls_row_elems[0])

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

class WidgetT1RowElement(WidgetRowElement):
    ROW_TITLE_DATA_NAME = ('TYPE', 'ADDR', 'SIZE', 'INSTANCES', 'REPORT ID')

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        #print(self.__class__.__name__, rv, index, data)
        kwargs = data
        row_kwargs = kwargs.get('w_row_kwargs')
        c_kwargs = kwargs.get('cls_kwargs')
        cls_row_elem, cls_row_idx, cls_row_data = c_kwargs.get('class_row_elems')
        cls_idx_elems = c_kwargs.get('class_idx_elems')
        cls_data_elems = c_kwargs.get('class_data_elems')

        self.__init2__(**row_kwargs)

        #index content
        row_data = row_kwargs.get('row_data', None)
        if row_data is not None:
            # idx content
            if cls_row_idx:
                self.add_layout(self.CHILD_ELEM_INDEX, cls_row_idx())
                v = row_kwargs['row_idx']
                w_field = self.create_field_element(col_idx=0, name='-', value=v, cls_kwargs=cls_idx_elems)
                self.add_children_layout(self.CHILD_ELEM_INDEX, w_field)

            #data content
            if cls_row_data:
                self.add_layout(self.CHILD_ELEM_DATA, cls_row_data())
                #line_space = sum(map(lambda v: v.width, row_data))
                for j, v in enumerate(row_data):
                    #percent = elem.width / line_space
                    #layout_kwargs = {'size_hint_x': percent}
                    layout_kwargs = {}
                    kwargs = dict(col_idx=j, name=v, value=v,   #set name and value same
                                  layout_kwargs=layout_kwargs, cls_kwargs=cls_data_elems)
                    w_field = self.create_field_element(**kwargs)
                    self.add_children_layout(self.CHILD_ELEM_DATA, w_field)

        self.index = index

        #print(self.__class__.__name__, rv.data[index])
        return super(WidgetRowElement, self).refresh_view_attrs(
            rv, index, data)

    # def refresh_view_attrs_old(self, rv, index, data):
    #     ''' Catch and handle the view changes '''
    #     #print(self.__class__.__name__, rv, index, data)
    #
    #     kwargs = data
    #     w_row_kwargs = kwargs.get('w_row_kwargs')
    #     #w_field_kwargs = kwargs.get('w_field_kwargs')
    #     c_kwargs = kwargs.get('cls_kwargs')
    #     cls_row_elem, cls_row_idx, cls_row_data = c_kwargs.get('class_row_elems')
    #     cls_idx_elems = c_kwargs.get('class_idx_elems')
    #     cls_data_elems = c_kwargs.get('class_data_elems')
    #
    #     super(WidgetRowT1Element, self).__init2__(**w_row_kwargs)
    #
    #     row_mm = w_row_kwargs.get('row_mm')
    #     field_size = len(row_mm)
    #
    #     #print(self.__class__.__name__, row_mm)
    #     if cls_data_elems:
    #         self.add_layout(self.CHILD_ELEM_DATA, cls_row_data())
    #         # pid = row_mm.get_field('type')
    #         # addr = row_mm.get_field('start_address')
    #         # size = row_mm.get_field('size_minus_one') + 1
    #         # instances = row_mm.get_field('instances_minus_one') + 1
    #         # num_report_ids = row_mm.get_field('num_report_ids') * instances
    #         val = row_mm.values()
    #         #print(self.__class__.__name__, val)
    #         pid, addr, size, instances, num_report_ids = val
    #         size = size + 1
    #         instances = instances + 1
    #         num_report_ids = num_report_ids * instances
    #
    #         if num_report_ids:
    #             report_st = 1
    #             for k, v in self.REPORT_ID_TABLE.items():
    #                 if k == pid:
    #                     break
    #
    #                 report_st += v
    #
    #             report_end = report_st + num_report_ids - 1
    #             report_id = (report_st, report_end)
    #         else:
    #             report_id = None
    #
    #         if id not in self.REPORT_ID_TABLE.keys():
    #             self.REPORT_ID_TABLE[pid] = num_report_ids
    #
    #         elem_values = (pid, addr, size, instances, report_id)
    #
    #     for j in range(field_size):
    #         kwargs = dict(col_idx=j, value=elem_values[j], name=self.ROW_TITLE_DATA_NAME[j],
    #                       cls_kwargs=cls_data_elems)
    #         w_field = self.create_field_element(**kwargs)
    #         self.add_children_layout(self.CHILD_ELEM_DATA, w_field)
    #
    #     self.index = index
    #
    #     #print(self.__class__.__name__, self.REPORT_ID_TABLE)
    #
    #     return super(WidgetRowElement, self).refresh_view_attrs(
    #         rv, index, data)

class WidgetT1RowTitleElement(WidgetT1RowElement):
    pass