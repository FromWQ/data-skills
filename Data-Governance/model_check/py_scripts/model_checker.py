#!/usr/bin/env python3
"""
模型规范检查脚本
功能：
1. 从 input 目录读取 SQL 文件
2. 执行模型规范检查（表命名、字段规范、分区规范、存储规范）
3. 保存结果到 output/model_check_result.xlsx
4. 生成 Markdown 报告 output/model_check_report.md
"""

import os
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
from openpyxl import Workbook


class ModelChecker:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.input_dir = self.base_dir / "input"
        self.output_dir = self.base_dir / "output"

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 检查结果
        self.check_results = []

    def identify_layer(self, table_name):
        """识别表所属的数仓分层"""
        name_lower = table_name.lower()
        if name_lower.startswith('ods_'):
            return 'ODS'
        elif name_lower.startswith('dwd_'):
            return 'DWD'
        elif name_lower.startswith('dws_'):
            return 'DWS'
        elif name_lower.startswith('dim_'):
            return 'DIM'
        elif name_lower.startswith('ads_'):
            return 'ADS'
        else:
            return 'UNKNOWN'

    def check_table_name(self, table_name, sql_text):
        """检查表命名规范"""
        issues = []
        score = 10

        # 检查分层前缀
        layer_prefixes = ['ods_', 'dwd_', 'dws_', 'dim_', 'ads_']
        has_prefix = any(table_name.lower().startswith(p) for p in layer_prefixes)
        if not has_prefix:
            issues.append("表名缺少分层前缀 (ods_/dwd_/dws_/dim_/ads_)")
            score -= 5

        # 检查表名长度
        if len(table_name) > 64:
            issues.append(f"表名长度超过 64 字符 (当前{len(table_name)}字符)")
            score -= 2.5
        elif len(table_name) < 3:
            issues.append("表名长度少于 3 字符")
            score -= 2.5

        # 检查是否使用下划线命名
        if re.search(r'[a-z][A-Z]', table_name):
            issues.append("表名包含大写字母，应使用下划线命名")
            score -= 2.5

        return max(0, score), issues

    def check_fields(self, sql_text):
        """检查字段规范"""
        issues = []

        # 提取 CREATE TABLE 语句中的字段定义
        field_pattern = r'`?(\w+)`?\s+(?:STRING|BIGINT|INT|SMALLINT|TINYINT|DECIMAL|DOUBLE|FLOAT|DATE|DATETIME|TIMESTAMP|BOOLEAN)\s*COMMENT\s*[\'"]([^\'"]*)[\'"]'
        fields = re.findall(field_pattern, sql_text, re.IGNORECASE)

        total_fields = len(fields)
        if total_fields == 0:
            # 尝试另一种模式
            field_pattern = r'(\w+)\s+(?:STRING|BIGINT|INT|SMALLINT|TINYINT|DECIMAL|DOUBLE|FLOAT|DATE|DATETIME|TIMESTAMP|BOOLEAN)\s+COMMENT\s+[\'"]([^\'"]*)[\'"]'
            fields = re.findall(field_pattern, sql_text, re.IGNORECASE)
            total_fields = len(fields)

        # 检查空注释
        empty_comment_fields = []
        for field_name, comment in fields:
            if not comment or comment.strip() == '':
                empty_comment_fields.append(field_name)

        # 检查驼峰命名
        camel_case_fields = []
        for field_name, _ in fields:
            if re.search(r'[a-z][A-Z]', field_name):
                camel_case_fields.append(field_name)

        if empty_comment_fields:
            issues.append(f"{len(empty_comment_fields)} 个字段缺少注释：{', '.join(empty_comment_fields[:5])}{'...' if len(empty_comment_fields) > 5 else ''}")

        if camel_case_fields:
            issues.append(f"{len(camel_case_fields)} 个字段使用驼峰命名：{', '.join(camel_case_fields[:5])}{'...' if len(camel_case_fields) > 5 else ''}")

        # 计算得分
        score = 60  # 基础分
        if empty_comment_fields:
            score -= len(empty_comment_fields) * 2
        if camel_case_fields:
            score -= len(camel_case_fields) * 2

        return max(0, score), issues, total_fields

    def check_partition(self, sql_text):
        """检查分区规范"""
        issues = []
        score = 10

        # 检查是否有分区定义
        partition_match = re.search(r'PARTITIONED\s+BY\s*\(([^)]+)\)', sql_text, re.IGNORECASE)
        if not partition_match:
            # 尝试另一种模式
            partition_match = re.search(r'partitioned\s+by\s*\(\s*(\w+)\s+(?:string|varchar)', sql_text, re.IGNORECASE)

        if partition_match or 'partitioned by' in sql_text.lower():
            # 检查分区字段命名
            if 'dt string' in sql_text.lower() or 'dt STRING' in sql_text:
                pass  # 符合规范
            elif 'pt string' in sql_text.lower():
                issues.append("分区字段使用 pt 而非规范的 dt")
                score -= 2
        else:
            issues.append("未定义分区")
            score -= 5

        return max(0, score), issues

    def check_storage(self, sql_text):
        """检查存储规范"""
        issues = []
        score = 20

        # 检查存储格式
        if 'STORED AS ORC' in sql_text.upper():
            pass  # ORC 格式符合规范
        elif 'STORED AS PARQUET' in sql_text.upper():
            pass  # Parquet 格式符合规范
        elif 'STORED AS' in sql_text.upper():
            issues.append("存储格式非 ORC/Parquet")
            score -= 10
        else:
            issues.append("未明确存储格式")
            score -= 5

        # 检查压缩配置
        if 'orc.compress' in sql_text.lower() or 'parquet.compression' in sql_text.lower():
            pass  # 已配置压缩
        elif 'STORED AS ORC' in sql_text.upper() or 'STORED AS PARQUET' in sql_text.upper():
            issues.append("存储格式使用 ORC/Parquet 但未配置压缩格式")
            score -= 5

        return max(0, score), issues

    def check_sql_file(self, file_path):
        """检查单个 SQL 文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_text = f.read()

        # 提取表名
        table_name_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?', sql_text, re.IGNORECASE)
        if not table_name_match:
            return None

        table_name = table_name_match.group(1)

        # 执行各项检查
        name_score, name_issues = self.check_table_name(table_name, sql_text)
        field_score, field_issues, field_count = self.check_fields(sql_text)
        partition_score, partition_issues = self.check_partition(sql_text)
        storage_score, storage_issues = self.check_storage(sql_text)

        # 计算总分
        total_deduction = (10 - name_score) + (60 - field_score) + (10 - partition_score) + (20 - storage_score)
        final_score = 100 - total_deduction

        # 合并所有问题
        all_issues = name_issues + field_issues + partition_issues + storage_issues
        issue_desc = '；'.join(all_issues) if all_issues else '无问题，符合所有规范'

        return {
            '表名': table_name,
            '所属分层': self.identify_layer(table_name),
            '表命名检查扣分': 10 - name_score,
            '字段规范检查扣分': 60 - field_score,
            '分区规范检查扣分': 10 - partition_score,
            '存储规范检查扣分': 20 - storage_score,
            '总扣分': total_deduction,
            '最终得分': max(0, final_score),
            '问题描述': issue_desc,
            '字段数': field_count
        }

    def run_check(self):
        """执行模型检查"""
        print("=" * 60)
        print("模型规范检查工具")
        print("=" * 60)

        # 查找所有 SQL 文件
        sql_files = list(self.input_dir.glob("*.sql"))
        print(f"\n[1/4] 发现 {len(sql_files)} 个 SQL 文件")

        if not sql_files:
            print("  警告：input 目录下没有找到 SQL 文件!")
            return

        # 执行检查
        print("\n[2/4] 执行模型规范检查...")
        for sql_file in sql_files:
            print(f"  检查：{sql_file.name}")
            result = self.check_sql_file(sql_file)
            if result:
                self.check_results.append(result)

        print(f"  完成检查 {len(self.check_results)} 个表")

        # 保存结果
        print("\n[3/4] 保存检查结果...")
        self.save_to_excel()

        # 生成报告
        print("\n[4/4] 生成 Markdown 报告...")
        self.generate_report()

        print("\n" + "=" * 60)
        print("检查完成!")
        print("=" * 60)

    def save_to_excel(self):
        """保存检查结果到 Excel"""
        excel_path = self.output_dir / "model_check_result.xlsx"

        # 转换为 DataFrame
        df = pd.DataFrame(self.check_results)

        # 重新排列列顺序
        columns = ['表名', '所属分层', '字段数', '表命名检查扣分', '字段规范检查扣分',
                   '分区规范检查扣分', '存储规范检查扣分', '总扣分', '最终得分', '问题描述']
        df = df[columns]

        # 保存
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"  Excel 结果已保存到：{excel_path}")

    def generate_report(self):
        """生成 Markdown 报告"""
        report_path = self.output_dir / "model_check_report.md"

        # 统计信息
        total_tables = len(self.check_results)
        avg_score = sum(r['最终得分'] for r in self.check_results) / total_tables if total_tables > 0 else 0

        # 按分层统计
        layer_stats = {}
        for result in self.check_results:
            layer = result['所属分层']
            if layer not in layer_stats:
                layer_stats[layer] = {'count': 0, 'total_score': 0, 'tables': []}
            layer_stats[layer]['count'] += 1
            layer_stats[layer]['total_score'] += result['最终得分']
            layer_stats[layer]['tables'].append(result)

        # 生成报告内容
        report_content = f"""# 模型规范检查报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 开篇总结

