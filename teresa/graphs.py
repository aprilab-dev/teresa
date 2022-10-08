import os

from num2words import num2words

CUR_DIR = os.path.abspath(os.path.dirname(__file__))


class GptGraph:
    @staticmethod
    def radarcode_dem():
        """graph for radarcode dem using the interferogram module."""
        graph = "graphs/radarcode_dem.xml"
        return os.path.join(CUR_DIR, graph)


class GptGraphS1Coreg(GptGraph):
    @staticmethod
    def generate(mfile: tuple, sfile: tuple):
        mtype = "single" if len(mfile) == 1 else "multiple"
        stype = "single" if len(sfile) == 1 else "multiple"
        graph = f"graphs/coregister_subswath_{mtype}_master_{stype}_slave.xml"
        return os.path.join(CUR_DIR, graph)


class GptGraphS1Merge(GptGraph):
    @staticmethod
    def generate(subswaths: tuple):
        graph = f"graphs/merge_{num2words(len(subswaths))}_subswaths.xml"
        return os.path.join(CUR_DIR, graph)


class GptGraphGeneral(GptGraph):
    # not implemented
    ...
