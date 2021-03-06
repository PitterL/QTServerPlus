from collections import OrderedDict
import struct
import array
import ctypes
import copy
import os, re, json
from functools import partial

from server.devinfo import Page, ObjectTableElement

class RowElement(object):
    #Page 1, 3 .... row layout( Filed unit is 'bit', 1 byte each row)
    MAX_FIELD_SIZE = 8

    class BitField(object):
        def __init__(self, start, width):
            self.start = start
            self.width = width
            self.value = 0
            self.max_value = (1 << width) - 1

        def __str__(self):
            return "{}({s}, {w}, {v})".format(self.__class__.__name__, s=self.start, w=self.width, v=hex(self.value))

        def __repr__(self):
            return self.__str__()

        def set_value(self, value):
            if value < self.max_value:
                self.value = value
            else:
                print(self.__class__.__name__, "set_value overflow", self, value)

    def __init__(self, row_desc):
        # self.idx_desc = row_desc.idx
        # self.content_desc = row_desc.content
        self.desc = row_desc
        self.fields = OrderedDict()
        self._pos = 0   #store filed relative pos in initilize
        self.value_size = self.MAX_FIELD_SIZE // 8

        for n, v in self.desc.data_content():
            self.add_field(n, v)

        # for n, v in ele_d:
        #     self.add_field(n, v)

    def __str__(self):
        return self.__class__.__name__ + str((self.desc))

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

    def values(self):
        return [field.value for field in self.fields.values()]

    def items(self):
        return dict(zip(self.keys(), self.values()))

    def field_values(self):
        return list(self.fields.values())

    def add_field(self, name, width):
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
            field.set_value(val)

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
            self.max_value = 0xff << width

        def __str__(self):
            return "{}({s}, {w}, {v}, '{c}')".format(self.__class__.__name__, s=self.start, w=self.width, v=hex(self.value), c=self.c_type)

        def __repr__(self):
            return self.__str__()

        def set_value(self, value):
            if value < self.max_value:
                self.value = value
            else:
                print(self.__class__.__name__, "set_value overflow", self, value)

    def __init__(self, row_desc):
        # self.idx_desc = row_desc.idx
        # self.content_desc = row_desc.content
        self.desc = row_desc
        self.fields = OrderedDict()
        self.pos = 0
        self.value_size = 0

        for name, width in self.desc.data_content():
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

    def values(self):
        return [field.value for field in self.fields.values()]

    def items(self):
        return dict(zip(self.keys(), self.values()))

    def field_values(self):
        return list(self.fields.values())

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
            field.set_value(val)

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
        ROW_IDX_ELEM_SIZE = 2
        (I_ROW_NO, I_ROW_NAME) = range(ROW_IDX_ELEM_SIZE)

        RSV_IDX_NAME = 'Reserved'
        RSV_DATA_NAME = 'RSV'

        def __init__(self, idx, content):
            self.i_content = idx
            self.d_content = content

        # def __iter__(self):
        #     # print(self.__class__.__name__, self.__rows_mm)
        #     return iter(self.content)

        # def __getitem__(self, key):
        #     return self.content[key]

        def no(self):
            if self.i_content and len(self.i_content) > self.I_ROW_NO:
                name, _ = self.i_content[self.I_ROW_NO]
                return name

        def name(self):
            if self.i_content and len(self.i_content) > self.I_ROW_NAME:
                name, _ = self.i_content[self.I_ROW_NAME]
                return name

        def idx_content(self):
            return self.i_content

        def data_content(self):
            return self.d_content

    class PageDesc(object):
        def __init__(self, row_title=None, extra_info=None):
            self.title_content = []
            self.row_content = []
            self.extra_info = extra_info
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

    def __init__(self, id, addr, page_desc, values, cls_row_elem):
        self.__id = id
        self._addr = addr
        self.title = []
        self.__rows_mm = []
        self.__values = None
        self.value_size = 0
        self._extra_info = page_desc.extra_info

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
    def address(self):
        return self._addr

    def parent_inst(self):
         return -1

    def extra_info(self):
        return self._extra_info

    def valid(self):
        return self.__values is not None

    def get_value_size(self):
        return self.value_size

    def set_values(self, values):
        if len(values) != self.value_size:
            print("values length mismatch({} {}):({})".format(len(values), self.value_size, values))

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

    # def select(self, row_idx, field_name=None):
    #     if row_idx < len(self.__rows_mm):
    #         row_elem = self.__rows_mm[row_idx]
    #
    #         if field_name is None:
    #             return row_elem.get_value()
    #         else:
    #             return row_elem.get_field(field_name)

    # def select_idx(self, row_idx, col_idx=None):
    #     if row_idx < len(self.__rows_mm):
    #         row_elem = self.__rows_mm[row_idx]
    #
    #         #print(self.__class__.__name__, row_elem)
    #         if col_idx is None:
    #             return row_elem.get_value()
    #         else:
    #             return row_elem.get_field_by_idx(col_idx)

    def search(self, field_name):
        for row_elem in self.__rows_mm:
            value = row_elem.get_field(field_name)
            if value is not None:
                return value

    # def row(self, row_id):
    #     return self.__rows_mm[row_id]

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

        super(Page0Mem, self).__init__(self.PAGE_ID, 0, desc, values, RowElement)

    def parent_inst(self):
        return -1

