import os
import logging
import logging.config
from datetime import datetime

# define log filename based on dates
LOG_FNAME = "teresa_{:%Y-%m-%d_%H-%M-%S}.log".format(datetime.now())


def log_config():
    # https://stackoverflow.com/questions/13649664/how-to-use-logging-with-pythons-fileconfig-and-configure-the-logfile-filename
    logging.config.fileConfig(
        fname=os.path.join(os.path.abspath(os.path.dirname(__file__)), "log.conf"),
        defaults={"logfilename": LOG_FNAME},
    )
    logger = logging.getLogger("sLogger")

    return logger
