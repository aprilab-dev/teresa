from __future__ import annotations

import os


class GptGraph():
    def generate(self):
        # not implemented
        ...


class GptGraphS1Coreg(GptGraph):
    @staticmethod
    def generate(slc_pair):
        mtype = "single" if len(slc_pair.master.source) == 1 else "multiple"
        stype = "single" if len(slc_pair.slave.source) == 1 else "multiple"
        graph = f"graphs/coregister_subswath_{mtype}_master_{stype}_slave.xml"
        return os.path.join(os.path.abspath(os.path.dirname(__file__)), graph)


class GptGraphS1Merge(GptGraph):
    @staticmethod
    def generate():
        nsubswaths = "three"   # only support merging all three subswath.
        graph = f"graphs/merge_{nsubswaths}_subswaths.xml"
        return os.path.join(os.path.abspath(os.path.dirname(__file__)), graph)


class GptGraphGeneral(GptGraph):
    # not implemented
    ...
