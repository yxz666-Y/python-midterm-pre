# 无人设备电池健康评估与剩余寿命预测

Python数据分析编程题目三。已知成员：杨晓真，25121619。

## 运行分析

需要Python 3.12，建议创建虚拟环境：

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/analyze.py
python src/verify_results.py
```

输入是课程提供的636行容量CSV，保存在data/battery.csv。运行生成results中的逐点预测、各电池指标、经验误差带、寿命外推结果与figures中的四张图。算法是确定性的，没有随机打乱。

## 方法与结果

按每块电池前60%训练、中间20%验证、最后20%测试。比较上一循环基线、循环线性回归、历史特征岭回归。每次预测下一循环，允许使用前次真实观测。基线在四块电池测试RMSE上均最低。寿命实验单独使用前30%拟合趋势，以80%首循环容量作为研究阈值，不使用未来真实值拟合。

## 交付文件

- deliverables/题目三_项目报告.docx：按课程模板章节组织的报告。
- deliverables/*.pptx：8页可编辑PPT，图表含数据。
- deliverables/五分钟汇报讲稿.md 与 答辩准备.md。

## 提交前必须补充

组号、组长、学院、专业、其他两位成员姓名/学号、每人的真实分工及个人说明。PPT当前文件名明确保留待填项，确认后按“组号_3_组长姓名”命名。按用户最新要求，本项目不制作视频；课程文件中的视频要求仍需小组自行安排。不能把AI生成记录说成三位成员独立完成的提交。

PPT与视频在2026-10-31以前交学习通；报告2026-11-08晚12点前交Word电子版，另交纸质版至未来技术学院418。学习通上传、纸质打印和现场问答由小组完成。

## 文件生成与环境

报告构建脚本为src/build_report.py，依赖python-docx与模板references/项目报告模版.docx。运行前先生成分析图表。演示构建脚本使用Codex提供的@oai/artifact-tool运行环境，非分析必需依赖。图表字体使用macOS Arial Unicode MS，其他系统请安装中文字体并修改字体设置。

## 版本管理

仓库：https://github.com/yxz666-Y/python-midterm-pre
保留每次真实提交，不压缩或强制覆盖已有历史。仅把源码、输入、最终成果和结果数据入库，虚拟环境与渲染临时文件不入库。

本机PPT重建：设置RUNTIME_NODE_MODULES为Codex工作区依赖加载器返回的Node包目录，使用其Node运行src/build_slides.mjs。最终输出文件存在时，先将其移到工作副本或改用新的输出文件名，校验器不会覆盖已有文件。报告渲染所需的中文fontconfig配置只影响本机预览，不改变DOCX内容。

用户已取消视频制作。当前版本移除视频及生成脚本，既有Git提交历史保留。
