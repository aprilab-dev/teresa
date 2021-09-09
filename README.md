## TERESA 是什么？

`[Te]rraquanta's software for [Re]gistration and [Sa]mpling` 是一个用来做 SAR 的 SLC 的配准与重采样的服务（[什么是配准与重采样？](https://www.mdpi.com/2072-4292/10/9/1405/htm)）。更多的信息可以在 [everest 页面](https://everest.terraqt.ink/display/DEV/teresa)上找到。

`teresa` 可以实现对影像栈（a stack of SAR SLC images）的批量配准。目前 `teresa` 配准的实现方式是一个基于 `gpt`（[什么是 gpt？](http://step.esa.int/docs/tutorials/command_line_inSAR_processing.pdf)） 的 wrapper。

## 安装

目前 `teresa` 依然在开发中，所以还没有发布在大地量子的 pypi 平台上。目前的安装步骤如下:

### 1. 下载

```bash
git clone git@git.terraqt.io:arcticwind/seafringe/teresa.git $HOME/teresa
```

### 2. 安装依赖

我们推荐在安装时使用虚拟环境（[什么是虚拟环境？](https://realpython.com/python-virtual-environments-a-primer/)）。如果你熟悉虚拟环境的创建，可以使用任意你喜欢的虚拟环境创建方法。如果你没有什么所谓，我们推荐使用 python 自带的 `venv`。  

首先，请确认你已经安装了 `python3 >= 3.6`，且 python 在你的系统路径中：

```bash
which python3
```

接下来我们创建虚拟环境：

```bash
python3 -m venv $HOME/.venv/teresa
source $HOME/.venv/teresa/bin/activate
```

最后我们在虚拟环境中安装依赖包：

```bash
pip install --upgrade pip
pip install -e $HOME/teresa
```

现在你就可以使用 `teresa` 了。`teresa/example.py` 中有一个 work in progress (WIP) 的例子。

## 示例

鉴于 `teresa` 依然是一个开发中的产品，所以还没有例子可以展示。`teresa` 的开发进度可以参考[这里](https://everest.terraqt.ink/pages/viewpage.action?pageId=43746233)。

## 设置

因为 `teresa` 是一个关于 `gpt` 的 wrapper，所以我们需要设置 `gpt` 的路径。*部分*默认的 `gpt` 已经设置在了系统环境变量 `SNAP_GPT_EXECUTABLE` 中，你可以用以下方法查看：

```bash
>>> echo $SNAP_GPT_EXECUTABLE
/opt/snap/bin/gpt
```

如果你想要使用另一个版本的 `gpt`，或者你自己的服务器上没有设置 `SNAP_GPT_EXECUTABLE`， 你也可以在自己的 `.bashrc` 文件中设置 `SNAP_GPT_EXECUTABLE`，例如：

```bash
# .bashrc
>>> SNAP_GPT_EXECUTABLE="/your/own/path/of/gpt"
```

然后运行 `source .bashrc` 命令激活该环境变量。
