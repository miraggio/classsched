import time
import itertools
import sys
from copy import deepcopy
from operator import methodcaller
import local_utils as LU
import debug_log as log
import xls
import bisect

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

    def __init__(self, cl_name, tstart, tend):
        self.class_name = cl_name
        self.tstart = tstart
        self.tend = tend

    def __str__(self):
        return '{:10s} {:s}-{:s}'.format(self.class_name, self.tstart, self.tend)
#-


class Group:
    name = ''
    size = 0
    start = LU.Time(9, 0)
    classes = None
    num_scheds = 0
    schedule = None
    room_teacher = None
    sched_options = None
    NOT_SELECTED = -1
    sched_size = 0
    # state
    position_in_order = 0
    current_option = 0
    room_teacher_selected = None
    found_scheds = 0
    rt_selections = None

    def __init__(self, fields):
        self.name = fields[1]
        self.start = LU.str_time(fields[2])
        fields = fields[3:]
        self.room_teacher_selected = {}
        self.room_teacher = {}
        self.position_in_order = self.NOT_SELECTED
        self.current_option = self.NOT_SELECTED
        self.rt_selections = {}

        class_names = filter_from_dict(fields, G.classlist)

        classes = []
        for cl_name in class_names:
            cl = Class(cl_name)
            classes.append(cl)
            self.room_teacher_selected[cl.name] = self.NOT_SELECTED
            room_options = getRooms(cl, self)
            teacher_options = getTeachers(cl, self)
            x = [room_options, teacher_options]
            self.room_teacher[cl.name] = list(itertools.product(*x))
            Log.v('{:s} {:s} {:s}'.format(self.name, cl.name, self.room_teacher[cl.name]))
            self.rt_selections[cl.name] = {'r': room_options, 't': teacher_options, 'r_sel': self.NOT_SELECTED, 'r_sel': self.NOT_SELECTED}

        self.classes = classes

        self.sched_options = []
        permuts = list(itertools.permutations(range(len(self.classes))))
        num = len(permuts)
        pb = LU.ProgressBarExtended([num], 20)
        found = 0
        for n in range(num):
            order = permuts[n]
            sched = self.order_to_sched(order)
            if sched:
                self.sched_options.append(sched)
                found += 1
            pb.show('{:10s}'.format(self.name), [n], [n], found)

        self.num_scheds = len(self.sched_options)
        self.sched_size = len(self.sched_options[0])
        Log.v('{:s}: {:d} valid orders from {:d} total orders'.format(self.name, self.num_scheds, num))
        Log.v('{:s} from {:s} calsses: {:s}'.format(self.name, self.start, str([cl.name for cl in self.classes])))
        pb.done()

    def state(self):
        ret = []
        ret.append('-- Group {:10s} {:d}'.format(self.name, self.current_option))
        for cl in self.room_teacher:
            sel = self.room_teacher_selected[cl]
            r,t = self.room_teacher[cl][sel]
            ret.append('---- class {:10s} {:s} {:s} selection {:d}'.format(cl, r, t, sel))
        return ret

    def short_state(self):
        sel = []
        for cl in self.room_teacher_selected:
            sel.append(self.room_teacher_selected[cl])
        return 'option: {:d} sel {:s}'.format(self.current_option, ' '.join(str(sel)))

    def rewind_all_room_teachers(self):
        for cl in self.classes:
            self.room_teacher_selected[cl.name] = self.NOT_SELECTED
            self.rt_selections[cl.name]['r_sel'] = self.NOT_SELECTED
            self.rt_selections[cl.name]['t_sel'] = self.NOT_SELECTED

    def rewind_all(self):
        Log.v('{:s} rewind all'.format(self.name))
        self.position_in_order = self.NOT_SELECTED
        self.current_option = self.NOT_SELECTED
        self.rewind_all_room_teachers()
        self.found_scheds = 0

    def get_current_sched(self):
        if self.current_option in range(self.num_scheds):
            return self.sched_options[self.current_option]
        return None

    def show(self):
        print "----------------"
        print "Group", self.name, 'starts at', self.start
        for cl in self.classes:
            print "\t", cl

    def order_to_sched(self, order):
        schedule = []
        t = self.start

        for k in order:
            cl = self.classes[k]

            if t != self.start and cl.name != LUNCH_CLASS and schedule[-1].class_name != LUNCH_CLASS:
                t = t.add(G.break_min)
            time_valid = cl.start_from.err() or (cl.start_to.err() and t == cl.start_from) \
                        or (t >= cl.start_from and t <= cl.start_to)

            if not time_valid:
                Log.vvv('invalid order: {:s} cant start at {:s}'.format(cl.name, t))
                return None

            item = Sched_option_item(cl.name, t, t.add(cl.duration))

            t = t.add(cl.duration)
            schedule.append(item)

        return schedule

    def set_next_option_skip_bad(self, bad_pos):
        # we want to make sure option in position 'bad_pos' has moved
        # to other position in new order

        if bad_pos in range(self.sched_size):
            curr_sched = self.get_current_sched()
            bad_class = curr_sched[bad_pos]
            Log.v('{:s}: Change order: skip orders with calss {:s} at position {:d}'.\
                    format(self.name, bad_class.class_name, bad_pos))
            filter_bad_pos = True
        else:
            Log.v('{:s}: Change order'.format(self.name))
            filter_bad_pos = False

        n = self.NOT_SELECTED
        for n in range(self.current_option + 1, self.num_scheds):
            sched = self.sched_options[n]
            if (not filter_bad_pos) or (sched[bad_pos].class_name != bad_class.class_name):
                break
        if n in range(self.num_scheds):
            Log.v('{:s}: Found new order number {:d}'.format(self.name, n))
            self.rewind_all()
            self.current_option = n
            return True

        Log.v('{:s}: no more valid orders, stay on last No {:d})'.format(self.name, self.current_option))
        return False

    def get_num_orders(self):
        return self.num_scheds

    def commit_all_to_busy_cal(self, busy_cal):
            schedule = self.get_current_sched()
            for item in schedule:
                class_name = item.class_name
                curr_rt_sel = self.room_teacher_selected[class_name]
                room, teacher =  self.room_teacher[class_name][curr_rt_sel]
                busy_cal.commit(self.name, item.tstart, item.tend, [room, teacher])

    def get_room_teacher(self, class_name):
        curr_rt_sel = self.room_teacher_selected[class_name]
        room, teacher =  self.room_teacher[class_name][curr_rt_sel]
        return [room, teacher]

    def try_build_new_sched(cls, busy_cal, try_only, use_jocker=False):

        ret = cls.set_next_option_skip_bad(cls.NOT_SELECTED)
        if not ret:
            Log.d('try_build_new_sched: no more orders for group {:s}'.format(cls.name))
            return False
        Log.d('try_build_new_sched: Group {:s} sched no {:d} use Jocker {:s}'.\
                format(cls.name, cls.current_option, str(use_jocker)))

        if cls.name == 'K7-8A':
            busy_cal.show()

        while True:

            schedule = cls.get_current_sched()

            for item_pos in range(cls.sched_size):

                item = schedule[item_pos]
                class_name = item.class_name
                Log.v('{:s}: Try set room/teacher for {:s} [{:s}]'.format(cls.name, str(item), str(cls.room_teacher[class_name])))

                busy_rooms = []
                busy_teachers = []
                free_rooms = []
                ret = False
                rt_size = len(cls.room_teacher[class_name])

                for rt_sel in range(rt_size):
                    room, teacher = cls.room_teacher[class_name][rt_sel]

                    if room in busy_rooms or teacher in busy_teachers:
                        continue
                    if room not in free_rooms:
                        ret = busy_cal.applicable(item.tstart, item.tend, room)
                        if not ret:
                            busy_rooms.append(room)
                            continue
                        else:
                            free_rooms.append(room)

                    ret = busy_cal.applicable(item.tstart, item.tend, teacher)
                    if not ret:
                        Log.v('teacher {:s} busy'.format(teacher))
                        busy_teachers.append(room)
                        continue

                    Log.v('{:s}: new pair {:d} found: {:s}/{:s} for {:s}'.\
                            format(cls.name, rt_sel, room, teacher, str(item)))

                    break
                if ret:
                    cls.room_teacher_selected[class_name] = rt_sel
                    continue
                # failed to alloc resources for this class
                Log.d('{:s}: order {:d} failed to alloc resources for class {:s}'.\
                        format(cls.name, cls.current_option, str(item)))
                break

            if ret:
                # Done for all items in current order
                Log.v('{:s}: allocated resources for order {:d}'.format(cls.name, cls.current_option))
                # save state
                cls.position_in_order = item_pos
                if not try_only:
                    cls.commit_all_to_busy_cal(busy_cal)
                return True

            # failed to assign room/teacher for class, need to change order
            ret = cls.set_next_option_skip_bad(cls.NOT_SELECTED)
            if not ret:
                break
        Log.d('{:s}: no more orders'.format(cls.name))
        return False

    def try_change_current_sched(cls, busy_cal, use_jocker=False):
        schedule = cls.get_current_sched()
        Log.v('Group {:s} try make changes in current order {:d}'.format(cls.name, cls.current_option))
        for item_pos in range(cls.position_in_order, cls.sched_size):

            item = schedule[item_pos]
            class_name = item.class_name
            curr_rt_sel = cls.room_teacher_selected[class_name]
            sel_room, sel_teacher = cls.room_teacher[class_name][curr_rt_sel]
            Log.v('{:s}: Try to change sel {:d} room {:s}/teacher{:s} for {:s}'. \
                    format(cls.name, curr_rt_sel, sel_room, sel_teacher, str(item)))

            busy_cal.remove_allocation(cls.name, sel_room, item.tstart)
            busy_cal.remove_allocation(cls.name, sel_teacher, item.tstart)
            #busy_cal.show()
            Log.d('{:s}: class {:s} removed {:d} {:s}/{:s}'.format(cls.name, item.class_name,\
                    curr_rt_sel, sel_room, sel_teacher))
            busy_rooms = []
            busy_teachers = []
            free_rooms = []

            rt_size = len(cls.room_teacher[class_name])
            for rt_sel in range(curr_rt_sel + 1, rt_size):
                room, teacher = cls.room_teacher[class_name][rt_sel]

                if room in busy_rooms or teacher in busy_teachers:
                    continue
                if room not in free_rooms:
                    ret = busy_cal.applicable(item.tstart, item.tend, room)
                    if not ret:
                        Log.v('room {:s} busy'.format(room))
                        busy_rooms.append(room)
                        continue
                    else:
                        free_rooms.append(room)

                ret = busy_cal.applicable(item.tstart, item.tend, teacher)
                if not ret:
                    Log.v('teacher {:s} busy'.format(teacher))
                    busy_teachers.append(room)
                    continue

                Log.d('{:s}: class {:s} replaced {:d} {:s}/{:s} -> {:d} {:s}/{:s}'.\
                        format(cls.name, item.class_name, curr_rt_sel, sel_room,\
                        sel_teacher, rt_sel, room, teacher))
                busy_cal.commit(cls.name, item.tstart, item.tend, [room, teacher])
                cls.room_teacher_selected[class_name] = rt_sel
                cls.position_in_order = item_pos
                return True

            # Didn't manage to make changes in current class - add back to busy cal
            busy_cal.commit(cls.name, item.tstart, item.tend, [sel_room, sel_teacher])
            Log.d('{:s}: class {:s} placed back {:d} {:s}/{:s}'.format(cls.name, item.class_name,\
                    curr_rt_sel, sel_room, sel_teacher))
        # Didn't manage to make changes in this order
        Log.d('Group {:s} no more options in current order {:d}'.format(cls.name, cls.current_option))
        return False


    def has_current_state(cls):
        if cls.current_option == cls.NOT_SELECTED:
            Log.v('Group {:s}: is rewinded'.format(cls.name))
            return False

        schedule = cls.get_current_sched()
        item = schedule[cls.position_in_order]
        class_name = item.class_name
        curr_rt_sel = cls.room_teacher_selected[class_name]
        sel_room, sel_teacher = cls.room_teacher[class_name][curr_rt_sel]

        Log.v('Group {:s} state: order {:d} pos {:d} sel {:d} [selected {:s}/{:s}]'.\
                    format(cls.name, cls.current_option, cls.position_in_order, \
                    curr_rt_sel, sel_room, sel_teacher))
        return True

    def update_schedule(self, busy_cal, use_jocker=False):
        ret = self.has_current_state()
        if ret:
            ret = self.try_change_current_sched(busy_cal, use_jocker)
            if ret:
                self.found_scheds += 1
                return True
            # thid oredr is over - remove whole group from busy calendar
            busy_cal.remove_group(self.name)
        ret = self.try_build_new_sched(busy_cal, False, use_jocker)
        if ret:
            self.found_scheds += 1
        return ret
