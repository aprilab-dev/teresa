import click
import logging
import os
import shutil

import click_log
import coloredlogs
from datetime import datetime

from teresa import stack, version
from teresa.helpers import QueryS1Data
from teresa.coregistration import COREG_DIR


logger = logging.getLogger("sLogger")
# coleredlogs 的 handlers 缺省，暂时注释掉
coloredlogs.install(  # set colored logs for console in cli
    level=logger.level,
    logger=logger,
    fmt=logger.handlers[0].formatter._fmt,  # type: ignore
)


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
    help="The directory where resampled and coregistered SLCs are saved.",
)
@click.option(
    "--master",
    "-m",
    required=True,
    type=click.DateTime(formats=["%Y%m%d"]),
    help="The master image in [yyyymmdd] format for coregistering the stack.",
)
@click_log.simple_verbosity_option(logger=logger)
@click.option("--dry-run", "-n", "dry_run", default=False, is_flag=True, help="Dry run.")
@click.option("--prune/--no-prune", default=True, help="清除运行中的冗余数据")
@click.option("--aoi", default=None, help="请输入 AOI 文件，缺省时则全景处理")  # 增加一个输入参数
def coregister(source_dir, destination, master, dry_run: bool, prune: bool, aoi: bool):
    """
    Coregistrating a stack of SAR SLC images from source directory
    """

    # run coregistration
    loaded_stack = stack.Sentinel1SlcStack(sourcedir=source_dir).load()
    if aoi:
        loaded_stack = loaded_stack.crop(aoi=aoi)  # 此处就不做调整了，因为此时的 aoi 一定存在。
    loaded_stack.coregister(
        output=destination,
        master=datetime.strftime(master, "%Y%m%d"),
        dry_run=dry_run,
        prune=prune,
    )

    if dry_run:  # cleanup entire folder if dry run
        shutil.rmtree(os.path.join(destination, COREG_DIR))


@main.command()
@click.option(
    "--output-path",
    "-o",
    "output_path",
    required=False,
    default="./result.txt",
    type=click.Path(exists=False, file_okay=True, dir_okay=True, resolve_path=True),
    help="数据 txt 文件的路径，缺省时默认输出在当前工作路径下。",
)
@click.option(
    "--aoi",
    "aoi",
    type=str,
    required=True,
    help="AOI 数据，可以是 geojson 文件，也可以是 POLYGON 字符串, 如'POLYGON(....)'",
)
@click.option(
    "--start-time",
    "-t1",
    required=True,
    type=click.DateTime(formats=["%Y%m%d"]),
    help="查询的起始时间.",
)
@click.option(
    "--end-time",
    "-t2",
    required=True,
    type=click.DateTime(formats=["%Y%m%d"]),
    help="查询的终止时间",
)
def query(aoi, start_time, end_time, output_path):
    """基于 aoi、起止时间，查询数据。"""

    # 将时间转为 xxxx-xx-xx 格式的字符串形式。
    start_time = datetime.strftime(start_time, "%Y-%m-%d")
    end_time = datetime.strftime(end_time, "%Y-%m-%d")
    query_s1 = QueryS1Data(aoi=aoi, start_time=start_time, end_time=end_time).query()
    query_s1.serialize(output_path)
