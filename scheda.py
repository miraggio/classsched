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
    start_from = LU.Time()
    start_to = LU.Time()
    duration = 0
    def __init__(self, name_duration):
        v = name_duration.split(":")
        self.name, self.duration,  = v[0], int(v[1])
        if len(v) > 3:
            self.start_from = LU.str_time(':'.join(v[2:4]))
        if len(v) > 5:
            self.start_to = LU.str_time(':'.join(v[4:6]))
        Log.v('New Class {:s}'.format(str(self)))

    def __str__(self):
        return '{:s}:{:d} start window {:s}-{:s}'.format(self.name, self.duration, self.start_from, self.start_to)
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
            ret.append(r.name)
    if len(ret):
        return ret
    for r in attrs:
        if r.matches(grp.name, cl.name):
            ret.append(r.name)
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
    def show_selection(self):
        if self.sel_teacher >= 0:
            t_str = self.teacher_names[self.sel_teacher]
        else:
            t_str = JOCKER
        if self.sel_room >= 0:
            r_str = self.room_names[self.sel_room]
        else:
            r_str = UNIVERSE
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
    classes = None
    class_room_options = None
    class_teacher_options = None
    num_scheds = 0
    current_option = 0
    schedule = None
    curr_order_valid = False
    first_valid_option_no = -1
    room_teacher = None

    def __init__(self, fields):
        self.name = fields[1]
        self.start = LU.str_time(fields[2])
        fields = fields[3:]

        class_names = filter_from_dict(fields, G.classlist)

        classes = []
        for cl in class_names:
            classes.append(Class(cl))
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


        self.room_teacher = {}
        x = [room_options, t_options]
        for cl in self.classes:
            self.room_teacher[cl.name] = list(itertools.product(*x))
            Log.vvv('{:s} {:s} {:s}'.format(self.name, cl.name, self.room_teacher[cl.name]))

        self.gen_permutations()
        self.set_first_option()

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

        t = self.start
        self.curr_order_valid = True
        for k in order:
            cl = self.classes[k]

            if t != self.start and cl.name != LUNCH_CLASS and self.schedule[-1].class_name != LUNCH_CLASS:
                t = t.add(G.break_min)
            time_valid = cl.start_from.err() or (cl.start_to.err() and t == cl.start_from) \
                        or (t >= cl.start_from and t <= cl.start_to)
            if not time_valid:
                Log.vvv('invalid order: {:s} cant start at {:s}'.format(cl.name, t))
                self.curr_order_valid = False
                break

            item = Sched_option_item(cl.name, self.class_room_options[cl.name], \
                    self.class_teacher_options[cl.name], t, t.add(cl.duration))

            t = t.add(cl.duration)
            self.schedule.append(item)

        if self.curr_order_valid:
            for item in self.schedule:
                item.rewind_room()
                item.rewind_teacher()

        Log.vvv('gen order for {:s}: [{:d}]={:s} valid {:d}'.format \
                (self.name, self.current_option, order, self.curr_order_valid))

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
                self.first_valid_option_no = n
                order = G.permuts[len(self.classes)][self.current_option]
                Log.v('First order for {:s}: [{:d}]={:s} valid {:d}'.format \
                        (self.name, self.current_option, order, self.curr_order_valid))
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

    def next_sched(cls, busy_cal, use_jocker=False):
        busy_cal.remove_group(cls.name)

        # (0)
        while True:
            Log.v('Group {:s}: trying to allocate resources for order {:d} valid {:d}, use Jocker {:s}'.\
                    format(cls.name, cls.current_option, cls.curr_order_valid, str(use_jocker)))
            if not cls.curr_order_valid:
                Log.e('Current option is invalid - this should never happen!!!')
                return False

            # (1) try classes in current order
            for item_pos in range(len(cls.schedule)):
                item = cls.schedule[item_pos]
                room = item.selected_room()
                teacher = item.selected_teacher()

                Log.v('Try to chage room or teacher: {:s} {:s}'.format(cls.name, str(item)))
                # (3)
                while True:
                    ret = item.next_room()
                    if not ret:
                        Log.v("No more rooms available for class", str(item))
                        room = None
                        break;

                    room = item.selected_room()
                    ret = busy_cal.applicable(item.tstart, item.tend, room)
                    if ret:
                        Log.v('new room {:s} found for {:s}'.format(room, str(item)))
                        break
                    Log.v('room {:s} busy, try next'.format(room))
                # (3) end
                if not ret:
                    if use_jocker:
                        item.rewind_room() # this wil set selection to -1
                        Log.v("Jocker room assigned to {:s}".format(str(item)))
                        ret = True
                    else:
                        break
                elif teacher:
                    Log.v('new room found and there is old teacher {:s}'.format(teacher))
                    break

                # (4) Try if teacher can be added or is busy during this class time
                while True:
                    ret = item.next_teacher()
                    if not ret:
                        Log.v("No more teachers available for class", str(item))
                        teacher = None
                        break

                    teacher = item.selected_teacher()
                    ret = busy_cal.applicable(item.tstart, item.tend, teacher)
                    if ret:
                        Log.v('new teacher {:s} found for {:s}'.format(teacher, str(item)))
                        break
                    Log.v('teacher {:s} busy, try next'.format(teacher))
                # (4) end
                if (not ret) and use_jocker:
                    item.rewind_teacher() # this wil set selection to -1
                    Log.v("Jocker teacher assigned to {:s}".format(str(item)))
                    ret = True
                if not ret:
                    Log.v("Failed to select new room/teacher for {:s}, see busy calendar".format(str(item)))
                    break
            # (1) end
            if ret:
                Log.v('{:s}: order {:d} added'.format(cls.name, cls.current_option))
                for item in cls.schedule:
                    busy_cal.commit(cls.name, item.tstart, item.tend, \
                            [item.selected_room(), item.selected_teacher()])
                return True

            Log.v("{:s}: failed to select new room/teacher for {:s} order no {:d}, see busy calendar".format \
                    (cls.name, str(item), cls.current_option))
            busy_cal.show()

            ret = cls.gen_next_option_move_bad(item_pos)
            if not ret:
                Log.v("No more order options for {:s}".format(cls.name))
                return False
            Log.v('Try next classes order {:d} options for {:s}'.format(cls.current_option, cls.name))
        # (0) end
