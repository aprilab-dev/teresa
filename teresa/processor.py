import abc
import logging
import subprocess
from config import Config, LocalConfig
from typing import Union


class GptError(RuntimeError):
    pass  # categorize GPTERROR


class Processor(abc.ABC):
    @abc.abstractmethod
    def process(self):
        pass


class GptProcessor(Processor):
    def __init__(
        self,
        executable: str = Config.SNAP_GPT_EXECUTABLE,
        cache_size: str = LocalConfig.SNAP_GPT_CACHE_SIZE,
        cores: int = LocalConfig.SNAP_GPT_NTHREADS,
    ):
        self._executable = executable
        self._cache_size = cache_size
        self._cores = cores

    def process(self, graph: str, dry_run: bool = False, debug: bool = False, **kwargs):
        params = ["{} {} ".format(self._executable, graph)]
        params += ["-P{}='{}' ".format(name, value) for name, value in kwargs.items()]
        params.append("-c {} -q {} ".format(self._cache_size, self._cores))
        if debug:
            params.append("-e")
        command = "".join(params)

        try:
            logging.info("Run: {}".format(command))
            if dry_run:
                return
            subprocess.run(command, shell=True, check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise GptError(
                "GPT command failed \n {} \n Stderr: {}".format(
                    command, e.stderr.decode("utf-8")
                )
            ) from e


class DorisProcessor(Processor):  # leave room for other sensors
    def __init__(self):
        pass

    def process(self):
        pass
