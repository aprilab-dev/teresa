import os
import rasterio
import numpy as np
from datetime import datetime

def lt4_to_res(res_file, l0, lN, p0, pN):

    fileout = "image.raw"
    
    # 确保以追加模式(a)打开，这样不会覆盖 header2doris 写入的头部信息
    with open(res_file, "a") as outStream:
        outStream.write("\n")
        outStream.write("**************************************************\n")
        outStream.write("*_Start_crop:			LT4\n")
        outStream.write("**************************************************\n")
        outStream.write(f"Data_output_file: 	{fileout}\n")
        outStream.write("Data_output_format: 			complex_short\n")
        outStream.write(f"First_line (w.r.t. original_image): 	{l0}\n")
        outStream.write(f"Last_line (w.r.t. original_image): 	{lN}\n")
        outStream.write(f"First_pixel (w.r.t. original_image): 	{p0}\n")
        outStream.write(f"Last_pixel (w.r.t. original_image): 	{pN}\n")
        outStream.write("**************************************************\n")
        outStream.write("* End_crop:_NORMAL\n")
        outStream.write("**************************************************\n")
        outStream.write("\n")
        outStream.write(f"    Current time: {datetime.now()}\n")
        outStream.write("\n")

    # 替换 res 文件头部的 process_control 状态标识 (将 crop: 0 改为 1)
    if os.path.exists(res_file):
        with open(res_file, "r") as inputStream:
            textStream = inputStream.read()
        sourceText = "crop:\t\t0"
        replaceText = "crop:\t\t1"
        if sourceText in textStream:
            with open(res_file, "w") as outputStream:
                outputStream.write(textStream.replace(sourceText, replaceText))

def lt4_dump_data(source_data_path, work_dir):
    """
    从 LT4 TIFF 文件中提取纯二进制 SLC 数据，并更新 Doris 记录。
    接口已完全对齐 teresa 规范。
    """
    
    if not os.path.exists(source_data_path):
        raise FileNotFoundError(f"找不到文件: {source_data_path}")

    target_data_path = os.path.join(work_dir, "image.raw")
    res_file = os.path.join(work_dir, "slave.res")

    with rasterio.open(source_data_path) as src:
        data = src.read()
        I = data[0]
        Q = data[1]
        complex_data = np.stack((I, Q), axis=-1)
        complex_data.tofile(target_data_path)

        bands, height, width = data.shape
        l0, lN = 1, height
        p0, pN = 1, width
        lt4_to_res(res_file, l0, lN, p0, pN)

if __name__ == "__main__":
    # 测试路径
    test_tiff = "/data/test/junjun/teresa_test_data/teresa_doris/lt4/first_priority/JZ1_MYC_STRIP1_013549_E113.3_N39.8_20260306_SLC_HH_L10000068072/JZ1_MYC_STRIP1_013549_E113.3_N39.8_20260306_SLC_HH_L10000068072.tiff"
    work_directory = "./"  # 设定当前目录为工作目录
    lt4_dump_data(test_tiff, work_directory)
