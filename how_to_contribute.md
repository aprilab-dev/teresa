# 新增卫星类型

## 一、准备文件

新增一种卫星类型时，需要准备以下两个文件：

1. `xxx_dump_data.py`
2. `xxx_dump_header2doris.py`

其中：

- **`xxx_dump_data.py`**：负责将原始 SAR 数据转换为 DORIS 可以识别的格式。  
- **`xxx_dump_header2doris.py`**：负责将原始 meta 数据转换为 DORIS 可以识别的格式。  

---

## 二、Teresa 接口对接流程

### 1. 放置文件

将上述两个文件放入目录：

teresa/teresa/dump/

---

### 2. 注册卫星类型

在文件：

teresa/teresa/dump/dump_funcs_map

中添加对应的卫星类型映射。

---

### 3. 添加正则匹配规则

在文件：

teresa/teresa/slcStack.py

中添加对应的正则匹配项。需要准备以下 5 类正则表达式：

1. 根据雷达的 meta 文件名，匹配雷达类型的正则表达式  
2. 判断一个文件是否为 meta 文件的正则表达式  
3. 判断一个文件是否为 data 文件的正则表达式  
4. 从 meta 文件名中提取日期的正则表达式  
5. 从 data 文件名中提取日期的正则表达式  

---

# 三、xxx_dump_header2doris.py 实现说明

## 需要实现函数： 
### lt1_dump_header2doris()

该函数的作用：
	•	在配准过程中提取 DORIS 所需的 meta 数据
	•	输出为 resultfile 文件



需要构造一个名为 xxx（卫星名）的类，并实现以下方法：

1. usage() ：输出基本信息（包含雷达类型，按实际卫星修改）。
2. read_meta() ：将 meta 数据字段从原始命名映射为 DORIS 命名，实现一一对应转换。
3. update_external_orbit() ： 单独处理轨道数据的读取与更新。
4. export2res()：将处理后的 meta 数据导出为 resultfile 文件。


可以参考：bc 的 meta.xml 最终生成的 resultfile 的 teresa/dump/lt1_dump_header2doris.py



# 四、xxx_dump_data.py 实现说明

## 需要实现函数：

xxx_dump_data()，该函数内部需要调用两个函数：
lt1_to_data()
lt1_to_res()

各函数功能说明

1. lt1_to_data()：读取原始数据；转换为 DORIS 可以识别的格式



2. lt1_to_res()：获取 data 的尺寸信息；将尺寸信息写入 resultfile 文件

可以参考：teresa/teresa/dump/bc_dump_data.py

