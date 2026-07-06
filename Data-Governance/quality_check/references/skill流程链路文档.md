# 数仓表质量健康评估 Skill 流程链路文档

> 版本：v1.0
> 更新时间：2026-04-23

---

## 一、前置材料

### 1.1 材料清单

| 序号 | 材料名称 | 存放位置 | 形态 | 用途 |
|------|---------|---------|------|------|
| 1 | 数据库配置 | Data-Governance/quality_check/input/db_config.json | JSON文件 | 建立MySQL连接 |
| 2 | 质量校验规则集 | Data-Governance/quality_check/references/rule_v2.md | Markdown文件 | 提供校验标准和SQL模板 |
| 3 | 数仓表数据 | MySQL数据库 fengji | 数据库表 | 被校验的业务数据 |
| 4 | 执行脚本 | Data-Governance/quality_check/py_scripts/dq_quality_checker.py | Python文件 | 自动化执行载体 |

### 1.2 数据库配置详情

**db_config.json 文件字段说明：**

| 字段 | 类型 | 含义 | 示例 |
|------|------|------|------|
| name | string | 连接标识名 | 数仓质量评估数据库配置 |
| host | string | MySQL主机地址 | localhost |
| port | int | 端口号 | 3306 |
| user | string | 用户名 | root |
| password | string | 密码 | root |
| database | string | 数据库名 | warehouse_test |
| charset | string | 字符集 | utf8mb4 |

### 1.3 规则集详情

**rule_v2.md 规则分类：**

| 类别 | 数量 | 适用对象 | 编号范围 |
|------|------|---------|---------|
| 通用规则 | 5条 | 全分层 | COM_001~COM_005 |
| ODS层专属 | 4条 | ODS层表 | ODS_001~ODS_004 |
| DWD层专属 | 3条 | DWD层表 | DWD_001~DWD_003 |
| DWS层专属 | 3条 | DWS层表 | DWS_001~DWS_003 |
| DIM层专属 | 3条 | DIM层表 | DIM_001~DIM_003 |
| ADS层专属 | 3条 | ADS层表 | ADS_001~ADS_003 |

**规则信息项：** 规则ID、规则名称、严重程度(BLOCK/WARN/INFO)、校验标准、SQL模板

### 1.4 数仓表筛选范围

**表名前缀匹配：**

| 前缀 | 分层 | 全称 |
|------|------|------|
| ods | ODS层 | 原始接入层 |
| dwd | DWD层 | 明细清洗层 |
| dws | DWS层 | 汇总宽表层 |
| dim | DIM层 | 维度层 |
| ads | ADS层 | 应用报表层 |

---

## 二、执行流程

### 2.1 流程概览

| 阶段 | 名称 | 执行参数 | 核心任务 |
|------|------|---------|---------|
| 阶段0 | 环境初始化 | --init | 创建表结构，补全字段 |
| 阶段1 | 元数据同步 | --sync | 读取字段信息写入元数据表 |
| 阶段2 | 规则校验 | --check | 生成并执行校验SQL，记录结果 |
| 阶段3 | 报告生成 | --report | 计算评分，输出Markdown报告 |

### 2.2 阶段0：环境初始化

**目标：** 建立评估所需的存储结构

**操作明细：**

| 序号 | 操作 | SQL或判断逻辑 | 条件 |
|------|------|--------------|------|
| 0-1 | 检查table_layer字段 | SELECT FROM information_schema.COLUMNS WHERE COLUMN_NAME='table_layer' | 无则添加 |
| 0-2 | 添加table_layer字段 | ALTER TABLE meta_table_column ADD COLUMN table_layer VARCHAR(16) | 0-1无结果时执行 |
| 0-3 | 检查dq_check_result表 | SELECT FROM information_schema.TABLES WHERE TABLE_NAME='dq_check_result' | 无则创建 |
| 0-4 | 创建dq_check_result表 | CREATE TABLE dq_check_result (...) | 0-3无结果时执行 |
| 0-5 | 更新分层标识 | UPDATE meta_table_column SET table_layer='ODS' WHERE table_name LIKE 'ods%' | 按五个分层分别执行 |
| 0-6 | 验证结果 | SELECT table_layer, COUNT(DISTINCT table_name) GROUP BY table_layer | 输出各层表数 |

