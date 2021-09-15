class GptGraph():
    def select_graph(self):
        # not implemented
        ...


class GptGraphS1Coreg(GptGraph):
    @staticmethod
    def generate(slc_pair):
        mtype = "single" if len(slc_pair.master.source) == 1 else "multiple"
        stype = "single" if len(slc_pair.slave.source) == 1 else "multiple"
        return f"graphs/coregister_subswath_{mtype}_master_{stype}_slave.xml"


class GptGraphS1Merge(GptGraph):
    @staticmethod
    def generate() -> str:
        return "graphs/merge_subswath.xml"


class GptGraphGeneral(GptGraph):
    # not implemented
    ...
