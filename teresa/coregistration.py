import abc
import processor
from . import stack


class Coregistration(abc.ABC):

    @abc.abstractmethod
    def coregister(self):
        ...

class Sentinel1Coregistration(Coregistration):
    # concrete creater
    def __init__(
        self,
        slc_pair: stack.SlcPair,
        output_path: str,
        polarization: str = "vv",
        dry_run: bool = False,
        coreg_processor: processor.GptProcessor = processor.GptProcessor(),
    ):
        self.graph = "None"
        self.slc_pair = slc_pair
        self.output_path = output_path
        self.polarization = polarization
        self.dry_run = dry_run
        self._processor = coreg_processor  # interface

    def _prepare(self):
        # 1. select graph based on input meta.
        self._select_graph("dummy_graph.xml")  # administritive stuff

    def _select_graph(self, graph: str):
        """Implement the logic for selecting the correct graph for processing.

        Parameters
        ----------
        graph : str
            [description]
        """
        self.graph = graph  # input meta and output graph(xml)

    def _coregister(self):
        # the lofic for swath coregistration.
        # The concrete implementation is actually in _subswath_coregister.
        for nsubswath in range(0, 3):
            self._coregister_subswath(nsubswath)

    def _coregister_subswath(self, nsubswath):
        """TODO: add description."""
        self._processor.process(
            self.graph,
            dry_run=True,
        )  # concrete implementation

        # graph = self._get_subswath_coregistration_graph(secondary, reference, esd=esd)

        # Execute the actual coregistration
        self._processor.process(
            self.graph,
            subswath=f"IW{nsubswath}",
            polorization=self.polarization.upper(),
            master_file=self.slc_pair.master.file,
            slave_file=self.slc_pair.slave.file,
            output_path=self.output_path,
            dry_run=self.dry_run,
        )

        if self.dry_run:
            # do something to show the dry run result
            pass

        return True

    def _merge(self):
        self._processor.process(self.graph)

    def _finalize(self):
        pass  # the logic for cleaning up

    def coregister(
        self,
        master: stack.Image,
        slave: stack.Image,
        dry_run: bool = False,
    ):
        self._prepare()
        self._coregister()
        self._merge()
        self._finalize()


class TSXCoregistration(Coregistration):
    def __init__(self):
        pass

    def coregistration(self):
        pass
