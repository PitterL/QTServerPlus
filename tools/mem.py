from collections import OrderedDict
import struct
import array
import ctypes
import re, json

from server.devinfo import Page, ObjectTableElement

class RowElement(object):
    RSV_NAME = ('rsv', 'reserved')
    MAX_SIZE = 8

    class BitField(object):
        def __init__(self, start, width):
            self.start = start
            self.width = width
            self.value = 0

        def __str__(self):
            return "{}({s}, {w}, {v})".format(self.__class__.__name__, s=self.start, w=self.width, v=hex(self.value))

        def __repr__(self):
            return self.__str__()

    def __init__(self, *ele_t, **ele_d):
        self.fields = OrderedDict()
        self.seq_rsv = 0
        self.pos = 0
        self.size = self.MAX_SIZE / 8

        for n, v in ele_t:
            self.add_field(n, v)

        for n, v in ele_d:
            self.add_field(n, v)

    def __str__(self):
        return str(self.fields)

    def __repr__(self):
        return super(RowElement, self).__repr__() + '(' + self.__str__() + ')'

    def add_field(self, name, width):
        if name.lower() in RowElement.RSV_NAME: #cover rsv name with a seq suffix
            name = RowElement.RSV_NAME[0] + str(self.seq_rsv)
            self.seq_rsv += 1

        if name not in self.fields.keys():
            self.fields[name] = RowElement.BitField(self.pos, width)
            self.pos += width

        if self.pos > RowElement.MAX_SIZE:
            raise Exception("pos{} out of mem".format(self.pos))

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

    def value_size(self):
        return self.size

    def set_value(self, val):
        for field in self.fields.values():
            field.value = (val >> field.start) & ((1 << field.width) - 1)

    def get_value(self):
        val = 0
        for field in self.fields.values():
            val |= (field.value << field.start)
        return val

    def __iter__(self):
        return iter(tuple(self.fields.items()))

class RowElementByte(object):

    class ByteField(object):
        def __init__(self, start, width, c_type):
            self.start = start
            self.width = width
            self.c_type = c_type
            self.value = 0

        def __str__(self):
            return "{}({s}, {w}, {v}, '{c}')".format(self.__class__.__name__, s=self.start, w=self.width, v=hex(self.value), c=self.c_type)

        def __repr__(self):
            return self.__str__()

    def __init__(self, *ele_t):
        self.fields = OrderedDict()
        self.pos = 0
        self.size = 0

        for elem in ele_t:
            self.add_field(*elem)
            self.size += elem[1]

    def __str__(self):
        return str(self.fields)

    def __repr__(self):
        return super(RowElementByte, self).__repr__() + '(' + self.__str__() + ')'

    def add_field(self, name, width, c_type):
        if name not in self.fields.keys():
            self.fields[name] = RowElementByte.ByteField(self.pos, width, c_type)
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

    def value_size(self):
        return self.size

    def set_value(self, t_val):
        for field in self.fields.values():
            if field.start + field.width > len(t_val):
                break

            field.value = struct.unpack_from(field.c_type, t_val[field.start: field.start + field.width])[0]

    def get_value(self):
        t_val = []
        #print(self.__class__.__name__, self.fields)
        for field in self.fields.values():
            t_val.extend(struct.pack('<' + field.c_type, field.value))

        return array.array('B', t_val)

    def __iter__(self):
        return iter(tuple(self.fields.items()))

class PageElementMmap(object):

    def __init__(self, id, mmap, values, row_elem_type):
        self.__id = id
        self.__rows_mm = []
        self.__values = None
        for mem in mmap:
            r = row_elem_type(*mem)
            self.__rows_mm.append(r)

        if values:
            self.set_values(values)

        #print(self.__class__.__name__, "init", self)

    def __str__(self):
        return super(PageElementMmap, self).__str__() + "page id {}, inst {}".format(self.id(), self.parent_inst())

    def valid(self):
        return self.__values is not None

    def id(self):
        return self.__id

    def instance_id(self):
        if isinstance(self.id(), tuple):
            return self.id()[-1]

    def parent_inst(self):
        return 0

    def set_values(self, values):
        self.__values = values
        for i, row_elem in enumerate(self.__rows_mm):
            size = row_elem.value_size()
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

    def __iter__(self):
        #print(self.__class__.__name__, self.__rows_mm)
        return iter(self.__rows_mm)

    def __getitem__(self, key):
        return self.__rows_mm[key]

