
import numpy as np
import matplotlib.pyplot as plt


def plot_amplitude(filename, nlines, npixels, downsample_factor=2):
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
    data = np.fromfile(filename, dtype=np.int16)
    
    # 每个像素由 (real, imag) 两个 float32 构成
    data = data.reshape(nlines, npixels, 2)
    complex_img = data[:,:,0] + 1j * data[:,:,1]

    # 下采样
    complex_img = complex_img[::downsample_factor, ::downsample_factor]

    # 计算幅度
    amplitude = np.abs(complex_img)
    amp_display = np.log1p(amplitude)

    # 计算相位
    phase = np.angle(complex_img)
    phase_norm = ((phase + np.pi) / (2 * np.pi) * 255).astype(np.uint8)

    # plt.imsave("amplitude.png", amp_display, cmap="gray")
    # plt.imsave("phase.png", phase_norm, cmap="hsv", vmin=0, vmax=255)


    # 保存 PNG
    plt.figure(figsize=(6,6))
    plt.imshow(amp_display, cmap='gray')
    plt.axis('off')
    plt.savefig("amplitude.png", dpi=300, bbox_inches='tight')

    plt.figure(figsize=(6,6))
    plt.imshow(phase_norm, cmap='hsv', vmin=-np.pi, vmax=np.pi)
    plt.colorbar()

    plt.axis('off')
    plt.savefig("phase.png", dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()


def plot_phase(filename, output_png, nlines, npixels, dtype, downsample_factor=4):
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
    num_of_lines  = 17920
    num_of_pixels = 20736
    filename      = "/data/tests/jinting/changsha/insar/stack/process_pro/workspace/20240309/slave_rsmp.raw"

    plot_amplitude(filename, num_of_lines, num_of_pixels)
    # plot_phase(filename, num_of_lines, num_of_pixels, dtype)
