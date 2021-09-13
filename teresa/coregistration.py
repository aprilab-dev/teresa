import abc
import processor
import graphs


class Coregistration(abc.ABC):

    @abc.abstractmethod
    def coregister(self):
        ...

class Sentinel1Coregistration(Coregistration):
    # concrete creater
    def __init__(
        self,
        slc_pair,  # TODO: add typehint
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
        # administritive stuff
        ...

    def _coregister(self):
        # the lofic for swath coregistration.
        # The concrete implementation is actually in _subswath_coregister.
        for nsubswath in range(0, 3):
            self._coregister_subswath(nsubswath)

    def _coregister_subswath(self, nsubswath):
        """TODO: add description."""

        graph = graphs.GptGraphS1Coreg.generate()

        # Execute the actual coregistration
        self._processor.process(
            graph,
            subswath=f"IW{nsubswath}",
            polorization=self.polarization.upper(),
            master_file=self.slc_pair.master.folder,
            slave_file=self.slc_pair.slave.folder,
            output_path=self.output_path,
            dry_run=self.dry_run,
        )

        if self.dry_run:
            # do something
            pass

        return True

    def _merge(self):
        # self._processor.process(self.graph)
        pass

    def _finalize(self):
        pass  # the logic for cleaning up

    def coregister(self):
        self._prepare()
        self._coregister()
        self._merge()
        self._finalize()


class TSXCoregistration(Coregistration):
    def __init__(self):
        pass

    def coregistration(self):
        pass
