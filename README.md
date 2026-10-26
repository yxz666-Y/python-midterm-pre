# 无人设备电池健康评估与剩余寿命预测

Python数据分析编程题目三。杨晓真，25121619。

## 当前进度：按步骤重新开展

本轮只完成数据读取、清洗、退化曲线和个体差异分析；后续再开展特征提取、至少两种模型的比较与不确定性评估。不制作视频。

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/01_read_and_clean.py
python src/02_visualize_degradation.py
```

1. `src/01_read_and_clean.py`：检查字段、缺失、重复、主键冲突、数值有效性与循环连续性，排序并保存清洗结果。636条记录全部保留，不修改原始CSV。
2. `src/02_visualize_degradation.py`：绘制全部容量曲线，统一前132次循环比较相对首循环容量，导出统计表与PPT数据。
3. `figures/step02/`：三张当前分析图。
4. `results/step01/`、`results/step02/`：当前分析的可复查数据。
5. `deliverables/题目三_工作过程_读取清洗与退化分析.pptx`：从读取、清洗到可视化的10页工作过程记录，图表可编辑。

前132次容量下降：B0005 26.49%，B0006 35.36%，B0007 21.90%，B0018 27.70%。首循环归一化用于描述个体差异，不等于制造商额定容量口径的SOH，也不是剩余寿命预测。B0018只有132次记录，不把观测结束当作失效。

## 历史材料与版本

按用户要求，旧报告和旧PPT已从当前版本删除，原始报告模板仍保留。旧的 `src/analyze.py`、`src/build_report.py`、`src/build_slides.mjs`、根层 results/figures 与原讲稿、答辩材料属于此前版本，不代表本次逐步工作进度；当前入口仅为以上01、02脚本及过程PPT。不要运行旧构建脚本生成交付件。

仓库：https://github.com/yxz666-Y/python-midterm-pre

每个阶段进行真实Git提交并推送，保留既有历史，不压缩或强制覆盖。后续学习通提交、组员实际分工和组号等信息仍需补充；本过程稿不是全项目最终提交稿。

## PPT重建

使用Codex工作区依赖加载器返回的Node与Node包目录：设置 `RUNTIME_NODE_MODULES`，运行 `src/build_process_slides.mjs`。该脚本使用 `@oai/artifact-tool` 并做文件结构及布局检查。`PRESENTATIONS_SKILL` 可指定演示文稿技能目录。已有输出需移到临时目录后重建，校验器不会覆盖已有交付文件。分析绘图默认使用macOS Arial Unicode MS；其他系统请配置中文字体。
