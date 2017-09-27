from server.devinfo import Page

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
        self.fields = {}
        self.seq_rsv = 0
        self.pos = 0
        self.i = 0

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

    def full(self):
        return self.pos == RowElement.MAX_SIZE

    def set_field(self, name, val):
        if name in self.fields.keys():
            field = self.fields[name]
            max_value = (1 << field.width) - 1
            if val < max_value:
                raise ElemError("Filed {} width {} bit, value{} over max".format(name, field.width, val))

            field.value = val

    def get_field(self, name):
        #print(self.__class__.__name__, name, self.fields.keys(), name in self.fields.keys())
        if name in self.fields.keys():
            return self.fields[name].value

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

class PageElementMmap(object):

    def __init__(self, id, mmap, values=None):
        self.__id = Page.ID_INFORMATION
        self.all_rows = []
        for mem in mmap:
            r = RowElement(*mem)
            self.all_rows.append(r)

        if values:
            self.set_values(values)

    def id(self):
        return self.__id

    def set_values(self, values):
        if len(self.all_rows) != len(values):
            print("{} set_values len mismatch:\n{}\n{}".format(self.__class__.__name__, self.all_rows, values))

        for i, row_elem in enumerate(self.all_rows):
            if i >= len(values):
                break

            row_elem.set_value(values[i])

    def raw_values(self):
        values = []
        for row_elem in self.all_rows:
            values.append(row_elem.get_value())

        return values

    def select(self, row_idx, field_name=None):
        if row_idx < len(self.all_rows):
            row_elem = self.all_rows[row_idx]

            if not field_name:
                return row_elem.get_value()
            else:
                return row_elem.get_field(field_name)

    def __iter__(self):
        return iter(self.all_rows)

class PageMem(PageElementMmap):
    def __init__(self, id, mmap, values=None):
        super(PageMem, self).__init__(id, mmap, values)

class Page0Mem(PageMem):
    PAGE_ID = Page.ID_INFORMATION
    Mmap = (
        (("familiy_id", 8),),
        (("variant_id", 8),),
        (("version", 8),),
        (("build", 8),),
        (("maxtrix_xsize", 8),),
        (("maxtrix_ysize", 8),),
        (("object_num", 8),),
        #(('a', 3), ('b', 2), ('c', 1), ('d', 2)),
        #(("rsv", 4), ("rsv", 4)),
        #(('reserved',8),)
    )

    def __init__(self, values=None):
        super(Page0Mem, self).__init__(self.PAGE_ID, self.Mmap, values)

class PagesMemoryMap(object):

    def __init__(self):
        self.mmap_table = {}

    def load(self, chip_id):
        mmem = Page0Mem(chip_id)
        self.mmap_table[mmem.id()] = mmem

    def unload(self):
        self.mmap_table.clear()

    def get_mmap(self, page_id):
        if page_id in self.mmap_table.keys():
            return self.mmap_table[page_id]

class ChipMemoryMap(object):
    CHIP_TABLE = {}

    def __init__(self, chip_id):
        pass

    @staticmethod
    def parse_datasheet(self):
        pass

    @classmethod
    def get_chip_mmap(cls, chip_id):
        key = tuple(chip_id)
        if key in cls.CHIP_TABLE.keys():
            return cls.CHIP_TABLE[key]
        else:
            mmap = PagesMemoryMap()
            mmap.load(key)
            cls.CHIP_TABLE[key] = mmap
            return mmap