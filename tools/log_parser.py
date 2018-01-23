import re
from datetime import datetime
import numpy as np
import pandas as pd

class loader(object):
    def __init__(self, filename=None):
        self.f = None
        self.load_file(filename)

    def load_file(self, filename):
        if filename:
            if self.f:
                self.f.close()
            try:
                self.f = open(filename, 'r')
                self.filename = filename
            except:
                print("unable to open file {}".format(filename))

    def close_file(self):
        self.f.close()
        self.f = None

class reference(object):
    def __init__(self, dt, n, np_data):
        self.dt = dt
        self.n = n
        self.maxtrix = (mx, my) = (len(np_data), len(np_data[0]))

        row_name = ["X{}".format(i) for i in range(mx)]
        col_name = ["Y{}".format(i) for i in range(my)]
        self.data = pd.DataFrame(np_data, index=row_name, columns=col_name)
        print(self.data)

class mxt_app_log(loader):
    PARSING_WORD = {'MXTAPP': {'sep':',', 'title':r'[xX](\d+)[yY](\d+)', 'row_name':"%H:%M:%S.%f", 'st': 2, 'end': None},
                    'HAWKEYE': {'sep': ',', 'title': r'[xX](\d+)[yY](\d+)', 'row_name': "%H:%M:%S %f", 'st': 1, 'end': None}}

    def __init__(self, type, filename=None):
        super().__init__()

        self.title = None
        self.parsing_word = self.PARSING_WORD[type]
        self.matrix_xy = None
        self.load_file(filename)
        self.frames = []

    def parse(self, filename=None):
        if filename:
            self.load_file(filename)

        if not self.f:
            return

        del self.frames[:]

        for line in list(self.f):
            if line.isspace():
                continue

            content = line.split(self.parsing_word['sep'])
            if content[-1].isspace():
                content.pop()   #remove null tail

            if not self.title:
                channel_list = content[2:]
                pat = re.compile(self.parsing_word['title'])

                mx, my = (0, 0)
                for name in channel_list:
                    t = pat.match(name)
                    if t:
                        x, y = map(int, t.groups())
                        if mx < x:
                            mx = x

                        if my < y:
                            my = y

                self.matrix = (mx + 1, my + 1)
                self.title = channel_list[0].split('_')[0]
            else:
                try:
                    dt = datetime.strptime(content[0], self.parsing_word['row_name'])
                    n = int(content[1])
                    v = np.array(list(map(int, content[self.parsing_word['st']:self.parsing_word['end']]))).reshape(self.matrix)
                    ref = reference(dt, n ,v)
                    self.frames.append(ref)
                except:
                    print("Invalid data value:", content)

        self.close_file()

    def save_to_file(self, output=None):
        if not output:
            output = self.filename + '.xlsx'

        writer = pd.ExcelWriter(output)

        for frame in self.frames:
            frame.data.to_excel(writer, sheet_name=str(frame.n))

        writer.save()

if __name__ == '__main__':
    log = mxt_app_log('HAWKEYE')
    #filename = r"D:\trunk\customers2\BYD\12.8_Qin100_1664s\log\ref2.log"
    filename = r"D:\trunk\tools\maXStudio control files\Hawkeye_20180116_105452.csv"
    log.parse(filename)
    log.save_to_file()