
'''
snapSlcStack
'''
import re
import os

class snapSlcStack():
    def __init__(self, params):
        super().__init__()
        self.work_dir = params['Stack_parameters']["work_dir"]
        self.data_dirs = params['Stack_parameters']["data_dirs"]
        self.swaths = params['Stack_parameters']["swaths"]
        self.min_lon = params['Stack_parameters']["min_lon"]
        self.max_lon = params['Stack_parameters']["max_lon"]
        self.min_lat = params['Stack_parameters']["min_lat"]
        self.max_lat = params['Stack_parameters']["max_lat"]
        self.master_date = params['Stack_parameters']["masterDate"]
        self.mastre_path  = None
        self.slave_path_list = []

        self.intialize()
    
    def intialize(self):
        """
        Initialize the snapSlcStack class with parameters.
        """
        # 1. 初始化 mastre_path 和 slave_path_list
        # S1A_IW_SLC__1SDV_20220106T101357_20220106T101424_041339_04EA18_C3CA.zip

        for data_dir in self.data_dirs:
            slc_files = os.listdir(data_dir)
            slc_files.sort()
            for slc_name in slc_files:
                if slc_name.endswith('.zip'): # test if it is S1 .zip FILE
                    match = re.search(r"\d{8}(?=T)", slc_name)
                    if match:
                        date = match.group()
                        if date == self.master_date:
                            self.mastre_path = os.path.join(data_dir, slc_name)
                        else:
                            self.slave_path_list.append(os.path.join(data_dir, slc_name))

