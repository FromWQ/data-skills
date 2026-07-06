# 数仓表质量健康评估

> 本技能用于对数仓各分层表进行数据质量健康评估，生成量化评分报告。

## 触发关键词

| 关键词 | 说明 |
|--------|------|
| 质量检查 | 执行数仓数据质量检查 |
| 数据质量检查 | 对表数据进行规则检查 |
| 质量评分 | 对表进行数据质量检查并生成评分 |

## 一、前置依赖

### 1.1 数据库配置文件 `db_config.json`

位置：`Data-Governance/quality_check/input/db_config.json`

```json
{
    "name": "数据库连接名称",
    "host": "数据库主机地址",
    "port": 3306,
    "user": "用户名",
    "password": "密码",
    "database": "数据库名",
    "charset": "utf8mb4"
}
```

**说明：** 无需手动配置表列表，系统会自动扫描数据库中以 `ods/dwd/dws/ads/dim` 开头的表。

### 1.2 数据库连接工具 `db_connector.py`

位置：`Data-Governance/quality_check/py_scripts/db_connector.py`

主要功能：
- `sync_table_metadata()` - 同步表元数据到 meta_table_column 表
- `query_data(sql)` - 执行查询SQL
- `execute_sql(sql)` - 执行更新SQL

### 1.3 质量校验规则集 `rule_v2.md`

位置：`Data-Governance/quality_check/references/rule_v2.md`

包含通用规则（COM_001~COM_005）和分层专属规则（ODS/DWD/DWS/DIM/ADS）。

---

## 二、数据表结构

### 2.1 元数据表 `meta_table_column`

存储数仓表的字段元数据信息，用于识别字段类型和生成校验SQL。

```sql
CREATE TABLE `meta_table_column` (
    `id`                BIGINT          NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `table_name`        VARCHAR(128)    NOT NULL COMMENT '表名称',
    `table_comment`     VARCHAR(512)    DEFAULT NULL COMMENT '表注释/描述',
    `table_layer`       VARCHAR(16)     NOT NULL COMMENT '表所属分层：ODS/DWD/DWS/DIM/ADS',
    `column_name`       VARCHAR(64)     NOT NULL COMMENT '字段名称',
    `column_type`       VARCHAR(64)     NOT NULL COMMENT '字段类型，如：varchar(255)、decimal(18,2)',
    `column_comment`    VARCHAR(512)    DEFAULT NULL COMMENT '字段注释/描述',
    `column_tag`        VARCHAR(16)     NOT NULL DEFAULT 'ATTRIBUTE' COMMENT '字段标签：DIMENSION/MEASURE/ATTRIBUTE',
    `is_pk`             TINYINT(1)      DEFAULT 0 COMMENT '是否主键：0-否，1-是',
    `is_partition`      TINYINT(1)      DEFAULT 0 COMMENT '是否分区字段：0-否，1-是',
    `created_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_table_column` (`table_name`, `column_name`),
    KEY `idx_table_name` (`table_name`),
    KEY `idx_table_layer` (`table_layer`),
    KEY `idx_column_tag` (`column_tag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='表字段元数据表';
