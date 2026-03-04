import os
import h5py
from datetime import datetime

def csk_to_res(res_file, l0, lN, p0, pN):
    """
    将 crop (裁剪) 块信息追加写入到 Doris 的 res 文件中。
    这一步对 Doris 读取二进制矩阵至关重要。
    """
    fileout = "image.raw"
    
    # 确保以追加模式(a)打开，这样不会覆盖 header2doris 写入的头部信息
    with open(res_file, "a") as outStream:
        outStream.write("\n")
        outStream.write("**************************************************\n")
        outStream.write("*_Start_crop:			CSK\n")
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

def csk_dump_data(source_data_path, work_dir):
    """
    从 CSK HDF5 文件中提取纯二进制 SLC 数据，并更新 Doris 记录。
    接口已完全对齐 teresa 规范。
    """
    print(f"正在读取 CSK 数据: {source_data_path}")
    
    if not os.path.exists(source_data_path):
        raise FileNotFoundError(f"找不到文件: {source_data_path}")

    target_data_path = os.path.join(work_dir, "image.raw")
    res_file = os.path.join(work_dir, "slave.res")

    with h5py.File(source_data_path, 'r') as f:
        if 'S01/SBI' in f:
            sbi_dataset = f['S01/SBI']
            shape = sbi_dataset.shape
            print(f"找到数据集 S01/SBI, 形状: {shape}, 类型: {sbi_dataset.dtype}")
            
            # 1. 生成纯二进制文件
            with open(target_data_path, 'wb') as out_f:
                out_f.write(sbi_dataset[:].tobytes())
                
            print(f"数据已成功 Dump 至: {target_data_path}")
            
            # 2. 将数据矩阵的边界信息写入 slave.res
            l0, lN = 1, shape[0]
            p0, pN = 1, shape[1]
            csk_to_res(res_file, l0, lN, p0, pN)
            print(f"Crop 参数已成功追加至: {res_file}")

        else:
            raise KeyError("在 HDF5 文件中未找到 'S01/SBI' 数据集！")

if __name__ == "__main__":
    # 测试路径
    test_h5 = "2663070-1923945/CSKS4_SCS_B_HI_04_HH_RD_SF_20240115100904_20240115100912.h5"
    work_directory = "./"  # 设定当前目录为工作目录
    csk_dump_data(test_h5, work_directory)
