import time
import itertools
import sys
from copy import deepcopy
from operator import methodcaller
import local_utils as LU

# constants

__debug = True
_rooms = []
_teachers = []
_groups = []
_schedules = []

_permuts = {}

roomlist = []
teacherlist = []
classlist = []
grouplist = []

_lunch_class = "Lunch"


def is_room(x):
    return x in roomlist
def is_teacher(x):
    return x in teacherlist
def is_class(x):
    return x in classlist
def is_group(x):
    return x in grouplist

def check_lists():
    for x in roomlist:
        if is_teacher(x) or is_class(x) or is_group(x):
            print "Duplicate entry: ", x
            return False
    for x in teacherlist:
        if is_room(x) or is_class(x) or is_group(x):
            print "Duplicate entry: ", x
            return False
    for x in classlist:
        if is_teacher(x) or is_room(x) or is_group(x):
            print "Duplicate entry: ", x
            return False
    for x in grouplist:
        if is_teacher(x) or is_class(x) or is_room(x):
            print "Duplicate entry: ", x
            return False
    return True
#-

def filter_from_dict(values, dict):
    ret = []
    for x in values:
        v = x.split(":")
        if v[0] in dict:
            ret.append(x)
    return ret
#-


class Attribute:
    attr_name = ''
    name = ''
    group_class = None
    def __init__(self, name, fields):
        self.attr_name = name
        self.group_class = {}
        self.group_class["*"] = []
        self.name = fields[0]
        self.add(fields[1:])
        #self.show()
    def show(self):
        print self.attr_name, self.name
        for gn in self.group_class.keys():
            print "\t", gn, ": ", self.group_class[gn]

    def __str__(self):
        return self.name
    def add(self, fields):
        class_names = filter_from_dict(fields, classlist)
        group_names = filter_from_dict(fields, grouplist)
        for gn in group_names:
            if gn not in self.group_class.keys():
                self.group_class[gn] = []
            for cn in class_names:
                self.group_class[gn].append(cn)
        if len(group_names) == 0:
            for cn in class_names:
                self.group_class["*"].append(cn)
    def matches(self, gr_name, cl_name):
        return cl_name in self.group_class["*"]
    def dedicated(self, gr_name, cl_name):
        if gr_name in self.group_class.keys():
            return cl_name in self.group_class[gr_name]
        return False
#-

class Class:
    name = ''
    duration = 0
    def __init__(self, name_duration):
        self.name, duration = name_duration.split(":")
        self.duration = int(duration)
        #print self
    def __str__(self):
        return '{:s}:{:d}'.format(self.name, self.duration)
#-

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

def minutes2Time(mins):
    return Time(mins / 60, mins % 60)

def time_overlap(start1, end1, start2, end2):
    start1m = start1.minutes()
    start2m = start2.minutes()
    stop1m = end1.minutes()
    stop2m = end2.minutes()
    dur1 = stop1m - start1m
    dur2 = stop2m - start2m
    if dur1 <= dur2:
        overlap = not ((stop1m <= start2m) or (start1m >= stop2m))
    else:
        overlap = not ((stop2m <= start1m) or (start2m >= stop1m))
    return overlap
#-

def str_time(s):
    hm = s.split(":")
    return Time(int(hm[0]), int(hm[1]))
#-

def getAttributes(attrs, cl, grp):
    ret = []
    for r in attrs:
        if r.dedicated(grp.name, cl.name):
            ret.append(r)
    if len(ret):
        return ret
    for r in attrs:
        if r.matches(grp.name, cl.name):
            ret.append(r)
    return ret
#-

def getRooms(cl, grp):
    return getAttributes(_rooms, cl, grp)
#-

def getTeachers(cl, grp):
    return getAttributes(_teachers, cl, grp)
#-

