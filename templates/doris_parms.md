# Teresa 配置参数说明

本文档详细说明了 `Teresa` 软件中配置文件各部分的参数含义，便于用户理解和调整处理流程。

---

## 📁 stack_parameters 堆栈参数配置

| 参数名       | 说明                                      | 
|--------------|-------------------------------------------|
| work_dir     | 处理工作目录的路径                         |
| data_dirs    | 输入 SLC 数据的路径（可为单个或多个路径）     |
| masterDate   | 主图像日期（格式：YYYYMMDD），为空则自动选择最优主图像 |

---




## 🛰 coarsecorr 粗配准参数

| 参数名       | 说明                                      |值              |
|------------------|-------------------------------------|-----------------|
| CC_METHOD    | 选择对幅度图进行相关性计算的方法：  |magfft：将图像进行 fft 转换后，在频域计算；magspace：直接在空间域计算 |
| CC_ACC       | 用于设置 搜索 主从图像之间偏移量的范围。这个范围，如果采用的是 magfft ，会自动设置为窗口的一半；如果是 magspace 需要用这个参数主动设置  |格式：\<lines> \<pixels> ：9 9。就是 doris 会走动搜索最大为 正负8 像素的偏移 |
| CC_NWIN      | 表示估算偏移相关性窗口的数量              |  建议至少 5 个以上的窗口，越多越稳定，越小偏差越大
| CC_WINSIZE   | 表示用于相关性计算的窗口大小。窗口太小会不稳定，窗口太大可能会跨越地物边界          | 格式：\<lines> \<pixels> 
| CC_INITOFF   | 用于粗配准的初始偏移量设置       |格式：orbit  ｜  3 5  。如果是 orbit，则会从上一步 coarseorb 的输出中读取。如果是两个数字，则就是自己指定了
---

## 🔍 fine 精配准参数

| 参数名        | 说明                                     | 值 |
|------------------|-------------------------------------|-----------------|
| FC_METHOD      | 精配准方法（如：oversample）             |magfft：频域 （快，补边会引起 patch 大小变化）；magspace：空域 （稳定 patch 尺寸，速度慢）；oversample：频域 + 过采样  （理论最佳，抗混叠）|
| FC_NWIN        | 要在整幅图像上分布的窗口数量，这些窗口用于进行相关性计算以估算精配准偏移。         | r4：real4：32-bit 浮点（常见于 SRTM .float）；r8：real8：64-bit 双精度浮点
| FC_WINSIZE     | 相关性窗口的尺寸（行 × 列）         |窗口越大，匹配越稳定，但精细结构可能会被平均；窗口太小则容易受噪声影响。如果你使用的是高分辨率影像或纹理丰富的区域，可以适当减小窗口；如果影像噪声大或内容稀疏（如沙漠、海面），可以适当加大。 |
| FC_ACC         | 精度（单位为像素，格式："方位向 距离向"） | 建议设置为 8 8 。如果你使用的是 FFT 方法（频域相关），那么这个搜索精度值必须是2 的幂，例如：4、8、16、32 等。在 COARSECORR 步骤完成后的 日志文件中，如果 初始偏移量与最终估计值 之间的偏差大于 1，那么你应该考虑使用更大的窗口（如 FINE WINDOW 96 96） 和 更大的搜索范围（如 FINE ACCURACY 16 16） 来确保精配准稳定可靠。
| FC_INITOFF     | 设置初始偏移量          | coarsecorr：表示使用 coarsecorr 步骤生成的；
| FC_OSFACTOR    | 过采样因子                               | 推荐设置为 32，这样可以将主从影像配准精度提高到 0.1 像素 以内
| FC_SHIFTAZI    | 是否修正方位向偏移（ON/OFF）             | ON/OFF

---

## 🔄 coregpm 精配准多项式建模参数