#}

class BusyCalendar:
    cal = None
    grp_list = None
    ignore_list = None
    def __init__(self, ignore=[]):
        self.ignore_list = ignore
        self.cal = {}
        self.grp_list = {}
        Log.v('BusyCalendar ignore_list {:s}'.format(str(self.ignore_list)))

    def applicable(self, startT, endT, resource):
        if resource in self.ignore_list:
            return True
        if resource in self.cal.keys():
            start_min, end_min = [startT.minutes(), endT.minutes()]
            for t in range(start_min, end_min, G.time_step):
                if t in self.cal[resource]:
                    return False
        return True

    def show_time_table(self, resource):
        if resource in self.cal.keys():
            for t in self.cal[resource]:
                Log.v('{:s} {:s}'.format(resource, minutes2Time(t)))

    def commit(self, group, startT, endT, resources):
        start_min, end_min = [startT.minutes(), endT.minutes()]
        added = False
        for res in resources:
            if not res or res in self.ignore_list:
                continue

            if res not in self.cal.keys():
                self.cal[res] = []
            for t in range(start_min, end_min, G.time_step):
                if t not in self.cal[res]:
                     self.cal[res].append(t)

            added = True
            if group not in self.grp_list.keys():
                self.grp_list[group] = {}
            if res not in self.grp_list[group].keys():
                self.grp_list[group][res] = [[start_min, end_min]]
            else:
                self.grp_list[group][res].append([start_min, end_min])
        if added:
            self.__rebuild()

    def remove_group(self, group):
        if group in self.grp_list.keys():
            Log.v('remove_group {:s}'.format(group))
            del self.grp_list[group]
            self.__rebuild()

    def __rebuild(self):
        self.cal = {}
        for group in self.grp_list.keys():
            for res in self.grp_list[group].keys():
                if res not in self.cal.keys():
                    self.cal[res]=[]
                for times in self.grp_list[group][res]:
                    start_min, end_min = times
                    for t in range(start_min, end_min, G.time_step):
                        self.cal[res].append(t)

    def show(self):
        Log.d("BusyCalendar")
        for group in self.grp_list.keys():
            for res in self.grp_list[group].keys():
                for times in self.grp_list[group][res]:
                    Log.d(' - {:10s} {:10s} {:s}-{:s}'.format(group, \
                            res, minutes2Time(times[0]), minutes2Time(times[1])))
#}

