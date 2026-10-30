# 电池容量退化分析与预测

杨晓真 · 学号25121619

当前项目只保留两种主要模型：普通最小二乘线性回归与随机森林回归。容量保持仅作为比较基线，不列为第三种主要模型。

## 数据与清洗

- `data/battery.csv`：原始数据，4块电池共636条循环记录。
- `src/01_read_and_clean.py`：字段和类型规范、缺失、重复、正容量与循环连续性检查，输出results/step01。
- `src/01b_check_capacity_jumps.py`：按训练阶段变化量的IQR规则检查统计跳变，并单独生成限幅敏感性对照。识别58条待核查，其中30条进入处理对照，尚未证实为测量错误。模型继续使用原值保留版。
- `src/02_visualize_degradation.py`：容量退化曲线、共同前132次窗口及个体差异，输出results/step02和figures/step02。

## 两种主要模型

- `src/comparison_common.py`：独立提取循环次数、上次容量、此前5次均值及斜率，提供统一评价口径。
- `src/06_linear_regression.py`：普通线性回归，四个相同输入，无正则化、无参数搜索。结果在results/step06。
- `src/07_random_forest.py`：300棵树，固定随机种子25121619，验证段从6种树深与叶大小组合选参。结果与保存模型在results/step07。
- `src/08_compare_regression_and_forest.py`：比较两种模型及容量保持基线，核对逐点预测，结果在results/step08，6张图在figures/step08。
- `docs/普通线性回归与随机森林建模说明.md`：特征、时间划分、参数、误差和解释范围。
- `docs/数据清洗与预处理说明.md`：数据清洗与预处理说明.md的字段、清洗检查顺序、实测结果、跳变标记与产物清单，可作为报告对应章节的内容。

预测第t次容量时，容量特征最多使用第t−1次数据。每块电池按原始循环数量的60%和80%设训练与验证边界，测试前在训练加验证段重新拟合。测试估计器固定，逐次获得真实历史进行下一循环预测。两种模型使用相同129个测试目标，不代表129块独立电池。

四电池等权平均测试RMSE：普通回归0.017370 Ah，随机森林0.058766 Ah，比较基线0.014425 Ah。森林在前三块电池后期高估，不能凭复杂度判断预测效果。完整结果保留，没有按测试误差追加调参。

## 运行

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/01_read_and_clean.py
python src/01b_check_capacity_jumps.py
python src/02_visualize_degradation.py
python src/06_linear_regression.py
python src/07_random_forest.py
python src/08_compare_regression_and_forest.py
python -m unittest discover -s tests -v
```

当前共37项检查通过（数据清洗7项、跳变对照3项、回归5项、森林4项、第九步18项），24组指标独立重算一致。图表默认使用Arial Unicode MS，其他系统需配置中文字体。两个模型的数字文件名保留，运行顺序以上述清单为准。若GitHub连接受限可直接用 GitHub Desktop（它会读取系统代理），或临时指定代理：`git -c http.proxy=http://127.0.0.1:代理端口 push origin main`（不改变本机 git 配置）。

## 当前交付材料

- `deliverables/普通线性回归与随机森林预测报告_杨晓真_25121619.docx`：当前两种主要模型的报告。
- `deliverables/题目三_工作过程.pptx`：24页，记录数据读取清洗、统计跳变、退化差异、特征与时间划分、两种主要模型的过程与结果，以及第22至24页的误差高估风险、提前预警与寿命外推不确定性、使用维护与更换建议。
- `tools/build_regression_forest_report.py`：报告生成脚本，文档依赖在tools/requirements-report.txt。
- `tools/append_ppt_pages.py`：在过程PPT末尾追加第22至24页，`python tools/append_ppt_pages.py`；重复运行会因页面已存在而停止，不会重复追加。文档依赖同样在tools/requirements-report.txt。
- `tools/build_slides.py`：生成精炼汇报版`deliverables/题目三_汇报.pptx`（13页，覆盖题目三四项基本任务），`python tools/build_slides.py`。

## Git版本管理

每次新增算法或调整方案单独提交并推送。普通回归、随机森林原始算法提交分别为a1a2940、8e4d38e。当前分支按用户确认的方法清理，用删除提交保留版本留痕，不重写历史。项目结果仅适用于这四块、24℃、一次时间划分下的容量预测，不能直接解释为已验证的剩余寿命或真实飞行时长。


## 第九步 新版评估与不确定性

在01、06、07、08完成后运行 `python src/09_evaluation_and_uncertainty.py`。读取新版统一预测，补充两种主要模型及基线的偏差、高估风险、80%研究阈值覆盖核查；另保留滚动预警和寿命趋势外推作为辅助诊断，不将其当成普通回归或随机森林已验证的多步预测。

结果在results/step09，四张图在figures/step09，章节说明见 `docs/第九步_新版评估与不确定性.md`。本步骤新增18项检查通过；原模型、报告与PPT保持原状。阈值不是通用更换标准，外推敏感性不是置信区间，滚动窗口不是独立样本。
