import abc
import logging
import subprocess
from typing import Union

from .config import Config, LocalConfig

logger = logging.getLogger("sLogger")


class GptError(RuntimeError):
    pass  # categorize GPTERROR


class Processor(abc.ABC):
    @abc.abstractmethod
    def process(self):
        ...


class GptProcessor(Processor):
    def __init__(
        self,
        executable: Union[str, None] = Config.SNAP_GPT_EXECUTABLE,
        cache_size: Union[str, None] = LocalConfig.SNAP_GPT_CACHE_SIZE,
        cores: Union[int, None] = LocalConfig.SNAP_GPT_NTHREADS,
    ):
        self._executable = executable
        self._cache_size = cache_size
        self._cores = cores

    def process(self, graph: str, dry_run: bool = False, debug: bool = True, **kwargs):
        params = ["{} {} ".format(self._executable, graph)]
        params.append("-c {} -q {} ".format(self._cache_size, self._cores))
        if debug:
            params.append("-e ")
        params += ["-P{}='{}' ".format(name, value) for name, value in kwargs.items()]
        command = "".join(params)

        try:
            logger.info("GPT-DRY-RUN: %s", command)
            if dry_run:
                return
            subprocess.run(command, shell=True, check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as excep:
            raise GptError(
                "GPT command failed \n {} \n Stderr: {}".format(
                    command, excep.stderr.decode("utf-8")
                )
            ) from excep


class DorisProcessor(Processor):  # leave room for other sensors
    def __init__(self):
        pass

    def process(self):
        pass
