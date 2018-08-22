import xlsxwriter
import local_utils as LU

class CellColors:
    tbl = None
    size = 0
    idx = 0
    special_colors = {"Universe": "white", "Jocker": "white"}
    def __init__(self):
        self.tbl = ["#00CCFF", "#CCFFFF", "#CCFFCC", "#FFFF99", \
            "#99CCFF", "#FF99CC", "#CC99FF", "#FFCC99", "#3366FF", \
            "#33CCCC", "#99CC00", "#FFCC00", "#FF9900"]
        self.size = len(self.tbl)
        self.rewind()
    def rewind(cls):
        cls.idx = -1
    def get_next(cls, name):
        if name in cls.special_colors.keys():
            return cls.special_colors[name]
        if cls.idx < cls.size:
            cls.idx += 1
            return cls.tbl[cls.idx]
        else:
            print "Error, no more colors in table"


class WorkBookWriter:
    format_time = None
    format_group = None
    format_content = None
    name = None
    workbook = None
    worksheet = None
    first_row = 0
    time_step_min = 10
    tcolors = None
    rcolors = None
    FIRST_COLUMN = 0
    teacher_to_format = None
    room_to_format = None

    def __init__(self, name, time_step_min=10):
        self.teacher_to_format = {}
        self.room_to_format = {}
        self.time_step_min = time_step_min
        self.workbook = xlsxwriter.Workbook(name)
        self.worksheet = self.workbook.add_worksheet()
        self.tcolors = CellColors()
        self.rcolors = CellColors()
        self.format_time = self.workbook.add_format({'bold': True, 'align': 'center'})
        self.format_group = self.workbook.add_format({'bold': True, 'align': 'center'})

    def __get_region_columns(self, time_start, time_step, start, end):
        start_row = (start.minutes() - time_start) / time_step
        stop_row = (end.minutes() - time_start) / time_step - 1
        return [self.first_row + 1 + start_row, self.first_row + 1 + stop_row]

    #expexted item "K5-6A Video 09:00 10:00 513 Mary"
    def export(cls, items):
        book = []
        rooms = []
        teachers = {}
        groups = []
        classes = []

        start_min = 23 * 60 + 59
        end_min = 0

        for s in items:
            group, cl, start, stop, room, teacher = s.split()
            start = LU.str_time(start)
            stop = LU.str_time(stop)

            book.append([group, cl, start, stop, room, teacher])

            if room not in rooms:
                rooms.append(room)
            if group not in groups:
                groups.append(group)
            if cl not in classes:
                classes.append(cl)

            if teacher not in cls.teacher_to_format.keys():
                color = cls.tcolors.get_next(teacher)
                cls.teacher_to_format[teacher] = cls.workbook.add_format( \
                        {'bg_color': color, 'align': 'center', 'valign': 'vcenter', 'border': 1})

            if room not in cls.room_to_format.keys():
                color = cls.rcolors.get_next(room)
                cls.room_to_format[room] = cls.workbook.add_format( \
                        {'bg_color': color, 'align': 'center', 'valign': 'vcenter', 'border': 1})

            minutes = stop.minutes() - start.minutes()

            if teacher not in teachers.keys():
                teachers[teacher] = minutes
            else:
                teachers[teacher] += minutes

            if start.minutes() < start_min:
                start_min = start.minutes()
            if stop.minutes() > end_min:
                end_min = stop.minutes()

        groups.sort()
        rooms.sort()

        group_to_column = {}
        for k in range(len(groups)):
            group_to_column[groups[k]] = cls.FIRST_COLUMN + k + 1

        row = cls.first_row + 1
        col = cls.FIRST_COLUMN
        for t in range(start_min, end_min + 1, cls.time_step_min):
            h = t / 60
            m = t % 60
            cls.worksheet.write(row, col, '{:02d}:{:02d}'.format(h, m), cls.format_time)
            row += 1

        last_row = row
        shift = len(groups) + 4

        row = cls.first_row
        col = cls.FIRST_COLUMN + 1
        for g in groups:
            cls.worksheet.write(row, col, g, cls.format_group)
            cls.worksheet.write(row, col + shift, g, cls.format_group)
            col += 1

        last_col = col

        for rec in book:
            group, cl, start, stop, room, teacher = rec
            [r1, r2] = cls.__get_region_columns(start_min, cls.time_step_min, start, stop)
            col = group_to_column[group]
            content = '{:s}\n{:s}\n{:s}'.format(cl, teacher, room)
            if r1 == r2:
                cls.worksheet.write(r1, col, content, cls.teacher_to_format[teacher])
                cls.worksheet.write(r1, col + shift, content, cls.room_to_format[room])
            else:
                cls.worksheet.merge_range(r1, col, r2, col, content, cls.teacher_to_format[teacher])
                cls.worksheet.merge_range(r1, col + shift, r2, col + shift, content, cls.room_to_format[room])
            if r2 > last_row:
                last_row = r2

        col = last_col + 1
        row = cls.first_row + 1
        for t in teachers.keys():
            color = cls.teacher_to_format[t]
            cls.worksheet.write(row, col, t, cls.teacher_to_format[t])
            cls.worksheet.write(row, col + 1, teachers[t], cls.teacher_to_format[t])
            row += 1

        if row > last_row:
            cls.first_row = row + 3
        else:
            cls.first_row = last_row + 3

    def save(cls):
        cls.workbook.close()


