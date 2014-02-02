class Logger:

    def __init__(self, verbose = False):
        self.verbose = verbose

    def String(self, message):
        if self.verbose:
            print message