class Sched_option_item:
    class_name = ''
    tstart = None
    tend = None
    room_names = None
    teacher_names = None
    nr = 0
    nt = 0
    sel_teacher = 0
    sel_room = 0
    is_ok = " "
    def __init__(self, cl_name, room_names, teacher_names, tstart, tend):
        self.class_name = cl_name
        self.tstart = tstart
        self.tend = tend
        self.room_names = room_names
        self.teacher_names = teacher_names

        self.nr = len(self.room_names)
        self.nt = len(self.teacher_names)
    def ok(self):
        self.is_ok = "*"
    def make_copy(self):
        return Sched_option_item(self.class_name, self.room_names, self.teacher_names, \
                self.tstart, self.tend)
    def show_selection(self):
        t_str = self.teacher_names[self.sel_teacher]
        r_str = self.room_names[self.sel_room]
        return '{:s} {:10s} {:s}-{:s} {:s} {:s}'.format(self.is_ok, \
                self.class_name, self.tstart, self.tend, r_str, t_str)
    def __str__(self):
        t_str = LU.list2str(self.teacher_names)
        r_str = LU.list2str(self.room_names)
        return '{:s} {:10s} {:s}-{:s} [{:s}] [{:s}]'.format(self.is_ok, \
                self.class_name, self.tstart, self.tend, r_str, t_str)
    def rewind_teacher(self):
        self.sel_teacher = 0
    def next_teacher(self):
        if self.sel_teacher < (self.nt - 1):
            self.sel_teacher += 1
            return True
        return False
    def rewind_room(self):
        self.sel_room = 0
    def next_room(self):
        if self.sel_room < (self.nr - 1):
            self.sel_room += 1
            return True
        return False
    def selected_teacher(self):
        return self.teacher_names[self.sel_teacher]
    def selected_room(self):
        return self.room_names[self.sel_room]
#-

class Sched:
    sched_items = None
    group_name = ''
    def __init__(self, shedopt):
        self.sched_items = []
        self.group_name = shedopt.group_name
    def add_one(self, item):
        self.sched_items.append(item)
    def add_list(self, items):
        for k in items:
            self.add_one(k)
    def show(self):
        print 'Schedule for group {:10s}\n'.format(self.group_name)
        LU.print_list("classes: ", self.sched_items, "\t")


class Sched_option:
    #items is list of Sched objects
    items = None
    list_iter = None
    def __init__(self):
        self.items = []
    def add_item(self, item):
        self.items.append(item)
    def show(self):
        print self
        LU.print_list("classes: ", self.items, "\t")
    def first(self):
        sched = Sched(self)
        self.list_iter = LU.OptionListIterator(self.items)
        x = self.list_iter.first()
        sched.add_list(x)
        return sched
    def next(self):
        x = self.list_iter.next()
        if not x:
            return None
        sched = Sched(self)
        sched.add_list(x)
        return sched
#}

