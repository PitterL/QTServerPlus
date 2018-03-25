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
        #print(self.data)
        print("Get page", n)

    def max(self, size=None):
        if isinstance(size, (tuple, list)):
            xsize, ysize = size
            d = self.data.iloc[:xsize, :ysize]
        else:
            d = self.data
        return d.max().max()

    def min(self, size=None):
        if isinstance(size, (tuple, list)):
            xsize, ysize = size
            d = self.data.iloc[:xsize, :ysize]
        else:
            d = self.data

        return d.min().min()

class DebugViewLog(loader):
    FILE_FORMAT = {'mxtapp': {'sep':',', 'title':r'[xX](\d+)[yY](\d+)', 'row_name':"%H:%M:%S.%f", 'st': 2, 'end': None},
                    'hawkeye': {'sep': ',', 'title': r'[xX](\d+)[yY](\d+)', 'row_name': "%H:%M:%S %f", 'st': 1, 'end': None},
                    'studio': {'sep': ',', 'title': r'[xX](\d+)[yY](\d+)', 'row_name': "%H:%M:%S %f", 'st': 1, 'end': None}}

    def __init__(self, type, size, filename=None):
        super().__init__()

        self.title = None
        self.parsing_word = self.FILE_FORMAT[type]
        self.channel_size = size
        self.matrix_size = None
        self.load_file(filename)
        self.frames = []

    @classmethod
    def supported_format(cls, format):
        return format in cls.FILE_FORMAT.keys()

    def set_maxtrix_size(self, size):
        self.matrix_size = size
        if not self.channel_size:
            self.channel_size = size    #default value for channel size

    def parse(self, filename=None):
        if filename:
            self.load_file(filename)

        if not self.f:
            return

        del self.frames[:]

        for i, line in enumerate(list(self.f)):
            if line.isspace():
                continue

            content = line.split(self.parsing_word['sep'])
            if content[-1].isspace():
                content.pop()   #remove null tail

            if not self.title:
                #channel_list = content[2:]
                channel_list = content[self.parsing_word['st']:self.parsing_word['end']]
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

                size = (mx + 1, my + 1)
                self.set_maxtrix_size(size)
                self.title = channel_list[0].split('_')[0]
            else:
                try:
                    dt = datetime.strptime(content[0], self.parsing_word['row_name'])
                    st = self.parsing_word['st']
                    end = self.parsing_word['end']
                    if st > 1:
                        n = int(content[1])
                    else:
                        n = i

                    v = np.array(list(map(int, content[st: end]))).reshape(self.matrix_size)
                    ref = reference(dt, n ,v)
                    self.frames.append(ref)
                except:
                    print("Invalid data value:", content)

        self.close_file()

    def save_to_file(self, limit, output=None):
        if not output:
            output = self.filename + '.xlsx'

        writer = pd.ExcelWriter(output)

        for frame in self.frames:
            if limit:
                inside, low, hight = limit
                v_max = frame.max(self.channel_size)
                v_min = frame.min(self.channel_size)
                if v_max <= hight and v_min >= low:
                    v_inside = True
                else:
                    v_inside = False

                if v_inside != inside:
                    continue

            print("Save page", frame.n)
            frame.data.to_excel(writer, sheet_name=str(frame.n))

        writer.save()

        print("Save to:", output)

if __name__ == '__main__':
    # log = DebugViewLog('HAWKEYE')
    # #filename = r"D:\trunk\customers2\BYD\12.8_Qin100_1664s\log\ref2.log"
    # filename = r"D:\trunk\tools\maXStudio control files\Hawkeye_20180125_190246.csv"
    # log.parse(filename)
    # log.save_to_file()

    import os
    import sys
    import argparse

    def parse_range(limit_txt):
        if not limit_txt:
            return

        limit_txt = limit_txt.strip()
        pat = re.compile(r'\^?\((-?\d+)[ \t]*,[ \t]*(-?\d+)\)')
        if limit_txt:
            result = pat.match(limit_txt)
            if result:
                low, high = result.groups()
                if limit_txt[0] == '^':
                    inside = False
                else:
                    inside = True
                limit = (inside, int(low), int(high))
                print("Set limit:", limit)
                return limit

    def parse_size(size_txt):
        if not size_txt:
            return size_txt

        size_txt = size_txt.strip()
        pat = re.compile(r'\((-?\d+)[ \t]*,[ \t]*(-?\d+)\)')
        if size_txt:
            result = pat.match(size_txt)
            if result:
                low, high = result.groups()
                size = (int(low), int(high))
                print("Set size:", size)
                return size

    def runstat(args=None):
        parser = parse_args(args)
        aargs = args if args is not None else sys.argv[1:]
        args = parser.parse_args(aargs)
        print(args)

        if not args.filename and not args.type:
            parser.print_help()
            return

        format = args.type
        if not DebugViewLog.supported_format(format):
            print("Unsupported type", format)
            return

        limit = parse_range(args.range)
        size = parse_size(args.size)

        path = args.filename
        if path:
            if os.path.exists(path):
                log_parser = DebugViewLog(format, size)
                log_parser.parse(path)
                log_parser.save_to_file(limit)
            else:
                print('Un-exist file name \'{:s}\''.format(path))

    def parse_args(args=None):

        parser = argparse.ArgumentParser(
            prog='xparse',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='Tools for parsing debug log to xlxs file')

        parser.add_argument('--version',
                            action='version', version='%(prog)s v1.0.0',
                            help='show version')

        parser.add_argument('-f', '--filename', required=True,
                            nargs='?',
                            default='',
                            metavar='LOG_FILE',
                            help='where the \'XCFG|TXT\' file will be load')

        parser.add_argument('-t', '--type', required=True,
                            nargs='?',
                            default='',
                            const='.',
                            metavar='hawkeye|mxtapp|studio',
                            help='format of of file data content')

        parser.add_argument('-r', '--range', required=False,
                            nargs='?',
                            default='',
                            const='.',
                            metavar='^(low, hight)',
                            help='value range to save result, store to (low, high), ^ mean not in range')

        parser.add_argument('-s', '--size', required=False,
                            nargs='?',
                            default='',
                            const='.',
                            metavar='^(XSIZE, YSIZE)',
                            help='value to told XSIZE/YSIZE')

        return parser


    cmd = None
    #cmd = r'-t mxtapp -r ^(19000,28000) -s (30,52) -f D:\trunk\customers2\BYD\12.8_Qin100_1664s\log\ref2.log.csv'.split()
    #cmd = r"-t studio -r ^(-100,100) -f  D:\trunk\customers2\Desay\Desay_DFLZM_SX7_10.1Inch_641T_14804_Goworld\log\Graphical_Debug_Viewer_Log_19_三月_11_22_48.csv".split()
    runstat(cmd)