本次检查共覆盖 **{total_tables}** 个数据表，整体平均得分 **{avg_score:.1f}** 分。

## 一、评估概览

### 整体评分

| 分层 | 表数 | 平均分 | 最高分 | 最低分 |
|------|------|--------|--------|--------|
"""

        for layer, stats in sorted(layer_stats.items()):
            if stats['count'] > 0:
                scores = [t['最终得分'] for t in stats['tables']]
                avg = sum(scores) / len(scores)
                report_content += f"| {layer} | {stats['count']} | {avg:.1f} | {max(scores)} | {min(scores)} |\n"

        report_content += """
### 评分等级说明

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 模型质量优秀 |
| 75-89 | 良好 | 模型质量良好 |
| 60-74 | 一般 | 模型质量一般 |
| 40-59 | 较差 | 模型质量较差 |
| 0-39 | 危险 | 存在严重问题 |

## 二、问题分布

### 检查项扣分统计

| 检查项 | 总扣分 | 说明 |
|--------|--------|------|
| 表命名检查 | """ + str(sum(r['表命名检查扣分'] for r in self.check_results)) + """ | 表名规范 |
| 字段规范检查 | """ + str(sum(r['字段规范检查扣分'] for r in self.check_results)) + """ | 字段命名、注释、类型 |
| 分区规范检查 | """ + str(sum(r['分区规范检查扣分'] for r in self.check_results)) + """ | 分区设计 |
| 存储规范检查 | """ + str(sum(r['存储规范检查扣分'] for r in self.check_results)) + """ | 存储格式、压缩配置 |

