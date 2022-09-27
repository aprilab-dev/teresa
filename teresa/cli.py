from email.policy import default
import os
import click
import shutil
import logging
import coloredlogs
import click_log
from datetime import datetime
from teresa import stack, version
from teresa.coregistration import COREG_DIR



logger = logging.getLogger("sLogger")
# coleredlogs 的 handlers 缺省，暂时注释掉
# coloredlogs.install(  # set colored logs for console in cli
#     level=logger.level,
#     logger=logger,
#     fmt=logger.handlers[0].formatter._fmt  # type: ignore
# )


@click.group()
@click.version_option(message="%(version)s")
def main():
    """
    Teresa is a command line tool for coregistering a stack of SAR SLC images.
    For more details see: https://git.terraqt.io/arcticwind/seafringe/teresa.
    """
    logger.info(f"Using TERESA version: {version.__version__} for this run.")


@main.command()
@click.option(
    "--source-dir",
    "-s",
    "source_dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    help="The source directory where S1 SLC folders/zip files are stored.",
)
@click.option(
    "--destination",
    "-d",
    required=True,
    type=click.Path(exists=False, dir_okay=True, resolve_path=True),
    help="The directory where resampled and coregistered SLCs are saved.")
@click.option(
    "--master",
    "-m",
    required=True,
    type=click.DateTime(formats=["%Y%m%d"]),
    help="The master image in [yyyymmdd] format for coregistering the stack."
)
@click_log.simple_verbosity_option(logger=logger)
@click.option("--dry-run", "-n", "dry_run", default=False, is_flag=True, help="Dry run.")
@click.option("--prune/--no-prune", default=True, help="Remove temporary processing data.")
@click.option("--aoi",default=None, help="请输入 AOI 文件，缺省时则全景处理") # 增加一个输入参数
def coregister(source_dir, destination, master, dry_run: bool, prune: bool, aoi: bool):
    """
    Coregistrating a stack of SAR SLC images from source directory
    """

    # run coregistration
    loaded_stack = stack.Sentinel1SlcStack(sourcedir=source_dir).load().crop(aoi=aoi)
    loaded_stack.coregister(
        output=destination,
        master=datetime.strftime(master, "%Y%m%d"),
        dry_run=dry_run,
        prune=prune,
    )

    if dry_run:  # cleanup entire folder if dry run
        shutil.rmtree(os.path.join(destination, COREG_DIR))