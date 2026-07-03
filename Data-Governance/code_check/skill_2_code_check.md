# 数仓代码检查

> 本技能用于对数仓各分层（ODS/DIM/DWD/DWS/ADS）的 SQL 代码进行质量评估，生成量化评分报告。
> **说明**：本技能采用纯文件处理方式，中间表和结果表不落本地数据库，所有处理结果直接输出到对应目录。

## 触发关键词

| 关键词 | 说明 |
|--------|------|
| 检查 SQL 代码 | 执行数仓代码质量检查 |
| SQL 代码检查 | 对 SQL 代码进行规则检查 |
| 代码评分 | 评估 SQL 代码质量并生成评分 |
| 代码审查 | 审查数仓 SQL 代码规范 |

---

## 一、前置依赖

### 1.1 任务信息来源 `task_info_data.xlsx`

位置：`Data-Governance/code_check/input/task_info_data.xlsx`

核心字段：
- `tenant_id`     -- 租户 ID
- `project_id`    -- 项目 ID
- `name`          -- 任务名称
- `task_type`     -- 任务类型 (17=hiveSQL)
- `sql_text`      -- SQL 文本
- `is_deleted`    -- 是否删除：0-否，1-是
- `gmt_create`    -- 创建时间
- `gmt_modified`  -- 修改时间

### 1.2 代码检查规则集 `code_rules.md`

位置：`Data-Governance/code_check/references/code_rules.md`

包含 SQL 代码检查规则和最佳实践，共 5 大类 45 条规则。

---

## 二、检查规则

### 2.1 代码规范检查

基于《数据中台项目 - 数据开发标准》编码规范章节提炼：

| 规则 ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_NAM_001 | 命名规范 | 表名、字段名使用下划线命名 | WARN |
| COD_NAM_002 | 分层前缀规范 | 表名必须以分层前缀开头（ods/dwd/dws/dim/ads） | WARN |
| COD_NAM_003 | 注释规范 | 必须包含功能说明注释 | WARN |
| COD_NAM_004 | 别名规范 | 别名应有意义，避免使用 a/b/c 等单字母 | INFO |
| COD_NAM_005 | 字段命名一致性 | 同类型字段在不同表中命名应一致 | WARN |
| COD_NAM_006 | 时间字段规范 | 必须包含 gmt_create 和 gmt_modified 字段 | WARN |
| COD_NAM_007 | 主键字段规范 | 主键字段建议使用 id 或{table}_id 命名 | INFO |
| COD_NAM_008 | 布尔字段规范 | 布尔字段建议使用 is_/has_/can_前缀 | INFO |
| COD_NAM_009 | 关联字段规范 | 外键字段建议使用{table}_id 格式 | INFO |
| COD_NAM_010 | 禁用保留字 | 禁止使用 SQL 保留字作为表名或字段名 | WARN |
| COD_NAM_011 | 驼峰命名规范 | 字段名禁用驼峰命名，必须使用下划线 | WARN |
| COD_NAM_012 | 表名长度规范 | 表名长度建议 3-50 字符 | INFO |
| COD_NAM_013 | 字段长度规范 | VARCHAR 字段建议明确长度，避免过长 | INFO |
| COD_NAM_014 | 数字类型规范 | 金额字段必须使用 DECIMAL，禁止使用 FLOAT/DOUBLE | WARN |
| COD_NAM_015 | 代码头部注释 | SQL 文件头部必须有主题、功能描述、创建者、创建日期 | WARN |
| COD_NAM_016 | 修改日志注释 | 代码头部必须有修改日志记录 | INFO |
| COD_NAM_017 | 单行字段规范 | SELECT 语句字段按每行一个字段编排 | INFO |
| COD_NAM_018 | AS 对齐规范 | 多个字段的 AS 建议对齐在同一列 | INFO |
| COD_NAM_019 | 子句换行规范 | FROM/WHERE/GROUP BY 等子句需换行编写 | INFO |
| COD_NAM_020 | 运算符空格规范 | 算术运算符、逻辑运算符前后保留一个空格 | INFO |
| COD_NAM_021 | CASE 语句规范 | CASE 语句必须包含 ELSE 子语 | WARN |
| COD_NAM_022 | 字段注释规范 | 字段注释紧跟在字段后面 | WARN |

