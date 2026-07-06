# 数仓数据质量评估系统

> 一键执行数仓各分层表的数据质量健康评估，生成量化评分报告。

---

## 📁 目录结构

```
skill_3_quality_check/
├── input/                      # 输入目录
│   └── db_config.json          # 数据库配置（需修改）
├── output/                     # 输出目录（空）
├── py_scripts/                 # Python 脚本
│   ├── db_connector.py         # 数据库连接工具
│   └── dq_quality_checker.py   # 主执行脚本
├── references/                 # 参考文档
│   ├── README.md               # 本文档
│   ├── rule_v2.md              # 质量校验规则集
│   ├── 部署指南.md              # 部署说明
│   └── 执行问题记录.md          # 问题记录
└── output/                    # 评估报告输出
    └── quality_check_report.md
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install pymysql
```

### 2. 配置数据库

编辑 `input/db_config.json`：

```json
{
    "name": "你的配置名称",
    "host": "你的 MySQL 地址",
    "port": 3306,
    "user": "你的用户名",
    "password": "你的密码",
    "database": "你的数据库名",
    "charset": "utf8mb4"
}
```

### 3. 执行评估

```bash
# 进入项目目录
cd /path/to/skill_3_quality_check

# 一键执行完整流程
python3 py_scripts/dq_quality_checker.py --all
```

### 4. 查看报告

```bash
cat output/quality_check_report.md
```

---

## 📊 评估规则

### 通用规则 (COM_001 ~ COM_005)

| 规则 ID | 规则名称 | 严重程度 |
|--------|---------|---------|
| COM_001 | 分区连续无缺失 | BLOCK |
| COM_002 | 数据量波动合理 | WARN |
| COM_003 | 关键字段非空率 | BLOCK |
| COM_004 | 时间字段无异常 | WARN |
| COM_005 | 脏数据/乱码检查 | INFO |

### 分层专属规则

| 分层 | 规则数量 | 规则 ID 范围 |
|------|---------|-------------|
| ODS | 4 条 | ODS_001 ~ ODS_004 |
| DWD | 3 条 | DWD_001 ~ DWD_003 |
| DWS | 3 条 | DWS_001 ~ DWS_003 |
| DIM | 3 条 | DIM_001 ~ DIM_003 |
| ADS | 3 条 | ADS_001 ~ ADS_003 |

详细规则见 `references/rule_v2.md`。

---

## 📈 评分体系

### 单表评分

```
单表得分 = 100 - (BLOCK 失败数 × 25) - (WARN 失败数 × 10) - (INFO 失败数 × 3)
最低分为 0 分
```

### 评分等级

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 数据质量优秀，可放心使用 |
| 75-89 | 良好 | 数据质量良好，存在轻微问题 |
| 60-74 | 一般 | 数据质量一般，需要关注 |
| 40-59 | 较差 | 数据质量较差，需要尽快修复 |
| 0-39 | 危险 | 数据质量严重问题，必须立即处理 |

---

## 🔧 命令行参数

```bash
python3 py_scripts/dq_quality_checker.py --help

可选参数:
  --init      初始化环境（创建表）
  --sync      同步元数据
  --check     执行质量检查
  --report    生成评估报告
  --all       执行完整流程
```

---

## 📂 输出说明

### 数据库表

| 表名 | 说明 |
|------|------|
| `meta_table_column` | 表字段元数据表 |
| `dq_check_result` | 质量校验结果表 |

### 评估报告

位置：`output/quality_check_report.md`

报告包含：
- 开篇总结
- 评估概览（整体评分、规则通过率、分层评分）
- 问题分布（严重程度、TOP10 排行）
- 分层详情
- 问题处理建议
- 趋势对比
- 附录

**注意**: 每次执行评估会覆盖原有的报告文件。

### 检查结果表 (Excel)

位置：`output/quality_check_result.xlsx`

Excel 文件包含 1 个 Sheet：`质量检查结果`

| 列名 | 说明 |
|------|------|
| 表名 | 被检查的表名称 |
| 分层 | ODS/DWD/DWS/DIM/ADS |
| 规则 ID | 规则编号 |
| 规则名称 | 规则名称 |
| 严重程度 | BLOCK/WARN/INFO |
| 检查字段 | 被检查的字段 |
| 检查状态 | PASS/FAIL |
| 异常数量 | 异常记录数 |
| 总记录数 | 表总记录数 |
| 异常率 (%) | 异常记录占比 |
| 校验标准 | 校验标准值 |
| 实际值 | 实际检测值 |
| 分析结果 | 问题描述、原因分析、修复建议 |
| 检查时间 | 校验执行时间 |

**注意**: 每次执行评估会覆盖原有的结果表文件，数据来源于 `dq_check_result` 表。

**依赖**: 需要安装 `openpyxl` 库 (`pip3 install openpyxl`)

---

## ⚠️ 注意事项

1. **数据库权限**：确保有创建表和查询的权限
2. **执行时间**：根据表数量，约 3-20 分钟不等
3. **大表优化**：超过 1000 万行的表会自动使用 LIMIT 采样
4. **配置文件**：`host` 不要包含 `jdbc:` 前缀

---

## 📞 技术支持

- 部署指南：见 `references/部署指南.md`
- 问题记录：见 `references/执行问题记录.md`
- 规则详情：见 `references/rule_v2.md`

---

*文档版本：v1.1*
*更新时间：2026-07-06*
