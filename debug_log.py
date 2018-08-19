import sys

ERROR = 0
WARNING = 1
DEBUG = 2
VERBOSE = 3

class Debug:
    level = 0
    def __init__(self, level):
        self.level = level
    def __pr(self, prefix, level, *args):
        if self.level >= level:
            sys.stderr.write(prefix + ": " + ' '.join(map(str,args)) + '\n')
    def e(cls, *args):
        cls.__pr("E", ERROR, args)
    def w(cls, *args):
        cls.__pr("W", WARNING, args)
    def d(cls, *args):
        cls.__pr("D", DEBUG, args)
    def v(cls, *args):
        cls.__pr("V", VERBOSE, args)
    def verbose(cls):
        return cls.level == VERBOSE