#}

class BusyCalendar:
    cal = None
    grp_list = None
    ignore_list = None
    def __init__(self, ignore=[]):
        self.ignore_list = ignore
        self.cal = {}
        self.grp_list = {}
        Log.v('BusyCalendar: ignore_list {:s}'.format(str(self.ignore_list)))

    def applicable(self, startT, endT, resource):
        if resource in self.ignore_list:
            return True

        if resource not in self.cal.keys():
            return True

        t1, t2 = [startT.minutes(), endT.minutes()]
        n = bisect.bisect(self.cal[resource], t1)
        if  n % 2:
            Log.v('calendar conflict {:s} {:s}-{:s} with {:s}-{:s}'.\
                    format(resource, startT, endT, LU.min2T(self.cal[resource][n - 1]), LU.min2T(self.cal[resource][n])))
            return False

        if (n == len(self.cal[resource])) or (self.cal[resource][n] >= t2):
            return True

        Log.v('calendar conflict {:s} {:s}-{:s} with {:s} at {:s}'.\
                            format(resource, startT, endT, LU.min2T(self.cal[resource][n]), LU.min2T(self.cal[resource][n + 1])))
        return False

    def commit(self, group, startT, endT, resources):
        t1, t2 = [startT.minutes(), endT.minutes()]

        for res in resources:
            if (not res) or (res in self.ignore_list):
                continue

            if res not in self.cal.keys():
                self.cal[res] = [t1, t2]
            else:
                n = bisect.bisect(self.cal[res], t1)
                self.cal[res].insert(n, t1)
                self.cal[res].insert(n + 1, t2)

            if res not in self.grp_list.keys():
                self.grp_list[res] = {}
            if group not in self.grp_list[res].keys():
                self.grp_list[res][group] = [[t1, t2]]
            else:
                self.grp_list[res][group].append([t1, t2])

            if group == 'K9-10A' and 'Tatjana' == res:
                Log.d('---{:s}/{:s} {:s} {:s} {:s}-{:s} added to BusyCalendar'.format(resources[1], resources[0], group, res, startT, endT))

            Log.v('{:s} {:s} {:s}-{:s} added to BusyCalendar'.format(group, res, startT, endT))
            #self.show_time_table(res)

    def remove_group(self, group):
        for res in self.grp_list.keys():
            if group in self.grp_list[res].keys():
                for t1, t2 in self.grp_list[res][group]:
                    n = bisect.bisect(self.cal[res], t1)
                    del self.cal[res][n - 1]
                    del self.cal[res][n - 1]

                del self.grp_list[res][group]
        Log.d('Grpoup {:s} removed from BusyCalendar'.format(group))

    def remove_allocation(self, group, res, tstart):
        if res not in self.grp_list.keys():
            return
        if group not in self.grp_list[res].keys():
            return

        tmp = []
        for t1, t2 in self.grp_list[res][group]:
            if t1 != tstart.minutes():
                tmp.append([t1, t2])
                continue
            n = bisect.bisect(self.cal[res], t1)
            del self.cal[res][n - 1]
            del self.cal[res][n - 1]
            Log.v('Grpoup {:s} {:s} {:s}-{:s} removed from BusyCalendar'.format(group, res, LU.min2T(t1), LU.min2T(t2)))
        self.grp_list[res][group] = tmp

    def show(self):
        Log.v("BusyCalendar")
        out = []
        for res in sorted(self.grp_list.keys()):
            for group in sorted(self.grp_list[res].keys()):
                for times in self.grp_list[res][group]:
                    Log.v('{:10s} {:10s} {:s}-{:s}'.format(res, group, \
                            LU.min2T(times[0]), LU.min2T(times[1])))

    def show_time_table(self):
        for resource in self.cal.keys():
            self.show_time_table_for_res(resource)

    def show_time_table_for_res(self, resource):
        for n in range(len(self.cal[resource]) / 2):
            Log.d(('{:s} {:s}-{:s}'.format(resource, \
                    LU.min2T(self.cal[resource][n*2]), LU.min2T(self.cal[resource][n*2+1]))))

    def state(self):
        ret = ['BusyCalendar']
        for res in sorted(self.grp_list.keys()):
            for group in sorted(self.grp_list[res].keys()):
                for times in self.grp_list[res][group]:
                    ret.append('{:10s} {:10s} {:s}-{:s}'.format(res, group, \
                            LU.min2T(times[0]), LU.min2T(times[1])))
        for resource in self.cal.keys():
            for n in range(len(self.cal[resource]) / 2):
                ret.append(('{:s} {:s}-{:s}'.format(resource, \
                        LU.min2T(self.cal[resource][n*2]), LU.min2T(self.cal[resource][n*2+1]))))
        return ret

    def ignored(self, res):
        return res in self.ignore_list

