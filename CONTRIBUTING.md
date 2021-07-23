# teresa 开发守则

首先，如果你看到了这个页面，恭喜你，希望你即将可以成为 `teresa` 的开发者！但是，在开始之前，请认真阅读这个文档，以确保你的开发之路一切顺利！

## 安装与配置

首先，你需要完成 `README.md` 中关于安装的部分。除此之外，你还需要以下步骤：

安装测试依赖包，并进行一次完整的单元测试：

```bash
pip install -e $HOME/teresa[test]
python3 -m pytest tests
```

当你向 `teresa` 贡献代码时，请参考以下步骤：

```bash
git checkout develop  # start from develop branch
git checkout -b FRINGE-XX_new_feature_here  # checkout new branch, new branch name must correspond to a jira ticket number
```

当你添加了新的代码后，记得 commit。记得使用有意义的、含义明确的 commit message！

```bash
git add *
git commit -m "Your commit message"
```

然后把你的 branch 推到 git：

```bash
git push --set-upstream origin FRINGE-XX_new_feature_here  # push to upstream
```

## 开发规范

为了避免不必要的返工和无效的工作，请**认！真！阅！读！** [ git 开发规范](https://everest.terraqt.ink/pages/viewpage.action?pageId=43746032) 和[ python 代码开发规范](https://everest.terraqt.ink/pages/viewpage.action?pageId=31242919)。