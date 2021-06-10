import abc

class Processor(abc.ABC):

    @abc.abstractmethod
    def process(self):
        pass

class GptProcessor(Processor):

    def __init__(self):
        pass

    def process(self):
        pass

class DorisProcessor(Processor):
    def __init__(self):
        pass

    def process(self):
        pass