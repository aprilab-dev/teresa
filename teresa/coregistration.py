import abc
import processor
from typing import Union
from . import stack


class Coregistration(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def coregister(self):
        pass


class Sentinel1Coregistration(Coregistration):
    # concrete creater
    def __init__(self, processor: processor.GptProcessor = processor.GptProcessor()):
        self._processor = processor  # interface
        self.graph = "None"

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
        """Implement the logic for coregistering by calling GPT. 

        Parameters
        ----------
        nsubswath : [type]
            [description]
        """
        self._processor.process(
            self.graph,
            dry_run=True, 
        )  # concrete implementation

    def _merge(self):
        self._processor.process(self.graph)

    def _finalize(self):
        pass # the logic for cleaning up

    def coregister(
        self,
        master:stack.Image,
        slave:stack.Image,
        dry_run:bool=False,
        **kwargs,
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

