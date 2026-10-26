"""第一步：读取、检查并整理电池数据，不训练预测模型。

在项目根目录运行：python src/01_read_and_clean.py
原始文件始终保留；整理后的数据另存到 results/step01/。
"""
from pathlib import Path

import numpy as np
import pandas as pd

# 1. 找到原始数据。路径相对于本脚本所在项目，不依赖终端当前目录。
PROJECT_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_DIR / "data" / "battery.csv"
OUTPUT_DIR = PROJECT_DIR / "results" / "step01"

# 2. CSV第一行为列名，每一行代表一块电池的一次循环观测。
# DataFrame可以理解为Python中的二维表格。
df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
print("前5行：")
print(df.head())
print("\n原始数据的行数和列数：", df.shape)
print("\n原始数据类型：")
print(df.dtypes)

# 3. 核对字段。字段错误时停止，防止对错误文件继续分析。
expected_columns = ["battery_id", "cycle", "capacity_Ah", "ambient_temp_C"]
if list(df.columns) != expected_columns:
    raise ValueError("CSV列名或顺序与题目数据不一致，请先核对文件。")

# 4. 统一类型。去掉编号首尾空白；无法转成数字的内容记为NaN。
# 空字符串也视为缺失；不把它误当作一个电池编号。
df["battery_id"] = df["battery_id"].astype("string").str.strip()
df["battery_id"] = df["battery_id"].replace("", pd.NA)
for column in ["cycle", "capacity_Ah", "ambient_temp_C"]:
    df[column] = pd.to_numeric(df[column], errors="coerce")

# 5. 检查缺失。当前数据没有缺失，所以不需要填充或删行。
# 如果以后换数据出现缺失，先停止并核查原因，而不是随意填0。
print("\n各列缺失值数量（包含数值转换失败）：")
print(df.isna().sum())
if df.isna().any().any():
    raise ValueError("发现缺失或无法解析的数据，请核查原始记录。")

# 6. 去除完全相同的重复行。当前文件重复数为0，不会删掉任何行。
print("\n完全重复行数：", int(df.duplicated().sum()))
df = df.drop_duplicates().copy()

# 同一块电池的同一次循环不应有两条不同的记录。
# 这种冲突不能靠随意保留第一条解决，所以单独检查并停止。
if df.duplicated(subset=["battery_id", "cycle"]).any():
    raise ValueError("同一电池、同一循环存在不同记录，请核查冲突。")

# 7. 检查数值的基本合理性。不能把无穷值或小数循环编号当作有效数据。
numeric_columns = ["cycle", "capacity_Ah", "ambient_temp_C"]
if not np.isfinite(df[numeric_columns].to_numpy()).all():
    raise ValueError("数值列含无穷值。")
if ((df["cycle"] <= 0) | (df["cycle"] % 1 != 0)).any():
    raise ValueError("循环次数必须是正整数。")
if (df["capacity_Ah"] <= 0).any():
    raise ValueError("容量必须大于0，请核对异常记录。")
df["cycle"] = df["cycle"].astype(int)

# 8. 按电池和循环排序，重新编号表格行索引；不改变cycle字段的取值。
df = df.sort_values(["battery_id", "cycle"]).reset_index(drop=True)
for battery_id, group in df.groupby("battery_id"):
    cycles = group["cycle"].tolist()
    expected_cycles = list(range(1, max(cycles) + 1))
    if cycles != expected_cycles:
        raise ValueError(f"{battery_id}的循环编号不是从1开始的连续序列。")

# 9. 初步分析：每块电池有多少次循环，容量范围和首末容量是多少。
summary = df.groupby("battery_id").agg(
    records=("cycle", "size"),
    first_capacity_Ah=("capacity_Ah", "first"),
    last_capacity_Ah=("capacity_Ah", "last"),
    min_capacity_Ah=("capacity_Ah", "min"),
    max_capacity_Ah=("capacity_Ah", "max"),
)
summary["capacity_loss_pct"] = (
    1 - summary["last_capacity_Ah"] / summary["first_capacity_Ah"]
) * 100

# 分电池计算相邻容量差值。正差值表示局部回升，不直接认定为错误。
capacity_change = df.groupby("battery_id")["capacity_Ah"].diff()
summary["rebound_count"] = (
    capacity_change.gt(0).groupby(df["battery_id"]).sum()
)
print("\n分电池汇总：")
print(summary.round(4).to_string())
print("\n环境温度取值：", sorted(df["ambient_temp_C"].unique()))
print("\n整理后的行数和列数：", df.shape)

# 10. 另存文件，绝不覆盖原始数据。index=False避免多写一列行号。
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_DIR / "battery_clean.csv", index=False, encoding="utf-8-sig")
summary.to_csv(OUTPUT_DIR / "battery_summary.csv", encoding="utf-8-sig")
print("\n输出目录：", OUTPUT_DIR)