class Page1Mem(PageElementMmap):
    PAGE_ID = Page.OBJECT_TABLE
    ROW_MMAP = (
        ("type", 1), ("start_address", 2), ("size_minus_one", 1), ("instances_minus_one", 1), ("num_report_ids", 1)
    )
    PAGE_TITLE = ((('N',1),), ROW_MMAP)

    def __init__(self, addr, object_num, values=None):
        self.reg_report_table = OrderedDict()   #page_id to repo id map
        desc = PageElementMmap.PageDesc(self.PAGE_TITLE)
        for i in range(object_num):
            idx = (str(i), 1)
            desc.add_content((idx,), self.ROW_MMAP)

        #self.Mmap * object_num
        super(Page1Mem, self).__init__(self.PAGE_ID, addr, desc, values, RowElementByte)

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

    def __init__(self, page_id, addr, parent_inst, desc, values=None):
        self._parent_inst = parent_inst
        #desc = self.load_page_desc(page_id, parent_inst, size)
        super(Page2Mem, self).__init__(page_id, addr, desc, values, RowElement)

    def parent_inst(self):
        return self._parent_inst

class PageMessageMap(PageElementMmap):

    def __init__(self, page_id, parent_inst, report_id, report_range, desc):
        super(PageMessageMap, self).__init__(report_id, None, desc, None, RowElement)
        self._page_id = page_id
        self._parent_inst = parent_inst
        self._report_range = report_range

    def page_id(self):
        return self._page_id

    def parent_inst(self):
        return self._parent_inst

    def report_range(self):
        return self._report_range