### 2.2 性能优化检查

| 规则 ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_PER_001 | 全表扫描预警 | 检测无 WHERE 条件的 SELECT | BLOCK |
| COD_PER_002 | 笛卡尔积检测 | 检测笛卡尔积 JOIN（JOIN 前无 ON 条件） | BLOCK |
| COD_PER_003 | 大表 LIMIT 限制 | 大表查询未限制返回行数（LIMIT>10000 或无 LIMIT） | WARN |
| COD_PER_004 | COUNT 优化 | 建议使用 COUNT(*) 或 COUNT(1) 而非 COUNT(字段) | INFO |
| COD_PER_005 | 模糊查询前缀 | 避免左百分号的 LIKE 查询 | WARN |
| COD_PER_006 | 批量 INSERT | 建议使用批量 INSERT 而非逐条 INSERT | INFO |

### 2.3 SQL 反模式检查

| 规则 ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_ANT_001 | SELECT * | 禁止使用 SELECT * | WARN |
| COD_ANT_002 | 隐式类型转换 | 避免字段类型隐式转换 | WARN |
| COD_ANT_003 | 负面查询 | NOT IN / NOT EXISTS 性能差，建议改写 | WARN |
| COD_ANT_004 | OR 条件优化 | OR 条件建议改写为 UNION ALL | WARN |
| COD_ANT_005 | 子查询嵌套 | 避免超过 2 层嵌套子查询 | WARN |
| COD_ANT_006 | 分页深度 | 避免大偏移量分页（OFFSET>10000） | INFO |

### 2.4 安全合规检查

| 规则 ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_SEC_001 | 敏感字段脱敏 | 手机号、身份证必须脱敏 | BLOCK |
| COD_SEC_002 | 危险操作预警 | 避免直接 DROP TABLE/TRUNCATE TABLE | BLOCK |
| COD_SEC_003 | 无限制 DELETE | DELETE 操作必须带 WHERE 条件 | BLOCK |
| COD_SEC_004 | 明文密码检测 | 禁止在 SQL 中出现明文密码 | BLOCK |
| COD_SEC_005 | 邮箱脱敏 | 邮箱地址应部分脱敏 | WARN |
| COD_SEC_006 | 银行账号脱敏 | 银行账号必须脱敏 | BLOCK |

### 2.5 分层原则检查

| 规则 ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_LAY_001 | ODS 层禁止聚合 | ODS 层不应包含聚合计算 | BLOCK |
| COD_LAY_002 | DWD 层禁止跨层引用 | DWD 只引用 ODS/DIM | BLOCK |
| COD_LAY_003 | DWS 层单主题域 | DWS 按主题域组织 | WARN |
| COD_LAY_004 | ADS 层引用规范 | ADS 只引用 DWS/DIM | BLOCK |
| COD_LAY_005 | DIM 层禁止引用明细 | DIM 只引用 ODS/DIM，禁止引用 DWD/DWS/ADS | BLOCK |

---

## 三、处理流程

执行脚本：`Data-Governance/code_check/py_scripts/code_checker.py`

> **重要说明**：本技能采用纯文件处理方式，所有中间结果和最终结果均通过文件传递，不依赖数据库。

### 步骤 1：读取 Excel 数据

从 `input/task_info_data.xlsx` 读取任务数据，筛选有效 SQL 代码：

```python
import pandas as pd

df = pd.read_excel('input/task_info_data.xlsx')
```

### 步骤 2：加载检查规则

从 `references/code_rules.md` 加载 44 条检查规则：

```python
rules = load_rules('references/code_rules.md')
# 返回规则列表：
# [{'rule_id': 'COD_NAM_001', 'rule_name': '命名规范', 'severity': 'WARN', ...}, ...]
```

### 步骤 3：执行规则检查

对每条 SQL 代码应用所有规则进行检查：

```python
for code in valid_codes:
    sql_text = code['sql_text']
    for rule in rules:
        is_fail = check_rule(sql_text, rule)
        # 记录检查结果
```

### 步骤 4：计算代码评分

**评分公式：**

