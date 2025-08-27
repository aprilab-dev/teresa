
import numpy as np
import matplotlib.pyplot as plt

# 文件名 & 参数
filename = "/data/tests/junjun/coregTest/bc3/workspace/20240415/cint.minrefpha.raw"
nlines = 3979       # 行数 (multilooked)
npixels = 3010      # 列数 (multilooked)
dtype = np.float32  # complex_real4 = 复数 (两个 float32)

# 读入数据
data = np.fromfile(filename, dtype=dtype)

# 每个像素由 (real, imag) 两个 float32 构成
data = data.reshape((nlines, npixels, 2))
cpx = data[:,:,0] + 1j * data[:,:,1]

# --------- 计算幅度 ---------
amp = np.abs(cpx)
amp_norm = (amp / np.max(amp) * 255).astype(np.uint8)

# --------- 计算相位 ---------
phase = np.angle(cpx)   # 范围 [-pi, pi]
# 归一化到 [0,255] 便于保存
phase_norm = ((phase + np.pi) / (2 * np.pi) * 255).astype(np.uint8)

# 可选：下采样（比如缩小一半）
downsample_factor = 2
amp_down = amp_norm[::downsample_factor, ::downsample_factor]
phase_down = phase_norm[::downsample_factor, ::downsample_factor]

# 保存 PNG
plt.imsave("cint_minrefdem_amp.png", amp_down, cmap="gray")
plt.imsave("cint_minrefdem_phase.png", phase_down, cmap="jet")  # 相位用彩色更直观

print("✅ 转换完成，输出文件：cint_minrefdem_amp.png 和 cint_minrefdem_phase.png")