### 2.3 阶段1：元数据同步

**目标：** 将数仓表字段信息结构化存储到meta_table_column表

**操作明细：**

| 序号 | 操作 | 数据来源 | 处理方式 |
|------|------|---------|---------|
| 1-1 | 获取表清单 | information_schema.TABLES | WHERE TABLE_NAME LIKE 'ods%' OR 'dwd%'... |
| 1-2 | 获取字段信息 | information_schema.COLUMNS | 遍历每张表 |
| 1-3 | 识别字段标签 | 字段名关键词匹配 | name/code结尾→DIMENSION，mny/amount→MEASURE，其他→ATTRIBUTE |
| 1-4 | 判断主键 | column_name='id' | is_pk=1 |
| 1-5 | 判断分区字段 | column_name IN ('pt','dt','partition_date') | is_partition=1 |
| 1-6 | 批量写入 | INSERT INTO meta_table_column | 每表所有字段 |
| 1-7 | 更新分层 | UPDATE table_layer | 按表名前缀 |

**字段标签识别规则：**

| 标签 | 匹配关键词 | 示例字段 |
|------|---------|---------|
| DIMENSION | name, code, type, status, flag, org, date, time | org_name, bill_status |
| MEASURE | mny, amount, cost, price, qty, rate, percent 或 decimal类型 | contract_mny, total_amount |
| ATTRIBUTE | 不符合以上规则 | memo, create_user_code |

### 2.4 阶段2：规则校验

**目标：** 对每张表执行适用的质量校验规则，记录异常情况

**操作明细：**

| 序号 | 操作 | 处理逻辑 |
|------|------|---------|
| 2-1 | 清空本次历史结果 | DELETE FROM dq_check_result WHERE check_time < NOW()-1秒 |
| 2-2 | 获取待校验表 | SELECT DISTINCT table_name, table_layer FROM meta_table_column |
| 2-3 | 统计表数据量 | SELECT COUNT(*) as total_rows FROM {表名} |
| 2-4 | 匹配适用规则 | 按table_layer筛选，按字段类型判断是否应用 |
| 2-5 | 识别字段类型 | 时间字段(datetime类型/name含time)、金额字段(name含mny/amount)、枚举字段(name含status/flag) |
| 2-6 | 生成校验SQL | 替换规则模板中的{table_name}、{field_name}占位符 |
| 2-7 | 执行SQL | query_data(check_sql)，记录开始和结束时间 |
| 2-8 | 解析结果 | 获取anomaly_count，计算anomaly_rate = count/total_rows×100 |
| 2-9 | 判断状态 | anomaly_count=0 → PASS，否则 → FAIL |
| 2-10 | 生成分析文本 | PASS → "{规则名}校验通过"，FAIL → "{字段}存在{数量}条{问题类型}" |
| 2-11 | 写入结果表 | INSERT INTO dq_check_result (所有字段) |

**规则应用判断表：**

| 规则 | 应用条件 | 检查字段识别 |
|------|---------|-------------|
| ODS_001 主键缺失 | 有id字段 | column_name='id' |
| ODS_002 主键重复 | 有id字段 | column_name='id' |
| ODS_004 删除标识 | 有dr字段 | column_name='dr' |
| DWD_001 指标非负 | 有金额字段(≤3个) | name含mny/amount或decimal类型 |
| DWD_003 枚举合法性 | 有枚举字段(≤2个) | name含state/status/flag |
| COM_004 时间异常 | 有时间字段(≤5个) | 类型datetime或name含time/date |
| COM_006 金额非负 | 有金额字段(≤3个) | name含mny/amount |
| COM_007 枚举空值 | 有枚举字段(≤2个) | name含state/status/flag |

