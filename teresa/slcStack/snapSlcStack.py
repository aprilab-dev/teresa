
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
        self.min_lon = params['Stack_parameters']["min_lon"]
        self.max_lon = params['Stack_parameters']["max_lon"]
        self.min_lat = params['Stack_parameters']["min_lat"]
        self.max_lat = params['Stack_parameters']["max_lat"]
        self.master_date = params['Stack_parameters']["masterDate"]
        self.pol = params['Stack_parameters']["pol"]
        self.wkt = ""
        self.dates = []
        self.slave_dates = []
        self.data_path_map = {}

        self.intialize()
    
    def intialize(self):
        """
        Initialize the snapSlcStack class with parameters.
        """
        # 1. 初始化 self.data_path_map
        # key 是日期， value 是日期对应的数据文件路径列表
        slc_zip_files = []
        for file_name in os.listdir(self.data_dirs):
            if file_name.endswith(".zip"):
                slc_zip_files.append(file_name)
        
        for file_name in slc_zip_files:
            date = file_name[17:25]   # 提取日期
            self.dates.append(date)
            files_path = os.path.join(self.data_dirs, file_name)
            self.data_path_map.setdefault(date, []).append(files_path)
        
        # 2. 生成 wkt
        self.wkt = self._generate_wkt(self.min_lon, self.max_lon, self.min_lat, self.max_lat)
        self.wkt = (f"POLYGON (({self.min_lon} {self.min_lat}, "
                                f"{self.max_lon} {self.min_lat}, "
                                f"{self.max_lon} {self.max_lat}, "
                                f"{self.min_lon} {self.max_lat}, "
                                f"{self.min_lon} {self.min_lat}))")
        
        # 3. 检查 master_date 是否合法
        if (not self.master_date) | (self.master_date and self.master_date not in self.dates):
            raise ValueError(f"Master date {self.master_date} not found. Please check the input parameters.")

        # 4. 生成 slave_dates 列表
        self.slave_dates = [date for date in self.dates if date != self.master_date]
