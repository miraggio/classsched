import sys

ERROR = 0
WARNING = 1
INFO = 2
DEBUG = 3
VERBOSE = 4

class Logger:
    level = 0
    out = None
    def __init__(self, level=INFO, out="stderr"):
        self.level = level
        self.out = out

    def __pr(self, prefix, level, *args):
        if self.level >= level:
            if self.out == "stdout":
                sys.stdout.write(prefix + ": " + ' '.join(map(str,args)) + '\n')
            else:
                sys.stderr.write(prefix + ": " + ' '.join(map(str,args)) + '\n')

    def set_loglevel(self, level):
	    self.level = level

    def set_output(self, out):
	    self.out = out

    def flush(self):
        if self.out == "stdout":
            sys.stdout.flush()
        else:
            sys.stderr.flush()

    def e(cls, *args):
        cls.__pr("E", ERROR, args)

    def w(cls, *args):
        cls.__pr("W", WARNING, args)

    def d(cls, *args):
        cls.__pr("D", DEBUG, args)

    def v(cls, *args):
        cls.__pr("V", VERBOSE, args)

    def i(cls, *args):
        cls.__pr("I", INFO, args)

    def verbose(cls):
        return cls.level == VERBOSE

