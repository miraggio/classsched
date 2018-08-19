import time
import itertools
import sys
from copy import deepcopy
from operator import methodcaller
import local_utils as LU
import debug_log as log
import xls

# constants

LUNCH_CLASS = "Lunch"
LUNCH_TIME_FRAME = "LunchWindow"

def is_room(x):
    return x in G.roomlist
def is_teacher(x):
    return x in G.teacherlist
def is_class(x):
    return x in G.classlist
def is_group(x):
    return x in G.grouplist

def check_lists():
    for x in G.roomlist:
        if is_teacher(x) or is_class(x) or is_group(x):
            Log.e("Duplicate entry: ", x)
            return False
    for x in G.teacherlist:
        if is_room(x) or is_class(x) or is_group(x):
            Log.e("Duplicate entry: ", x)
            return False
    for x in G.classlist:
        if is_teacher(x) or is_room(x) or is_group(x):
            Log.e("Duplicate entry: ", x)
            return False
    for x in G.grouplist:
        if is_teacher(x) or is_class(x) or is_room(x):
            Log.e("Duplicate entry: ", x)
            return False
    return True
#-

def first_subf(field):
    x = field.split(":")
    return x[0]


def filter_from_dict(values, dict):
    ret = []
    for x in values:
        v = first_subf(x)
        if v in dict:
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
        class_names = filter_from_dict(fields, G.classlist)
        group_names = filter_from_dict(fields, G.grouplist)
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
        v = name_duration.split(":")
        self.name, duration = v[0], v[1]
        self.duration = int(duration)
        #print self
    def __str__(self):
        return '{:s}:{:d}'.format(self.name, self.duration)
#-

def minutes2Time(mins):
    return LU.Time(mins / 60, mins % 60)

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
    return getAttributes(G.rooms, cl, grp)
#-

