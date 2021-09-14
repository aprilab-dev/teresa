class GptGraph():
    def select_graph(self):
        # not implemented
        ...


class GptGraphS1Coreg(GptGraph):
    @staticmethod
    def generate(slc_pair):
        if len(slc_pair.master.source) > 1 and len(slc_pair.slave.source) > 1:
            return "graphs/coregister_subswath_multiple_slice.xml"
        if len(slc_pair.master.source) > 1 and len(slc_pair.slave.source) == 1:
            return "graphs/coregister_subswath_single_reference_slice.xml"
        if len(slc_pair.master.source) == 1 and len(slc_pair.slave.source) > 1:
            return "graphs/coregister_subswath_single_secondary_slice.xml"

        return "graphs/coregister_subswath_single_slice.xml"  # both are single slice


class GptGraphS1Merge(GptGraph):
    @staticmethod
    def generate() -> str:
        return "graphs/merge_subswath.xml"


class GptGraphGeneral(GptGraph):
    # not implemented
    ...