| 参数名         | 说明                                   |值|
|------------------|-------------------------------------|-----------------|
| CPM_THRESHOLD  | 设置 多项式系数估计的相关性阈值           |这个阈值的选择取决于你在 FINE 步骤中使用的窗口大小。如果使用的是较小的窗口，估计出的相关性值会更偏向 1.0，也就是“看起来都很高”，因此在这种情况下应该使用更高的阈值，以排除虚高的不可靠点。如果你用的是 64 × 64 像素的窗口，那么设置相关性阈值为 0.2 是一个不错的选择。|
| CPM_DEGREE     | 二维多项式的阶数。                       |建议 2 
| CPM_WEIGHT     | 在进行最小二乘拟合时，根据每个偏移估计点的相关性（correlation）对其赋权，从而调整它在模型拟合中的影响力。              | BAMLER：默认推荐。基于理论模型（精度 ~ 相关性函数），最合理，最稳定；NONE：不使用加权，所有点权重相等（容易受异常点影响）；LINEAR：相关性值作为权重（相关性 0.8 → 权重 0.8）；QUADRATIC：权重 = 相关性²（相关性 0.8 → 权重 0.64，更强调高相关性点）
| CPM_MAXITER    | 最大迭代次数                            | Doris 会重复执行最小二乘拟合，每次迭代自动剔除最不符合模型的偏移点（异常值），直到所有观测点通过异常值检验，或达到这里设置的最大迭代次数

---

## 🎯 resample 重采样参数

| 参数名          | 说明                                |值|
|------------------|-------------------------------------|-----------------|
| RS_METHOD        | 选择用于插值的核函数（interpolation kernel）          | RECT：简单的阶跃函数（即最近邻插值）；TRI：线性插值（triangular kernel）；CC4P / CC6P：4 点或 6 点的三次卷积核（Cubic Convolution）；TS6P / TS8P / TS16P：截断 sinc 核函数，分别使用 6、8、16 个点（Truncated Sinc）；KNAB6 / KNAB8 / KNAB10 / KNAB16：使用 Knab 采样窗函数，并带有默认的过采样因子；RC6P / RC12P：6 点或 12 点的Raised Cosine（升余弦）核，这是推荐使用的插值方法（精度最高，效果最好）。
| RS_SHIFTAZI      | 是否修正方位向偏移（ON/OFF）       | ON：移动插值核频谱以匹配多普勒中心。（多普勒中心频率值较大时推荐）；OFF：不进行频谱对齐。（多普勒中心频率值非常小时推荐）
| RS_OUT_FILE      | 输出重采样结果文件名（如 slave_rsmp.raw） |
| RS_OUT_FORMAT    | 设置重采样后从影像的输出数据格式，可选两种：                 |CR4：复数单精度浮点（complex real*4）； CI2：复数短整型（complex int*2），也叫复短整型，与典型的 SLC 原始格式一致。

---

## 🌗 interfero 干涉图生成模块
| 参数名            | 说明                                         | 值 |
|------------------|-------------------------------------|-----------------|
| INT_OUT_CINT      | 输出干涉图（复数干涉图）文件名 |如 interfero.raw
| INT_MULTILOOK     | 多视处理因子（格式："方位向 距离向"）         | 多视因子，如果没有预期的多视，把这个设定为“1 1”。

---


## 🗺 dem 数字高程模型 DEM 参数

| 参数名             | 说明                                      | 值|
|------------------|-------------------------------------|-----------------|
| CRD_IN_DEM          | 输入 DEM 文件路径                         |
| CRD_IN_FORMAT       | DEM 数据格式（如：r4）                    |r4：real4：32-bit 浮点（常见于 SRTM .float）；r8：real8：64-bit 双精度浮点
| CRD_IN_SIZE         | DEM 行列数（格式："行 列"）              | 
| CRD_IN_DELTA        | DEM 分辨率（格式："纬度间隔 经度间隔"）  | SRTM 的是 0.000277777777778 0.000277777777778
| CRD_IN_UL           | DEM 左上角坐标（格式："纬度 经度"）      | 格式：纬度（范围 -90 到 +90），经度（范围 -180 到 +180）
| CRD_IN_NODATA       | DEM 中的无效值标记                        | 就是 Doris 会把所有等于这个值的高程点忽略掉，不参与计算
| CRD_OUT_FILE        | DEM 输出文件路径（如 /dev/null 表示不输出） |
| CRD_OUT_DEM_LP      | 输出的雷达坐标下 DEM 文件名               |

---

✳️ 更多模块参数将在后续版本中添加。
✳️ 同时可参考 doris 技术手册。