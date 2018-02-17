from collections import OrderedDict
import struct
import array
import ctypes
import os, re, json
from functools import partial

from server.devinfo import Page, ObjectTableElement

class RowElement(object):
    #Page 1, 3 .... row layout( Filed unit is 'bit', 1 byte each row)
    RSV_NAME = ('rsv', 'reserved')
    MAX_FIELD_SIZE = 8

    class BitField(object):
        def __init__(self, start, width):
            self.start = start
            self.width = width
            self.value = 0

        def __str__(self):
            return "{}({s}, {w}, {v})".format(self.__class__.__name__, s=self.start, w=self.width, v=hex(self.value))

        def __repr__(self):
            return self.__str__()

    def __init__(self, row_desc):
        self.idx_desc = row_desc.idx
        self.content_desc = row_desc.content
        self.fields = OrderedDict()
        self.seq_rsv = 0
        self._pos = 0   #store filed relative pos in initilize
        self.value_size = self.MAX_FIELD_SIZE // 8

        for n, v in self.content_desc:
            self.add_field(n, v)

        # for n, v in ele_d:
        #     self.add_field(n, v)

    def __str__(self):
        return self.__class__.__name__ + str((self.idx_desc, self.content_desc))

    def __repr__(self):
        return '<' + self.__str__() + '>'

    def __iter__(self):
        return iter(tuple(self.fields.items()))

    def __getitem__(self, item):
        return self.fields[item]

    def __len__(self):
        return len(self.fields)

    def keys(self):
        return list(self.fields.keys())

    def field_values(self):
        return list(self.fields.values())

    def values(self):
        return [field.value for field in self.fields.values()]

    def add_field(self, name, width):
        if name.lower() in RowElement.RSV_NAME: #cover rsv name with a seq suffix
            name = RowElement.RSV_NAME[0] + str(self.seq_rsv)
            self.seq_rsv += 1

        if name not in self.fields.keys():  #Input filed order from Bit 7 to Bit 0
            self.fields[name] = RowElement.BitField(RowElement.MAX_FIELD_SIZE - self._pos - width, width)
            self._pos += width

        if self._pos > RowElement.MAX_FIELD_SIZE:
            raise Exception("pos{} out of mem".format(self._pos))

    #def full(self):
    #    return self.pos == RowElement.MAX_SIZE

    def set_field(self, name, val):
        if name in self.fields.keys():
            field = self.fields[name]
            max_value = (1 << field.width) - 1
            if val > max_value:
                raise ElemError("Filed {} width {} bit, value{} over max".format(name, field.width, val))

            field.value = val

    def get_field(self, name):
        #print(self.__class__.__name__, name, self.fields.keys(), name in self.fields.keys())
        if name in self.fields.keys():
            return self.fields[name].value

    def get_field_by_idx(self, idx):
        #print(self.__class__.__name__, "get idx {}, ({})".format(idx, self.fields))
        if idx < len(self.fields.values()):
            field = list(self.fields.values())[idx]
            return field.value

    def get_value_size(self):
        return self.value_size

    def set_value(self, val):
        for field in self.fields.values():
            field.value = (val >> field.start) & ((1 << field.width) - 1)

    def get_value(self):
        val = 0
        for field in self.fields.values():
            val |= (field.value << field.start)
        return val

