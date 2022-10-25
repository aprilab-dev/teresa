import os
from psutil import virtual_memory


class Config:
    # https://github.com/microsoftgraph/python-sample-auth/blob/master/config.py
    # https://github.com/amundsen-io/amundsenfrontendlibrary/blob/master/amundsen_application/config.py
    SNAP_GPT_EXECUTABLE = os.getenv(
        "SNAP_GPT_EXECUTABLE", "gpt"
    )  # 当无法获取环境中 GPT 路径时，默认为 gpt


class LocalConfig(Config):
    # https://forum.step.esa.int/t/slow-performance-of-snap-for-tops-all-swath-ifg/17180/3
    # https://forum.step.esa.int/t/gpt-and-snap-performance-parameters-exhaustive-manual-needed/8797
    # gpt -c SNAP_GPT_CACHE_SIZE -p SNAP_GPT_NTHREADS
    SNAP_GPT_CACHE_SIZE = f"{virtual_memory().total / 1024**3 * 0.70:.0f}G"
    SNAP_GPT_NTHREADS = os.cpu_count()  # use all cores by default
