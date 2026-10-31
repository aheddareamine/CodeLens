import fire 

class Calc:
    def __init__(self, verbose):
        self.verbose = verbose

    def add(self, x, y):
        if self.verbose:
            print(f"adding {x} and {y}")
        return x + y

fire.Fire(Calc)