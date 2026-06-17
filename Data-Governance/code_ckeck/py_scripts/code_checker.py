#!/usr/bin/env python3
"""
SQL代码检查脚本
功能：
1. 连接数据库
2. 执行 code_chk0.sql 清空 rdos_batch_task 表
3. 从 inputs/excel/task_info_data.xlsx 导入数据到 rdos_batch_task 表
4. 从 rdos_batch_task 表直接读取SQL代码
5. 加载检查规则 (44条规则)
6. 执行规则检查
7. 保存结果到 code_check_result 表
8. 生成Markdown报告和Excel文档
9. 计算代码评分
"""

import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

import pymysql


class CodeChecker:
    def __init__(self):
        self.base_dir = Path("/Users/wuqi/Documents/GitHub/data-skills/Data-Governance/code_ckeck")
        self.config_path = self.base_dir / "configs/db_config.json"
        self.rules_path = self.base_dir / "configs/code_rules.md"
        self.excel_path = self.base_dir / "inputs/docs/task_info_data.xlsx"
        self.sql_path_0 = self.base_dir / "sql_scripts/chk_sql/code_chk0.sql"
        self.output_dir = self.base_dir / "outputs/docs"
        self.rules = self.load_rules()
        self.conn = None

    def load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_rules(self):
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            content = f.read()

        rules = []
        current_category = ""

        lines = content.split('\n')
        in_rule_table = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('### ') and '检查' in line:
                current_category = line.replace('### ', '').replace('检查', '').strip()
                in_rule_table = False
                continue
                
            if line.startswith('|') and '规则ID' in line:
                # 表头行
                in_rule_table = True
                continue
                
            if in_rule_table and line.startswith('|') and '---' not in line:
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
                
            if in_rule_table and not line.startswith('|'):
                # 表格结束
                in_rule_table = False
                
        return rules

    def connect_db(self):
        config = self.load_config()
        db_config = config['target_db']
        
        self.conn = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset=db_config['charset'],
            cursorclass=pymysql.cursors.DictCursor
        )

    def execute_sql_file(self, sql_file_path):
        """执行SQL文件"""
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句（以分号分隔）
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        cursor = self.conn.cursor()
        for sql_stmt in sql_statements:
            if sql_stmt:
                cursor.execute(sql_stmt)
        self.conn.commit()
        cursor.close()

    def import_from_excel(self):
        """从Excel文件导入数据到rdos_batch_task表"""
        print("  读取Excel文件...")
        
        # 读取Excel文件
        df = pd.read_excel(self.excel_path)
        print(f"  Excel文件包含 {len(df)} 行数据")
        
        # 准备插入数据
        cursor = self.conn.cursor()
        
        # 构建INSERT语句
        columns = list(df.columns)
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join([f"`{col}`" for col in columns])
        insert_sql = f"INSERT INTO `rdos_batch_task` ({column_names}) VALUES ({placeholders})"
        
        # 转换数据为列表
        data_to_insert = []
        for index, row in df.iterrows():
            row_data = []
            for col in columns:
                value = row[col]
                # 处理NaN值
                if pd.isna(value):
                    row_data.append(None)
                else:
                    row_data.append(str(value) if isinstance(value, (pd.Timestamp, datetime)) else value)
            data_to_insert.append(tuple(row_data))
        
        print(f"  准备插入 {len(data_to_insert)} 条记录...")
        
        # 批量插入
        batch_size = 1000
        total_inserted = 0
        for i in range(0, len(data_to_insert), batch_size):
            batch = data_to_insert[i:i+batch_size]
            cursor.executemany(insert_sql, batch)
            self.conn.commit()
            total_inserted += len(batch)
            print(f"    已插入 {total_inserted}/{len(data_to_insert)} 条记录")
        
        cursor.close()
        print(f"  成功导入 {total_inserted} 条记录到 rdos_batch_task 表")

    def identify_layer(self, sql_text):
        """识别SQL所属的数仓分层"""
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
        """根据规则ID获取整改建议"""
        suggestions = {
            'COD_NAM_001': '使用下划线命名规范，避免驼峰命名',
            'COD_NAM_002': '确保表名以正确的分层前缀开头（ods/dwd/dws/dim/ads）',
            'COD_NAM_003': '添加必要的功能说明注释',
            'COD_PER_001': '添加WHERE条件避免全表扫描',
            'COD_PER_002': '为JOIN操作添加ON条件避免笛卡尔积',
            'COD_ANT_001': '明确指定需要的字段，避免使用SELECT *',
            'COD_SEC_001': '对敏感字段进行脱敏处理',
            'COD_SEC_002': '避免在生产环境中执行危险的DROP/TRUNCATE操作',
            'COD_SEC_003': 'DELETE操作必须添加WHERE条件',
            'COD_LAY_001': 'ODS层不应包含聚合计算，保持原始数据'
        }
        return suggestions.get(rule_id, '请参考相关规范进行修改')

    def check_rule(self, sql_text, rule):
        """检查单条SQL是否违反指定规则"""
        sql_lower = sql_text.lower()
        rule_id = rule['rule_id']
        
        # 根据规则ID实现具体的检查逻辑
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
            # 无限制DELETE
            delete_match = 'delete' in sql_lower
            where_match = 'where' in sql_lower
            return delete_match and not where_match
            
        elif rule_id == 'COD_LAY_001':
            # ODS层禁止聚合
            is_ods = 'ods_' in sql_lower
            has_aggregation = any(func in sql_lower for func in ['sum(', 'count(', 'avg(', 'max(', 'min('])
            return is_ods and has_aggregation
            
        # 其他规则默认返回False（不违反）
        return False

    def get_code_list_from_db(self, layers=None):
        """从 rdos_batch_task 表直接读取代码列表"""
        # 构建基础查询
        query_sql = """SELECT id, tenant_id, project_id, name, task_type, sql_text
FROM rdos_batch_task
WHERE is_deleted = 1
AND sql_text IS NOT NULL
AND sql_text != ''"""
        
        # 添加分层过滤条件
        if layers:
            layer_conditions = []
            for layer in layers:
                layer = layer.lower().strip()
                layer_conditions.append(f"name LIKE '{layer}_%'")
            if layer_conditions:
                query_sql += " AND (" + " OR ".join(layer_conditions) + ")"
        
        query_sql += "\nORDER BY tenant_id, project_id, name"

        cursor = self.conn.cursor()
        cursor.execute(query_sql)
        results = cursor.fetchall()
        cursor.close()

        code_list = []
        for idx, row in enumerate(results):
            sql_text = row.get('sql_text', '')
            code_id = row.get('id')
            if code_id is None:
                code_id = idx + 1
            if sql_text and str(sql_text).strip():
                code_list.append({
                    'code_id': code_id,
                    'code_name': row.get('name', ''),
                    'task_name': row.get('name', ''),
                    'task_type': row.get('task_type', 0),
                    'sql_text': sql_text
                })

        return code_list

    def create_result_table(self):
        """创建检查结果表"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS `code_check_result` (
            `id`                BIGINT          NOT NULL AUTO_INCREMENT COMMENT '主键ID',
            `code_id`           BIGINT          NOT NULL COMMENT '代码ID',
            `task_name`         VARCHAR(255)    NOT NULL COMMENT '任务名称',
            `code_layer`        VARCHAR(16)     NOT NULL COMMENT '所属分层',
            `rule_id`           VARCHAR(16)     NOT NULL COMMENT '规则ID',
            `rule_name`         VARCHAR(64)     NOT NULL COMMENT '规则名称',
            `rule_severity`     VARCHAR(16)     NOT NULL COMMENT '严重程度',
            `check_status`      VARCHAR(16)     NOT NULL COMMENT '检查结果：PASS/FAIL',
            `issue_location`    VARCHAR(256)    DEFAULT NULL COMMENT '问题位置',
            `issue_desc`        TEXT            DEFAULT NULL COMMENT '问题描述',
            `suggestion`        TEXT            DEFAULT NULL COMMENT '整改建议',
            `check_time`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            KEY `idx_code_id` (`code_id`),
            KEY `idx_rule_id` (`rule_id`),
            KEY `idx_task_name` (`task_name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='代码检查结果表';
        """
        
        cursor = self.conn.cursor()
        cursor.execute(create_sql)
        self.conn.commit()
        cursor.close()

    def save_check_result(self, results):
        """保存检查结果到数据库"""
        if not results:
            print("没有检查结果需要保存")
            return
            
        cursor = self.conn.cursor()
        
        insert_sql = """
        INSERT INTO code_check_result 
        (code_id, task_name, code_layer, rule_id, rule_name, rule_severity, check_status, issue_location, issue_desc, suggestion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        batch_size = 1000
        for i in range(0, len(results), batch_size):
            batch = results[i:i+batch_size]
            data = []
            for result in batch:
                data.append((
                    result['code_id'],
                    result['task_name'],
                    result['code_layer'],
                    result['rule_id'],
                    result['rule_name'],
                    result['rule_severity'],
                    result['check_status'],
                    result['issue_location'],
                    result['issue_desc'],
                    result['suggestion']
                ))
            
            cursor.executemany(insert_sql, data)
            self.conn.commit()
            
        cursor.close()
        print(f"已保存 {len(results)} 条检查结果到code_check_result表")

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
            score_info['score'] = max(0, score)  # 确保分数不低于0
        
        return code_scores

    def generate_markdown_report(self, results, code_scores):
        """生成Markdown格式的检查报告"""
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
                layer_stats[layer] = {'count': 0, 'total_score': 0, 'block_issues': 0, 'warn_issues': 0}
            layer_stats[layer]['count'] += 1
            layer_stats[layer]['total_score'] += score_info['score']
            layer_stats[layer]['block_issues'] += score_info['block_fails']
            layer_stats[layer]['warn_issues'] += score_info['warn_fails']
        
        # 生成报告内容
        report_content = f"""# 数仓代码检查报告

