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
LUNCH_TEACHER = "LunchTeacher"
LUNCH_ROOM = "Canteen"
JOCKER = "Jocker"
UNIVERSE = "Universe"

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
        Log.d("---- {:s} {:s} ".format(self.attr_name, self.name))
        for gn in self.group_class.keys():
            Log.d("{:10s}: {:s}".format(gn, str(self.group_class[gn])))

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
    sel_teacher = -1
    sel_room = -1
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
    def nok(self):
        self.is_ok = " "
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
        self.sel_teacher = -1

    def next_teacher(self):
        if self.sel_teacher < (self.nt - 1):
            self.sel_teacher += 1
            return True
        return False

    def rewind_room(self):
        self.sel_room = -1

    def next_room(self):
        if self.sel_room < (self.nr - 1):
            self.sel_room += 1
            return True
        return False

    def selected_teacher(self):
        if self.sel_teacher in range(len(self.teacher_names)):
            return self.teacher_names[self.sel_teacher]
        return None

    def selected_room(self):
        if self.sel_room in range(len(self.room_names)):
            return self.room_names[self.sel_room]
        return None
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
    curr_order_valid = False

    def __init__(self, fields):
        self.name = fields[1]
        self.start = LU.str_time(fields[2])
        fields = fields[3:]

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
        print "Group", self.name, 'starts at', self.start
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
        self.curr_order_valid = True
        for k in order:
            cl = self.classes[k]
            if self.has_lunch and (cl.name == LUNCH_CLASS):
                if t < self.lunch_earlyest_time or t > self.lunch_latest_time:
                    Log.v('Lunch position invalid in order {:d}'.format(self.current_option))
                    self.curr_order_valid = False
            item = Sched_option_item(cl.name, self.class_room_options[cl.name], \
                    self.class_teacher_options[cl.name], t, t.add(cl.duration))
            t = t.add(cl.duration)
            self.schedule.append(item)
        return self.curr_order_valid

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
        Log.v('gen_next_option: Looking for next order for {:s}, current order {:s}'.\
                format(self.name, self.current_option))
        n = self.current_option + 1
        while n < self.num_scheds:
            ret = self.gen_option_no(n)
            if ret:
                Log.v('gen_next_option: found order {:s}'.\
                    format(self.current_option))
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

    def next_sched(cls, busy_cal):
        busy_cal.remove_group(cls.name)
        # (0)
        while True:
            Log.v('Group {:s}: trying to allocate resources for order {:d} valid {:d}'.\
                    format(cls.name, cls.current_option, cls.curr_order_valid))
            if not cls.curr_order_valid:
                Log.e('Current option is invalid - this should never happen!!!')
                return False

            # (1) try classes in current order
            for item_pos in range(len(cls.schedule)):
                item = cls.schedule[item_pos]
                room = item.selected_room()
                teacher = item.selected_teacher()

                Log.v('Try to chage room or teacher: {:s}'.format(str(item)))
                # (3)
                while True:
                    ret = item.next_room()
                    if not ret:
                        Log.v("No more rooms available for class", str(item))
                        break;

                    room = item.selected_room()
                    ret = busy_cal.applicable(item.tstart, item.tend, room, cls.name)
                    if ret:
                        Log.v('new room {:s} found for {:s}'.format(room, str(item)))
                        break
                    Log.v('room {:s} busy, try next'.format(room))
                # (3) end
                if ret and teacher:
                    break

                # (4) Try if teacher can be added or is busy during this class time
                while True:
                    ret = item.next_teacher()
                    if not ret:
                        Log.v("No more teachers available for class", str(item))
                        break

                    teacher = item.selected_teacher()
                    ret = busy_cal.applicable(item.tstart, item.tend, teacher, cls.name)
                    if ret:
                        Log.v('new teacher {:s} found for {:s}'.format(teacher, str(item)))
                        break
                    Log.v('teacher {:s} busy, try next'.format(teacher))
                # (4) end
                if not ret:
                    Log.v("Failed to select new room/teacher for {:s}, see busy calendar".format(str(item)))
                    busy_cal.show()
                    break
            # (1) end
            if ret:
                Log.v('{:s}: order {:d} added'.format(cls.name, cls.current_option))
                for item in cls.schedule:
                    busy_cal.commit(cls.name, item.tstart, item.tend, \
                            [item.selected_room(), item.selected_teacher()])
                busy_cal.show()
                return True

            Log.v('{:s}: Failed to add current order {:d}'.format(cls.name, cls.current_option))
            ret = cls.gen_next_option_move_bad(item_pos)
            if not ret:
                Log.v("No more order options for ", cls.name)
                return False
            Log.v('Try next classes order {:d} options for {:s}'.format(cls.current_option, cls.name))
            for item in cls.schedule:
                item.rewind_room()
                item.rewind_teacher()
        # (0) end
#}