class RowElementByte(object):
    # Page 2 .... row layout( Filed unit is 'bype', several bytes each row)
    class ByteField(object):
        def __init__(self, start, width):
            self.start = start
            self.width = width
            if width == 4:
                self.c_type = 'L'
            elif width == 2:
                self.c_type = 'H'
            else:
                assert width == 1, "Unsupport RowElementByte width %d" % width
                self.c_type = 'B'

            self.value = 0

        def __str__(self):
            return "{}({s}, {w}, {v}, '{c}')".format(self.__class__.__name__, s=self.start, w=self.width, v=hex(self.value), c=self.c_type)

        def __repr__(self):
            return self.__str__()

    def __init__(self, row_desc):
        self.idx_desc = row_desc.idx
        self.content_desc = row_desc.content
        self.fields = OrderedDict()
        self.pos = 0
        self.value_size = 0

        for name, width in self.content_desc:
            self.add_field(name, width)
            self.value_size += width

    def __str__(self):
        return str(self.fields)

    def __repr__(self):
        return super(RowElementByte, self).__repr__() + '(' + self.__str__() + ')'

    def __iter__(self):
        return iter(tuple(self.fields.items()))

    def __getitem__(self, item):
        return self.fields[item]

    def __len__(self):
        return len(self.fields)

    def keys(self):
        return list(self.fields.keys())

    def field_values(self):
        return list(self.fields.values())

    def values(self):
        return [field.value for field in self.fields.values()]

    def add_field(self, name, width):
        if name not in self.fields.keys():
            self.fields[name] = RowElementByte.ByteField(self.pos, width)
            self.pos += width

    #    if self.pos > self.MAX_SIZE:
    #        raise Exception("pos{} out of mem".format(self.pos))

    #def full(self):
    #    return self.pos == self.MAX_SIZE

    def set_field(self, name, val):
        if name in self.fields.keys():
            field = self.fields[name]
            max_value = (1 << (field.width + 8)) - 1
            if val > max_value:
                raise ElemError("Filed {} width {} bit, value{} over max".format(name, field.width, val))

            field.value = val

    def get_field(self, name):
        if name in self.fields.keys():
            return self.fields[name].value

    def get_field_by_idx(self, idx):
        #print(self.__class__.__name__, "get idx {}, ({})".format(idx, self.fields))
        if idx < len(self.fields.values()):
            field = list(self.fields.values())[idx]
            return field.value

    def get_value_size(self):
        return self.value_size

    def set_value(self, t_val):
        for field in self.fields.values():
            if field.start + field.width > len(t_val):
                break

            field.value = struct.unpack_from(field.c_type, t_val[field.start: field.start + field.width])[0]

    def get_value(self):
        #bytes formated array
        t_val = []
        #print(self.__class__.__name__, self.fields)
        for field in self.fields.values():
            t_val.extend(struct.pack('<' + field.c_type, field.value))

        return array.array('B', t_val)

class PageElementMmap(object):

    class RowDesc(object):
        def __init__(self, idx, content):
            self.idx = idx
            self.content = content

        def __iter__(self):
            # print(self.__class__.__name__, self.__rows_mm)
            return iter(self.content)

        def __getitem__(self, key):
            return self.content[key]

    class PageDesc(object):
        def __init__(self, row_title=None):
            self.title_content = []
            self.row_content = []
            if row_title:
                self.add_title(*row_title)

        def __iter__(self):
            # print(self.__class__.__name__, self.__rows_mm)
            return iter(self.row_content)

        def __getitem__(self, key):
            return self.row_content[key]

        def __len__(self):
            return len(self.row_content)

        def title(self):
            return self.title_content

        def content(self):
            return self.row_content

        def row(self):
            return self.row_content

        def add_content(self, idx, content):
            self.row_content.append(PageElementMmap.RowDesc(idx, content))

        def add(self, content):
            self.add_content(None, content)

        def add_title(self, idx, content):
            self.title_content.append(PageElementMmap.RowDesc(idx, content))

    def __init__(self, id, page_desc, values, cls_row_elem):
        self.__id = id
        self.title = []
        self.__rows_mm = []
        self.__values = None
        self.value_size = 0
        #self.title = page_desc.title()

        for row_title_desc in page_desc.title():
            r = cls_row_elem(row_title_desc)
            self.title.append(r)

        for row_desc in page_desc.content():
            r = cls_row_elem(row_desc)
            self.__rows_mm.append(r)
            self.value_size += r.get_value_size()

        if values:
            self.set_values(values)

        #print(self.__class__.__name__, "init", self)

    def __str__(self):
        return super(PageElementMmap, self).__str__() + "id {}, inst {}".format(self.id(), self.parent_inst())

    def __iter__(self):
        #print(self.__class__.__name__, self.__rows_mm)
        return iter(self.__rows_mm)

    def __getitem__(self, key):
        return self.__rows_mm[key]

    def __len__(self):
        return len(self.__rows_mm)

    def id(self):
        return self.__id

    # def instance_id(self):
    #     if isinstance(self.id(), tuple):
    #         return self.id()[-1]

    def parent_inst(self):
         return -1

    def valid(self):
        return self.__values is not None

    def get_value_size(self):
        return self.value_size

    def set_values(self, values):
        assert len(values) == self.value_size, \
            "values length mismatch({} {}):({})".format(len(values), self.value_size, values)

        self.__values = values[:self.value_size]
        for i, row_elem in enumerate(self.__rows_mm):
            size = row_elem.get_value_size()
            if size * (i + 1) > len(values):
                print("{} set_values length {} {} over {}".format(self.__class__.__name__, i, size, len(values)))
                break

            if size == 1:
                val = values[i]
            else:
                val = values[i * size: (i + 1) * size]
            row_elem.set_value(val)

    def raw_values(self):
        values = array.array('B', [])
        for row_elem in self.__rows_mm:
            val = row_elem.get_value()
            if isinstance(val, type(values)):
                values.extend(val)
            else:
                values.append(val)
        return values

    def select(self, row_idx, field_name=None):
        if row_idx < len(self.__rows_mm):
            row_elem = self.__rows_mm[row_idx]

            if field_name is None:
                return row_elem.get_value()
            else:
                return row_elem.get_field(field_name)

    def select_idx(self, row_idx, col_idx=None):
        if row_idx < len(self.__rows_mm):
            row_elem = self.__rows_mm[row_idx]

            #print(self.__class__.__name__, row_elem)
            if col_idx is None:
                return row_elem.get_value()
            else:
                return row_elem.get_field_by_idx(col_idx)

    def search(self, field_name):
        for row_elem in self.__rows_mm:
            value = row_elem.get_field(field_name)
            if value is not None:
                return value

    def row(self, row_id):
        return self.__rows_mm[row_id]

