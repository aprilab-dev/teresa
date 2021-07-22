class GptGraph():
    def select_graph(self):
        # not implemented
        ...


class GptGraphS1Coreg(GptGraph):
    @staticmethod
    def generate() -> str:
        return "graphs/coregister_subswath_multiple_slice.xml"


class GptGraphS1Merge(GptGraph):
    @staticmethod
    def generate() -> str:
        return "graphs/merge_subswath.xml"


class GptGraphGeneral(GptGraph):
    # not implemented
    ...
