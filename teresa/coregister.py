""" Creator
"""

import abc
import processor

class Coregister(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def coregistration(self):
        pass


class Sentinel1Coregister(Coregister):
    # concrete creater
    def __init__(self, processor: processor.Processor = processor.GptProcessor()):
        self._processor = processor  # interface

    def _prepare(self):
        pass  # administritive stuff

    def _coregister(self):
        # the lofic for swath coregistration. 
        # The concrete implementation is actually in _subswath_coregister. 
        for nsubswath in range(0, 3):
            self._subswath_coregister(nsubswath)

    def _subswath_coregister(self, nsubswath):
        # the logic for subswath coregistration
        self._processor.process()  # concrete implementation

    def _merge(self):
        self._processor.process()

    def _finalize(self):
        pass # the logic for cleaning up

    def coregistration(
        self,
        master,
        slave,
        aoi,
        dem,
        polarization,
        dry_run:bool=False,
        **kwargs,
    ):
        self._prepare()
        self._coregister()
        self._merge()
        self._finalize()


class TSXCoregister(Coregister):
    def __init__(self):
        pass

    def coregistration(self):
        pass