class Page0Mem(PageElementMmap):
    PAGE_ID = Page.ID_INFORMATION
    PAGE_TITLE = (None, (('ID INFORMATION', 8),))

    ROWS_MMAP = (
        (("familiy_id", 8),),
        (("variant_id", 8),),
        (("version", 8),),
        (("build", 8),),
        (("maxtrix_xsize", 8),),
        (("maxtrix_ysize", 8),),
        (("object_num", 8),),
        # test purpose below
        # (('a', 3), ('b', 2), ('c', 1), ('d', 2)),
        # (("rsv", 4), ("rsv", 4)),
        # (('reserved',8),)
    )

    def __init__(self, values=None):
        desc = PageElementMmap.PageDesc(self.PAGE_TITLE)
        for r_cont in self.ROWS_MMAP:
            desc.add(r_cont)

        super(Page0Mem, self).__init__(self.PAGE_ID, desc, values, RowElement)

    def parent_inst(self):
        return -1

class Page1Mem(PageElementMmap):
    PAGE_ID = Page.OBJECT_TABLE
    ROW_MMAP = (
        ("type", 1), ("start_address", 2), ("size_minus_one", 1), ("instances_minus_one", 1), ("num_report_ids", 1)
    )
    PAGE_TITLE = ((('N',1),), ROW_MMAP)

    def __init__(self, object_num, values=None):
        self.reg_report_table = OrderedDict()   #store report id range for each reg
        desc = PageElementMmap.PageDesc(self.PAGE_TITLE)
        for i in range(object_num):
            idx = (str(i), 1)
            desc.add_content((idx,), self.ROW_MMAP)

        #self.Mmap * object_num
        super(Page1Mem, self).__init__(self.PAGE_ID, desc, values, RowElementByte)

    def parent_inst(self):
        return -1

    def set_reg_reporter(self, reg_id, report_range):
        self.reg_report_table[reg_id] = report_range

    def get_reg_reporer(self, reg_id):
        if reg_id is not None:
            if reg_id in self.reg_report_table.keys():
                return self.reg_report_table[reg_id]
        else:
            return self.reg_report_table


