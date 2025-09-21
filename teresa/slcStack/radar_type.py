import re

# This map is used to store different types of radar data 
# and the regex patterns for matching radar types
# 这个 map 是用来放不同类型的雷达数据 匹配雷达类型的正则项的
radar_type_pat_map = {
    'LT1': r'^LT1.*\.meta\.xml$',
    'BC3': r'^bc3.*\.xml$',
    'BC4': r'^bc4.*\.xml$',
}

# This map is used to store different types of radar data and 
# the regex patterns for matching meta/XML files
# 这个 map 是用来放不同类型的雷达数据 匹配 meta/xml 的正则项的
is_meta_file = {
    'LT1': lambda x: bool(re.search(r'^LT1.*\.meta\.xml$', x)),
    'BC3': lambda x: bool(re.search(r'^bc3.*\.xml$', x)),
    'BC4': lambda x: bool(re.search(r'^bc4.*\.xml$', x)),
}

# This map is used to store different types of radar data and 
# the regex patterns for matching data files
# 这个 map 是用来放不同类型的雷达数据 匹配 data 的正则项的
is_data_file = { 
    'LT1': lambda x: bool(re.search(r'^LT1.*\.tiff$', x)),
    'BC3': lambda x: bool(re.search(r'^bc3.*\.tiff$', x)),
    'BC4': lambda x: bool(re.search(r'^bc4.*\.tiff$', x)),
}

# This map is used to extract the date from the filenames of different radar types
# 这个 map 是用来从不同类型雷达数据的文件名中提取日期的
get_date_from_filename = { 
    'LT1': {'meta': lambda x: re.search(r'LT1.*_(20\d{6})', x).group(1),
            'data': lambda x: re.search(r'LT1.*_(20\d{6})', x).group(1)},
    'BC3': {'meta': lambda x: re.search(r'bc3.*(20\d{6})', x).group(1),
            'data': lambda x: re.search(r'bc3.*(20\d{6})', x).group(1)},
    'BC4': {'meta': lambda x: re.search(r'bc4.*(20\d{6})', x).group(1),
            'data': lambda x: re.search(r'bc4.*(20\d{6})', x).group(1)},
}