class BusyCalendar:
    cal = None
    temp = None
    ignore_list = None
    def __init__(self, ignore=[]):
        self.ignore_list = ignore
        self.cal = {}
        self.temp = {}

    def applicable(self, startT, endT, key, group):
        if key in self.ignore_list:
            return True
        for grp in self.cal.keys():
            calendar = self.cal[grp]
            ret = self.__check_calendar(startT, endT, key, calendar)
            if not ret:
                return False
        return True

    def __check_calendar(self, startT, endT, key, calendar):
        start_min, end_min = [startT.minutes(), endT.minutes()]
        if key in calendar.keys():
            busy = calendar[key]
            for item in busy:
                start, end = item
                if not (end_min <= start or start_min >= end):
                    Log.v("Calendar conflict: {:s} {:s}-{:s} <> {:s}-{:s}".format \
                            (key, minutes2Time(start), minutes2Time(end), startT, endT))
                    return False
        return True

    def commit(self, group, startT, endT, keys):
        if group not in self.cal.keys():
            self.cal[group] = {}
        calendar = self.cal[group]

        start_min, end_min = [startT.minutes(), endT.minutes()]
        for key in keys:
            if key not in calendar.keys():
                calendar[key] = []
            calendar[key].append([start_min, end_min])

    def remove_group(cls, group):
        if group in cls.cal.keys():
            del cls.cal[group]

    def show(self):
        Log.d("BusyCalendar")
        for grp in self.cal.keys():
            calendar = self.cal[grp]
            for key in calendar.keys():
                busy = calendar[key]
                for times in busy:
                    Log.d(' - {:10s} {:10s} {:s}-{:s}'.format(grp, \
                            key, minutes2Time(times[0]), minutes2Time(times[1])))
#}

class CommonSched:
    g_items = None #list of groups
    busy_cal = None #busy calendar both teachers and rooms
    n_options = 1
    def __init__(self):
        self.g_items = []
        self.busy_cal = BusyCalendar([LUNCH_TEACHER, LUNCH_ROOM, JOCKER, UNIVERSE])

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

    def adjust(self, max_num=-1, sched_save_cb=None):
        groups_num = len(self.g_items)
        current_gno = 0

        while True:
            grp = self.g_items[current_gno]
            Log.v("Trying to add {:s} to the schedule".format(grp.name))
            ret = grp.next_sched(self.busy_cal)
            if ret:
                if current_gno < groups_num - 1:
                    Log.v("Moving to the next group")
                    current_gno += 1
                    self.g_items[current_gno].set_first_option()
                    continue

                Log.v("Last group added, saving schedule")
                if sched_save_cb:
                    sched_save_cb(self.current_sched_as_list())
                    if max_num > 0:
                        max_num -= 1
                        if max_num == 0:
                            return

                Log.v("Try find more for same group")
                continue
            else:
                if current_gno > 0:
                    Log.v("Moving to the previous group")
                    current_gno -= 1
                    continue

                Log.i("Seems nothing more to try, finishing")
                break
            # end if
        # end while

    def move_for_next_adjustment(cls):
        for grp in reversed(cls.g_items):
            while True:
                if grp.gen_next_option() == True:
                    return True
            Log.d("No more options for group", grp.name)
        Log.d("No more options for any of groups")
        return False

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

class TeacherStat:
    idle_max_pct = 0
    room_chg_max = 0
    classes_num_max = 0
    classes_num_min = 1000
    busy_min = 10000
    busy_max = 0
    n_teachers = 0
    n_classes = 0
    classes_time = 0
    jockers = 0
    universes = 0

    def __str__(cls):
        return 'idle {:f} rchg {:d} cnum {:d}-{:d} busy {:d}-{:d} t {:d} cl {:d} time {:d} J {:d} U {:d} rate {:.3f}'. \
        format(cls.idle_max_pct, cls.room_chg_max, cls.classes_num_min, cls.classes_num_max, \
        cls.busy_min, cls.busy_max, cls.n_teachers, cls.n_classes, cls.classes_time, \
        cls.jockers, cls.universes,
        cls.get_penalty_rate())

    def __pct(self, a, b):
        return a * 100 / b

    def get_penalty_rate(cls):
        pen = cls.idle_max_pct * 2 + cls.__pct(cls.room_chg_max, cls.n_classes) + \
                cls.__pct(cls.classes_num_max - cls.classes_num_min, cls.n_classes / cls.n_teachers) + \
                cls.__pct(cls.busy_max - cls.busy_min, cls.classes_time / cls.n_teachers) + \
                cls.jockers * 100 + cls.universes * 100
        return pen
#-

