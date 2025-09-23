import re

# This map is used to store different types of radar data 
# and the regex patterns for matching radar types
# 这个 map 是用来放不同类型的雷达数据 匹配雷达类型的正则项的
radar_type_pat_map = {
    'LT1': r'^LT1.*\.meta\.xml$',
    'BC': r'^bc.*\.xml$',
}

# This map is used to store different types of radar data and 
# the regex patterns for matching meta/XML files
# 这个 map 是用来放不同类型的雷达数据 匹配 meta/xml 的正则项的
is_meta_file = {
    'LT1': lambda x: bool(re.search(r'^LT1.*\.meta\.xml$', x)),
    'BC': lambda x: bool(re.search(r'^bc.*\.xml$', x)),
}

# This map is used to store different types of radar data and 
# the regex patterns for matching data files
# 这个 map 是用来放不同类型的雷达数据 匹配 data 的正则项的
is_data_file = { 
    'LT1': lambda x: bool(re.search(r'^LT1.*\.tiff$', x)),
    'BC': lambda x: bool(re.search(r'^bc.*\.tiff$', x)),
}

# This map is used to extract the date from the filenames of different radar types
# 这个 map 是用来从不同类型雷达数据的文件名中提取日期的
get_date_from_filename = { 
    'LT1': {'meta': lambda x: re.search(r'LT1.*_(20\d{6})', x).group(1),
            'data': lambda x: re.search(r'LT1.*_(20\d{6})', x).group(1)},
    'BC': {'meta': lambda x: re.search(r'bc.*(20\d{6})', x).group(1),
            'data': lambda x: re.search(r'bc.*(20\d{6})', x).group(1)},
}