class Page2Mem(PageElementMmap):

    def __init__(self, page_id, parent_inst, desc, values=None):
        self._parent_inst = parent_inst
        #desc = self.load_page_desc(page_id, parent_inst, size)
        super(Page2Mem, self).__init__(page_id, desc, values, RowElement)

    def parent_inst(self):
        return self._parent_inst

class PageMessageMap(PageElementMmap):

    def __init__(self, page_id, report_id, desc):
        super(PageMessageMap, self).__init__(report_id, desc, None, RowElement)
        self.page_id = page_id

class PagesMemoryMap(object):
    PATTERN_CONFIG_TABLE_NAME = re.compile("Configuration for [A-Z_]+(\d+)( Instance (\d))?")
    PATTERN_MESSAGE_TABLE_NAME = re.compile("Message Data for [A-Z_]+(\d+)( – (.*))?")
    MESSAGE_EXTRA_INFO_TABLE = {100: ["First Report ID", "Second Report ID", "Subsequent Touch Report IDs"]}
    SIZE_ROW_IDX_ELEM = 2

    def __init__(self, chip_id, product_doc=None):
        self.mem_map = OrderedDict()
        self.msg_map = dict()
        self._doc = product_doc #Fixme: product doc has some bugs of splitted rows

        #build page 0 memory map table
        mmem = Page0Mem(chip_id)
        self.set_mem_map(mmem)

        #build page 1 memory map table
        object_num = mmem.search('object_num')
        if object_num:
            mmem = Page1Mem(object_num)
            self.set_mem_map(mmem)

    def inited(self):
        return len(self.mem_map) > 2 #has get object table

    def build_default_desc(self, size):
        desc = PageElementMmap.PageDesc(None)
        for i in range(size):
            idx = (str(i), 1)
            desc.add_content((idx,), (('TBD', 8),))

        return desc

    def _parse_desc(self, table, size, fn_check_result, pat_name):
        if not table:
            return

        split_row_content = lambda row_value: (row_value[:self.SIZE_ROW_IDX_ELEM], row_value[self.SIZE_ROW_IDX_ELEM:])
        get_row_id = lambda idx: idx[0]
        get_data_elem_length = lambda elem: sum(map(lambda e: e[1], elem))

        for k, v in table.items():
            result = pat_name.match(k)
            if fn_check_result(result):
                print("Found desc:", k)
                title = split_row_content(v[0])
                desc = PageElementMmap.PageDesc(title)
                length_row_title = get_data_elem_length(title[1])
                for i in range(1, len(v)):
                    idx, elem = split_row_content(v[i])
                    length = get_data_elem_length(elem)
                    if length != length_row_title:
                        print("Skip not integrity desc:", v[i])
                        elem = (('TBD', 8),)
                    row_id = get_row_id(idx)
                    result = re.split('[–-]', row_id[0])
                    if len(result) > 1:
                        try:
                            st, end = map(int, result)
                            for id in range(st, end + 1):
                                idx_new = [(str(id), row_id[1])].extend(idx[1:])
                                desc.add_content(idx_new, elem)
                        except:
                            print("Falied split row id:", v[i])
                            break
                    else:
                        desc.add_content(idx, elem)

                if size is not None:
                    if len(desc) != size:
                        print("desc size mismatch(%d) (%d):" %(size, len(desc)), v)
                        break

                return desc

        #print(self.__class__.__name__, page_id, parent_inst, size)
        #desc = ((('TBD', 8),),) * size

    def load_page_mem_desc(self, page_id, parent_inst, size):
        def check_result(reg_id, inst_id, result):
            if not result:
                return

            if str(reg_id) == result.group(1):
                einfo = result.group(3)
                if not einfo or einfo == str(inst_id):
                    return True

        reg_id, inst_id = page_id
        fn_check_result = partial(check_result, reg_id, inst_id)
        desc = self._parse_desc(self._doc, size, fn_check_result, self.PATTERN_CONFIG_TABLE_NAME)
        if not desc:
            desc = self.build_default_desc(size)
        return desc

    def load_page_msg_desc(self, page_id, rrid, default_size):
        def get_extra_info(table, reg_id, rrid):
            if reg_id in table.keys():
                info = table[reg_id]
                if rrid < len(info):
                    return info[rrid]
                else:
                    return info[-1]

        def check_result(reg_id, rrid, result):
            if not result:
                return

            if str(reg_id) == result.group(1):
                einfo = get_extra_info(self.MESSAGE_EXTRA_INFO_TABLE, reg_id, rrid)
                if not einfo or einfo == result.group(3):
                    return True

        reg_id, inst_id = page_id
        fn_check_result = partial(check_result, reg_id, rrid)
        desc = self._parse_desc(self._doc, None, fn_check_result, self.PATTERN_MESSAGE_TABLE_NAME)
        if not desc:
            print("No found message desc for page {} report_id {}".format(page_id, rrid))
            desc = self.build_default_desc(default_size)
        return desc

    def set_mem_map(self, mmem):
        #print(self.__class__.__name__, "set_mem_map", mmem)
        self.mem_map[mmem.id()] = mmem

    def get_mem_map_tab(self, page_id=None):
        if page_id is not None:
            if page_id in self.mem_map.keys():
                return self.mem_map[page_id]
        else:
            return self.mem_map

    def set_msg_map(self, mmsg):
        # print(self.__class__.__name__, "set_mem_map", mmem)
        self.msg_map[mmsg.id()] = mmsg

    def get_reg_reporer(self, reg_id=None):
        mmap = self.get_mem_map_tab(Page.OBJECT_TABLE)
        if mmap:
            return mmap.get_reg_reporer(reg_id)

    def get_msg_map_tab(self, report_id=None):
        if report_id is not None:
            if report_id in self.msg_map.keys():
                return self.msg_map[report_id]
        else:
            return self.msg_map

    def create_chip_mmap_pages(self):
        if self.inited():
            return

        page0_mmap = self.get_mem_map_tab(Page.ID_INFORMATION)
        if not page0_mmap:
            return

        page1_mmap = self.get_mem_map_tab(Page.OBJECT_TABLE)
        if not page1_mmap:
            return

        #build other pages memory map table
        esize = ctypes.sizeof(ObjectTableElement)
        object_num = page0_mmap.search('object_num')
        if object_num:
            data = page1_mmap.raw_values()
            repo_st = 1
            for n in range(object_num):
                #print(self.__class__.__name__, data[n * esize: (n + 1) * esize])
                element = ObjectTableElement(*struct.unpack_from("<BHBBB", data[n * esize: (n + 1) * esize]))
                inst = element.instances_minus_one + 1
                num_repo = element.num_report_ids
                if num_repo:
                    page1_mmap.set_reg_reporter(element.type, range(repo_st, repo_st + num_repo * inst))
                for i in range(inst):
                    page_id = (element.type, i)
                    size = element.size_minus_one + 1
                    desc = self.load_page_mem_desc(page_id, inst, size)
                    mmem = Page2Mem(page_id, inst, desc)
                    self.set_mem_map(mmem)
                    if num_repo:
                        msg_reg = self.get_mem_map_tab((5, 0))
                        for j in range(num_repo):
                            desc = self.load_page_msg_desc(page_id, j, len(msg_reg))
                            mmsg = PageMessageMap(page_id, repo_st, desc)
                            self.set_msg_map(mmsg)
                            repo_st += 1

class ChipMemoryMap(object):
    CHIP_TABLE = {}

    def __init__(self, chip_id):
        pass

    @classmethod
    def get_datasheet(cls, chip_id):
        name = "db\\{:02x}_{:02x}_{:02x}.db".format(*chip_id[:3])

        for dir in ('.', '..'):
            path = os.path.join(dir, name)
            if os.path.exists(path):
                with open(path, 'r') as fp:
                    return json.load(fp)

    @classmethod
    def get_chip_mmap(cls, chip_id):
        cid = tuple(chip_id)
        if cid in cls.CHIP_TABLE.keys():
            return cls.CHIP_TABLE[cid]
        else:
            content = cls.get_datasheet(cid)
            mmap = PagesMemoryMap(cid, content)
            cls.CHIP_TABLE[cid] = mmap
            return mmap