import os


class Config:
    # https://github.com/microsoftgraph/python-sample-auth/blob/master/config.py
    # https://github.com/amundsen-io/amundsenfrontendlibrary/blob/master/amundsen_application/config.py
    SNAP_GPT_EXECUTABLE = os.getenv("SNAP_GPT_EXECUTABLE", None)


class LocalConfig(Config):

    LOG_LEVEL = "DEBUG"
    SNAP_GPT_CACHE_SIZE = "16G"
    SNAP_GPT_NTHREADS = os.cpu_count()