class Group:
    name = ''
    size = 0
    start = Time(9, 0)
    lfrom = Time(9, 0)
    lto = Time(9, 0)
    classes = None
    class_room_options = None
    class_teacher_options = None
    num_scheds = 0
    current_option = 0
    schedule = None
    has_lunch = False

    def __init__(self, fields):
        self.name = fields[1]
        self.size = fields[2]
        self.start = str_time(fields[3])
        self.lfrom = str_time(fields[4])
        class_names = filter_from_dict(fields[5:], classlist)

        classes = []
        for cl in class_names:
            new_class = Class(cl)
            classes.append(new_class)
            if new_class.name == _lunch_class:
                print self.name, "has Lunch from", self.lfrom
                self.has_lunch = True
        self.classes = classes

        class_room_options = {}
        for cl in self.classes:
            room_options = []
            room_options = getRooms(cl, self)
            class_room_options[cl.name] = room_options
        self.class_room_options = class_room_options

        class_teacher_options = {}
        for cl in self.classes:
            t_options = []
            t_options = getTeachers(cl, self)
            class_teacher_options[cl.name] = t_options
        self.class_teacher_options = class_teacher_options

        self.gen_permutations()

    def show(self):
        print "----------------"
        print "Group", self.name, 'size', self.size, 'starts at', self.start
        for cl in self.classes:
            print "\t", cl
            room_options = self.class_room_options[cl.name]
            for ro in room_options:
                print "\t\t", ro

    def gen_permutations(self):
        size = len(self.classes)
        if size not in _permuts.keys():
            _permuts[size] = list(itertools.permutations(range(size)))
        self.num_scheds = len(_permuts[size])
        print "Group ", self.name, self.num_scheds, " options "

    def get_current_option_no(self):
        return self.current_option

    def gen_current_option(self):
        self.schedule = []
        size = len(self.classes)
        order = _permuts[size][self.current_option]
        print self.name, "option order", self.current_option, order

        t = self.start

        for k in order:
            cl = self.classes[k]
            if self.has_lunch and (cl.name == _lunch_class):
                if t < self.lfrom:
                    # Lunch starts not in lunch time window
                    return False
            item = Sched_option_item(cl.name, self.class_room_options[cl.name], \
                    self.class_teacher_options[cl.name], t, t.add(cl.duration))
            t = t.add(cl.duration)
            self.schedule.append(item)
        return True

    def gen_option_no(self, n):
        if n < self.num_scheds:
            self.current_option = n
            return self.gen_current_option()
        return False

    def set_first_option(self):
        n = 0
        while n < self.num_scheds:
            ret = self.gen_option_no(n)
            if ret:
                return True
            n += 1
        return False

    def gen_next_option(self):
        n = self.current_option
        while n < self.num_scheds:
            ret = self.gen_option_no(n)
            if ret:
                return True
            n += 1
        return False

    def gen_next_option_move_bad(self, pad_pos):
        # we want to make sure option in position 'bad_pos' has moved
        # to other position in new order
        size = len(self.classes)
        bad_order = _permuts[size][self.current_option]
        bad_item_no = bad_order[pad_pos]

        n = self.current_option + 1
        while n < self.num_scheds:
            order = _permuts[size][n]
            if order[pad_pos] != bad_item_no:
                ret = self.gen_option_no(n)
                if ret:
                    return True
            n += 1
        return False

    def show_option(self, whole=False):
        if whole:
            for item in self.schedule:
                print item.describe()
        else:
            for item in self.schedule:
                print item
    def opt_range(self):
        return self.num_scheds
    def next_teacher(self):
        for item in self.schedule:
            if item.next_teacher():
                break
            else:
                item.rewind_teacher()
    def next_room(self):
        for item in self.schedule:
            if item.next_room():
                break
            else:
                item.rewind_room()
#-

class BusyCalendar:
    cal = None
    temp = None
    ignore_list = None
    def __init__(self, ignore=[]):
        self.ignore_list = ignore
        self.cal = {}
        self.temp = {}

    def try_add(self, startT, endT, keylist):
        new = [startT.minutes(), endT.minutes()]
        for key in keylist:
            if key in self.ignore_list:
                continue
            if key in self.cal.keys():
                busy = self.cal[key]
                for item in busy:
                    start = item[0]
                    end = item[1]

                    if new[1] <= start or new[0] >= end:
                        return False

        for key in keylist:
            if key in self.ignore_list:
                continue
            if not key in self.temp.keys():
                self.temp[key] = []
            self.temp[key].append(new)
        return True

    def commit(self):
        for key in self.temp.keys():
            if not key in self.cal.keys():
                self.cal[key] = []
            for val in self.temp[key]:
                self.cal[key].append(val)
        self.temp = {}

    def drop(self):
        self.temp = {}

    def show(self):
        print "BusyCalendar"
        for key in self.cal.keys():
            print "\t", key
            busy = self.cal[key]
            for times in busy:
                print '\t{:s}-{:s}'.format(minutes2Time(times[0]), minutes2Time(times[1]))
            print "\n"
#}