#}

class CommonSched:
    g_items = None #list of groups
    busy_cal = None #busy calendar both teachers and rooms
    longest_patterns = None

    def __init__(self):
        self.g_items = []
        self.busy_cal = BusyCalendar([LUNCH_TEACHER, LUNCH_ROOM, JOCKER, UNIVERSE])
        longest_patterns = {'group': 'n/a', 'depth': 0, 'paths': [], 'failures': []}

    def add_group(self, grp):
        self.g_items.append(grp)
        Log.v('Added {:s} with {:d} options'.format(grp.name, grp.get_num_orders()))

    def adjust(self, max_num=-1, sched_save_cb=None, use_jocker=False):

        groups_num = len(self.g_items)
        current_gno = 0
        with_jocker = False

        while True:

            grp = self.g_items[current_gno]

            if G.use_progress_bar:
                progress = [g.current_option for g in self.g_items]
                found = [g.found_scheds for g in self.g_items]
                G.pb.show('{:10}'.format(grp.name), progress, found, G.n_scheds_found)

            Log.d("Trying to add {:s} to the schedule".format(grp.name))
            ret = grp.update_schedule(self.busy_cal, with_jocker)

            if ret:
                Log.d("Succeeded to build schedule for {:s} {:s}".format(grp.name, grp.short_state()))
                if current_gno < groups_num - 1:
                    for gno in range(current_gno + 1, groups_num):
                        g = self.g_items[gno]
                        g.rewind_all()
                        rc = g.try_build_new_sched(self.busy_cal, True)
                        if not rc:
                            Log.w('{:s} not compartible with {:s}, Try to find more for same group'.format(grp.name, g.name))
                            break
                    if not rc:
                        Log.v("Try to find more for same group {:s}".format(grp.name))
                        continue

                    Log.v("Moving to the next group {:s}".format(self.g_items[current_gno + 1].name))
                    current_gno += 1
                    self.g_items[current_gno].rewind_all()
                    with_jocker = False
                    continue

                Log.v("Last group added, saving schedule (Jocker={:s})".format(str(with_jocker)))
                if sched_save_cb:
                    sched_save_cb(self.current_sched_as_list())
                    #if not self.verify_current():
                    #    self.dump()
                    #    return
                    if max_num > 0:
                        max_num -= 1
                        if max_num == 0:
                            return

                Log.v("Try to find more for same group {:s}".format(grp.name))
                continue
            else:
                Log.v("Failed to build schedule for {:s}".format(grp.name))

                if current_gno > 0:
                    Log.d("Moving to the previous group {:s}".format(self.g_items[current_gno - 1].name))
                    current_gno -= 1
                    continue

                Log.i("Seems nothing more to try, finishing")
                break
            # end if
        # end while

    def current_sched_as_list(cls):
        ret = []
        for grp in cls.g_items:
            schedule = grp.get_current_sched()
            for item in schedule:
                room, teacher = grp.get_room_teacher(item.class_name)
                s = '{:s} {:d} {:s} {:s} {:s} {:s} {:s}'.format(grp.name, grp.current_option, \
                        item.class_name, item.tstart, item.tend, room, teacher)
                ret.append(s)
        return ret

    def verify_current(cls):
        for grp in cls.g_items:
            schedule = grp.get_current_sched()
            for other in cls.g_items:
                if other.name == grp.name:
                    continue
                other_sched = other.get_current_sched()
                for it in schedule:
                    r, t = grp.get_room_teacher(it.class_name)
                    if cls.busy_cal.ignored(r) and cls.busy_cal.ignored(t):
                        continue
                    for ot in other_sched:
                        ro, to = other.get_room_teacher(ot.class_name)
                        if cls.busy_cal.ignored(ro) and cls.busy_cal.ignored(to):
                            continue
                        if LU.times_overlap(it.tstart, it.tend, ot.tstart, ot.tend):
                            if r == ro or t == to:
                                Log.e('Verification fail: {:s} {:s} {:s}-{:s} and {:s} {:s} {:s}-{:s}'.format\
                                        (grp.name, it.class_name, it.tstart, it.tend, \
                                         other.name, ot.class_name, ot.tstart, ot.tend))
                                return False
        return True

    def dump(cls):
        Log.e('---- State dump ----')
        for grp in cls.g_items:
            state = grp.state()
            for it in state:
                Log.e(it)
        cal_state = cls.busy_cal.state()
        for it in cal_state:
            Log.e(it)
        Log.e('---- dump end ----')

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
        group, unused, cl, start, stop, room, teacher = it.split()

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
    t1 = time.clock()
    CS.adjust(G.max_generates, save_scheduler, G.use_jocker)
    t2 = time.clock()
    sys.stderr.write('\nDone, {:d} generated in {:f} seconds\n'.format(G.n_scheds_found, t2 - t1))
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
G.max_generates = 100

Log.set_loglevel(log.WARNING)
Log.set_output("stdout")

main()
sys.exit()




