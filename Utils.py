class Logger:

    def __init__(self, verbose = False):
        self.verbose = verbose

    def Log(self, message):
        if self.verbose:
            print message
