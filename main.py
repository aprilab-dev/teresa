import os
import sys

from teresa.inteface import createSlcStack
from teresa.inteface import createCoregistion

def coregister(parms_path):
    """
    Coregistrating a stack of SAR SLC images from source directory
    """

    if not os.path.exists(parms_path):
        raise FileNotFoundError(f"File not found: {parms_path}")

    slc_stack = createSlcStack(parms_path)
    coregister = createCoregistion(parms_path, slc_stack)
    coregister.run()

if __name__ == "__main__":   
    # load parameters file:
    parmFile = sys.argv[1]

    coregister(parmFile)