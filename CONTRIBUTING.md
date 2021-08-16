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
git pull --all # 更新 develop branch！（你也可以从 main 来 checkout，记得也要先 pull）
git checkout -b FRINGE-XX_new_feature_here  # checkout new branch, new branch name must correspond to a jira ticket number
```

当你添加了新的代码后，记得 commit。记得使用有意义的、含义明确的 commit message！

```bash
git add *
git commit -m "FRINGE-XX Your commit message"  # 记得在 commit message 前加 ticket ID
```

然后把你的 branch 推到 git：

```bash
git push --set-upstream origin FRINGE-XX_new_feature_here  # push to upstream
```

## 解决冲突策略（Merge Conflicts）

我们解决 merge conflict 的策略大体是：每个人需要在提交 merge request 时，自行解决所有的 merge conflict。`main` 和 `develop` 分支的管理员不负责解决其他分支的 merge conflict。为了尽可能地避免冲突，推荐采用 rebase 策略，即：

```bash
git checkout develop  # 重新切回到 develop 或 main 分支
git pull --all  # 更新该分支
git checkout FRINGE-XX_new_feature_here  # 切回你需要做 MR 的分支
git rebase develop  # rebase，如果过程中有 merge conflict 则需自行解决
# 解决 rebase 过程中遇到的 merge conflict
git push --force-with-lease origin FRINGE-XX_new_feature_here  # 重新 push 你 rebase 后的分支
# 此时再提交 MR，就不会有 merge conflicts 了。
```

## 开发规范

为了避免不必要的返工和无效的工作，请**认！真！阅！读！** [ git 开发规范](https://everest.terraqt.ink/pages/viewpage.action?pageId=43746032) 和[ python 代码开发规范](https://everest.terraqt.ink/pages/viewpage.action?pageId=31242919)。