class CommonSched:
    g_items = None #list of groups
    busy_cal = None #busy calendar both teachers and rooms
    n_options = 1
    def __init__(self):
        self.g_items = []
        self.busy_cal = BusyCalendar(["Lunch", "Canteen"])
    def add_group(self, grp):
        grp.set_first_option()
        self.g_items.append(grp)
        n_options = grp.opt_range()
        for item in grp.schedule:
            n_options *= item.nr
            n_options *= item.nt
        self.n_options *= n_options
        print 'Added {:s} with {:d} options, total {:d} options\n'.format(grp.name, \
                n_options, self.n_options)
    def adjust(self, debug=False, verbose=False):
        ret = False
        # (0) iterate over groups
        for grp in self.g_items:

            # (1) try group order options
            while True:

                if verbose:
                    print "Trying classes order, group", grp.name
                    for item in grp.schedule:
                        print item.show_selection()
                    print "\n"

                # (2) try add classes one-by-one
                item_pos = 0
                for item in grp.schedule:
                    # (3) Try if room can be added or is busy during this class time
                    item.rewind_room()
                    while True:
                        room = item.selected_room()
                        ret = self.busy_cal.try_add(item.tstart, item.tend, [room])
                        if ret:
                            #item.ok()
                            if debug: print "Room forund for group", grp.name, item, "selected", room
                            break

                        if debug: print "Room busy:", room
                        ret = item.next_room()
                        if not ret:
                            if debug: print "No room available for class", item
                            break
                    # (3) end if room can be added or is busy during thos class time
                    if not ret:
                        if debug: print "Completely failed adding class (no room):", grp.name, item
                        break

                    # (4) Try if techer can be added or is busy during this class time
                    item.rewind_teacher()
                    while True:
                        teacher = item.selected_teacher()
                        ret = self.busy_cal.try_add(item.tstart, item.tend, [teacher])
                        if ret:
                            item.ok()
                            if debug: print "Teacher found for group", grp.name, item, "selected", teacher
                            break

                        if debug: print "Teacher busy", teacher
                        ret = item.next_teacher()
                        if not ret:
                            if debug: print "No teacher available for class", item
                            break

                    # (4) end if techer can be added or is busy during thos class time
                    if not ret:
                        if debug: print "Completely failed adding class (no teacher):", grp.name, item
                        break
                    # will try adding next class in this schedule
                    item_pos += 1
                # (2) end try add classes one-by-one
                if not ret:
                    self.busy_cal.drop()
                    ret = grp.gen_next_option_move_bad(item_pos)
                    #ret = grp.gen_next_option()
                    if not ret:
                        if debug: print "No more classes order options for ", grp.name
                        break
                    if debug: print "Try next classes order options for ", grp.name
                else:
                    # sore busy calendar
                    self.busy_cal.commit()
                    print "Success! Gropup added ", grp.name
                    for item in grp.schedule:
                        print item.show_selection()
                    self.busy_cal.show()
                    break
            # (1) end group order options
            if not ret:
                print "Completely failed adding group:", grp.name
                break
        # (0) end iterate over groups
        return ret

    def show_last(self):
        for grp in self.g_items:
            print 'Group {:10s}'.format(grp.name)
            for item in grp.schedule:
                print item.show_selection()
            print "\n"
#}


##########################################

def name_exist_in(records, rn):
    for r in records:
        if r.name == rn:
            return r
    return None
#-

def Show_Roms():
    for r in _rooms:
        r.show()

def Show_Teachers():
    for r in _teachers:
        r.show()

def get_input(f):
    global _rooms, _teachers, roomlist, teacherlist, classlist, grouplist
    for line in f:
        line = line.strip()
        fields = line.split()

        if fields[0] == '#room':
            r = name_exist_in(_rooms, fields[1])
            if r:
                r.add(fields[2:])
            else:
                r = Attribute("room", fields[1:])
                _rooms.append(r)

        if fields[0] == '#teacher':
            r = name_exist_in(_teachers, fields[1])
            if r:
                r.add(fields[2:])
            else:
                r = Attribute("teacher", fields[1:])
                _teachers.append(r)


        if fields[0] == '#group':
            r = Group(fields)
            _groups.append(r)

        if fields[0] == '#rooms':
            roomlist = fields[1:]
            LU.print_list("Rooms:", roomlist, "\t")
        if fields[0] == '#teachers':
            teacherlist = fields[1:]
            LU.print_list("Teachers:", teacherlist, "\t")
        if fields[0] == '#classes':
            classlist = fields[1:]
            LU.print_list("Classes:", classlist, "\t")
        if fields[0] == '#groups':
            grouplist = fields[1:]
            LU.print_list("Groups:", grouplist, "\t")
#}


def main():
    get_input(sys.stdin)
    check_lists()
    Show_Roms()
    Show_Teachers()

    print "\n\n1 ---\n\n"

    CS = CommonSched()
    for grp in _groups:
        CS.add_group(grp)
    ret = CS.adjust(True, True)

    CS.show_last()

    print "\n\n2---\n\n"


main()
sys.exit()




