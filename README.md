# 电池容量退化分析

杨晓真 · 25121619

## 当前步骤

- `src/01_read_and_clean.py`：数据读取与清洗。
- `src/02_visualize_degradation.py`：退化曲线与个体差异。
- `src/03_features_and_models.py`：历史特征、上一循环基线、线性回归与岭回归的单步容量预测。
- `docs/第三步_特征与建模.md`：建模口径、时间划分、评估结果及版本记录。
- `deliverables/题目三_工作过程.pptx`：34页过程PPT，记录读取清洗、退化分析、单步与多步建模、组员评估、统计跳变对照、普通回归与随机森林比较及Git版本。

## 运行

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/01_read_and_clean.py
python src/02_visualize_degradation.py
python src/03_features_and_models.py
python -m unittest discover -s tests -v
```

输入为 `data/battery.csv`。第二步和第三步均读取第一步清洗结果，第三步不依赖第二步输出。运行结果分别进入results/step01、step02、step03；图表进入figures对应步骤。图表默认使用Arial Unicode MS，其他系统需配置中文字体。

第三步按每块电池时间先后划分60%/20%/20%，历史窗口不含目标容量，岭回归只用验证段选参，测试前在前80%重拟合。测试是逐次获得历史实测容量后的单步预测，不能解释为固定起点多步预测或剩余寿命。

三种方法中，本次测试的上一循环基线误差最低。结果按真实计算保留，不因为复杂模型没有胜出而修改测试集。

## Git留痕

每新增算法或调整算法方案，运行相应检查后单独提交并推送；不改写或压缩历史。当前仓库保留用户确认的前两份代码和PPT，加上本轮新建的特征建模代码、测试、结果及说明；此前清除的旧材料不恢复。


## 第四步 评估与不确定性初步分析

- `src/04_evaluation_and_uncertainty.py`：读取01和03的结果，分析容量高估与低估、核对80%研究阈值事件覆盖，并进行固定起点线性寿命外推的历史长度敏感性实验。
- 新增滚动预警回测：从第30次起用已知历史预测未来5次内首次跨阈值，比较容量保持基线和最近20次线性趋势；提前量须在有效预测范围内，未知标签不计作负样本。
- 运行：`python src/04_evaluation_and_uncertainty.py`；结果在`results/step04`，四张图在`figures/step04`。
- 说明见`docs/第四步_评估与不确定性.md`；阶段Word报告及27页过程PPT已纳入该步的评估与风险说明。
- 四块电池首次跨80%阈值均早于第三步测试段，当前测试不能验证首次事件的提前预警；外推敏感性不是置信区间，80%不是设备通用更换标准。
- 加强每电池三种模型的完整性检查；修正单步误报被计为提前预警的问题。新增回测属于同四块电池上的探索性分析，重叠窗口不作为独立样本。
- 复查：`python -m unittest discover -s tests -v`。本轮24项检查通过。

## 补充清洗：统计跳变

`src/01b_check_capacity_jumps.py` 在第一步之后运行，用训练段变化量的1.5IQR/3IQR规则标记跳变，对极端点另生成限幅对照。详见 `docs/补充清洗_统计跳变与限幅对照.md`。当前识别58条待核查观测，其中30条进入处理对照；它们不是已证实的测量错误。原始数据及现有模型输入保持不变。

## 阶段报告与第五步

`deliverables/数据分析报告_杨晓真_25121619.docx` 为六页阶段报告，整合前四步的数据检查、差异、跳变对照、已有预测及预警风险。生成入口为 `tools/build_data_report.py`，文档依赖另列于 `tools/requirements-report.txt`，分析环境不必安装。

新一轮运行 `python src/05_multihorizon_models.py`，比较提前1、5、10次的容量保持、最近20次线性趋势和直接多步岭回归。详见 `docs/第五步_多步容量建模.md`，结果在results/step05，图表在figures/step05。主比较统一预测起点，模型拟合所用标签不得晚于预测起点，参数只由验证段选择。36项检查通过。第三步模型结果保持不变。

## 两轮建模与预测报告

`deliverables/两轮建模与预测报告_杨晓真_25121619.docx` 为10页专题报告，汇总第三步单步预测与第五步提前1、5、10次预测，包含特征定义、时间划分、岭回归选参、逐电池误差、8张实测与预测曲线和固定起点实例。两次实验的测试口径分别说明，不直接混比误差。报告保留预测失败案例，不将容量预测等同于剩余寿命预测。

运行 `python tools/plot_model_report.py` 从保存的预测表重绘图表，并独立重算核对第一轮24组与第二轮144组指标；核对记录和输入哈希在 `results/model_report/source_verification.json`，图表在 `figures/model_report`。安装文档依赖后运行 `python tools/build_model_report.py` 生成Word。此报告仅整理已有结果，没有修改模型、参数或测试数据。

## 新一轮普通回归与随机森林比较

为区分预测距离和算法，本轮固定预测下一次容量。`src/06_linear_regression.py` 使用普通最小二乘多元线性回归，`src/07_random_forest.py` 使用300棵树的随机森林。两者使用相同4个特征、相同时间划分、相同129个测试目标。森林仅根据验证段选择6种树深/叶大小组合，完整保存24条搜索结果。训练加验证重拟合后，测试估计器固定，逐次获得此前真实历史。

```sh
python src/06_linear_regression.py
python src/07_random_forest.py
python src/08_compare_regression_and_forest.py
python -m unittest discover -s tests -v
```

各模型分别保存在results/step06和step07，比较结果与核对记录在results/step08，6张图在figures/step08。普通回归、森林的独立Git版本分别为`a1a2940`、`8e4d38e`，均已推送。44项检查通过，24组指标独立重算一致。四电池等权平均测试RMSE为基线0.014425、回归0.017370、森林0.058766 Ah。直接容量森林在前三块电池后期持续高估，报告保留该失败结果，不在测试集上追加调参。

新报告为`deliverables/普通线性回归与随机森林预测报告_杨晓真_25121619.docx`，10页，解释提前距离、两类算法的原理和公平比较，并展示参数、完整误差、四块电池曲线与散点。生成入口`tools/build_regression_forest_report.py`，PPT第28至34页记录本轮过程。具体方案见`docs/第六七步_两类模型实验方案.md`。本轮是同四块已查看电池上的追加方法比较，不视为新电池外部验证。