def getTeachers(cl, grp):
    return getAttributes(G.teachers, cl, grp)
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
        return '{:s} {:10s} {:s} {:s} {:s} {:s}'.format(self.is_ok, \
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
    start = LU.Time(9, 0)
    lunch_earlyest_time = None
    lunch_latest_time = None
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
        self.start = LU.str_time(fields[3])
        fields = fields[4:]

        class_names = filter_from_dict(fields, G.classlist)

        classes = []
        for cl in class_names:
            classes.append(Class(cl))
        self.classes = classes

        self.__setup_lunch(fields)

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

    def __setup_lunch(cls, fields):
        for x in fields:
            if first_subf(x) == LUNCH_CLASS:
                v = x.split(":")

                cls.lunch_earlyest_time, cls.lunch_latest_time = \
                        [LU.Time(int(v[2]),int(v[3])), LU.Time(int(v[4]),int(v[5]))]
                cls.has_lunch = True
                Log.d('{:s} has {:d} minutes lunch wich starts in a window {:s}-{:s}'.format(\
                        cls.name, int(v[1]), cls.lunch_earlyest_time, cls.lunch_latest_time))
                break

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
        if size not in G.permuts.keys():
            G.permuts[size] = list(itertools.permutations(range(size)))
        self.num_scheds = len(G.permuts[size])
        Log.d("Group ", self.name, self.num_scheds, " options ")

    def get_current_option_no(self):
        return self.current_option

    def gen_current_option(self):
        self.schedule = []
        size = len(self.classes)
        order = G.permuts[size][self.current_option]
        Log.v(self.name, "option order", self.current_option, order)

        t = self.start

        for k in order:
            cl = self.classes[k]
            if self.has_lunch and (cl.name == LUNCH_CLASS):
                if t < self.lunch_earlyest_time or t > self.lunch_latest_time:
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
        bad_order = G.permuts[size][self.current_option]
        bad_item_no = bad_order[pad_pos]

        n = self.current_option + 1
        while n < self.num_scheds:
            order = G.permuts[size][n]
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
        Log.d('Added {:s} with {:d} options, total {:d} options\n'.format(grp.name, \
                n_options, self.n_options))
    def adjust(self, debug=False, verbose=False):
        ret = False
        # (0) iterate over groups
        for grp in self.g_items:

            # (1) try group order options
            while True:

                if Log.verbose():
                    sys.stderr.write("Trying classes order, group {:s}\n".format(grp.name))
                    for item in grp.schedule:
                        sys.stderr.write(item.show_selection() + '\n')
                    sys.stderr.write("\n")

                # (2) try add classes one-by-one
                item_pos = 0
                for item in grp.schedule:
                    # (3) Try if room can be added or is busy during this class time
                    item.rewind_room()
                    while True:
                        room = item.selected_room()
                        ret = self.busy_cal.try_add(item.tstart, item.tend, [room])
                        if ret:
                            Log.v("Room forund for group", grp.name, str(item), "selected", str(room))
                            break

                        Log.v("Room busy:", str(room))
                        ret = item.next_room()
                        if not ret:
                            Log.d("No room available for class", str(item))
                            break
                    # (3) end if room can be added or is busy during thos class time
                    if not ret:
                        Log.v("Completely failed adding class (no room):", grp.name, str(item))
                        break

                    # (4) Try if techer can be added or is busy during this class time
                    item.rewind_teacher()
                    while True:
                        teacher = item.selected_teacher()
                        ret = self.busy_cal.try_add(item.tstart, item.tend, [teacher])
                        if ret:
                            Log.v("Teacher found for group", grp.name, str(item), "selected", str(teacher))
                            break

                        Log.v("Teacher busy", str(teacher))
                        ret = item.next_teacher()
                        if not ret:
                            Log.v("No teacher available for class", str(item))
                            break

                    # (4) end if techer can be added or is busy during thos class time
                    if not ret:
                        Log.v("Completely failed adding class (no teacher):", grp.name, str(item))
                        break
                    item.ok()
                    # will try adding next class in this schedule
                    item_pos += 1
                # (2) end try add classes one-by-one
                if not ret:
                    self.busy_cal.drop()
                    ret = grp.gen_next_option_move_bad(item_pos)
                    #ret = grp.gen_next_option()
                    if not ret:
                        Log.v("No more classes order options for ", grp.name)
                        break
                    Log.v("Try next classes order options for ", grp.name)
                else:
                    # store busy calendar
                    self.busy_cal.commit()
                    Log.d("Success! Gropup added ", grp.name)
                    if Log.verbose():
                        for item in grp.schedule:
                            print item.show_selection()
                        self.busy_cal.show()
                    break
            # (1) end group order options
            if not ret:
                Log.v("Completely failed adding group:", grp.name)
                break
        # (0) end iterate over groups
        return ret

    def show_last(self):
        for grp in self.g_items:
            print 'Group {:10s}'.format(grp.name)
            for item in grp.schedule:
                print item.show_selection()
            print "\n"

    def current_sched_as_list(cls):
        ret = []
        for grp in cls.g_items:
            for item in grp.schedule:
                s = ' '.join([grp.name, item.show_selection()])
                ret.append(s)
        return ret

#}


##########################################

def name_exist_in(records, rn):
    for r in records:
        if r.name == rn:
            return r
    return None
#-

def Show_Roms():
    for r in G.rooms:
        r.show()

def Show_Teachers():
    for r in G.teachers:
        r.show()

def get_input(f):
    for line in f:
        line = line.strip()
        fields = line.split()

        if fields[0] == '#room':
            r = name_exist_in(G.rooms, fields[1])
            if r:
                r.add(fields[2:])
            else:
                r = Attribute("room", fields[1:])
                G.rooms.append(r)

        if fields[0] == '#teacher':
            r = name_exist_in(G.teachers, fields[1])
            if r:
                r.add(fields[2:])
            else:
                r = Attribute("teacher", fields[1:])
                G.teachers.append(r)


        if fields[0] == '#group':
            r = Group(fields)
            G.groups.append(r)

        if fields[0] == '#rooms':
            G.roomlist = fields[1:]
            LU.print_list("Rooms:", G.roomlist, "\t")
        if fields[0] == '#teachers':
            G.teacherlist = fields[1:]
            LU.print_list("Teachers:", G.teacherlist, "\t")
        if fields[0] == '#classes':
            G.classlist = fields[1:]
            LU.print_list("Classes:", G.classlist, "\t")
        if fields[0] == '#groups':
            G.grouplist = fields[1:]
            LU.print_list("Groups:", G.grouplist, "\t")
#}


class Global:
    rooms = []
    teachers = []
    groups = []
    permuts = {}
    roomlist = []
    teacherlist = []
    classlist = []
    grouplist = []

G = Global()

Log = log.Debug(log.WARNING)

def main():

    get_input(sys.stdin)
    check_lists()
    Show_Roms()
    Show_Teachers()

    print "\n\n1 ---\n\n"

    CS = CommonSched()
    for grp in G.groups:
        CS.add_group(grp)
    ret = CS.adjust()

    CS.show_last()

    sch = CS.current_sched_as_list()
    x = xls.XlsBook("sched.xlsx", sch)



main()
sys.exit()




