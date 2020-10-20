# 施工进度与挖坑

## 整体安排

### 文件树

- `mushroom` : 核心 python 包, 定义工作流和脚本中可能用到的对象.
- `workflows` : 储存应对特定任务的 shell 或 python 工作流脚本和样本输入文件.
- `scripts` : 利用 `mushroom` 中定义的对象来实现的完成多种研究目的的脚本, 也包含拷贝 `workflows` 中脚本的 convenience function 和 helper function.
- `doc` : mushroom 使用与开发文档
- `examples` : 除了 mushroom 包的使用样例外, 也包含一些小技巧.
- `db` : 数据库

### 测试文件

对于 Python 库, 每个子 package 的测试文件放置在该 package 下的 `test` 文件夹内. 使用 pytest 和 unittest 框架.
对于 workflow 中的 Bash 脚本, 暂不考虑做测试. 今后视情况用 bats 进行测试.

## Python 库 mushroom

原则是尽可能减少子 package 的数量. 主要的考虑因素不是模块的长度, 而是模块的功能一致, 集成度和自洽.

### 核心库 `_core`

- [ ] type hints

### VASP

### ABINIT

### WIEN2k

### GPAW

### 爬虫相关

#### SpringerMaterials

- [ ] `Cif` 类在读取 SpringerMaterials 上下载的 cif 文件时报错.

#### MaterialsProject

Require `pymatgen`

## 工作流 workflows

### VASP

#### hybrid functional

- [x] 截断和 kmesh 收敛测试
- [ ] SCF 和 DOS
- [x] 能带

#### GW

- [ ] 正常三步计算
- [x] 波函数截断 `ENCUT`, 介电矩阵截断 `ENCUTGW`, 能带数 `NBANDS` 收敛
- [ ] `NOMEGA` 收敛测试

#### 结构优化

- [ ] 表面能随 slab 层数和固定层数的收敛

### ABINIT

### WIEN2k

### GPAW

## 数据库 db

