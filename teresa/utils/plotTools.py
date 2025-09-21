
import numpy as np
import matplotlib.pyplot as plt

dtype_format_map = {
    "complex_short": np.complex64,   # 由两个 int16 表示 (I/Q)，常用于SAR数据
    "short": np.int16,
    "int": np.int32,
    "long": np.int64,
    "float": np.float32,
    "double": np.float64,
    "complex_float": np.complex64,
    "complex_double": np.complex128
}

def plot_amplitude(filename, output_png, nlines, npixels, dtype, downsample_factor=2):
    """
    读取 Doris 输出的复数文件，计算并保存幅度和相位图像。

    参数:
    - filename: str, 输入文件路径
    - nlines: int, 图像行数
    - npixels: int, 图像列数
    - dtype: 数据类型, 默认 np.float32 (complex_real4)
    - downsample_factor: int, 下采样因子，默认 2
    """
    # 读入数据
    data = np.fromfile(filename, dtype=dtype)
    
    # 每个像素由 (real, imag) 两个 float32 构成
    data = data.reshape((nlines, npixels, 2))
    cpx = data[:,:,0] + 1j * data[:,:,1]

    # 计算幅度
    amp = np.abs(cpx)
    amp_norm = (amp / np.max(amp) * 255).astype(np.uint8)

    # 下采样
    amp_down = amp_norm[::downsample_factor, ::downsample_factor]

    # 保存 PNG
    plt.imsave(output_png, amp_down, cmap="gray")


def plot_phase(filename, output_png, nlines, npixels, dtype, downsample_factor=2):
    """
    读取 Doris 输出的复数文件，计算并保存相位图像。

    参数:
    - filename: str, 输入文件路径
    - nlines: int, 图像行数
    - npixels: int, 图像列数
    - dtype: 数据类型, 默认 np.float32 (complex_real4)
    - downsample_factor: int, 下采样因子，默认 2
    """
    # 读入数据
    data = np.fromfile(filename, dtype=dtype)
    
    # 每个像素由 (real, imag) 两个 float32 构成
    data = data.reshape((nlines, npixels, 2))
    cpx = data[:,:,0] + 1j * data[:,:,1]

    # 计算相位
    phase = np.angle(cpx)   # 范围 [-pi, pi]
    phase_norm = ((phase + np.pi) / (2 * np.pi) * 255).astype(np.uint8)

    # 下采样
    phase_down = phase_norm[::downsample_factor, ::downsample_factor]

    # 保存 PNG
    plt.imsave(output_png, phase_down, cmap="jet")


if __name__ == "__main__":
    num_of_lines  = 15918
    num_of_pixels = 12040
    dtype         = dtype_format_map["complex_real4"]
    filename      = "/data/tests/junjun/coregTest/bc3/workspace/20240415/cint.minrefpha.raw"
    output_png    = "/data/tests/junjun/coregTest/bc3/workspace/20240415/minrefpha.png"

    plot_amplitude(filename, output_png, num_of_lines, num_of_pixels, dtype)
    # plot_phase(filename, num_of_lines, num_of_pixels, dtype)
