# 施工进度与挖坑

## 整体安排

### 文件树

- `mushroom` : 核心 python 包, 定义工作流和脚本中可能用到的对象.
- `scripts` : 利用 `mushroom` 中定义的对象来实现的完成多种研究目的的脚本, 也包含拷贝 `workflows` 中脚本的 convenience function 和 helper function.
- `doc` : mushroom 使用与开发文档
- `examples` : 除了 mushroom 包的使用样例外, 也包含一些小技巧和原型
- `db` : 数据库

### 单元测试

对于 Python 库, 每个子 package 的测试文件放置在该 package 下的 `test` 文件夹内. 使用 pytest 和 unittest 框架.
对于 workflow 中的 Bash 脚本, 暂不考虑做测试. 今后视情况用 bats 进行测试.

## Python 库 mushroom

原则是尽可能减少子 package 的数量. 主要的考虑因素不是模块的长度, 而是模块的功能一致, 集成度和自洽.

### 核心库 `core`

- band structure analysis `bs`
  - [x] `BandStructure` object
- density of states analysis `dos`
  - [x] `DensityOfStates` object
- io helper functions `ioutils`

### 数据库管理模块 `db`

### Wannier90 `w90`

### VASP `vasp`

- [x] DOSCAR reader
- [x] POSCAR reader/exporter (alias to `Cell.read_vasp`)
- [x] PROCAR reader
- [x] EIGENVAL reader
- [ ] KPOINTS reader/exporter
- [ ] LOCPOT reader
- [ ] POTCAR searcher
- [ ] WAVECAR reader
- [x] CHGCAR reader

XML reader for

- [x] kpoint list
- [ ] geometry at specific ion step 

### ABINIT `abi`

- [ ] 确认最佳的 abinit 输入 practice
- [ ] 设计 workflow 构成

### WIEN2k `w2k`

- [x] energy reader
  - [ ] Extracting fermi energy is not working correctly. A value lower than VBM can be obtained.
- [x] struct reader
- [ ] output2 reader
- [ ] output1 reader
- [ ] in1 reader
- [ ] calculators of relativistic potential

### GPAW `gpaw`

### 爬虫相关

#### SpringerMaterials

`Cif` 类在读取 SpringerMaterials, ICSD 上下载的部分 cif 文件时报错. 包括

- [x] Cu2O 52043

#### MaterialsProject

Require `pymatgen`

## Visualization

### XmGrace `graceplot`

- [x] base classes to manipulate attributes of elementary objects and options
- [x] Graph object for data plotting
- [x] Plot object for export
- [ ] Extensions like those in PyGrace, e.g. colorbar, matrix plot

### Gaussian Cube

- [x] Gaussian cube format <http://paulbourke.net/dataformats/cube/>

## 数据库 db

### 晶体结构 cell

### 特殊点路径 kpath

- [ ] 参考 SetayawanW10-AFLOW, 更好地对路径进行分类
- [ ] 数据库对象 `DBKPath` 的处理输入结构对称性的方法

### 工作流 workflows

#### VASP

一般局域泛函

- [x] Band and DOS
- [ ] 截断和 kmesh 收敛测试

杂化泛函

- [x] 截断和 kmesh 收敛测试
- [ ] SCF 和 DOS
- [x] Band

GW

- [ ] 正常三步计算
- [x] 波函数截断 `ENCUT`, 介电矩阵截断 `ENCUTGW`, 能带数 `NBANDS` 收敛
- [ ] `NOMEGA` 收敛测试

结构优化

- [ ] 表面能随 slab 层数和固定层数的收敛

#### ABINIT

#### WIEN2k

#### GPAW

