#!/usr/bin/env python3
"""
SQL 代码检查脚本（纯文件处理版本）
功能：
1. 从 input/task_info_data.xlsx 读取任务数据
2. 加载检查规则 (44 条规则)
3. 执行规则检查
4. 保存结果到 output/code_check_result.xlsx
5. 生成 Markdown 报告 output/code_check_report.md
6. 计算代码评分

重要：本脚本不依赖数据库，所有处理基于文件完成。
"""

import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
from openpyxl import Workbook


class CodeChecker:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.rules_path = self.base_dir / "references/code_rules.md"
        self.excel_path = self.base_dir / "input/task_info_data.xlsx"
        self.output_dir = self.base_dir / "output"
        self.rules = self.load_rules()

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_rules(self):
        """从 code_rules.md 加载检查规则"""
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            content = f.read()

        rules = []
        current_category = ""

        lines = content.split('\n')
        in_rule_table = False

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # 匹配分类标题：### 2.1 代码规范检查 或 ### 代码规范检查
            if line_stripped.startswith('### ') and ('检查' in line_stripped or '性能' in line_stripped or '反模式' in line_stripped or '安全' in line_stripped or '分层' in line_stripped):
                # 提取分类名，去掉数字编号
                cat_text = line_stripped.replace('### ', '').strip()
                # 去掉数字编号如 "2.1 "
                import re
                cat_text = re.sub(r'^\d+\.\d+\s*', '', cat_text)
                current_category = cat_text
                in_rule_table = False
                continue

            if line_stripped.startswith('|') and '规则' in line_stripped and 'ID' in line_stripped:
                # 表头行
                in_rule_table = True
                continue

            if in_rule_table and line_stripped.startswith('|') and '---' not in line_stripped:
                # 数据行
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 4:
                    rule_id = parts[0]
                    rule_name = parts[1]
                    check_content = parts[2]
                    severity = parts[3]

                    rules.append({
                        'rule_id': rule_id,
                        'rule_name': rule_name,
                        'check_content': check_content,
                        'severity': severity,
                        'category': current_category
                    })
                continue

            if in_rule_table and not line_stripped.startswith('|'):
                # 表格结束
                in_rule_table = False

        return rules

    def identify_layer(self, sql_text, task_name=''):
        """识别 SQL 所属的数仓分层"""
        # 优先基于任务名称识别分层
        if task_name:
            name_lower = task_name.lower()
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

        # 如果任务名称无法识别，则基于 SQL 内容识别
        sql_lower = sql_text.lower()

        if 'ods_' in sql_lower:
            return 'ODS'
        elif 'dwd_' in sql_lower:
            return 'DWD'
        elif 'dws_' in sql_lower:
            return 'DWS'
        elif 'dim_' in sql_lower:
            return 'DIM'
        elif 'ads_' in sql_lower:
            return 'ADS'
        else:
            return 'UNKNOWN'

    def get_suggestion(self, rule_id):
        """根据规则 ID 获取整改建议"""
        suggestions = {
            'COD_NAM_001': '使用下划线命名规范，避免驼峰命名',
            'COD_NAM_002': '确保表名以正确的分层前缀开头（ods/dwd/dws/dim/ads）',
            'COD_NAM_003': '添加必要的功能说明注释',
            'COD_PER_001': '添加 WHERE 条件避免全表扫描',
            'COD_PER_002': '为 JOIN 操作添加 ON 条件避免笛卡尔积',
            'COD_ANT_001': '明确指定需要的字段，避免使用 SELECT *',
            'COD_SEC_001': '对敏感字段进行脱敏处理',
            'COD_SEC_002': '避免在生产环境中执行危险的 DROP/TRUNCATE 操作',
            'COD_SEC_003': 'DELETE 操作必须添加 WHERE 条件',
            'COD_LAY_001': 'ODS 层不应包含聚合计算，保持原始数据'
        }
        return suggestions.get(rule_id, '请参考相关规范进行修改')

    def check_rule(self, sql_text, rule):
        """检查单条 SQL 是否违反指定规则"""
        sql_lower = sql_text.lower()
        rule_id = rule['rule_id']

        # 根据规则 ID 实现具体的检查逻辑
        if rule_id == 'COD_NAM_001':
            # 命名规范：检查是否包含驼峰命名
            return bool(re.search(r'[a-z][A-Z]', sql_text))

        elif rule_id == 'COD_NAM_002':
            # 分层前缀规范
            layer_prefixes = ['ods_', 'dwd_', 'dws_', 'dim_', 'ads_']
            has_valid_prefix = any(prefix in sql_lower for prefix in layer_prefixes)
            return not has_valid_prefix

        elif rule_id == 'COD_NAM_003':
            # 注释规范：检查是否有注释
            return '--' not in sql_text and '/*' not in sql_text

        elif rule_id == 'COD_PER_001':
            # 全表扫描预警：SELECT without WHERE
            select_match = re.search(r'select\s+.*?\s+from\s+(\w+)', sql_lower)
            where_match = 'where' in sql_lower
            return select_match and not where_match

        elif rule_id == 'COD_PER_002':
            # 笛卡尔积检测
            join_without_on = re.search(r'join\s+\w+\s*(?!on)', sql_lower)
            return bool(join_without_on)

        elif rule_id == 'COD_ANT_001':
            # SELECT *
            return 'select *' in sql_lower

        elif rule_id == 'COD_SEC_001':
            # 敏感字段脱敏
            sensitive_fields = ['phone', 'idcard', '身份证', '手机号']
            contains_sensitive = any(field in sql_lower for field in sensitive_fields)
            has_masking = 'mask' in sql_lower or 'substr' in sql_lower or 'concat' in sql_lower
            return contains_sensitive and not has_masking

        elif rule_id == 'COD_SEC_002':
            # 危险操作预警
            dangerous_ops = ['drop table', 'truncate table']
            return any(op in sql_lower for op in dangerous_ops)

        elif rule_id == 'COD_SEC_003':
            # 无限制 DELETE
            delete_match = 'delete' in sql_lower
            where_match = 'where' in sql_lower
            return delete_match and not where_match

        elif rule_id == 'COD_LAY_001':
            # ODS 层禁止聚合
            is_ods = 'ods_' in sql_lower
            has_aggregation = any(func in sql_lower for func in ['sum(', 'count(', 'avg(', 'max(', 'min('])
            return is_ods and has_aggregation

        elif rule_id == 'COD_LAY_002':
            # DWD 层禁止跨层引用（DWD 只引用 ODS/DIM）
            is_dwd = 'dwd_' in sql_lower
            has_invalid_ref = 'dws_' in sql_lower or 'ads_' in sql_lower
            return is_dwd and has_invalid_ref

        elif rule_id == 'COD_LAY_004':
            # ADS 层引用规范（ADS 只引用 DWS/DIM）
            is_ads = 'ads_' in sql_lower
            has_invalid_ref = 'ods_' in sql_lower or 'dwd_' in sql_lower
            return is_ads and has_invalid_ref

        elif rule_id == 'COD_LAY_005':
            # DIM 层禁止引用明细（DIM 只引用 ODS/DIM，禁止引用 DWD/DWS/ADS）
            is_dim = 'dim_' in sql_lower
            has_invalid_ref = 'dwd_' in sql_lower or 'dws_' in sql_lower or 'ads_' in sql_lower
            return is_dim and has_invalid_ref

        # 其他规则默认返回 False（不违反）
        return False

    def get_code_list(self, layers=None):
        """从 Excel 文件读取代码列表"""
        print(f"  读取 Excel 文件：{self.excel_path}")

        if not self.excel_path.exists():
            print(f"  警告：Excel 文件不存在：{self.excel_path}")
            return []

        df = pd.read_excel(self.excel_path)
        print(f"  Excel 文件包含 {len(df)} 行数据")

        # 筛选有效 SQL 代码
        valid_codes = df[
            (df['is_deleted'] == 1) &
            (df['sql_text'].notna()) &
            (df['sql_text'].astype(str).str.strip() != '')
        ]

        print(f"  筛选后有效 SQL 代码 {len(valid_codes)} 条")

        # 添加分层过滤条件
        if layers:
            layer_masks = []
            for layer in layers:
                layer = layer.lower().strip()
                layer_masks.append(valid_codes['name'].str.lower().str.startswith(f'{layer}_'))
            if layer_masks:
                mask = layer_masks[0]
                for m in layer_masks[1:]:
                    mask |= m
                valid_codes = valid_codes[mask]
            print(f"  指定分层 {layers} 筛选后 {len(valid_codes)} 条")

        code_list = []
        for idx, row in valid_codes.iterrows():
            sql_text = str(row.get('sql_text', '')).strip()
            if sql_text:
                code_list.append({
                    'code_id': idx + 1,
                    'code_name': row.get('name', ''),
                    'task_name': row.get('name', ''),
                    'task_type': row.get('task_type', 0),
                    'sql_text': sql_text,
                    'tenant_id': row.get('tenant_id', 0),
                    'project_id': row.get('project_id', 0)
                })

        return code_list

    def calculate_scores(self, results):
        """计算代码评分"""
        code_scores = {}

        for result in results:
            code_id = result['code_id']
            task_name = result['task_name']
            code_layer = result['code_layer']

            if code_id not in code_scores:
                code_scores[code_id] = {
                    'task_name': task_name,
                    'code_layer': code_layer,
                    'block_fails': 0,
                    'warn_fails': 0,
                    'info_fails': 0
                }

            if result['check_status'] == 'FAIL':
                severity = result['rule_severity'].upper()
                if severity == 'BLOCK':
                    code_scores[code_id]['block_fails'] += 1
                elif severity == 'WARN':
                    code_scores[code_id]['warn_fails'] += 1
                elif severity == 'INFO':
                    code_scores[code_id]['info_fails'] += 1

        # 计算最终得分
        for code_id, score_info in code_scores.items():
            score = 100 - (score_info['block_fails'] * 25) - (score_info['warn_fails'] * 10) - (score_info['info_fails'] * 3)
            score_info['score'] = max(0, score)  # 确保分数不低于 0

        return code_scores

    def save_results_to_excel(self, results, code_scores):
        """保存检查结果到 Excel 文件"""
        excel_path = self.output_dir / "code_check_result.xlsx"

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # 工作表 1：检查结果汇总
            summary_data = []
            for result in results:
                summary_data.append({
                    '代码 ID': result['code_id'],
                    '任务名称': result['task_name'],
                    '所属分层': result['code_layer'],
                    '规则 ID': result['rule_id'],
                    '规则名称': result['rule_name'],
                    '严重程度': result['rule_severity'],
                    '检查结果': result['check_status'],
                    '问题描述': result['issue_desc'],
                    '整改建议': result['suggestion']
                })
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='检查结果汇总', index=False)

            # 工作表 2：代码评分表
            score_data = []
            for code_id, info in code_scores.items():
                score_data.append({
                    '代码 ID': code_id,
                    '任务名称': info['task_name'],
                    '所属分层': info['code_layer'],
                    'BLOCK 问题数': info['block_fails'],
                    'WARN 问题数': info['warn_fails'],
                    'INFO 问题数': info['info_fails'],
                    '最终得分': info['score']
                })
            score_df = pd.DataFrame(score_data)
            score_df.to_excel(writer, sheet_name='代码评分表', index=False)

            # 工作表 3：分层统计表
            layer_stats = {}
            for code_id, info in code_scores.items():
                layer = info['code_layer']
                if layer not in layer_stats:
                    layer_stats[layer] = {'count': 0, 'total_score': 0, 'block_total': 0, 'warn_total': 0, 'scores': []}
                layer_stats[layer]['count'] += 1
                layer_stats[layer]['total_score'] += info['score']
                layer_stats[layer]['block_total'] += info['block_fails']
                layer_stats[layer]['warn_total'] += info['warn_fails']
                layer_stats[layer]['scores'].append(info['score'])

            layer_data = []
            for layer, stats in layer_stats.items():
                avg_score = stats['total_score'] / stats['count'] if stats['count'] > 0 else 0
                max_score = max(stats['scores']) if stats['scores'] else 0
                min_score = min(stats['scores']) if stats['scores'] else 0
                layer_data.append({
                    '分层': layer,
                    '代码数': stats['count'],
                    '平均分': round(avg_score, 2),
                    '最高分': max_score,
                    '最低分': min_score,
                    'BLOCK 总数': stats['block_total'],
                    'WARN 总数': stats['warn_total']
                })
            layer_df = pd.DataFrame(layer_data)
            layer_df.to_excel(writer, sheet_name='分层统计表', index=False)

            # 工作表 4：问题明细表
            issue_data = []
            for result in results:
                if result['check_status'] == 'FAIL':
                    issue_data.append({
                        '任务名称': result['task_name'],
                        '规则 ID': result['rule_id'],
                        '规则名称': result['rule_name'],
                        '严重程度': result['rule_severity'],
                        '问题描述': result['issue_desc'],
                        '整改建议': result['suggestion']
                    })
            issue_df = pd.DataFrame(issue_data)
            issue_df.to_excel(writer, sheet_name='问题明细表', index=False)

        print(f"检查结果已保存到：{excel_path}")
        return excel_path

    def generate_markdown_report(self, results, code_scores):
        """生成 Markdown 格式的检查报告"""
        report_path = self.output_dir / "code_check_report.md"

        # 统计信息
        total_codes = len(code_scores)
        total_results = len(results)
        pass_count = sum(1 for r in results if r['check_status'] == 'PASS')
        fail_count = sum(1 for r in results if r['check_status'] == 'FAIL')

        # 按分层统计
        layer_stats = {}
        for code_id, score_info in code_scores.items():
            layer = score_info['code_layer']
            if layer not in layer_stats:
                layer_stats[layer] = {'count': 0, 'total_score': 0, 'block_issues': 0, 'warn_issues': 0, 'info_issues': 0}
            layer_stats[layer]['count'] += 1
            layer_stats[layer]['total_score'] += score_info['score']
            layer_stats[layer]['block_issues'] += score_info['block_fails']
            layer_stats[layer]['warn_issues'] += score_info['warn_fails']
            layer_stats[layer]['info_issues'] += score_info['info_fails']

        # 生成报告内容
        report_content = f"""# 数仓代码检查报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 开篇总结

本次检查覆盖 **{total_codes}** 个代码任务，共执行 **{total_results}** 次规则检查。

- **通过**: {pass_count} 项
- **失败**: {fail_count} 项

## 一、评估概览

### 整体评分

| 分层 | 代码数 | 平均分 | BLOCK | WARN | INFO |
|------|--------|--------|-------|------|------|
"""

        for layer, stats in sorted(layer_stats.items()):
            avg_score = stats['total_score'] / stats['count'] if stats['count'] > 0 else 0
            report_content += f"| {layer} | {stats['count']} | {avg_score:.1f} | {stats['block_issues']} | {stats['warn_issues']} | {stats['info_issues']} |\n"

        report_content += """
### 评分等级说明

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 代码质量优秀 |
| 75-89 | 良好 | 代码质量良好 |
| 60-74 | 一般 | 代码质量一般 |
| 40-59 | 较差 | 代码质量较差 |
| 0-39 | 危险 | 存在严重问题 |

## 二、问题分布

### 严重程度分布

"""
        severity_counts = {'BLOCK': 0, 'WARN': 0, 'INFO': 0}
        for result in results:
            if result['check_status'] == 'FAIL':
                severity = result['rule_severity'].upper()
                if severity in severity_counts:
                    severity_counts[severity] += 1

        for severity, count in severity_counts.items():
            if count > 0:
                report_content += f"- **{severity}**: {count} 个\n"

        report_content += """
### 问题类型分布

"""
        category_counts = {}
        for result in results:
            if result['check_status'] == 'FAIL':
                category = result.get('category', '未知')
                category_counts[category] = category_counts.get(category, 0) + 1

        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            report_content += f"- **{category}**: {count} 个\n"

        report_content += """
## 三、分层详情

"""
        for layer, stats in sorted(layer_stats.items()):
            report_content += f"\n### {layer}层\n"
            report_content += "| 任务名称 | 评分 | BLOCK 问题 | WARN 问题 | INFO 问题 |\n"
            report_content += "|----------|------|-----------|----------|----------|\n"

            layer_codes = [(code_id, info) for code_id, info in code_scores.items() if info['code_layer'] == layer]
            # 按评分排序，显示最低的 5 个
            layer_codes_sorted = sorted(layer_codes, key=lambda x: x[1]['score'])[:5]
            for code_id, info in layer_codes_sorted:
                report_content += f"| {info['task_name']} | {info['score']} | {info['block_fails']} | {info['warn_fails']} | {info['info_fails']} |\n"

        report_content += """
## 四、TOP 问题

### 问题代码排行（按问题数量）

| 任务名称 | 所属分层 | 评分 | BLOCK | WARN | INFO |
|----------|----------|------|-------|------|------|
"""

        # 按问题总数排序，显示最多的 10 个
        codes_by_issues = sorted(
            code_scores.items(),
            key=lambda x: x[1]['block_fails'] + x[1]['warn_fails'] + x[1]['info_fails'],
            reverse=True
        )[:10]

        for code_id, info in codes_by_issues:
            if info['block_fails'] + info['warn_fails'] + info['info_fails'] > 0:
                report_content += f"| {info['task_name']} | {info['code_layer']} | {info['score']} | {info['block_fails']} | {info['warn_fails']} | {info['info_fails']} |\n"

        report_content += """
## 五、整改建议

### 优先级建议

1. **立即处理（BLOCK 级）**：
"""
        block_issues = [r for r in results if r['check_status'] == 'FAIL' and r['rule_severity'].upper() == 'BLOCK']
        for issue in block_issues[:5]:
            report_content += f"   - [{issue['task_name']}] {issue['rule_name']}: {issue['issue_desc']}\n"

        if not block_issues:
            report_content += "   - 无 BLOCK 级问题\n"

        report_content += """
2. **建议修复（WARN 级）**：
   - 完善代码注释和命名规范
   - 优化查询性能，避免全表扫描
   - 遵循分层设计原则

3. **持续优化（INFO 级）**：
   - 改进代码格式和可读性
   - 统一编码风格

## 六、最佳实践

- 使用明确的字段名替代 `SELECT *`
- 为所有查询添加适当的 `WHERE` 条件
- 对敏感字段实施脱敏处理
- 遵循分层命名规范（ods_/dwd_/dws_/dim_/ads_）
- 定期执行代码检查，持续改进代码质量
"""

        # 写入文件
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"Markdown 报告已生成：{report_path}")
        return report_path

    def run_check(self, layers=None):
        """执行完整的代码检查流程"""
        print("=" * 60)
        print("SQL 代码检查工具（纯文件处理版本）")
        print("=" * 60)

        print("\n[1/6] 加载检查规则...")
        print(f"共加载 {len(self.rules)} 条规则")
        for rule in self.rules[:5]:
            print(f"  - {rule['rule_id']}: {rule['rule_name']}")
        if len(self.rules) > 5:
            print(f"  ... 还有 {len(self.rules) - 5} 条规则")

        print("\n[2/6] 获取待检查代码...")
        code_list = self.get_code_list(layers)
        print(f"共获取 {len(code_list)} 条 SQL 代码")

        if not code_list:
            print("警告：没有找到待检查的代码!")
            if layers:
                print(f"可能的原因：指定的分层 {layers} 中没有匹配的任务")
            return []

        print("\n[3/6] 执行规则检查...")
        all_results = []

        for idx, code in enumerate(code_list, 1):
            sql_text = code['sql_text']
            code_id = code['code_id']
            code_name = code['code_name']
            code_layer = self.identify_layer(sql_text, code_name)

            print(f"  检查 [{idx}/{len(code_list)}] {code_name} (ID:{code_id}) - {code_layer}层")

            for rule in self.rules:
                is_fail = self.check_rule(sql_text, rule)

                result = {
                    'code_id': code_id,
                    'code_name': code_name,
                    'task_name': code_name,
                    'code_layer': code_layer,
                    'rule_id': rule['rule_id'],
                    'rule_name': rule['rule_name'],
                    'rule_severity': rule['severity'],
                    'check_status': 'FAIL' if is_fail else 'PASS',
                    'issue_location': '',
                    'issue_desc': rule['check_content'] if is_fail else '',
                    'suggestion': self.get_suggestion(rule['rule_id']) if is_fail else '',
                    'category': rule['category'],
                    'check_time': datetime.now()
                }
                all_results.append(result)

        pass_count = sum(1 for r in all_results if r['check_status'] == 'PASS')
        fail_count = sum(1 for r in all_results if r['check_status'] == 'FAIL')
        print(f"  检查完成：PASS {pass_count} 项，FAIL {fail_count} 项")

        print("\n[4/6] 计算代码评分...")
        code_scores = self.calculate_scores(all_results)

        print("\n[5/6] 保存检查结果...")
        self.save_results_to_excel(all_results, code_scores)

        print("\n[6/6] 生成检查报告...")
        self.generate_markdown_report(all_results, code_scores)

        print("\n" + "=" * 60)
        print("检查完成!")
        print("=" * 60)

        return all_results