**校验SQL模板示例：**

```sql
-- ODS_004 删除标识合法性
SELECT COUNT(*) as anomaly_count FROM {table} WHERE dr IS NOT NULL AND dr NOT IN (0,1)

-- COM_004 时间字段异常
SELECT COUNT(*) as anomaly_count FROM {table} WHERE {field} < '1970-01-02' OR {field} > '2099-12-31' OR {field} > NOW()

-- COM_006 金额非负
SELECT COUNT(*) as anomaly_count FROM {table} WHERE {field} < 0
```

### 2.5 阶段3：报告生成

**目标：** 聚合校验结果，计算评分，输出Markdown格式报告文件

**操作明细：**

| 序号 | 操作 | 处理方式 |
|------|------|---------|
| 3-1 | 创建输出目录 | mkdir Data-Governance/quality_check/output |
| 3-2 | 计算单表评分 | 100 - (BLOCK失败×25) - (WARN失败×10) - (INFO失败×3)，最低0分 |
| 3-3 | 计算分层评分 | AVG(该层所有表评分) |
| 3-4 | 计算整体评分 | Σ(分层评分×权重)，权重：ODS15%, DWD25%, DWS25%, DIM20%, ADS15% |
| 3-5 | 计算通过率 | PASS数/总规则数×100% |
| 3-6 | 统计问题数 | GROUP BY rule_severity 统计BLOCK/WARN/INFO失败数 |
| 3-7 | 获取问题明细 | SELECT WHERE check_status='FAIL' ORDER BY anomaly_count DESC |
| 3-8 | 获取TOP10规则 | 按fail_count排序取前10 |
| 3-9 | 判定健康等级 | ≥90优秀，≥75良好，≥60一般，≥40较差，<40危险 |
| 3-10 | 组装报告内容 | 按章节拼接：开篇总结、评估概览、问题分布、问题明细、处理建议 |
| 3-11 | 写入文件 | Write to 质量评估报告_{YYYYMMDD_HHmmss}.md |

**评分公式：**

```
单表得分 = MAX(0, 100 - Σ(BLOCK_FAIL×25) - Σ(WARN_FAIL×10) - Σ(INFO_FAIL×3))

分层得分 = AVG(该层各表得分)

整体得分 = ODS得分×0.15 + DWD得分×0.25 + DWS得分×0.25 + DIM得分×0.20 + ADS得分×0.15
```

**健康等级区间：**

| 分数 | 等级 | 状态 |
|------|------|------|
| 90-100 | 优秀 | 可放心使用 |
| 75-89 | 良好 | 存在轻微问题 |
| 60-74 | 一般 | 需要关注 |
| 40-59 | 较差 | 需尽快修复 |
| 0-39 | 危险 | 必须立即处理 |

---

## 三、中间产物

### 3.1 meta_table_column 表结构

**用途：** 存储数仓表字段元数据，为规则匹配提供字段类型、标签等信息

**DDL：**