class PagesMemoryMap(object):
    PATTERN_CONFIG_TABLE_NAME = re.compile("Configuration for [A-Z_]+(\d+)( Instance (\d))?")
    PATTERN_MESSAGE_TABLE_NAME = re.compile("Message Data for [A-Z_]+(\d+)( – (.*))?")
    MESSAGE_EXTRA_INFO_TABLE = {100: ["First Report ID", "Second Report ID", "Subsequent Touch Report IDs"]}

    SKIP_CONFIG_DESC = [117, 37, 5, 68, 71, 25, 56, 110]
    SKIP_MESSAGE_DESC = []

    def __init__(self, chip_id, product_doc=None):
        self.mem_map = OrderedDict()
        self.msg_map = dict()
        self._doc = product_doc #Fixme: product doc has some bugs of splitted rows
        self._chip_id = chip_id

        #build page 0 memory map table
        mmem = Page0Mem(chip_id)
        self.set_mem_map(mmem)

        #build page 1 memory map table
        object_num = mmem.search('object_num')
        if object_num:
            addr = mmem.get_value_size() #Page0 size if Page1 offset
            mmem = Page1Mem(addr, object_num)
            self.set_mem_map(mmem)
        else:
            print(self.__class__.__name__, "Invalid chip info", chip_id)

    def id(self):
        return self._chip_id

    def inited(self):
        return len(self.mem_map) > 2 #has get object table

    def build_default_desc(self, size):
        desc = PageElementMmap.PageDesc(None)
        for i in range(size):
            idx = (str(i), 1)
            desc.add_content((idx,), (('TBD', 8),))

        return desc

    def _parse_desc(self, table, size, fn_check_result, pat_name):
        RSV_NAME = ('rsv', 'reserved')
        def add_seq_replace_rsv(row_elem, old, new, r_seq, e_seq=None):
            for i in range(len(row_elem)):
                elem = row_elem[i]
                if elem[0].lower() in old:
                    elem[0] = new + str(r_seq)
                    r_seq += 1
                else:
                    if e_seq is not None:
                        c = elem[0][-1]
                        if not (c >= '0' and c <= '9'):
                            elem[0] = "%s %d" % (elem[0], e_seq)

            return r_seq

        if not table:
            return

        split_row_content = lambda row_value: (row_value[:PageElementMmap.RowDesc.ROW_IDX_ELEM_SIZE], row_value[PageElementMmap.RowDesc.ROW_IDX_ELEM_SIZE:])
        get_row_id = lambda idx: idx[0]
        get_row_idx_content = lambda idx: idx[1:]
        get_data_elem_length = lambda elem: sum(map(lambda e: e[1], elem))
        seq_i = seq_e = 0

        for k, v in table.items():
            result = pat_name.match(k)
            matched, extra = fn_check_result(result)
            if matched:
                print("Found desc:", k)
                title = split_row_content(v[0])
                desc = PageElementMmap.PageDesc(title, extra)
                length_row_title = get_data_elem_length(title[1])
                for i in range(1, len(v)):
                    idx, elem = split_row_content(v[i]) #row elem
                    length = get_data_elem_length(elem)
                    if length != length_row_title:
                        print("Skip not integrity desc:", v[i])
                        elem = (('TBD', 8),)
                    row_idx_id_no, _ = get_row_id(idx)
                    result = re.split('[–-]', row_idx_id_no)
                    if len(result) > 1:
                        try:
                            st, end = map(int, result)
                            for j in range(st, end + 1):
                                v_new = copy.deepcopy(v[i]) # need a copy for adjust index
                                idx, elem = split_row_content(v_new)
                                _, row_idx_id_name = get_row_id(idx)
                                row_idx_data = get_row_idx_content(idx)
                                seq_i = add_seq_replace_rsv(row_idx_data, RSV_NAME, PageElementMmap.RowDesc.RSV_IDX_NAME, seq_i, j - st)
                                seq_e = add_seq_replace_rsv(elem, RSV_NAME, PageElementMmap.RowDesc.RSV_DATA_NAME, seq_e, j - st)
                                idx_new = [(str(j), row_idx_id_name)]
                                idx_new.extend(row_idx_data)
                                desc.add_content(idx_new, elem)
                                print(idx_new, elem)
                        except:
                            print("Falied split row id:", v[i])
                            break
                    else:
                        seq_i = add_seq_replace_rsv(idx, RSV_NAME, PageElementMmap.RowDesc.RSV_IDX_NAME, seq_i)
                        seq_e = add_seq_replace_rsv(elem, RSV_NAME, PageElementMmap.RowDesc.RSV_DATA_NAME, seq_e)
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
            if result:
                if str(reg_id) == result.group(1):
                    einfo = result.group(3)
                    if not einfo or einfo == str(inst_id):
                        return True, einfo
            return False, None

        desc = None
        reg_id, inst_id = page_id
        if reg_id not in self.SKIP_CONFIG_DESC:
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
            if result:
                if str(reg_id) == result.group(1):
                    einfo = get_extra_info(self.MESSAGE_EXTRA_INFO_TABLE, reg_id, rrid)
                    if not einfo or einfo == result.group(3):
                        return True, einfo
            return False, None

        desc = None
        reg_id, inst_id = page_id
        if reg_id not in self.SKIP_MESSAGE_DESC:
            fn_check_result = partial(check_result, reg_id, rrid)
            desc = self._parse_desc(self._doc, None, fn_check_result, self.PATTERN_MESSAGE_TABLE_NAME)

        if not desc:
            print("No found message desc for page {} report_id {}".format(page_id, rrid))
            desc = self.build_default_desc(default_size)
        return desc

    def set_mem_map(self, mmem):
        #print(self.__class__.__name__, "set_mem_map", mmem)
        self.mem_map[mmem.id()] = mmem  #repo id to mmsg

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
                addr = element.start_address
                inst = element.instances_minus_one + 1
                num_repo = element.num_report_ids
                # if num_repo:
                #     page1_mmap.set_reg_reporter(element.type, (repo_st, repo_st + num_repo * inst - 1))
                for i in range(inst):
                    page_id = (element.type, i)
                    size = element.size_minus_one + 1
                    desc = self.load_page_mem_desc(page_id, inst, size)
                    mmem = Page2Mem(page_id, addr, inst, desc)
                    self.set_mem_map(mmem)
                    if num_repo:
                        inst_repo_range = (repo_st, repo_st + num_repo - 1)
                        page1_mmap.set_reg_reporter(page_id, inst_repo_range)   #page_id to repo id map
                        msg_reg = self.get_mem_map_tab((5, 0))
                        for j in range(num_repo):
                            desc = self.load_page_msg_desc(page_id, j, len(msg_reg))
                            mmsg = PageMessageMap(page_id, inst, repo_st + j, inst_repo_range, desc)
                            self.set_msg_map(mmsg)  #repo id to mmsg map
                        repo_st += num_repo

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
            if all(cid):
                content = cls.get_datasheet(cid)
                chip = PagesMemoryMap(cid, content)
                cls.CHIP_TABLE[cid] = chip
                return chip

    @classmethod
    def delete(cls, chip_id):
        cid = tuple(chip_id)
        if cid in cls.CHIP_TABLE.keys():
            del cls.CHIP_TABLE[cid]

