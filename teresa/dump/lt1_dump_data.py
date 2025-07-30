#!/usr/bin/env python3

import os
# activate_venv_path = os.path.join('/home/yuxiao/.virtualenvs/doris/', 'bin/activate_this.py')
# with open(activate_venv_path) as f:
#     exec(f.read(), {'__file__': activate_venv_path})

import os
import sys
import warnings
import rasterio
import numpy as np
from datetime import datetime

"""
LT1_DUMP_DATA() reads the LuTan-1 format SLC data, and writes to disk the
DORIS-compatible binary format for DORIS processing.
"""

# suppress NotGeoreferencedWarning
warnings.filterwarnings(
    "ignore", category=rasterio.errors.NotGeoreferencedWarning)  # type: ignore


def lt1_to_data(
    filein: str,
    fileout: str,
    l0: int = None,
    lN: int = None,
    p0: int = None,
    pN: int = None,
) -> tuple:
    """Convert LT1 data to DORIS format

    Parameters
    ----------
    filein : str
        Input LT1 SLC file path
    fileout : str
        Output DORIS format file path
    l0 : int, optional
        First line to read (1-based), by default None
    lN : int, optional
        Last line to read, by default None
    p0 : int, optional
        First pixel to read (1-based), by default None
    pN : int, optional
        Last pixel to read, by default None

    Returns
    -------
    tuple
        (number of lines, number of pixels)
    """

    if not os.path.exists(filein):
        raise FileNotFoundError("File {} not found!".format(filein))

    with rasterio.open(filein) as src:
        w = src.read()

    if l0 is None:
        l0 = 1
    if lN is None:
        lN = src.height
    if p0 is None:
        p0 = 1
    if pN is None:
        pN = src.width


    with open(fileout, "wb") as fout:
        for ln in range(l0 - 1, lN):
            cdata = np.empty((pN - p0 + 1) * 2, dtype="<i2")
            cdata[0::2] = w[0, ln, p0 - 1: pN]
            cdata[1::2] = w[1, ln, p0 - 1: pN]
            cdata.tofile(fout)

    return lN - l0 + 1, pN - p0 + 1


def lt1_to_res(resFile: str, l0: int, lN: int, p0: int, pN: int) -> bool:
    """Write crop information to result file

    Parameters
    ----------
    resFile : str
        Result file path
    l0 : int
        First line
    lN : int
        Last line
    p0 : int
        First pixel
    pN : int
        Last pixel

    Returns
    -------
    bool
        True if successful
    """

    fileout = "image.raw"

    if resFile is None:
        raise FileNotFoundError()

    # check whether the file exist
    
    outStream = open(resFile, "a")

    outStream.write("\n")
    outStream.write("**************************************************\n")
    outStream.write("*_Start_crop:			LT1\n")
    outStream.write("**************************************************\n")
    outStream.write("Data_output_file: 	%s\n" % fileout)
    outStream.write("Data_output_format: 			complex_short\n")

    outStream.write("First_line (w.r.t. original_image): 	%s\n" % l0)
    outStream.write("Last_line (w.r.t. original_image): 	%s\n" % lN)
    outStream.write("First_pixel (w.r.t. original_image): 	%s\n" % p0)
    outStream.write("Last_pixel (w.r.t. original_image): 	%s\n" % pN)
    outStream.write("Number of lines (non-multilooked): 	%s\n" % lN)
    outStream.write("Number of pixels (non-multilooked): 	%s\n" % pN)

    outStream.write("**************************************************\n")
    outStream.write("* End_crop:_NORMAL\n")
    outStream.write("**************************************************\n")

    outStream.write("\n")
    outStream.write("    Current time: {}\n".format(datetime.now()))
    outStream.write("\n")

    outStream.close()

    sourceText = "crop:			0"
    replaceText = "crop:			1"
    inputStream = open(resFile, "r")
    textStream = inputStream.read()
    inputStream.close()
    outputStream = open(resFile, "w")
    outputStream.write(textStream.replace(sourceText, replaceText))
    outputStream.close()

    return True

def lt1_dump_data(source_data_path, work_dir):

    target_data_path = os.path.join(work_dir, "image.raw")
    l0, lN, p0, pN = None, None, None, None  

    # read LT1 file
    az_lines, ra_samples = lt1_to_data(source_data_path, target_data_path, l0, lN, p0, pN)

    if l0 is None and lN is None and p0 is None and pN is None:
        l0: int = 1
        lN: int = az_lines
        p0: int = 1
        pN: int = ra_samples

    
    res_file = os.path.join(work_dir, "slave.res")
    lt1_to_res(res_file, l0, lN, p0, pN)