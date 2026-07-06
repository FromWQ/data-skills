#!/usr/bin/env python3
"""
数仓健康度评估总控脚本
串联 skill_1/skill_2/skill_3 执行完整评估，生成综合健康报告
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class DwHealthyChecker:
    """数仓健康度检查总控类"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.output_dir = self.base_dir / 'output'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 各专项报告路径
        self.model_report_path = self.base_dir / 'model_check' / 'output' / 'model_check_report.md'
        self.code_report_path = self.base_dir / 'code_check' / 'output' / 'code_check_report.md'
        self.quality_report_path = self.base_dir / 'quality_check' / 'output' / 'quality_check_report.md'

        # 综合报告路径
        self.healthy_report_path = self.output_dir / 'dw_healthy_report.md'

        # 各专项评分
        self.scores = {
            'model': {'score': 0, 'level': 'N/A', 'details': {}},
            'code': {'score': 0, 'level': 'N/A', 'details': {}},
            'quality': {'score': 0, 'level': 'N/A', 'details': {}}
        }

    def run_model_check(self):
        """执行模型规范检查"""
        print("\n" + "=" * 60)
        print("【步骤 1/4】执行模型规范检查...")
        print("=" * 60)

        script_path = self.base_dir / 'model_check' / 'py_scripts' / 'model_checker.py'
        result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        # 解析模型检查报告
        self._parse_model_report()
        return result.returncode == 0

    def run_code_check(self):
        """执行代码规范检查"""
        print("\n" + "=" * 60)
        print("【步骤 2/4】执行代码规范检查...")
        print("=" * 60)

        script_path = self.base_dir / 'code_check' / 'py_scripts' / 'code_checker.py'
        result = subprocess.run([sys.executable, str(script_path), '--all'], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        # 解析代码检查报告
        self._parse_code_report()
        return result.returncode == 0

    def run_quality_check(self):
        """执行数据质量检查"""
        print("\n" + "=" * 60)
        print("【步骤 3/4】执行数据质量检查...")
        print("=" * 60)

        script_path = self.base_dir / 'quality_check' / 'py_scripts' / 'dq_quality_checker.py'
        result = subprocess.run([sys.executable, str(script_path), '--all'], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        # 解析质量检查报告
        self._parse_quality_report()
        return result.returncode == 0

    def _parse_model_report(self):
        """解析模型检查报告获取评分"""
        try:
            with open(self.model_report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取平均分
            import re
            match = re.search(r'整体平均得分 \*\*(\d+\.?\d*)\*\*', content)
            if match:
                score = float(match.group(1))
                self.scores['model']['score'] = score
                self.scores['model']['level'] = self._get_level(score)

            # 提取各分层评分
            for layer in ['ODS', 'DWD', 'DWS', 'DIM', 'ADS']:
                match = re.search(rf'{layer}\s*\|\s*(\d+)\s*\|\s*(\d+\.?\d*)', content)
                if match:
                    self.scores['model']['details'][layer] = {
                        'count': int(match.group(1)),
                        'score': float(match.group(2))
                    }
        except Exception as e:
            print(f"⚠️  解析模型报告失败：{e}")

    def _parse_code_report(self):
        """解析代码检查报告获取评分"""
        try:
            with open(self.code_report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            import re
            # 提取各分层平均分
            for layer in ['ODS', 'DWD', 'DWS', 'DIM', 'ADS']:
                match = re.search(rf'{layer}\s*\|\s*\d+\s*\|\s*(\d+\.?\d*)', content)
                if match:
                    self.scores['code']['details'][layer] = float(match.group(1))

            # 计算整体平均分
            details = self.scores['code']['details']
            if details:
                avg_score = sum(details.values()) / len(details)
                self.scores['code']['score'] = avg_score
                self.scores['code']['level'] = self._get_level(avg_score)
        except Exception as e:
            print(f"⚠️  解析代码报告失败：{e}")

    def _parse_quality_report(self):
        """解析质量检查报告获取评分"""
        try:
            with open(self.quality_report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            import re
            # 提取整体评分
            match = re.search(r'\*\*整体健康评分\*\*: (\d+\.?\d*) 分', content)
            if match:
                score = float(match.group(1))
                self.scores['quality']['score'] = score
                self.scores['quality']['level'] = self._get_level(score)

            # 提取分层评分
            for layer in ['ODS', 'DWD', 'DWS', 'DIM', 'ADS']:
                match = re.search(rf'{layer}\s*\|\s*(\d+\.?\d*)\s*\|', content)
                if match:
                    self.scores['quality']['details'][layer] = float(match.group(1))
        except Exception as e:
            print(f"⚠️  解析质量报告失败：{e}")

    def _get_level(self, score):
        """根据评分返回等级"""
        if score >= 90:
            return '优秀'
        elif score >= 75:
            return '良好'
        elif score >= 60:
            return '一般'
        elif score >= 40:
            return '较差'
        else:
            return '危险'

    def generate_healthy_report(self):
        """生成综合健康报告"""
        print("\n" + "=" * 60)
        print("【步骤 4/4】生成综合健康报告...")
        print("=" * 60)

        # 计算综合得分
        weights = {'model': 0.25, 'code': 0.25, 'quality': 0.30}
        overall_score = sum(
            self.scores[k]['score'] * w
            for k, w in weights.items()
            if self.scores[k]['score'] > 0
        )

        # 调整权重归一化
        total_weight = sum(w for k, w in weights.items() if self.scores[k]['score'] > 0)
        if total_weight > 0:
            overall_score = overall_score / total_weight * 0.8  # 80% 来自三个专项

        overall_level = self._get_level(overall_score)

        # 生成报告内容
        report_content = self._build_report_content(overall_score, overall_level)

        # 保存报告
        with open(self.healthy_report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"\n✅ 综合健康报告已生成：{self.healthy_report_path}")
        print(f"   综合评分：{overall_score:.2f} 分（{overall_level}）")

        return overall_score, overall_level

    def _build_report_content(self, overall_score, overall_level):
        """构建报告内容"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 计算各专项加权分
        model_weighted = self.scores['model']['score'] * 0.25
        code_weighted = self.scores['code']['score'] * 0.25
        quality_weighted = self.scores['quality']['score'] * 0.30

        # 问题统计
        model_issues = self._count_issues(self.model_report_path)
        code_issues = self._count_issues(self.code_report_path)
        quality_issues = self._count_issues(self.quality_report_path)

        report = f"""# 数仓综合健康度评估报告

**生成时间**: {timestamp}

---

## 开篇总结

本次评估完成了模型规范、代码规范、数据质量三个专项的检查。

**综合评分**: {overall_score:.2f} 分（{overall_level}）

| 专项 | 评分 | 等级 | 权重 | 加权分 |
|------|------|------|------|--------|
| 模型规范 | {self.scores['model']['score']:.1f} | {self.scores['model']['level']} | 25% | {model_weighted:.1f} |
| 代码质量 | {self.scores['code']['score']:.1f} | {self.scores['code']['level']} | 25% | {code_weighted:.1f} |
| 数据质量 | {self.scores['quality']['score']:.1f} | {self.scores['quality']['level']} | 30% | {quality_weighted:.1f} |

---

## 一、评估概览

### 1.1 综合评分

| 指标 | 值 |
|------|-----|
| 综合评分 | {overall_score:.2f} 分 |
| 健康等级 | {overall_level} |
| 检查表数 | {sum(d.get('count', 0) for d in self.scores['model']['details'].values())} |
| 问题总数 | {model_issues + code_issues + quality_issues} |

### 1.2 专项评分对比

| 专项 | 评分 | 等级 | 状态 |
|------|------|------|------|
| 模型规范检查 | {self.scores['model']['score']:.1f} | {self.scores['model']['level']} | {'✅' if self.scores['model']['score'] >= 75 else '⚠️'} |
| 代码规范检查 | {self.scores['code']['score']:.1f} | {self.scores['code']['level']} | {'✅' if self.scores['code']['score'] >= 75 else '⚠️'} |
| 数据质量检查 | {self.scores['quality']['score']:.1f} | {self.scores['quality']['level']} | {'✅' if self.scores['quality']['score'] >= 75 else '⚠️'} |

### 1.3 评分等级说明

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 数仓健康状态优秀，可放心使用 |
| 75-89 | 良好 | 数仓健康状态良好，存在轻微问题 |
| 60-74 | 一般 | 数仓健康状态一般，需要关注修复 |
| 40-59 | 较差 | 数仓健康状态较差，需要尽快修复 |
| 0-39 | 危险 | 数仓健康状态危险，必须立即处理 |

---

## 二、专项评估结果

### 2.1 模型规范检查

**评分**: {self.scores['model']['score']:.1f} 分（{self.scores['model']['level']}）

**分层详情**:
"""
        # 添加模型检查分层详情
        for layer in ['ODS', 'DWD', 'DWS', 'DIM', 'ADS']:
            if layer in self.scores['model']['details']:
                detail = self.scores['model']['details'][layer]
                report += f"\n- {layer}层：{detail.get('count', 0)} 张表，{detail.get('score', 0):.1f} 分"

        report += f"""

**报告位置**: `Data-Governance/model_check/output/model_check_report.md`

### 2.2 代码规范检查

**评分**: {self.scores['code']['score']:.1f} 分（{self.scores['code']['level']}）

**问题数量**: {code_issues} 个

**报告位置**: `Data-Governance/code_check/output/code_check_report.md`

### 2.3 数据质量检查

**评分**: {self.scores['quality']['score']:.1f} 分（{self.scores['quality']['level']}）

**问题数量**: {quality_issues} 个

**报告位置**: `Data-Governance/quality_check/output/quality_check_report.md`

---

## 三、问题分布

### 3.1 按严重程度

| 严重程度 | 模型规范 | 代码规范 | 数据质量 | 合计 |
|---------|---------|---------|---------|------|
| BLOCK (阻断) | - | - | - | {model_issues + code_issues + quality_issues} |
| WARN (警告) | - | - | - | - |
| INFO (提示) | - | - | - | - |

### 3.2 按专项分布

| 专项 | 问题数 | 占比 |
|------|--------|------|
| 模型规范 | {model_issues} | {model_issues/max(1,model_issues+code_issues+quality_issues)*100:.1f}% |
| 代码规范 | {code_issues} | {code_issues/max(1,model_issues+code_issues+quality_issues)*100:.1f}% |
| 数据质量 | {quality_issues} | {quality_issues/max(1,model_issues+code_issues+quality_issues)*100:.1f}% |

---

## 四、TOP 问题清单

### 4.1 优先处理问题

根据检查结果，以下问题建议优先处理：

1. **模型规范方面**：
   - 字段注释补充：为缺少注释的字段添加 COMMENT
   - 存储压缩配置：为 ORC/Parquet 表配置压缩格式

2. **代码规范方面**：
   - 命名规范整改：统一使用下划线命名
   - 聚合操作规范：ODS 层不应包含聚合操作

3. **数据质量方面**：
   - 时间字段修复：检查异常时间数据
   - 关键字段非空：确保主键和关键字段不为空

---

## 五、整改建议

### 5.1 优先级建议

| 优先级 | 问题类型 | 处理时限 |
|--------|---------|---------|
| P0 (紧急) | BLOCK 级问题 | 2 小时内 |
| P1 (重要) | WARN 级问题 | 24 小时内 |
| P2 (一般) | INFO 级问题 | 下周迭代 |

### 5.2 修复计划建议

1. **立即处理**（本周内）：
   - 修复所有 BLOCK 级问题
   - 补充缺失的字段注释

2. **逐步优化**（本月内）：
   - 优化命名规范
   - 配置存储压缩

3. **持续监控**（常态化）：
   - 定期执行健康检查
   - 建立质量监控机制

---

## 六、附录

### 6.1 报告位置

| 报告 | 路径 |
|------|------|
| 综合健康报告 | `Data-Governance/output/dw_healthy_report.md` |
| 模型检查报告 | `Data-Governance/model_check/output/model_check_report.md` |
| 代码检查报告 | `Data-Governance/code_check/output/code_check_report.md` |
| 质量检查报告 | `Data-Governance/quality_check/output/quality_check_report.md` |

### 6.2 评估说明

- 综合评分 = 模型规范×25% + 代码质量×25% + 数据质量×30%
- 评分等级：优秀 (90+)、良好 (75+)、一般 (60+)、较差 (40+)、危险 (<40)

---

**报告生成完成** ✅
"""
        return report

    def _count_issues(self, report_path):
        """统计报告中的问题数量"""
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            import re
            # 尝试提取 FAIL 或问题数量
            matches = re.findall(r'FAIL|失败 | 问题', content)
            return len(matches)
        except:
            return 0


def main():
    parser = argparse.ArgumentParser(description='数仓健康度评估工具')
    parser.add_argument('--all', action='store_true', help='执行完整评估流程')
    parser.add_argument('--model', action='store_true', help='仅执行模型检查')
    parser.add_argument('--code', action='store_true', help='仅执行代码检查')
    parser.add_argument('--quality', action='store_true', help='仅执行质量检查')
    parser.add_argument('--report', action='store_true', help='仅生成综合报告')

    args = parser.parse_args()

    checker = DwHealthyChecker()

    if args.all:
        # 执行完整流程
        if checker.run_model_check():
            checker.run_code_check()
            checker.run_quality_check()
        checker.generate_healthy_report()
    else:
        if args.model:
            checker.run_model_check()
        if args.code:
            checker.run_code_check()
        if args.quality:
            checker.run_quality_check()
        if args.report:
            checker._parse_model_report()
            checker._parse_code_report()
            checker._parse_quality_report()
            checker.generate_healthy_report()

    if not any([args.all, args.model, args.code, args.quality, args.report]):
        parser.print_help()


if __name__ == '__main__':
    main()
