import logging

class snapCoregistion(object):
    def __init__(self, parms, slc_stack):
        """
        Initialize the snapCoregistion class.
        
        Parameters:
            parms (dict): A dictionary containing the parameters for coregistration.
            slc_stack (object): An object representing the stack of SLC images.
        """
        self.slc_stack = slc_stack
        self.snap_path = parms['SNAP_parameters']["snap_path"]
        self.repo_path = parms['SNAP_parameters']["repo_path"]
        self.ram = parms['SNAP_parameters']["ram"]
        self.cores = parms['SNAP_parameters']["cores"]

    def run(self):
        # 1. 创建工作路径
        # 2. 根据 aoi 进行分割
        # 3. prepare
        # 4. getMaster
        # 5. batchCoregister

        # def coregister(self):
        #     self._prepare()
        #     self._coregister()
        #     self._merge()
        #     if self.radarcode_dem:  # if radarcode dem, do it before the prune
        #         self._radarcode_dem()
        #     self._finalize()

        # 1. 创建工作路径
        pass



