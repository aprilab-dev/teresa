#!/home/yuxiao/.virtualenvs/doris/bin/python3

# import os
# activate_venv_path = os.path.join('/home/yuxiao/.virtualenvs/doris/', 'bin/activate_this.py')
# with open(activate_venv_path) as f:
#     exec(f.read(), {'__file__': activate_venv_path})

import os
import sys
import warnings
import rasterio
import numpy as np
from datetime import datetime
# from SarSpectrum import SarSpectrum

"""
BC3_DUMP_DATA() reads the BC3 format SLC data, and write to disk the
DORIS-compatale binary format for DORIS processing.
"""

# suppress NotGeoreferencedWarning
warnings.filterwarnings(
    "ignore", category=rasterio.errors.NotGeoreferencedWarning)  # type: ignore


def bc3_to_data(
    filein: str,
    fileout: str,
    l0: int = None,
    lN: int = None,
    p0: int = None,
    pN: int = None,
) -> tuple:

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
            cdata[0::2] = w[0, ln, p0 - 1: pN].real
            cdata[1::2] = w[0, ln, p0 - 1: pN].imag
            cdata.tofile(fout)

    return lN - l0 + 1, pN - p0 + 1


def bc3_to_res(resFile: str, l0: int, lN: int, p0: int, pN: int) -> bool:

    fileout = "image.raw"

    if resFile is None:
        raise FileNotFoundError()

    # check whether the file exist
    outStream = open(resFile, "a")

    outStream.write("\n")
    outStream.write("**************************************************\n")
    outStream.write("*_Start_crop:			FC1\n")
    outStream.write("**************************************************\n")
    outStream.write("Data_output_file: 	%s\n" % fileout)
    outStream.write("Data_output_format: 			complex_short\n")

    outStream.write("First_line (w.r.t. original_image): 	%s\n" % l0)
    outStream.write("Last_line (w.r.t. original_image): 	%s\n" % lN)
    outStream.write("First_pixel (w.r.t. original_image): 	%s\n" % p0)
    outStream.write("Last_pixel (w.r.t. original_image): 	%s\n" % pN)

    outStream.write("**************************************************\n")
    outStream.write("* End_crop:_NORMAL\n")
    outStream.write("**************************************************\n")

    outStream.write("\n")
    outStream.write("    Current time: {}\n".format(datetime.now))
    outStream.write("\n")

    outStream.close()

    # replace crop tag in result file from 0 (not done) to 1 (done)
    sourceText = "crop:			0"
    replaceText = "crop:			1"
    inputStream = open(resFile, "r")
    textStream = inputStream.read()
    inputStream.close()
    outputStream = open(resFile, "w")
    outputStream.write(textStream.replace(sourceText, replaceText))
    outputStream.close()

    return True


def bc3_dump_data_usage():
    print(
        "\nUsage: python3 bc3_dump_data_usage.py inputfile outputfile l0 lN p0 pN"
    )  # nopep8
    print("  where inputfile        is the input filename")
    print("        outputfile       is the output filename")
    print("        l0               is the first azimuth line (starting at 1)")
    print("        lN               is the last azimuth line")
    print("        p0               is the first range pixel (starting at 1)")
    print("        pN               is the last range pixel")


def bc3_dump_data(source_data_path, work_dir):

    target_data_path = os.path.join(work_dir, "image.raw")
    l0, lN, p0, pN = None, None, None, None  # type:ignore

    # read LT1 file
    az_lines, ra_samples = bc3_to_data(source_data_path, target_data_path, l0, lN, p0, pN)

    # ------------------ Plot is Optional -----------------------------------

    if l0 is None and lN is None and p0 is None and pN is None:
        l0: int = 1
        lN: int = az_lines
        p0: int = 1
        pN: int = ra_samples

    res_file = os.path.join(work_dir, "slave.res")
    bc3_to_res(res_file, l0, lN, p0, pN)  # write result file