def main():
    import argparse

    parser = argparse.ArgumentParser(description='SQL 代码检查工具（纯文件处理版本）')
    parser.add_argument('--all', action='store_true', help='执行完整检查流程')
    parser.add_argument('--check', action='store_true', help='仅执行规则检查')
    parser.add_argument('--layers', type=str, help='指定分层检查，如：ods,dwd,dws')

    args = parser.parse_args()

    checker = CodeChecker()

    if args.all:
        layers = args.layers.split(',') if args.layers else None
        checker.run_check(layers)
    elif args.check:
        layers = args.layers.split(',') if args.layers else None
        code_list = checker.get_code_list(layers)
        if code_list:
            all_results = []
            for idx, code in enumerate(code_list, 1):
                sql_text = code['sql_text']
                code_id = code['code_id']
                code_name = code['code_name']
                code_layer = checker.identify_layer(sql_text, code_name)

                print(f"检查 [{idx}/{len(code_list)}] {code_name} (ID:{code_id}) - {code_layer}层")

                for rule in checker.rules:
                    is_fail = checker.check_rule(sql_text, rule)

                    result = {
                        'code_id': code_id,
                        'code_name': code_name,
                        'task_name': code_name,
                        'code_layer': code_layer,
                        'rule_id': rule['rule_id'],
                        'rule_name': rule['rule_name'],
                        'rule_severity': rule['severity'],
                        'check_status': 'FAIL' if is_fail else 'PASS',
                        'issue_location': '',
                        'issue_desc': rule['check_content'] if is_fail else '',
                        'suggestion': checker.get_suggestion(rule['rule_id']) if is_fail else '',
                        'category': rule['category'],
                        'check_time': datetime.now()
                    }
                    all_results.append(result)

            pass_count = sum(1 for r in all_results if r['check_status'] == 'PASS')
            fail_count = sum(1 for r in all_results if r['check_status'] == 'FAIL')
            print(f"检查完成：PASS {pass_count} 项，FAIL {fail_count} 项")

            code_scores = checker.calculate_scores(all_results)
            checker.save_results_to_excel(all_results, code_scores)
            checker.generate_markdown_report(all_results, code_scores)
            print("检查结果已保存并生成报告文件")
        else:
            print("没有找到待检查的代码")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
