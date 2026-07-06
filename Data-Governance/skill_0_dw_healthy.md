---
name: 数仓健康度评估总控
description: 串联 skill_1/2/3 执行完整的数仓健康度评估，生成综合健康报告。
---

# 数仓健康度评估总控 Skill

## 一、概述

本 skill 是数仓健康度评估的总控入口，负责串联执行以下三个专项评估：

| 专项 | Skill | 说明 | 输出报告 |
|------|-------|------|---------|
| 模型规范检查 | skill_1_model_check | 检查数据表模型设计规范 | `model_check_report.md` |
| 代码规范检查 | skill_2_code_check | 检查 SQL 代码规范和质量 | `code_check_report.md` |
| 数据质量检查 | skill_3_quality_check | 检查数据质量和完整性 | `quality_check_report.md` |

执行完成后，基于三个专项报告生成**综合健康度报告**：`dw_healthy_report.md`

## 二、前置要求

### 2.1 环境依赖

| 依赖项 | 版本 | 用途 |
|--------|------|------|
| Python | 3.8+ | 执行脚本 |
| MySQL | 5.7+ | 数据库连接 |
| pandas | 1.0+ | 数据处理 |
| openpyxl | 3.0+ | Excel 生成 |
| pymysql | 1.0+ | 数据库连接 |

### 2.2 安装命令

```bash
pip3 install pandas openpyxl pymysql
```

### 2.3 目录结构

```
Data-Governance/
├── skill_0_dw_healthy.md        # 本文件（总控）
├── skill_1_model_check/         # 模型规范检查
├── skill_2_code_check/          # 代码规范检查
├── skill_3_quality_check/       # 数据质量检查
└── output/                      # 输出目录
    ├── model_check_report.md    # 模型检查报告
    ├── code_check_report.md     # 代码检查报告
    ├── quality_check_report.md  # 质量检查报告
    └── dw_healthy_report.md     # 综合健康报告（最终输出）
```

## 三、核心工作流

### 步骤 1：执行模型规范检查

```bash
python Data-Governance/model_check/py_scripts/model_checker.py
```

**检查内容**：
- 表命名规范（分层前缀、长度、命名规则）
- 字段规范（注释、命名、类型）
- 分区规范（分区字段设计）
- 存储规范（存储格式、压缩配置）

**输出**：
- `Data-Governance/model_check/output/model_check_report.md`
- `Data-Governance/model_check/output/model_check_result.xlsx`

### 步骤 2：执行代码规范检查

```bash
python Data-Governance/code_check/py_scripts/code_checker.py --all
```

**检查内容**：
- 安全合规检查（敏感数据、SQL 注入、权限）
- 性能优化检查（全表扫描、笛卡尔积、分区剪裁）
- 分层原则检查（ODS/DWD/DWS/ADS 分层规范）
- 代码规范检查（命名、注释、格式）
- SQL 反模式检查（SELECT *、隐式转换、负向查询）

**输出**：
- `Data-Governance/code_check/output/code_check_report.md`
- `Data-Governance/code_check/output/code_check_result.xlsx`

### 步骤 3：执行数据质量检查

```bash
python Data-Governance/quality_check/py_scripts/dq_quality_checker.py --all
```

**检查内容**：
- 通用规则（分区连续性、数据量波动、关键字段非空、时间字段合理性、脏数据检查）
- 分层专属规则（ODS/DWD/DWS/DIM/ADS 各层专属规则）

**输出**：
- `Data-Governance/quality_check/output/quality_check_report.md`
- `Data-Governance/quality_check/output/quality_check_result.xlsx`

### 步骤 4：生成综合健康报告

基于上述三个报告，生成综合健康度报告 `dw_healthy_report.md`。

**综合评分计算公式**：

```
综合得分 = 模型规范 × 25% + 代码质量 × 25% + 数据质量 × 30% + 血缘健康 × 20%

权重说明：
- 模型规范 (25%)：表设计是基础
- 代码质量 (25%)：SQL 质量影响运行效率
- 数据质量 (30%)：数据准确性最重要
- 血缘健康 (20%)：数据可追溯性
```

