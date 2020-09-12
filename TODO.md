# 施工进度

## 整体安排

### 文件树

- `mushroom` : 核心 python 包, 定义工作流和脚本中可能用到的对象.
- `workflows` : 储存应对特定任务的 shell 或 python 工作流脚本和样本输入文件.
- `scripts` : 利用 `mushroom` 中定义的对象来实现的完成多种研究目的的脚本, 也包含拷贝 `workflows` 中脚本的 convenience function 和 helper function.
- `doc` : mushroom 使用与开发文档
- `examples` : 除了 mushroom 包的使用样例外, 也包含一些小技巧.

### 测试文件

每个子 package 的测试文件放置在该 package 下的 `test` 文件夹内. 使用 pytest 和 unittest 框架.

## Python 库

原则是尽可能减少子 package 的数量. 主要的考虑因素不是模块的长度, 而是模块的集成度和自洽度.