```sql
CREATE TABLE `meta_table_column` (
    `id`                BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `table_name`        VARCHAR(128) NOT NULL COMMENT '表名称',
    `table_comment`     VARCHAR(512) COMMENT '表注释/描述',
    `table_layer`       VARCHAR(16) NOT NULL COMMENT '表所属分层：ODS/DWD/DWS/DIM/ADS',
    `column_name`       VARCHAR(64) NOT NULL COMMENT '字段名称',
    `column_type`       VARCHAR(64) NOT NULL COMMENT '字段类型，如varchar(255)、decimal(18,2)',
    `column_comment`    VARCHAR(512) COMMENT '字段注释/描述',
    `column_tag`        VARCHAR(16) NOT NULL DEFAULT 'ATTRIBUTE' COMMENT '字段标签：DIMENSION/MEASURE/ATTRIBUTE',
    `is_pk`             TINYINT(1) DEFAULT 0 COMMENT '是否主键：0-否，1-是',
    `is_partition`      TINYINT(1) DEFAULT 0 COMMENT '是否分区字段：0-否，1-是',
    `created_at`        DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_table_column` (`table_name`, `column_name`),
    KEY `idx_table_layer` (`table_layer`),
    KEY `idx_column_tag` (`column_tag`)
) ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='表字段元数据表';
```

**阶段1产出数据示例：**

| table_name | table_layer | column_name | column_type | column_tag | column_comment |
|------------|-------------|-------------|-------------|------------|----------------|
| ods_ztpc_xmglxt_ejc_prosub_settle_df | ODS | contract_mny | decimal(28,8) | MEASURE | 合同金额 |
| ods_ztpc_xmglxt_ejc_prosub_settle_df | ODS | bill_state | varchar(32) | DIMENSION | 单据状态 |
| ods_ztpc_xmglxt_ejc_prosub_settle_df | ODS | create_time | datetime | ATTRIBUTE | 创建时间 |

**产出条数：** Σ(每张表字段数量)，例如5张表共约150条

### 3.2 dq_check_result 表结构

**用途：** 存储所有校验规则的执行结果，供报告生成和历史对比

**DDL：**

```sql
CREATE TABLE `dq_check_result` (
    `id`                BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `table_name`        VARCHAR(128) NOT NULL COMMENT '被校验的表名称',
    `table_layer`       VARCHAR(16) NOT NULL COMMENT '表所属分层：ODS/DWD/DWS/DIM/ADS',
    `total_rows`        BIGINT DEFAULT 0 COMMENT '表总记录数',
    `rule_id`           VARCHAR(16) NOT NULL COMMENT '规则ID，如COM_001、ODS_001',
    `rule_name`         VARCHAR(64) NOT NULL COMMENT '规则名称',
    `rule_severity`     VARCHAR(16) NOT NULL COMMENT '严重程度：BLOCK/WARN/INFO',
    `check_field`       VARCHAR(128) COMMENT '校验的字段名称',
    `check_sql`         TEXT NOT NULL COMMENT '执行的校验SQL',
    `execute_status`    VARCHAR(16) NOT NULL COMMENT '执行状态：SUCCESS/FAILED/TIMEOUT',
    `execute_time`      INT DEFAULT 0 COMMENT 'SQL执行耗时(毫秒)',
    `check_status`      VARCHAR(16) NOT NULL COMMENT '校验结果：PASS/FAIL',
    `anomaly_count`     BIGINT DEFAULT 0 COMMENT '异常记录数',
    `anomaly_rate`      DECIMAL(10,4) DEFAULT 0 COMMENT '异常率(百分比)',
    `check_standard`    VARCHAR(256) COMMENT '校验标准值',
    `analysis_result`   TEXT COMMENT '分析结果：问题描述、原因分析、修复建议',
    `check_time`        DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '校验执行时间',
    KEY `idx_table_name` (`table_name`),
    KEY `idx_check_status` (`check_status`),
    KEY `idx_check_time` (`check_time`)
) ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='数据质量校验结果表';
```

**阶段2产出数据示例：**

| table_name | rule_id | rule_name | check_field | check_status | anomaly_count | anomaly_rate | analysis_result |
|------------|---------|-----------|-------------|--------------|---------------|--------------|-----------------|
| ods_ztpc_xmglxt_ejc_prosub_settle_df | ODS_004 | 删除标识合法性 | dr | FAIL | 12 | 60.0000 | dr字段存在12条非法值，需排查数据源 |
| dwd_pr_settle_volumes_info_df | DWD_003 | 枚举值合法性 | confirm_flag | FAIL | 100 | 100.0000 | confirm_flag字段存在100条空值 |
| ods_ztpc_xmglxt_ejc_prosub_settle_df | ODS_001 | 主键缺失检查 | id | PASS | 0 | 0.0000 | 主键缺失检查校验通过 |

**产出条数：** Σ(每张表应用规则数)，例如5张表共59条

---

## 四、交付成果

### 4.1 成果清单

| 序号 | 成果 | 形态 | 存放位置 | 主要用途 |
|------|------|------|---------|---------|
| 1 | 质量评估报告 | Markdown文件 | Data-Governance/quality_check/output/ | 阅读查看质量状况 |
| 2 | dq_check_result数据 | 数据库记录 | fengji.dq_check_result | 历史对比、趋势分析 |
| 3 | meta_table_column数据 | 数据库记录 | fengji.meta_table_column | 后续评估复用 |

### 4.2 质量评估报告详情

**文件命名：** 质量评估报告_{YYYYMMDD_HHmmss}.md

**文件位置：** Data-Governance/quality_check/output/

**章节结构：**

| 章节 | 内容 |
|------|------|
| 开篇总结 | 整体健康状态、核心问题数量、改进方向建议 |
| 一、评估概览 | 整体评分、规则通过率、阻断/警告问题数、分层评分表 |
| 二、问题分布 | TOP10问题规则排行（规则ID、名称、失败次数、影响表数） |
| 三、问题明细 | 每条失败记录详情（表名、规则、字段、异常数、异常率、分析） |
| 四、问题处理建议 | 阻断级问题清单、警告级问题清单（附问题描述） |

**报告片段示例：**

```markdown
## 开篇总结

