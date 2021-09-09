import logging
from . import config

def basic_config() -> None:
    if (sys.stdout.isatty() or sys.stdin.isatty()) and not os.getenv("SLURM_NTASKS", 0):
        logging_format = "%(asctime)s - [%(levelname)s] %(message)s"
    else:
        logging_format = "[%(hostname)s] %(asctime)s - [%(levelname)s] %(message)s"

    logging_settings = {
        "version": 1,
        "disable_exiting_loggers": False,
        "filters": {"hostname": {"()": f"{__name__}.HostnameFilter"}},
        "formatters": {"default": {"format": logging_format, "datefmt": "%Y-%m-%d %H:%M:%S"}},
        "handlers": {
            "default": {
                "level": config.LOGGING_LEVEL,
                "formatter": "default",
                "class": "logging.StreamHandler",
                # Keep stream compatible with the click stdout
                "stream": click.get_text_stream('stdout'),  # "ext://sys.stdout",
                # "stream": "ext://sys.stdout",
                "filters": ["hostname"],
            }
        },
        "loggers": {
            "": {
                "handlers": ["default"],
            }
        },
    }

    logging.config.dictConfig(logging_settings)
