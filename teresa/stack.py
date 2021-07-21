

class Image:
    def __init__(self, date: str, filepath:str):
        self.date = date
        self.file = filepath

class SlcPair:
    def __init__(self, master: Image, slave: Image):
        self.master = master
        self.slave = slave