**评分等级**：

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 数仓健康状态优秀，可放心使用 |
| 75-89 | 良好 | 数仓健康状态良好，存在轻微问题 |
| 60-74 | 一般 | 数仓健康状态一般，需要关注修复 |
| 40-59 | 较差 | 数仓健康状态较差，需要尽快修复 |
| 0-39 | 危险 | 数仓健康状态危险，必须立即处理 |

## 四、一键执行脚本

### 4.1 完整执行

```bash
python Data-Governance/py_scripts/dw_healthy_checker.py --all
```

### 4.2 分步执行

```bash
# 仅执行模型检查
python Data-Governance/py_scripts/dw_healthy_checker.py --model

# 仅执行代码检查
python Data-Governance/py_scripts/dw_healthy_checker.py --code

# 仅执行质量检查
python Data-Governance/py_scripts/dw_healthy_checker.py --quality

# 仅生成综合报告
python Data-Governance/py_scripts/dw_healthy_checker.py --report
```

## 五、综合报告格式

综合健康度报告 `dw_healthy_report.md` 包含以下章节：

```markdown
# 数仓综合健康度评估报告

**生成时间**: YYYY-MM-DD HH:MM:SS

## 开篇总结
- 整体评分和等级
- 各专项评分汇总
- 核心问题概述

## 一、评估概览
### 1.1 综合评分
### 1.2 专项评分对比
### 1.3 评分等级说明

## 二、专项评估结果
### 2.1 模型规范检查
### 2.2 代码规范检查
### 2.3 数据质量检查

## 三、问题分布
### 3.1 按严重程度
### 3.2 按问题类型
### 3.3 按分层分布

## 四、TOP 问题清单
### 4.1 阻断级问题 (BLOCK)
### 4.2 警告级问题 (WARN)

## 五、整改建议
### 5.1 优先级建议
### 5.2 修复计划建议

## 六、最佳实践
```

## 六、输出文件说明

| 文件名 | 位置 | 说明 |
|--------|------|------|
| `dw_healthy_report.md` | `Data-Governance/output/` | **综合健康报告（最终输出）** |
| `model_check_report.md` | `Data-Governance/model_check/output/` | 模型规范检查报告 |
| `code_check_report.md` | `Data-Governance/code_check/output/` | 代码规范检查报告 |
| `quality_check_report.md` | `Data-Governance/quality_check/output/` | 数据质量检查报告 |

## 七、注意事项

### 7.1 执行顺序

必须按以下顺序执行：
1. 模型规范检查 → 2. 代码规范检查 → 3. 数据质量检查 → 4. 生成综合报告

### 7.2 数据依赖

- 质量检查依赖数据库连接（需配置 `db_config.json`）
- 模型和代码检查基于文件执行（无需数据库）

### 7.3 执行时间

根据数仓规模，执行时间大致如下：

| 表数量 | 预计时间 |
|--------|---------|
| 1-10 张 | 3-5 分钟 |
| 10-50 张 | 5-15 分钟 |
| 50-100 张 | 15-30 分钟 |
| 100+ 张 | 30+ 分钟 |

### 7.4 常见问题

**问题 1：数据库连接失败**
```
解决方案：检查 input/db_config.json 配置是否正确
```

**问题 2：openpyxl 库缺失**
```
解决方案：pip3 install openpyxl
```

**问题 3：报告生成失败**
```
解决方案：确认三个专项报告已生成
```

## 八、示例输出

### 综合评分表示例

| 专项 | 评分 | 权重 | 加权分 |
|------|------|------|--------|
| 模型规范 | 89.8 | 25% | 22.5 |
| 代码质量 | 75.0 | 25% | 18.8 |
| 数据质量 | 97.8 | 30% | 29.3 |
| 血缘健康 | N/A | 20% | 0.0 |
| **综合得分** | **70.6** | 100% | **70.6** |

### 评级结果

```
数仓健康等级：一般（70.6 分）

建议：
1. 优先修复 BLOCK 级问题
2. 逐步处理 WARN 级问题
3. 持续监控数据质量
```

---

*文档版本：v2.0*
*更新时间：2026-07-06*
