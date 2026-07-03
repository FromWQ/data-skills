#!/usr/bin/env python3
"""
检查结果查看脚本
功能：读取 code_check_result.xlsx 文件，展示检查结果摘要
"""

import pandas as pd
from pathlib import Path

base_dir = Path(__file__).parent.parent
excel_path = base_dir / "output/code_check_result.xlsx"

if not excel_path.exists():
    print(f"检查结果文件不存在：{excel_path}")
    print("请先运行 code_checker.py 生成检查结果")
    exit(1)

# 读取 Excel 文件
xlsx = pd.ExcelFile(excel_path)

print("=" * 60)
print("代码检查结果摘要")
print("=" * 60)

# 读取各工作表
summary_df = pd.read_excel(xlsx, sheet_name='检查结果汇总')
score_df = pd.read_excel(xlsx, sheet_name='代码评分表')
layer_df = pd.read_excel(xlsx, sheet_name='分层统计表')
issue_df = pd.read_excel(xlsx, sheet_name='问题明细表')

# 汇总统计
print("\n【分层统计】")
print(layer_df.to_string(index=False))

print("\n【评分统计】")
print(f"  总代码数：{len(score_df)}")
print(f"  平均分：{score_df['最终得分'].mean():.2f}")
print(f"  最高分：{score_df['最终得分'].max()}")
print(f"  最低分：{score_df['最终得分'].min()}")

print("\n【问题汇总】")
print(f"  BLOCK 级问题：{issue_df[issue_df['严重程度'] == 'BLOCK'].shape[0]} 个")
print(f"  WARN 级问题：{issue_df[issue_df['严重程度'] == 'WARN'].shape[0]} 个")
print(f"  INFO 级问题：{issue_df[issue_df['严重程度'] == 'INFO'].shape[0]} 个")

print("\n【TOP 5 问题代码】")
top5 = score_df.nsmallest(5, '最终得分')[['任务名称', '所属分层', '最终得分', 'BLOCK 问题数', 'WARN 问题数']]
print(top5.to_string(index=False))

print("\n" + "=" * 60)