```

**字段标签说明：**

| 标签 | 说明 | 识别规则 |
|------|------|---------|
| DIMENSION | 维度字段 | 字段名包含/结尾：name, code, type, status, flag, org, dept, region, date, time 等 |
| MEASURE | 指标字段 | 字段名包含：mny, amount, price, cost, qty, count, rate, percent 等；或类型为 decimal/double/float 且不以 _id 结尾 |
| ATTRIBUTE | 属性字段 | 不符合上述规则的普通字段 |

### 2.2 校验结果表 `dq_check_result`

存储数据质量校验SQL执行后的结果分析内容。

```sql
CREATE TABLE `dq_check_result` (
    `id`                    BIGINT          NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `table_name`            VARCHAR(128)    NOT NULL COMMENT '被校验的表名称',
    `table_layer`           VARCHAR(16)     NOT NULL COMMENT '表所属分层：ODS/DWD/DWS/DIM/ADS',
    `partition_value`       VARCHAR(32)     DEFAULT NULL COMMENT '分区值，如：2026-04-20',
    `total_rows`            BIGINT          DEFAULT 0 COMMENT '表总记录数/分区数据量',
    `rule_id`               VARCHAR(16)     NOT NULL COMMENT '规则ID，如：COM_001、ODS_001',
    `rule_name`             VARCHAR(64)     NOT NULL COMMENT '评估规则名称',
    `rule_severity`         VARCHAR(16)     NOT NULL COMMENT '严重程度：BLOCK/WARN/INFO',
    `check_field`           VARCHAR(128)    DEFAULT NULL COMMENT '校验的字段名称',
    `check_sql`             TEXT            NOT NULL COMMENT '执行的评估SQL',
    `execute_status`        VARCHAR(16)     NOT NULL COMMENT '执行状态：SUCCESS/FAILED/TIMEOUT',
    `execute_time`          INT             DEFAULT 0 COMMENT 'SQL执行耗时(毫秒)',
    `error_message`         TEXT            DEFAULT NULL COMMENT '执行失败时的错误信息',
    `check_status`          VARCHAR(16)     NOT NULL COMMENT '校验结果状态：PASS/FAIL',
    `anomaly_count`         BIGINT          DEFAULT 0 COMMENT '异常记录数',
    `anomaly_rate`          DECIMAL(10,4)   DEFAULT 0.0000 COMMENT '异常率(百分比)',
    `check_standard`        VARCHAR(256)    DEFAULT NULL COMMENT '校验标准值',
    `actual_value`          TEXT            DEFAULT NULL COMMENT '实际检测值',
    `analysis_result`        TEXT            DEFAULT NULL COMMENT '分析结果：问题描述、原因分析、修复建议',
    `related_table`         VARCHAR(128)    DEFAULT NULL COMMENT '关联表名',
    `snapshot_data`         JSON            DEFAULT NULL COMMENT '快照数据（异常样本记录）',
    `check_time`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '校验执行时间',
    `checker`               VARCHAR(64)     DEFAULT NULL COMMENT '执行人/调度任务',
    `created_at`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_table_name` (`table_name`),
    KEY `idx_table_layer` (`table_layer`),
    KEY `idx_rule_id` (`rule_id`),
    KEY `idx_check_status` (`check_status`),
    KEY `idx_check_time` (`check_time`),
    KEY `idx_table_rule` (`table_name`, `rule_id`, `partition_value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据质量校验结果表';
```

---

## 三、评估流程

### 步骤0：初始化环境

首次执行评估前，需要完成以下初始化操作：

**操作清单：**

| 序号 | 操作内容 | 执行方式 |
|------|---------|---------|
| 1 | 创建 meta_table_column 表 | 执行第二章2.1节的DDL语句 |
| 2 | 创建 dq_check_result 表 | 执行第二章2.2节的DDL语句 |
| 3 | 同步元数据 | 执行 `python db_connector.py` 或调用 `sync_table_metadata()` |
| 4 | 补充分层信息 | 执行SQL更新table_layer字段（见下方SQL） |
| 5 | 确认规则文件 | 检查 rule_v2.md 文件存在 |

**更新分层信息SQL：**

```sql
UPDATE meta_table_column SET table_layer = 'ODS' WHERE table_name LIKE 'ods%';
UPDATE meta_table_column SET table_layer = 'DWD' WHERE table_name LIKE 'dwd%';
UPDATE meta_table_column SET table_layer = 'DWS' WHERE table_name LIKE 'dws%';
UPDATE meta_table_column SET table_layer = 'DIM' WHERE table_name LIKE 'dim%';
UPDATE meta_table_column SET table_layer = 'ADS' WHERE table_name LIKE 'ads%';
```

**验证初始化结果：**

```sql
-- 检查各分层表数量
SELECT table_layer, COUNT(DISTINCT table_name) as table_count
FROM meta_table_column GROUP BY table_layer;

-- 检查字段标签分布
SELECT table_layer, column_tag, COUNT(*) as cnt
FROM meta_table_column GROUP BY table_layer, column_tag;
```

### 步骤1：同步元数据

执行 `db_connector.py` 中的 `sync_table_metadata()` 函数，将数仓表的字段信息同步到 `meta_table_column` 表。

**筛选条件：** 表名以 ods/dwd/dws/ads/dim 开头

**输出：** 每个表的字段名称、类型、注释、自动识别的字段标签

### 步骤2：生成并执行校验SQL

根据 `rule_v2.md` 中的规则集，结合 `meta_table_column` 表中的字段信息，为每个表生成对应的校验SQL并执行。

#### 2.1 分层识别规则

| 表名前缀 | 分层 | 适用规则 |
|---------|------|---------|
| ods_ | ODS层 | 通用规则 + ODS专属规则 |
| dwd_ | DWD层 | 通用规则 + DWD专属规则 |
| dws_ | DWS层 | 通用规则 + DWS专属规则 |
| dim_ | DIM层 | 通用规则 + DIM专属规则 |
| ads_ | ADS层 | 通用规则 + ADS专属规则 |

#### 2.2 规则应用逻辑

**规则应用原则：每个规则独立判断，只要满足该规则的应用条件就执行校验。**

**通用规则（所有分层）：**

| 规则ID | 规则名称 | 应用条件 |
|--------|---------|---------|
| COM_001 | 分区连续无缺失 | 表有分区字段（pt/dt/partition_date） |
| COM_002 | 数据量波动合理 | 表有分区字段 |
| COM_003 | 关键字段非空率 | 存在主键字段（id）或关键字段 |
| COM_004 | 时间字段无异常 | 存在时间字段（datetime/date类型，或字段名/注释包含时间关键词） |
| COM_005 | 脏数据/乱码检查 | 存在varchar/text类型字段 |
| COM_006 | 金额非负检查 | 存在金额字段（字段名/注释包含mny/amount/cost/fee等） |
| COM_007 | 枚举值合法性 | 存在枚举字段（字段名/注释包含state/status/type/flag等） |

**时间字段识别规则：**

| 识别方式 | 条件 | 示例 |
|---------|------|------|
| 字段类型 | datetime/date/timestamp | create_time: datetime |
| 字段名称 | 包含time/date结尾或中间 | insert_time, desired_date, confirm_time |
| 字段注释 | 包含"时间"、"日期"关键词 | "期望完成时间"、"创建时间" |

**金额字段识别规则：**

| 识别方式 | 条件 | 示例 |
|---------|------|------|
| 字段名称 | 包含mny/amount/cost/fee/price | contract_mny, total_amount |
| 字段注释 | 包含"金额"、"费用"、"成本"关键词 | "合同金额"、"材料费" |
| 字段类型 | decimal/double/float（非_id结尾） | completed_mny: decimal(28,8) |

**分层专属规则应用条件：**

| 分层 | 规则ID | 规则名称 | 应用条件 |
|------|--------|---------|---------|
| ODS | ODS_001 | 主键缺失检查 | 存在主键字段（id） |
| ODS | ODS_002 | 主键重复检查 | 存在主键字段（id） |
| ODS | ODS_003 | 完全重复检查 | 无特殊条件（所有表都检查） |
| ODS | ODS_004 | 删除标识合法性 | 存在dr字段 |
| DWD | DWD_001 | 指标非负检查 | 存在金额/数量类字段 |
| DWD | DWD_003 | 枚举值合法性 | 存在枚举字段 |
| DWS | DWS_001 | 分组维度唯一 | 存在维度字段（name/code结尾） |
| DWS | DWS_002 | 汇总指标空值率 | 存在金额字段 |
| DIM | DIM_001 | 维度编码唯一 | 存在code字段 |
| DIM | DIM_003 | 核心属性非空 | 存在name字段 |
| ADS | ADS_001 | 分组维度唯一 | 存在维度字段 |
| ADS | ADS_002 | 关键指标非空 | 存在金额字段 |

#### 2.3 执行校验SQL流程

**执行步骤：**

1. **获取待校验表清单**
   ```sql
   SELECT DISTINCT table_name, table_layer
   FROM meta_table_column
   ORDER BY table_layer, table_name;
   ```

2. **为每个表匹配适用规则**
   - 根据table_layer确定分层
   - 根据字段信息（is_pk、column_tag、column_type等）判断规则应用条件
   - 生成该表适用的规则列表

3. **读取规则SQL模板**
   - 从rule_v2.md中读取对应规则的SQL模板
   - 将模板中的 `{table_name}`、`{key_field}` 等占位符替换为实际值

4. **执行校验SQL**
   - 使用 db_connector.query_data(sql) 执行查询
   - 记录执行开始时间和结束时间，计算耗时
   - 捕获执行异常，记录error_message

5. **解析校验结果**

   **PASS/FAIL判断逻辑：**

   | 规则类型 | PASS条件 | FAIL条件 |
   |---------|---------|---------|
   | 计数类规则 | anomaly_count = 0 | anomaly_count > 0 |
   | 空值率规则 | null_rate ≤ 阈值 | null_rate > 阈值 |
   | 波动率规则 | fluctuation_pct ≤ 30% | fluctuation_pct > 30% |
   | 枚举值规则 | invalid_count = 0 | invalid_count > 0 |

   **异常率计算：**
   ```
   anomaly_rate = anomaly_count / total_rows × 100
   ```

6. **生成分析结果**

   根据校验结果生成analysis_result字段内容，格式如下：

   ```
   【问题描述】{具体问题描述，如：id字段存在128条重复记录}
   【原因分析】{可能原因，如：上游同步任务去重逻辑缺失或数据源本身有重复}
   【修复建议】{具体建议，如：1.检查上游同步逻辑；2.执行去重SQL：DELETE FROM table WHERE id IN (...)}
   ```

#### 2.4 结果写入

将校验结果写入 `dq_check_result` 表，INSERT语句示例：

```sql
INSERT INTO dq_check_result (
    table_name, table_layer, partition_value, total_rows,
    rule_id, rule_name, rule_severity, check_field,
    check_sql, execute_status, execute_time, error_message,
    check_status, anomaly_count, anomaly_rate, check_standard,
    actual_value, analysis_result, check_time
) VALUES (
    'ods_project_base', 'ODS', '2026-04-20', 10000,
    'ODS_002', '主键重复检查', 'BLOCK', 'id',
    'SELECT COUNT(*) AS duplicate_pk_count FROM (SELECT id, COUNT(*) AS cnt FROM ods_project_base GROUP BY id HAVING COUNT(*) > 1) t',
    'SUCCESS', 125, NULL,
    'FAIL', 128, 1.28, '主键重复计数=0',
    '128条重复记录', '【问题描述】id字段存在128条重复记录\n【原因分析】上游同步任务去重逻辑缺失\n【修复建议】检查同步逻辑，执行去重',
    NOW()
);
```

**批量写入优化：**
- 每完成一个表的校验，批量INSERT该表所有规则的结果
- 使用事务保证写入完整性

### 步骤3：生成评估报告

#### 3.1 计算评分

评分公式详见第四章。核心评分SQL示例：

```sql
-- 单表评分
SELECT 
    table_name, table_layer,
    100 - (SUM(CASE WHEN rule_severity='BLOCK' AND check_status='FAIL' THEN 25 ELSE 0 END)
          + SUM(CASE WHEN rule_severity='WARN' AND check_status='FAIL' THEN 10 ELSE 0 END)
          + SUM(CASE WHEN rule_severity='INFO' AND check_status='FAIL' THEN 3 ELSE 0 END)) AS score
FROM dq_check_result
WHERE check_time >= '2026-04-20'
GROUP BY table_name, table_layer;
```

#### 3.2 输出报告

报告保存路径：`Data-Governance/quality_check/output/quality_check_report.md`

报告结构详见第五章5.1节。

---

## 四、评分体系

### 4.1 单表评分公式

```
单表得分 = 100 - (BLOCK失败数 × 25) - (WARN失败数 × 10) - (INFO失败数 × 3)

最低分为0分，不出现负分
```

**评分等级：**

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 数据质量优秀，可放心使用 |
| 75-89 | 良好 | 数据质量良好，存在轻微问题 |
| 60-74 | 一般 | 数据质量一般，需要关注 |
| 40-59 | 较差 | 数据质量较差，需要尽快修复 |
| 0-39 | 危险 | 数据质量严重问题，必须立即处理 |

### 4.2 分层评分公式

```
分层得分 = Σ(该分层所有表得分) / 该分层表数量
```

### 4.3 整体数仓评分公式

```
整体得分 = Σ(各分层得分 × 分层权重)

权重建议：
- ODS层：15%
- DWD层：25%
- DWS层：25%
- DIM层：20%
- ADS层：15%
```

### 4.4 健康度指标

| 指标 | 计算方式 | 说明 |
|------|---------|------|
| 规则通过率 | PASS数 / 总规则执行数 × 100% | 整体规则执行通过率 |
| 阻断问题数 | BLOCK级别FAIL总数 | 必须立即处理的问题数 |
| 警告问题数 | WARN级别FAIL总数 | 需要关注的问题数 |
| 提示问题数 | INFO级别FAIL总数 | 建议优化的问题数 |

---

## 五、报告格式与评估原则

### 5.1 报告格式形式

评估报告采用 **Markdown格式**，输出文件命名规则：`质量评估报告_{YYYYMMDD_HHmmss}.md`

**报告结构（六大章节）：**

| 章节 | 内容要点 |
|------|---------|
| 开篇总结 | 整体健康状态概述（100-200字），突出核心问题，给出改进方向建议 |
| 一、评估概览 | 整体评分、规则通过率、分层评分汇总表 |
| 二、问题分布 | 严重程度分布图、问题规则TOP10排行 |
| 三、分层详情 | 各分层表评分排行、问题明细列表 |
| 四、问题处理建议 | 阻断级问题清单（附修复建议）、警告级问题清单 |
| 五、趋势对比 | 与历史评估结果对比（如有历史数据） |
| 六、附录 | 评估规则清单、数据来源说明 |

**报告特点：**
- 表格为主，数据直观清晰
- 支持可视化进度条展示问题分布
- 问题明细附分析结果和修复建议
- 报告底部标注生成时间和版本号

### 5.2 评估原则

**原则一：分层优先级原则**

评估优先级：BLOCK > WARN > INFO

- BLOCK级问题发现后应立即阻断下游同步
- WARN级问题记录日志，定时汇总通知
- INFO级问题仅记录，供后续分析参考

**原则二：问题处理时效原则**

| 严重程度 | 处理时限 | 责任人 |
|---------|---------|--------|
| BLOCK | 2小时内 | 表负责人 |
| WARN | 24小时内评估 | 数据管理员 |
| INFO | 下周迭代评估 | 数据管理员 |

**原则三：大表采样原则**

单表数据量超过1000万行时：
- 使用采样查询（如 LIMIT 10000）
- 或按分区抽样检查
- 避免全表扫描影响性能

**原则四：历史对比原则**

每次评估结果保留历史记录，支持：
- 同表不同时期质量趋势分析
- 同分层整体健康度变化趋势
- 问题修复效果验证

**原则五：客观量化原则**

评分计算完全基于规则执行结果：
- 不主观评判，以SQL执行结果为准
- 异常数量、异常率均为实测值
- 分析结果包含问题原因和具体修复SQL建议

---

## 六、执行脚本

本skill配套Python执行脚本 `dq_quality_checker.py`，可一键执行完整评估流程。

### 6.1 脚本位置

`Data-Governance/quality_check/py_scripts/dq_quality_checker.py`

### 6.2 使用方式

```bash
# 初始化环境（首次执行）
python dq_quality_checker.py --init

# 同步元数据
python dq_quality_checker.py --sync

# 执行校验SQL
python dq_quality_checker.py --check

# 生成评估报告
python dq_quality_checker.py --report

# 执行完整流程（初始化 + 同步 + 校验 + 报告）
python dq_quality_checker.py --all
```

### 6.3 脚本功能模块

| 模块 | 功能 | 对应skill步骤 |
|------|------|--------------|
| init_environment() | 创建表、添加字段、更新分层信息 | 步骤0 |
| sync_metadata() | 调用db_connector同步元数据 | 步骤1 |
| run_all_checks() | 获取表清单、匹配规则、执行SQL、写入结果 | 步骤2 |
| generate_report() | 计算评分、生成Markdown报告 | 步骤3 |

---

## 七、注意事项

1. **分区表处理**：对于分区表，优先校验最新分区数据
2. **大表优化**：单表数据量超过1000万时，使用采样查询或限制条数
3. **执行顺序**：先执行BLOCK级别规则，发现问题立即阻断
4. **并发控制**：同一时间只允许一个评估任务运行
5. **历史保留**：评估结果按check_time保留，支持历史对比分析