class CommonSched:
    g_items = None #list of groups
    busy_cal = None #busy calendar both teachers and rooms
    n_options = 1
    longest_patterns = None

    def __init__(self):
        self.g_items = []
        self.busy_cal = BusyCalendar([LUNCH_TEACHER, LUNCH_ROOM, JOCKER, UNIVERSE])
        longest_patterns = {'group': 'n/a', 'depth': 0, 'paths': [], 'failures': []}

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

    def adjust(self, max_num=-1, sched_save_cb=None, use_jocker=False):
        groups_num = len(self.g_items)
        current_gno = 0
        self.g_items[current_gno].set_first_option()
        with_jocker = False

        while True:

            grp = self.g_items[current_gno]

            if G.use_progress_bar:
                progress = [g.current_option for g in self.g_items]
                G.pb.show('{:10}'.format(grp.name), progress, G.n_scheds_found)

            Log.v("Trying to add {:s} to the schedule".format(grp.name))
            ret = grp.next_sched(self.busy_cal, with_jocker)

            if ret:
                if current_gno < groups_num - 1:
                    Log.v("Moving to the next group")
                    current_gno += 1
                    self.g_items[current_gno].set_first_option()
                    with_jocker = False
                    continue

                Log.v("Last group added, saving schedule (Jocker={:s})".format(str(with_jocker)))
                if sched_save_cb:
                    sched_save_cb(self.current_sched_as_list())
                    if max_num > 0:
                        max_num -= 1
                        if max_num == 0:
                            return

                if with_jocker:
                    if current_gno > 0:
                        Log.v("Moving to the previous group")
                        current_gno -= 1
                        with_jocker = False
                        continue
                    else:
                        return

                Log.v("Try to find more for same group")
                continue
            else:
                if with_jocker:
                    Log.v("Failed to build schedule with Jocker for {:s}, STOP here".format(grp.name))
                    return

                Log.v("Failed to build schedule for {:s}".format(grp.name))
                if use_jocker:
                    with_jocker = True
                    Log.v("Try to build schedule with Jocker for {:s}".format(grp.name))
                    self.g_items[current_gno].set_first_option() ## ???
                    continue

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

class SchedStat:
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

    ts = SchedStat()
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

        if len(fields) < 1:
            continue

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

        if fields[0] == '#break':
            G.break_min = int(fields[1])

        if fields[0] == '#use_jocker':
            G.use_jocker = True

#}


def save_scheduler(items):

    G.n_scheds_found += 1
    ts = stat_schedule(items)
    pen = ts.get_penalty_rate()
    last = G.best_max - 1

    Log.d('New schedule, rate {:f} total {:d}'.format(pen, G.n_scheds_found))
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
            Log.flush()

def main():

    get_input(sys.stdin)
    check_lists()
    Show_Roms()
    Show_Teachers()

    CS = CommonSched()
    for grp in G.groups:
        CS.add_group(grp)

    if G.use_progress_bar:
        totals = [grp.num_scheds for grp in CS.g_items]
        G.pb = LU.ProgressBarExtended(totals, 6)


    Log.i("Starting big work")
    Log.flush()
    CS.adjust(G.max_generates, save_scheduler, G.use_jocker)
    Log.i('Done, {:d} generated'.format(G.n_scheds_found))
    G.pb.done()

    if G.n_scheds_found:
        work_book = xls.WorkBookWriter(G.out_file_name, 5)
        G.best_scheds.sort(key=lambda x: x[0])
        for x in G.best_scheds:
            Log.i('Schedule rate {:.3f}'.format(x[0]))
            items = x[1]
            for it in items:
                Log.i(str(it))
            work_book.export(items)

        work_book.save()

class Global:
    rooms = []
    teachers = []
    groups = []
    permuts = {}
    roomlist = []
    teacherlist = []
    classlist = []
    grouplist = []
    n_scheds_found = 0
    scheds_to_save = []
    best_scheds = []
    best_collected = 0
    best_max = 10
    max_generates = 100
    use_progress_bar = False
    pb = None
    use_jocker = False
    out_file_name = "sched.xlsx"
    break_min = False
    time_step = 5

G = Global()
Log = log.Logger()

G.use_progress_bar = True
G.best_max = 10
G.max_generates = 1000
Log.set_loglevel(log.VERBOSE)
Log.set_output("stdout")

main()
sys.exit()




