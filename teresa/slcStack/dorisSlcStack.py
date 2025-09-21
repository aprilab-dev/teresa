import os
import re

from teresa.slcStack.radar_type import radar_type_pat_map, is_meta_file, is_data_file, get_date_from_filename
from teresa.utils.TeresaLog import global_log

class dorisSlcStack():
    def __init__(self, params):
        self.params = params
        self.data_dir = self.params['stack_parameters']['data_dirs']
        self.work_dir = self.params['stack_parameters']['work_dir']
        self.master_date = self.params['stack_parameters']['masterDate']

        self.meta_path_map = dict()
        self.data_path_map = dict()
        self.dates = []
        self.radar_type = ""

        self.initialize()
        # Check whether master_date is valid
        # 检查 master_date 是否合法
        if (not self.master_date) | (self.master_date and self.master_date not in self.dates):
            raise ValueError(f"Master date {self.master_date} not found. Please check the input parameters.")
        
        # Initialize logs and print logs
        # 初始化日志、打印日志
        global_log.radar_type = self.radar_type
        global_log.start_global(task_count=len(self.dates) - 1)


    def initialize(self):
        """
        Initialize the dorisSlcStack object with parameters.
        """
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(f"Data directory {self.data_dir} does not exist.")

        # Determine the radar type
        # 确定雷达类型
        for radar_type, pattern in radar_type_pat_map.items():
            is_matched = self.check_radar_type(pattern)
            if is_matched:
                self.radar_type = radar_type
                break
        if not self.radar_type:
            raise ValueError("No matching radar type found in the data directory.")
        
        # Initialize self.data_path_map, where the key is the date and 
        # the value is the path to the data files corresponding to that date
        # 初始化 self.data_path_map，其中， key 是日期，value 是日期对应的数据文件路径
        for dirpath, _, filenames in os.walk(os.path.abspath(self.data_dir)):
            for filename in filenames:
                # Use regex matching to find the data files and initialize self.data_path_map
                # 通过正则匹配，找到 data 数据文件，初始化 self.data_path_map
                data_file = is_data_file[self.radar_type](filename)
                if data_file:
                    date_str = get_date_from_filename[self.radar_type]['data'](filename)
                    full_path = os.path.join(dirpath, filename)
                    self.data_path_map[date_str] = full_path  

                # Use regex matching to find the meta files and initialize self.meta_path_map
                # 通过正则匹配，找到 meta 元文件，初始化 self.meta_path_map
                meta_file = is_meta_file[self.radar_type](filename)
                if meta_file:
                    date_str = get_date_from_filename[self.radar_type]['meta'](filename)
                    full_path = os.path.join(dirpath, filename)
                    self.meta_path_map[date_str] = full_path   

        # Initialize self.dates, the list of dates
        # 初始化 self.dates 日期列表  
        #! 其实，这里可以检查一下 meta 和 data 的日期是否一致的，偷懒了 
        self.dates = sorted(set(self.meta_path_map.keys()) | set(self.data_path_map.keys()))

    def check_radar_type(self, pattern):
        """
        Check if the radar type matches the given pattern.
        """
        regex = re.compile(pattern)
        # Traverse all files under the data_dir directory and check for matches 
        # 遍历 data_dir 目录下的所有文件，检查是否有匹配
        for _, _, filenames in os.walk(self.data_dir, followlinks=True):
            for filename in filenames:
                if regex.match(filename):
                    return True
        return False