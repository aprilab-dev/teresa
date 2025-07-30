<p align="center">
  <img width="256" src="logo.png" alt="teresa">
</p>

# TERESA 是什么？
`TERESA（Terrain Registration and Sampling Software）`是由西北工业大学电子信息学院 APRILAB(Automated Phase Reconstruction and Interferometry Lab) 小组开发的一款面向国产卫星的 SAR 图像批量配准工具。该工具以欧洲开发的 SAR 处理软件 DORIS 为基础，进行了深入的定制与优化，专门针对中国国产合成孔径雷达（SAR）卫星数据的特点进行适配与增强。

当前版本的 Teresa 已成功支持包括 Lutan-1、涪城一号系列等国产主力 SAR 卫星的图像数据处理的自动化批处理，能够在保持高精度配准效果的同时，大幅提升处理效率与稳定性。工具支持自动化批量处理流程，适用于大规模干涉图生成、地表形变监测和相关 InSAR 应用。

未来版本将持续扩展更多国产SAR平台的兼容性，并进一步集成智能配准算法与并行加速框架，服务于国产遥感数据处理的自主可控与工程化落地。

------------------------------------------------------------

📦 安装方式
---------


克隆项目并安装依赖（conda 环境下）

    git clone https://github.com/aprilab-dev/teresa.git
    conda env create -f environment.yml 

pyproject.toml 安装

    git clone https://github.com/aprilab-dev/teresa.git
    cd teresa

    # 推荐使用虚拟环境
    conda env create -f environment.yml 
    conda activate teresa

    # 使用 PEP 517 标准安装
    pip install -e .


------------------------------------------------------------

🚀 快速开始
---------
编译得到 doris 的可执行文件，具体参考：

    https://github.com/aprilab-dev/doris.git

向 teresa 配置 doris 可执行文件：

    向 dorisProcessor 类， self._doris 函数中的 _DORIS 变量中，配置本地的 doris 可执行文件的路径

通过导入配置文件运行：

    python main.py templates/doris.parms

通过 pyproject.toml 安装后，在终端使用运行：

    teresa --parms_path templates/doris.parms

------------------------------------------------------------

⚙️ 配置文件 doris.params 参数说明
----------

    详见：/templates/README.md

------------------------------------------------------------

📁 项目结构
----------

    teresa/
    ├── templates/        参数文件目录
    ├── teresa/           配准逻辑实现
        ├── coregistion/  配置逻辑所在
        ├── dump/         不同的国产卫星数据导入模块
        ├── processor/    实现配准各个步骤
        ├── slcStack/     存放关于 slc 的相关数据
        ├── utils/        工具函数
        ├── cli.py        命令行功能相关
    ├── setup.py          命令行功能相关
    ├── main.py           主程序入口
    └── README.md         项目说明文档

------------------------------------------------------------

🧪 得到的工作路径示例
----------

    workspace/
    ├── yyyymmdd/     存放原 slc 数据 和 meta 文件软连接、配准后的数据、
    ├── yyyymmdd/     以及中间生成的 log 文件
    ├── dem/          存放 dem 相关的中文文件和结果
    ├── dorisin/      存放依赖的 dorisin 文件
    └── master/       存放主影像的软连接和相关数据

------------------------------------------------------------

👥 开发团队
----------

APRILab  
Automated Phase Reconstruction and Interferometry Lab 
西北工业大学 电子信息学院   
联系邮箱：yuxiao.qin@nwpu.edu.cn  
团队主页：[APRILab](https://github.com/aprilab-dev)

------------------------------------------------------------

📜 许可证
--------

本项目采用 GNU 开源。详见 LICENSE 文件。

------------------------------------------------------------

🧭 贡献指南
---------

欢迎任何形式的贡献，包括 issue、代码提交（PR）或文档补充。  

------------------------------------------------------------