def stat_schedule(items):
    FIRST_MINUTE = 0
    LAST_MINUTE = 23 * 60 + 59
    teacher_stat = {}
    teachers = []
    num_classes = 0
    classes_time = 0
    jockers = 0
    universes = 0
    for it in items:
        group, cl, start, stop, room, teacher = it.split()

        if teacher == LUNCH_TEACHER:
            continue

        if teacher == JOCKER:
            jockers += 1
        if room == UNIVERSE:
            jockers += 1

        start = LU.str_time(start)
        stop = LU.str_time(stop)

        num_classes += 1
        if teacher not in teachers:
            teachers.append(teacher)

        if teacher not in teacher_stat.keys():
            # started, ended, busy, classes, room_changes, last_room, last_class
            teacher_stat[teacher] = {'start': LAST_MINUTE, 'end': FIRST_MINUTE, \
                    'busy': 0, 'classes': 0, 'rchg': 0, 'clchg': 0, \
                    'lr': 'n/a', 'lc': 'n/a'}
        busy = stop.minutes() - start.minutes()
        classes_time += busy
        ts = teacher_stat[teacher]
        if start.minutes() < ts['start']:
            ts['start'] = start.minutes()
        if stop.minutes() > ts['end']:
            ts['end'] = stop.minutes()
        ts['classes'] += 1
        ts['busy'] += busy
        if ts['lr'] != room:
            ts['lr'] = room
            ts['rchg'] += 1
        if ts['lc'] != cl:
            ts['lc'] = cl
            ts['clchg'] += 1
        teacher_stat[teacher] = ts

    ts = TeacherStat()
    ts.n_teachers = len(teachers)
    ts.n_classes = num_classes
    ts.classes_time = classes_time
    ts.jockers = jockers
    ts.universes = universes

    for teacher in teacher_stat.keys():
        t = teacher_stat[teacher]
        idle = (t['end'] - t['start'] - t['busy']) * 100 / t['busy']
        if idle > ts.idle_max_pct:
            ts.idle_max_pct = idle
        if t['rchg'] > ts.room_chg_max:
            ts.room_chg_max = t['rchg']
        if t['clchg'] > ts.classes_num_max:
            ts.classes_num_max = t['clchg']
        if t['clchg'] < ts.classes_num_min:
            ts.classes_num_min = t['clchg']
        if t['busy'] < ts.busy_min:
            ts.busy_min = t['busy']
        if t['busy'] > ts.busy_max:
            ts.busy_max = t['busy']
    return ts
#-

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
            Log.d("Rooms:", str(G.roomlist))

        if fields[0] == '#teachers':
            G.teacherlist = fields[1:]
            Log.d("Teachers:", str(G.teacherlist))

        if fields[0] == '#classes':
            G.classlist = fields[1:]
            Log.d("Classes:", str(G.classlist))

        if fields[0] == '#groups':
            G.grouplist = fields[1:]
            Log.d("Groups:", str(G.grouplist))
#}


def save_scheduler(items):

    G.n_scheds_found += 1
    ts = stat_schedule(items)
    pen = ts.get_penalty_rate()
    last = G.best_max - 1

    Log.i('New schedule, rate {:f} total {:d}'.format(pen, G.n_scheds_found))
    Log.flush()
    if len(G.best_scheds) < G.best_max:
        G.best_scheds.append([pen, items])
        if len(G.best_scheds) == G.best_max:
            G.best_scheds.sort(key=lambda x: x[0])
    else:
        if pen < G.best_scheds[last][0]:
            Log.v('rates {:f} - {:f}'.format(G.best_scheds[0][0], G.best_scheds[last][0]))
            Log.v(str(list(map(lambda x: x[0], G.best_scheds))))
            Log.v('replacing {:f} with {:f}'.format(G.best_scheds[last][0], pen))
            del G.best_scheds[last]
            G.best_scheds.append([pen, items])
            G.best_scheds.sort(key=lambda x: x[0])
            Log.v(str(list(map(lambda x: x[0], G.best_scheds))))
            Log.v("-------")

def main():

    get_input(sys.stdin)
    check_lists()
    Show_Roms()
    Show_Teachers()

    CS = CommonSched()
    for grp in G.groups:
        CS.add_group(grp)

    G.best_max = 10

    Log.i("Starting big work");
    CS.adjust(1000, save_scheduler)
    Log.i('Done, {:d} generated'.format(G.n_scheds_found))

    G.best_scheds.sort(key=lambda x: x[0])
    for x in G.best_scheds:
        Log.i('Schedule rate {:.3f}'.format(x[0]))
        items = x[1]
        for it in items:
            Log.i(str(it))
        G.work_book.export(items)

    G.save_workbook()

class Global:
    rooms = []
    teachers = []
    groups = []
    permuts = {}
    roomlist = []
    teacherlist = []
    classlist = []
    grouplist = []
    work_book = None
    n_scheds_found = 0
    scheds_to_save = None
    best_scheds = []
    best_collected = 0
    best_max = 10

    def __init__(self, wb_name="sched.xlsx"):
        self.work_book = xls.WorkBookWriter(wb_name)
        self.scheds_to_save = []

    def save_workbook(cls):
        cls.work_book.save()

G = Global("sched.xlsx")
Log = log.Debug(log.INFO, "stdout")

main()
sys.exit()