```
代码得分 = 100 - (BLOCK 失败数 × 25) - (WARN 失败数 × 10) - (INFO 失败数 × 3)
```

**分层评分统计：**

```python
# 按分层聚合评分
layer_scores = {}
for code_id, score_info in code_scores.items():
    layer = score_info['code_layer']
    # 计算该层平均分、问题数等
```

### 步骤 5：保存检查结果

将检查结果保存为 Excel 文件：

输出位置：`Data-Governance/code_check/output/code_check_result.xlsx`

Excel 包含以下工作表：
- `检查结果汇总` - 所有检查规则的执行结果
- `代码评分表` - 每条代码的得分情况
- `分层统计表` - 各分层的聚合统计
- `问题明细表` - 所有问题的详细信息

### 步骤 6：生成检查报告

将检查结果输出为 Markdown 格式的报告：

输出位置：`Data-Governance/code_check/output/code_check_report.md`

---

## 四、评分体系

### 4.1 评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 规范符合度 | 20% | 命名、注释、格式规范 |
| 性能表现 | 25% | 查询效率、资源占用 |
| 安全合规 | 25% | 敏感数据、权限控制 |
| 分层原则 | 15% | 分层设计规范性 |
| 代码质量 | 15% | 可读性、可维护性 |

### 4.2 评分等级

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 代码质量优秀 |
| 75-89 | 良好 | 代码质量良好 |
| 60-74 | 一般 | 代码质量一般 |
| 40-59 | 较差 | 代码质量较差 |
| 0-39 | 危险 | 存在严重问题 |

---

## 五、报告格式

### 5.1 报告结构

| 章节 | 内容 |
|------|------|
| 开篇总结 | 整体代码质量概述 |
| 一、评估概览 | 整体评分、分层评分 |
| 二、问题分布 | 严重程度分布、问题类型分布 |
| 三、分层详情 | 各分层代码问题明细 |
| 四、TOP 问题 | 问题代码排行 |
| 五、整改建议 | 修复建议 |
| 六、最佳实践 | 代码优化建议 |

### 5.2 报告示例

```markdown
# 数仓代码检查报告

## 开篇总结
本次检查覆盖 X 个代码，发现 Y 个问题...

## 一、评估概览
| 分层 | 代码数 | 平均分 | BLOCK | WARN |
|------|--------|--------|-------|------|
| ODS | 30 | 85 | 2 | 5 |
...
```

---

## 六、执行脚本

配套脚本 `code_checker.py`：

```bash
# 执行代码检查
python py_scripts/code_checker.py --all

# 指定分层检查
python py_scripts/code_checker.py --layers ods,dwd

# 指定代码检查
python py_scripts/code_checker.py --code-ids 1,2,3
```

---

## 七、输出说明

### 7.1 输出目录结构

```
Data-Governance/code_check/output/
├── code_check_report.md       # Markdown 检查报告
├── code_check_result.xlsx     # Excel 检查结果
└── logs/
    └── code_check.log         # 执行日志（可选）
```

### 7.2 Excel 输出格式

`code_check_result.xlsx` 包含以下工作表：

| 工作表名称 | 说明 | 列名 |
|-----------|------|------|
| 检查结果汇总 | 所有规则检查详情 | 代码 ID, 任务名称，所属分层，规则 ID, 规则名称，严重程度，检查结果，问题描述，整改建议 |
| 代码评分表 | 每条代码得分 | 代码 ID, 任务名称，所属分层，BLOCK 问题数，WARN 问题数，INFO 问题数，最终得分 |
| 分层统计表 | 各分层聚合统计 | 分层，代码数，平均分，最高分，最低分，BLOCK 总数，WARN 总数 |
| 问题明细表 | 所有问题详情 | 任务名称，规则 ID, 规则名称，严重程度，问题描述，整改建议 |

---

## 八、注意事项

1. **安全第一**：敏感数据检查必须通过
2. **性能优先**：BLOCK 级性能问题必须修复
3. **分层原则**：严格遵守数仓分层规范
4. **持续检查**：建议集成到 CI/CD 流程
5. **文件处理**：本技能不依赖数据库，所有数据通过 Excel 文件传递
