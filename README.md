# 电池容量退化分析

杨晓真 · 25121619

当前仅保留两份分析代码、新版工作过程PPT，以及运行必需的原始CSV和依赖说明。

- `src/01_read_and_clean.py`：数据读取与清洗。
- `src/02_visualize_degradation.py`：退化曲线与电池个体差异分析。
- `deliverables/题目三_工作过程_读取清洗与退化分析.pptx`：当前10页过程PPT。
- `data/battery.csv`：两步分析使用的课程原始数据。

## 运行顺序

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/01_read_and_clean.py
python src/02_visualize_degradation.py
```

运行后自动创建 `results/step01/`、`results/step02/` 和 `figures/step02/`；第二步使用第一步生成的清洗数据。绘图使用Arial Unicode MS中文字体，其他系统需配置可用中文字体。

旧报告、旧PPT、其他脚本、讲稿、参考文件副本和已有图表/结果均已从当前版本清除。Git提交历史保留，清理操作也会推送GitHub留痕。