class ElementProcessor():
    COMBINE_WORDS = {'lsbits': 0, 'lsbyte': 0, 'msbyte': 1 }

    def __init__(self):
        self._data = {}
        self._compound = {}

    def save_compound_value(self, field_name, field, row_name, row_fields_num):
        def get_name(words, name):
            for word in words:  #word: 'Current X Position', name 'XPos' is match
                w = word.lower().replace(' ', '')
                n = name.lower().replace(' ', '')
                if n in w or w in n:
                    return word
            return name

        #compond value
        result = field_name.rsplit(maxsplit=1)
        if len(result) == 2:
            main, suffix = result
            tag = suffix.lower()
            if tag in self.COMBINE_WORDS.keys():    #suffix in list
                #if main not in self._compound:
                name = get_name(self._compound.keys(), main)
                if name not in self._compound.keys():
                    self._compound[name] = []
                k = self.COMBINE_WORDS[tag]
                v = (row_name, field) #order as key
                self._compound[name].append((k, v))
                return True

    def _process_compound(self):
        for main, v in self._compound.items():
            if not v:
                continue

            value = 0
            ns = set()  #check whether row_name is same
            for (_, data) in sorted(v, reverse=True):
                row_name, field = data
                value <<= field.width
                value += field.value

                result = row_name.rsplit(maxsplit=1)    #e.g. row name is 'XPOS 1'
                if result[-1].isdigit():
                    row_name = result[0]

                ns.add(row_name)

            if len(ns) < len(v):
                name = ns.pop() #use row name
            else:
                name = main #if row name is not same, use main name

            self._data[name] = value

    def save_value(self, field_name, field, row_name, row_fields_num):
        #normal value
        if row_fields_num == 1:
            name = row_name
        else:
            name = field_name
        self._data[name] = field.value

    #field_name, field, row_name, row_fields_num
    def push(self, *args):
        result = self.save_compound_value(*args)
        if not result:
            self.save_value(*args)

    def output(self):
        self._process_compound()
        return self._data

    def clear(self):
        self._data = {}
        self._compound = {}