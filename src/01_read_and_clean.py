from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_DIR / "data" / "battery.csv"
OUTPUT_DIR = PROJECT_DIR / "results" / "step01"

df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
print("前5行：")
print(df.head())
print("\n原始数据的行数和列数：", df.shape)
print("\n原始数据类型：")
print(df.dtypes)

expected_columns = ["battery_id", "cycle", "capacity_Ah", "ambient_temp_C"]
if list(df.columns) != expected_columns:
    raise ValueError("CSV列名或顺序与题目数据不一致，请先核对文件。")

df["battery_id"] = df["battery_id"].astype("string").str.strip()
df["battery_id"] = df["battery_id"].replace("", pd.NA)
for column in ["cycle", "capacity_Ah", "ambient_temp_C"]:
    df[column] = pd.to_numeric(df[column], errors="coerce")

print("\n各列缺失值数量（包含数值转换失败）：")
print(df.isna().sum())
if df.isna().any().any():
    raise ValueError("发现缺失或无法解析的数据，请核查原始记录。")

print("\n完全重复行数：", int(df.duplicated().sum()))
df = df.drop_duplicates().copy()

if df.duplicated(subset=["battery_id", "cycle"]).any():
    raise ValueError("同一电池、同一循环存在不同记录，请核查冲突。")

numeric_columns = ["cycle", "capacity_Ah", "ambient_temp_C"]
if not np.isfinite(df[numeric_columns].to_numpy()).all():
    raise ValueError("数值列含无穷值。")
if ((df["cycle"] <= 0) | (df["cycle"] % 1 != 0)).any():
    raise ValueError("循环次数必须是正整数。")
if (df["capacity_Ah"] <= 0).any():
    raise ValueError("容量必须大于0，请核对异常记录。")
df["cycle"] = df["cycle"].astype(int)

df = df.sort_values(["battery_id", "cycle"]).reset_index(drop=True)
for battery_id, group in df.groupby("battery_id"):
    cycles = group["cycle"].tolist()
    expected_cycles = list(range(1, max(cycles) + 1))
    if cycles != expected_cycles:
        raise ValueError(f"{battery_id}的循环编号不是从1开始的连续序列。")

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

capacity_change = df.groupby("battery_id")["capacity_Ah"].diff()
summary["rebound_count"] = (
    capacity_change.gt(0).groupby(df["battery_id"]).sum()
)
print("\n分电池汇总：")
print(summary.round(4).to_string())
print("\n环境温度取值：", sorted(df["ambient_temp_C"].unique()))
print("\n整理后的行数和列数：", df.shape)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_DIR / "battery_clean.csv", index=False, encoding="utf-8-sig")
summary.to_csv(OUTPUT_DIR / "battery_summary.csv", encoding="utf-8-sig")
print("\n输出目录：", OUTPUT_DIR)
