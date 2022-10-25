import os
import logging
import logging.config
from datetime import datetime

# HARDCODE the log into /tmp/log folder.
LOG_FOLDER = "/tmp/log/teresa"
# define log filename based on dates
LOG_FNAME = os.path.join(
    LOG_FOLDER, "teresa_{:%Y-%m-%d_%H-%M-%S}.log".format(datetime.now())
)
os.makedirs(LOG_FOLDER, exist_ok=True)


def log_config():

    # This is a really bad but simple workaround to delete empyth log files.
    # Now we simply traverse the log folder and delete empty files.
    # The correct way should be deleting empth log file **after** each run,
    # or simply do not generate log file at all if there's no writing.
    # However, after investigation, it seems that the two proposed approaches
    # are not so easy to implement. Since this is not the critical part of the
    # program, we decide to use this simpler approach for getting to where we
    # need to be.
    # traverse all logs in the directory and delete if empty
    for f in os.listdir(LOG_FOLDER):
        if os.stat(os.path.join(LOG_FOLDER, f)).st_size == 0:
            os.remove(os.path.join(LOG_FOLDER, f))

    # https://stackoverflow.com/questions/13649664/how-to-use-logging-with-pythons-fileconfig-and-configure-the-logfile-filename
    logging.config.fileConfig(
        fname=os.path.join(os.path.abspath(os.path.dirname(__file__)), "log.conf"),
        defaults={"logfilename": LOG_FNAME},
    )
    logger = logging.getLogger("sLogger")
    # https://stackoverflow.com/questions/53125305/testing-logging-output-with-pytest
    # logger.propagate = True

    return logger