class Page0Mem(PageElementMmap):
    PAGE_ID = Page.ID_INFORMATION
    Mmap = (
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
        super(Page0Mem, self).__init__(self.PAGE_ID, self.Mmap, values, RowElement)

class Page1Mem(PageElementMmap):
    PAGE_ID = Page.OBJECT_TABLE
    Mmap = (
        (("type", 1, 'B'), ("start_address", 2, 'H'), ("size_minus_one", 1, 'B'), ("instances_minus_one", 1, 'B'), ("num_report_ids", 1, 'B'),),
    )

    def __init__(self, object_num, values=None):
        super(Page1Mem, self).__init__(self.PAGE_ID, self.Mmap * object_num, values, RowElementByte)

class Page2Mem(PageElementMmap):

    def __init__(self, page_id, parent_inst, desc, values=None):
        self.__parent_inst = parent_inst
        #desc = self.load_page_desc(page_id, parent_inst, size)
        super(Page2Mem, self).__init__(page_id, desc, values, RowElement)

    def parent_inst(self):
        return self.__parent_inst

    # def load_page_desc(self, page_id, parent_inst, size):
    #     #print(self.__class__.__name__, page_id, parent_inst, size)
    #     desc = ((('TBD', 8),),) * size
    #     return desc

class PagesMemoryMap(object):

    def __init__(self, chip_id, datasheet=None):
        self.mmap_table = OrderedDict()
        self.datasheet = datasheet

        #build page 0 memory map table
        mmem = Page0Mem(chip_id)
        self.set_mmap(mmem)

        #build page 1 memory map table
        object_num = mmem.search('object_num')
        if object_num:
            mmem = Page1Mem(object_num)
            self.set_mmap(mmem)

    def inited(self):
        return len(self.mmap_table) > 2 #has get object table

    def load_page_desc(self, page_id, parent_inst, size):
        pat_name = re.compile("Configuration for [A-Z_]+(\d+)( Instance (\d))?")
        reg_id, inst_id = page_id
        for k, v in self.datasheet.items():
            result = pat_name.match(k)
            if result is not None:
                if str(reg_id) == result.group(1):
                    if not result.group(3) or str(inst_id) == result.group(3):
                        print("Found desc:", k)
                        if len(v) != size + 1:
                            print("desc size mismatch(%d) (%d):" %(size, len(v)), v)
                            break

                        desc = []
                        for row in v[1:]:
                            elem = row[2:]
                            length = sum(map(lambda e: e[1], elem))
                            if length != 8:
                                print("Skip not integrity desc:", elem)
                                elem = (('TBD', 8),)
                            desc.append(elem)
                        print(desc)
                        return desc

        return ((('TBD', 8),),) * size

        #print(self.__class__.__name__, page_id, parent_inst, size)
        desc = ((('TBD', 8),),) * size
        return desc

    def set_mmap(self, mmem):
        #print(self.__class__.__name__, "set_mmap", mmem)
        self.mmap_table[mmem.id()] = mmem

    def get_mmap(self, page_id=None):
        if page_id is not None:
            if page_id in self.mmap_table.keys():
                return self.mmap_table[page_id]
        else:
            return self.mmap_table

    def create_default_mmap_pages(self):
        if self.inited():
            return

        page0_mmap = self.get_mmap(Page.ID_INFORMATION)
        if not page0_mmap:
            return

        page1_mmap = self.get_mmap(Page.OBJECT_TABLE)
        if not page1_mmap:
            return

        #build other pages memory map table
        esize = ctypes.sizeof(ObjectTableElement)
        object_num = page0_mmap.search('object_num')
        if object_num:
            data = page1_mmap.raw_values()
            for n in range(object_num):
                #print(self.__class__.__name__, data[n * esize: (n + 1) * esize])
                element = ObjectTableElement(*struct.unpack_from("<BHBBB", data[n * esize: (n + 1) * esize]))
                inst = element.instances_minus_one + 1
                for i in range(inst):
                    page_id = (element.type, i)
                    size = element.size_minus_one + 1
                    desc = self.load_page_desc(page_id, inst, size)
                    mmem = Page2Mem(page_id, inst, desc)
                    self.set_mmap(mmem)

class ChipMemoryMap(object):
    CHIP_TABLE = {}

    def __init__(self, chip_id):
        pass

    @classmethod
    def get_datasheet(cls, chip_id):
        name = "..\\db\\{:02x}_{:02x}_{:02x}.db".format(*chip_id[:3])
        with open(name, 'r') as fp:
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