当前数仓整体健康状态为**危险**（7.0分）。

核心问题：发现9个阻断级问题和19个警告级问题。

改进方向：建议优先修复阻断级问题，预计修复后整体得分可提升至90分以上。

## 一、评估概览

### 1.1 整体评分

| 指标 | 数值 | 说明 |
|------|------|------|
| 整体得分 | 7.0分 | 危险 |
| 规则通过率 | 52.5% | 31/59 |
| 阻断问题数 | 9个 | BLOCK级别失败 |
| 警告问题数 | 19个 | WARN级别失败 |

### 1.2 分层评分

| 分层 | 表数量 | 平均得分 | 等级 | 阻断问题 | 警告问题 |
|------|-------|---------|------|---------|---------|
| ADS层 | 1张 | 0.0分 | 危险 | 3 | 4 |
| DWD层 | 1张 | 0.0分 | 危险 | 4 | 4 |
| ODS层 | 3张 | 46.7分 | 较差 | 2 | 11 |
```

---

## 五、数据流转全景

```
前置材料
├── db_config.json        ──→ 连接参数
├── rule_v2.md            ──→ 规则库+SQL模板
├── 数仓表数据(ods/dwd...)──→ 校验对象
└── dq_quality_checker.py ──→ 执行载体

        ↓ 阶段0：环境初始化

中间产物(结构)
├── meta_table_column表结构
└── dq_check_result表结构

        ↓ 阶段1：元数据同步

中间产物(数据)
├── meta_table_column记录 ──→ 每表每字段的元数据

        ↓ 阶段2：规则校验

中间产物(数据)
├── dq_check_result记录   ──→ 每表每规则的校验结果

        ↓ 阶段3：报告生成

交付成果
├── 质量评估报告.md       ──→ 最终交付，可直接阅读
├── dq_check_result数据   ──→ 供历史对比分析
└── meta_table_column数据 ──→ 供后续评估复用
```

---

## 六、执行方式

| 命令 | 执行阶段 | 说明 |
|------|---------|------|
| python dq_quality_checker.py --init | 阶段0 | 首次执行初始化 |
| python dq_quality_checker.py --sync | 阶段1 | 同步元数据 |
| python dq_quality_checker.py --check | 阶段2 | 执行校验 |
| python dq_quality_checker.py --report | 阶段3 | 生成报告 |
| python dq_quality_checker.py --all | 阶段0→1→2→3 | 完整流程 |

---

*文档版本：v1.0*
*生成时间：2026-04-23*