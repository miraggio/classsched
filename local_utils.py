import itertools
import sys
import time

def print_list(name, l, tab) :
    print name
    for x in l :
        print tab,x

def list2str(l):
    return " ".join(str(x) for x in l)

class MultiIndex:
    i = None
    irange = None
    size = 0
    current = 0
    maxopt = 1
    def __init__(self, irange):
        self.size = len(irange)
        self.irange = irange
        self.i = list(itertools.repeat(0, self.size))
        for k in irange:
            self.maxopt *= k
    def first(self):
        self.current = 0
        self.i = list(itertools.repeat(0, self.size))
        return self.i
    def next(self):
        self.current += 1
        if self.current >= self.maxopt:
            return None
        for k in range(self.size):
            self.i[k] += 1
            if self.i[k] >= self.irange[k]:
                self.i[k] = 0
            else:
                break
        return self.i
    def __str__(self):
        return '{:d} range [{:s}] current [{:s}]'.format(self.current, list2str(self.irange),  list2str(self.i))

class OptionListIterator:
    l = None
    maxopt = 1
    cur_opt = 0
    temp = None
    size = 0
    def __init__(self, option_list):
        self.l = option_list
        self.size = len(option_list)
        for i in range(self.size):
            self.maxopt *= option_list[i].iter_range()
    def first(self):
        self.temp = []
        self.cur_opt = 0
        for i in range(self.size):
            self.temp.append(self.l[i].first())
        return self.temp
    def next(self):
        self.cur_opt += 1
        if self.cur_opt >= self.maxopt:
            return None
        for i in range(self.size):
            el = self.l[i].next()
            if not el:
                self.temp[i] = self.l[i].first()
            else:
                self.temp[i] = el
                break;
        return self.temp


class ProgressBar:
    total = 0
    bar_len = 80
    started = 0
    prefix = ""
    def __init__(self, total, bar_len, prefix):
        self.total = total
        self.bar_len = bar_len
        self.started = time.clock()
        self.prefix = prefix
    def show(self, count):
        count += 1
        filled_len = int(round(self.bar_len * count / float(self.total)))
        percents = round(100.0 * count / float(self.total), 1)
        bar = '=' * filled_len + '-' * (self.bar_len - filled_len)
        out = '{:s}: [{:s}] {:5.1f}%  {:d} of {:d} {:d} seconds\r'.\
            format(self.prefix, bar, percents, count, self.total, int(time.clock() - self.started));
        sys.stderr.write(out)
        sys.stderr.flush()
    def done(self):
        sys.stderr.write("\n")


class Time:
    h = 9
    m = 0
    def __init__(self, h, m):
        self.h = h
        self.m = m
    def __str__(self):
        return '{:02d}:{:02d}'.format(self.h, self.m)
    def __gt__(self, other):
        return self.minutes() > other.minutes()
    def __lt__(self, other):
        return self.minutes() < other.minutes()
    def add(self, mins):
        mm = self.h * 60 + self.m + mins
        hh = int(mm / 60)
        mm = mm % 60
        return Time(hh, mm)
    def minutes(self):
        return self.h * 60 + self.m
#-

def str_time(s):
    hm = s.split(":")
    return Time(int(hm[0]), int(hm[1]))
