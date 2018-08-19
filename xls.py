import xlsxwriter
import local_utils as LU


#expexted "K5-6A Video 09:00-10:00 513 Mary"

class CellColors:
    tbl = None
    size = 0
    idx = 0
    def __init__(self):
        self.tbl = ["#00CCFF", "#CCFFFF", "#CCFFCC", "#FFFF99", \
            "#99CCFF", "#FF99CC", "#CC99FF", "#FFCC99", "#3366FF", \
            "#33CCCC", "#99CC00", "#FFCC00", "#FF9900"]
        self.size = len(self.tbl)
        self.rewind()
    def rewind(cls):
        cls.idx = -1
    def get_next(cls):
        if cls.idx < cls.size:
            cls.idx += 1
            return cls.tbl[cls.idx]
        else:
            print "Error, no more colors in table"

class XlsBook:
    def __init__(self, name, items):

        CORNER = [0, 0]
        TIME_STEP_MIN = 10
        colors = CellColors()

        workbook = xlsxwriter.Workbook(name)
        worksheet = workbook.add_worksheet()
        format_time = workbook.add_format({'bold': True, 'align': 'center'})
        format_group = workbook.add_format({'bold': True, 'align': 'center'})
        
        book = []
        rooms = []
        teachers = []
        groups = []
        classes = []

        start_min = 23 * 60 + 59
        end_min = 0

        for s in items:
            print "---", s.split()
            group, ok, cl, start, stop, room, teacher = s.split()

            start = LU.str_time(start)
            stop = LU.str_time(stop)

            book.append([group, cl, start, stop, room, teacher])

            if room not in rooms:
                rooms.append(room)
            if teacher not in teachers:
                teachers.append(teacher)
            if group not in groups:
                groups.append(group)
            if cl not in classes:
                classes.append(cl)

            if start.minutes() < start_min:
                start_min = start.minutes()
            if stop.minutes() > end_min:
                end_min = stop.minutes()
            
        
        groups.sort()
        rooms.sort()
        
        group_to_column = {}
        k = 1
        for g in groups:
            group_to_column[g] = CORNER[0] + k
            k += 1
        
        room_to_color = {}
        for r in rooms:
            room_to_color[r] = colors.get_next()
            
        row = CORNER[0] + 1
        col = CORNER[0]
        for t in range(start_min, end_min + 1, TIME_STEP_MIN):
            h = t / 60
            m = t % 60
            worksheet.write(row, col, '{:02d}:{:02d}'.format(h, m), format_time)
            row += 1

        row = CORNER[0]
        col = CORNER[0] + 1
        for g in groups:
            worksheet.write(row, col, g, format_group)
            col += 1

        workbook.close()

    