## 三、分层详情

"""

        for layer, stats in sorted(layer_stats.items()):
            report_content += f"\n### {layer}层\n"
            report_content += "| 表名 | 字段数 | 得分 | 主要问题 |\n"
            report_content += "|------|--------|------|----------|\n"

            for table in sorted(stats['tables'], key=lambda x: x['最终得分']):
                issue_short = table['问题描述'][:30] + '...' if len(table['问题描述']) > 30 else table['问题描述']
                report_content += f"| {table['表名']} | {table['字段数']} | {table['最终得分']} | {issue_short} |\n"

        report_content += """
## 四、TOP 问题表

### 得分最低的 5 个表

| 表名 | 分层 | 得分 | 主要问题 |
|------|------|------|----------|
"""

        sorted_tables = sorted(self.check_results, key=lambda x: x['最终得分'])[:5]
        for table in sorted_tables:
            issue_short = table['问题描述'][:40] + '...' if len(table['问题描述']) > 40 else table['问题描述']
            report_content += f"| {table['表名']} | {table['所属分层']} | {table['最终得分']} | {issue_short} |\n"

        report_content += """
## 五、整改建议

### 优先修复项

1. **字段注释补充**：为所有缺少注释的字段添加 COMMENT
2. **字段命名规范**：将驼峰命名改为下划线命名
3. **存储压缩配置**：为 ORC/Parquet 表添加压缩配置

### 建议配置

```sql
-- 推荐的存储配置
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY')
```

## 六、最佳实践

- 表名使用 `分层前缀_业务域_表名_增量标识` 格式
- 所有字段必须有 COMMENT 注释
- 分区字段统一使用 `dt` (日期)
- 使用 ORC 或 Parquet 列式存储
- 配置适当的压缩格式（SNAPPY/ZLIB）
"""

        # 写入文件
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"  Markdown 报告已保存到：{report_path}")


def main():
    checker = ModelChecker()
    checker.run_check()


if __name__ == "__main__":
    main()