## 开篇总结
本次检查覆盖{total_codes}个代码，共执行{total_results}次规则检查，发现{fail_count}个问题。

## 一、评估概览
| 分层 | 代码数 | 平均分 | BLOCK | WARN |
|------|--------|--------|-------|------|"""
        
        for layer, stats in layer_stats.items():
            avg_score = stats['total_score'] / stats['count'] if stats['count'] > 0 else 0
            report_content += f"\n| {layer} | {stats['count']} | {avg_score:.1f} | {stats['block_issues']} | {stats['warn_issues']} |"
        
        report_content += """

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
                report_content += f"- {severity}: {count} 个\n"
        
        report_content += """
### 问题类型分布
"""
        category_counts = {}
        for result in results:
            if result['check_status'] == 'FAIL':
                category = result.get('category', '未知')
                category_counts[category] = category_counts.get(category, 0) + 1
        
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            report_content += f"- {category}: {count} 个\n"
        
        report_content += """
## 三、分层详情
"""
        for layer, stats in layer_stats.items():
            report_content += f"\n### {layer}层\n"
            report_content += "| 任务名称 | 评分 | BLOCK问题 | WARN问题 |\n"
            report_content += "|----------|------|-----------|----------|\n"
            
            layer_codes = [(code_id, info) for code_id, info in code_scores.items() if info['code_layer'] == layer]
            for code_id, info in layer_codes[:5]:  # 只显示前5个
                report_content += f"| {info['task_name']} | {info['score']} | {info['block_fails']} | {info['warn_fails']} |\n"
        
        report_content += """
## 四、TOP问题
| 任务名称 | 规则ID | 规则名称 | 严重程度 |
|----------|--------|---------|----------|"""
        
        # 获取失败的问题
        fail_results = [r for r in results if r['check_status'] == 'FAIL']
        top_problems = sorted(fail_results, key=lambda x: x['rule_severity'], reverse=True)[:10]
        
        for result in top_problems:
            report_content += f"\n| {result['task_name']} | {result['rule_id']} | {result['rule_name']} | {result['rule_severity']} |"
        
        report_content += """
## 五、整改建议
1. **安全第一**：优先修复BLOCK级别的安全问题
2. **性能优化**：解决全表扫描、笛卡尔积等性能问题  
3. **规范完善**：补充必要的注释和遵循命名规范
4. **分层原则**：确保各层代码符合数仓分层设计原则

## 六、最佳实践
- 使用明确的字段名替代SELECT *
- 为所有查询添加适当的WHERE条件
- 对敏感字段实施脱敏处理
- 遵循分层命名规范（ods_/dwd_/dws_/dim_/ads_）
"""
        
        # 写入文件
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"Markdown报告已生成: {report_path}")

    def generate_excel_report(self, results):
        """生成Excel格式的检查报告"""
        excel_path = self.output_dir / "code_check_report.xlsx"
        
        # 转换为DataFrame
        df_data = []
        for result in results:
            df_data.append({
                '代码ID': result['code_id'],
                '任务名称': result['task_name'],
                '所属分层': result['code_layer'],
                '规则ID': result['rule_id'],
                '规则名称': result['rule_name'],
                '严重程度': result['rule_severity'],
                '检查结果': result['check_status'],
                '问题描述': result['issue_desc'],
                '整改建议': result['suggestion'],
                '检查时间': result['check_time']
            })
        
        df = pd.DataFrame(df_data)
        
        # 保存到Excel
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"Excel报告已生成: {excel_path}")

    def run_check(self, layers=None):
        print("=" * 60)
        print("SQL代码检查工具")
        print("=" * 60)

        print("\n[1/9] 连接数据库...")
        self.connect_db()
        print("数据库连接成功")

        print("\n[2/9] 执行 code_chk0.sql 清空原始表...")
        self.execute_sql_file(self.sql_path_0)
        print("rdos_batch_task 表已清空并重建")

        print("\n[3/9] 从Excel导入数据...")
        if self.excel_path.exists():
            self.import_from_excel()
        else:
            print(f"警告: Excel文件不存在: {self.excel_path}")
            return []

        print("\n[4/9] 加载检查规则...")
        print(f"共加载 {len(self.rules)} 条规则")
        for rule in self.rules[:5]:
            print(f"  - {rule['rule_id']}: {rule['rule_name']}")
        if len(self.rules) > 5:
            print(f"  ... 还有 {len(self.rules) - 5} 条规则")

        print("\n[5/9] 获取待检查代码...")
        code_list = self.get_code_list_from_db(layers)
        print(f"共获取 {len(code_list)} 条SQL代码")

        if not code_list:
            print("警告: 没有找到待检查的代码!")
            if layers:
                print(f"可能的原因: 指定的分层 {layers} 中没有匹配的任务")
            return []

        print("\n[6/9] 执行规则检查...")
        all_results = []

        for idx, code in enumerate(code_list, 1):
            sql_text = code['sql_text']
            code_id = code['code_id']
            code_name = code['code_name']
            code_layer = self.identify_layer(sql_text)

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
        print(f"  检查完成: PASS {pass_count} 条, FAIL {fail_count} 条")

        print("\n[7/9] 保存检查结果...")
        self.create_result_table()
        self.save_check_result(all_results)

        print("\n[8/9] 计算代码评分...")
        code_scores = self.calculate_scores(all_results)
        
        print("\n[9/9] 生成报告文件...")
        self.generate_markdown_report(all_results, code_scores)
        self.generate_excel_report(all_results)

        print("\n" + "=" * 60)
        print("检查完成!")
        print("=" * 60)

        if self.conn:
            self.conn.close()

        return all_results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='SQL代码检查工具')
    parser.add_argument('--all', action='store_true', help='执行完整检查流程')
    parser.add_argument('--check', action='store_true', help='仅执行规则检查')
    parser.add_argument('--layers', type=str, help='指定分层检查，如: ods,dwd,dws')
    
    args = parser.parse_args()
    
    checker = CodeChecker()
    
    if args.all:
        layers = args.layers.split(',') if args.layers else None
        checker.run_check(layers)
    elif args.check:
        checker.connect_db()
        layers = args.layers.split(',') if args.layers else None
        code_list = checker.get_code_list_from_db(layers)
        if code_list:
            all_results = []
            for idx, code in enumerate(code_list, 1):
                sql_text = code['sql_text']
                code_id = code['code_id']
                code_name = code['code_name']
                code_layer = checker.identify_layer(sql_text)
                
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
            print(f"检查完成: PASS {pass_count} 条, FAIL {fail_count} 条")
            
            checker.create_result_table()
            checker.save_check_result(all_results)
            
            # 生成报告
            code_scores = checker.calculate_scores(all_results)
            checker.generate_markdown_report(all_results, code_scores)
            checker.generate_excel_report(all_results)
            print("检查结果已保存并生成报告文件")
        else:
            print("没有找到待检查的代码")
        checker.conn.close()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()