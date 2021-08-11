

class Image:
    def __init__(self, date: str, folder:str):
        self.date = date
        self.folder = folder

class SlcPair:
    def __init__(self, master: Image, slave: Image):
        self.master = master
        self.slave = slave

