import click
import logging
import click_log
from datetime import datetime
from . import stack

logger = logging.getLogger("sLogger")
click_log.basic_config(logger)


@click.group()
@click.version_option(message="%(version)s")
def main():
    """
    Teresa is a command line tool for coregistering a stack of SAR SLC images.
    For more details see: https://git.terraqt.io/arcticwind/seafringe/teresa.
    """
    pass


master = "20210401"



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
@click_log.simple_verbosity_option(logger)
@click.option("--dry_run", "-n", default=False, is_flag=True, help="Dry run.")
def coregister(source_dir, destination, master, dry_run):
    """
    Coregistrating a stack of SAR SLC images from source directory
    """

    # run coregistration
    loaded_stack = stack.Sentinel1SlcStack(sourcedir=source_dir).load()
    loaded_stack.coregister(
        output=destination,
        master=datetime.strftime(master, "%Y%m%d"),
        dry_run=dry_run
    )
