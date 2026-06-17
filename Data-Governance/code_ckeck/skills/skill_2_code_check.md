# 数仓代码检查

> 本技能用于对数仓各分层（ODS/DIM/DWD/DWS/ADS）的SQL代码进行质量评估，生成量化评分报告。

## 触发关键词

| 关键词 | 说明 |
|-----|-----|
| 检查SQL代码 | 执行数仓代码质量检查 |
| SQL代码检查 | 对SQL代码进行规则检查 |
| 代码评分 | 评估SQL代码质量并生成评分 |
| 代码审查 | 审查数仓SQL代码规范 |

## 一、前置依赖

### 1.1 任务信息来源 `task_info_data.xlsx`

位置：`Data-Governance/code_ckeck/inputs/docs/task_info_data.xlsx`

核心字段：
- `tenant_id`     -- 租户ID
- `project_id`    -- 项目ID
- `name`          -- 任务名称
- `task_type`     -- 任务类型
- `sql_text`      -- SQL文本
- `is_deleted`    -- 是否删除：0-否，1-是
- `gmt_create`    -- 创建时间
- `gmt_modified`  -- 修改时间
其他字段暂未列举。

### 1.2 数据库配置文件 `db_config.json`

位置：`Data-Governance/code_ckeck/configs/db_config.json`

```json
{
    "target_db": {
        "name": "zhaogang_test",
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "root",
        "database": "zhaogang_test",
        "charset": "utf8mb4",
        "description": "目标分析数据库"
    }
}
```

### 1.3 代码存储表 `rdos_batch_task`

读取task_info_data.xlsx文件，将文件所有字段列的数据存储到`zhaogang_test`.`rdos_batch_task`表中作为原始表。

```sql
CREATE TABLE IF NOT EXISTS `zhaogang_test`.`rdos_batch_task` (
  `id` int(11) DEFAULT NULL COMMENT '主键',
  `tenant_id` int(11) DEFAULT NULL COMMENT '租户id',
  `project_id` int(11) DEFAULT NULL COMMENT '项目id',
  `node_pid` int(11) DEFAULT NULL COMMENT '父文件夹id',
  `name` varchar(255) DEFAULT NULL COMMENT '任务名称',
  `task_type` tinyint(4) DEFAULT NULL COMMENT '任务类型 -1:虚节点,0:sparksql,1:spark,2:数据同步,3:pyspark,4:R,5:深度学习,6:python,7:shell,8:机器学习,9:hadoopMR,10:工作流,12:carbonSQL,13:notebook,14:算法实验,15:libra sql,16:kylin,17:hiveSQL',
  `engine_type` tinyint(4) DEFAULT NULL COMMENT '执行引擎类型 0:flink,1:spark,2:datax,3:learning,4:shell,5:python2,6:dtyarnshell,7:python3,8:hadoop,9:carbon,10:postgresql,11:kylin,12:hive',
  `compute_type` tinyint(4) DEFAULT NULL COMMENT '计算类型 0实时，1 离线',
  `sql_text` text COMMENT 'sql 文本',
  `task_params` text COMMENT '任务参数',
  `schedule_conf` text COMMENT '调度配置 json格式',
  `period_type` tinyint(4) DEFAULT NULL COMMENT '周期类型',
  `schedule_status` tinyint(4) DEFAULT NULL COMMENT '0未开始,1正常调度,2暂停',
  `submit_status` tinyint(4) DEFAULT NULL COMMENT '0未提交,1已提交',
  `gmt_create` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '新增时间',
  `gmt_modified` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  `modify_user_id` int(11) DEFAULT NULL COMMENT '最后修改task的用户',
  `create_user_id` int(11) DEFAULT NULL COMMENT '新建task的用户',
  `owner_user_id` int(11) DEFAULT NULL COMMENT '负责人id',
  `version` int(11) DEFAULT NULL COMMENT 'task版本',
  `is_deleted` tinyint(4) DEFAULT NULL COMMENT '0正常 1逻辑删除',
  `task_desc` text,
  `main_class` varchar(500) DEFAULT NULL,
  `exe_args` text,
  `flow_id` int(11) DEFAULT NULL COMMENT '工作流id',
  `use_other` int(11) DEFAULT NULL COMMENT '是否引用其他内容: 1-使用模板 2-使用组件 3-否',
  `component_version` varchar(100) DEFAULT NULL COMMENT '组件版本',
  `component_id` int(11) DEFAULT NULL COMMENT '使用的组件版本id',
  `yarn_resource_id` int(11) DEFAULT NULL COMMENT '任务指定的资源组id',
  `agent_resource_id` int(11) DEFAULT NULL COMMENT '任务指定的agent资源id',
  `depend_on_settings` tinyint(4) DEFAULT NULL COMMENT '依赖设置  0-手动依赖 1-自动推荐',
  `calender_id` int(11) DEFAULT NULL COMMENT '任务自定义调度日历id',
  `task_group` tinyint(4) DEFAULT NULL COMMENT '0: 周期任务,1:手动任务',
  `sort` int(11) DEFAULT NULL COMMENT '排序权重',
  `chosen_database` varchar(100) DEFAULT NULL COMMENT '任务手动选择的schema',
  `prod_task_id` int(11) DEFAULT NULL COMMENT '生产项目任务id',
  `remote_file_name` varchar(255) DEFAULT NULL COMMENT '旧任务名称，用于git任务重命名',
  `identity` varchar(100) DEFAULT NULL COMMENT '多集群运行的数据源id',
  `data_source_type` int(11) DEFAULT NULL COMMENT '数据源类型',
  `dt` varchar(50) DEFAULT NULL COMMENT '分区'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='离线任务表';
```

### 1.4 代码检查规则集 `code_rules.md`

位置：`Data-Governance/code_ckeck/configs/code_rules.md`

包含SQL代码检查规则和最佳实践。

---

## 二、检查规则

### 2.1 代码规范检查

基于《数据中台项目-数据开发标准》编码规范章节提炼：

| 规则ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_NAM_001 | 命名规范 | 表名、字段名使用下划线命名 | WARN |
| COD_NAM_002 | 分层前缀规范 | 表名必须以分层前缀开头（ods/dwd/dws/dim/ads） | WARN |
| COD_NAM_003 | 注释规范 | 必须包含功能说明注释 | WARN |
| COD_NAM_004 | 别名规范 | 别名应有意义，避免使用a/b/c等单字母 | INFO |
| COD_NAM_005 | 字段命名一致性 | 同类型字段在不同表中命名应一致 | WARN |
| COD_NAM_006 | 时间字段规范 | 必须包含gmt_create和gmt_modified字段 | WARN |
| COD_NAM_007 | 主键字段规范 | 主键字段建议使用id或{table}_id命名 | INFO |
| COD_NAM_008 | 布尔字段规范 | 布尔字段建议使用is_/has_/can_前缀 | INFO |
| COD_NAM_009 | 关联字段规范 | 外键字段建议使用{table}_id格式 | INFO |
| COD_NAM_010 | 禁用保留字 | 禁止使用SQL保留字作为表名或字段名 | WARN |
| COD_NAM_011 | 驼峰命名规范 | 字段名禁用驼峰命名，必须使用下划线 | WARN |
| COD_NAM_012 | 表名长度规范 | 表名长度建议3-50字符 | INFO |
| COD_NAM_013 | 字段长度规范 | VARCHAR字段建议明确长度，避免过长 | INFO |
| COD_NAM_014 | 数字类型规范 | 金额字段必须使用DECIMAL，禁止使用FLOAT/DOUBLE | WARN |
| COD_NAM_015 | 代码头部注释 | SQL文件头部必须有主题、功能描述、创建者、创建日期 | WARN |
| COD_NAM_016 | 修改日志注释 | 代码头部必须有修改日志记录 | INFO |
| COD_NAM_017 | 单行字段规范 | SELECT语句字段按每行一个字段编排 | INFO |
| COD_NAM_018 | AS对齐规范 | 多个字段的AS建议对齐在同一列 | INFO |
| COD_NAM_019 | 子句换行规范 | FROM/WHERE/GROUP BY等子句需换行编写 | INFO |
| COD_NAM_020 | 运算符空格规范 | 算术运算符、逻辑运算符前后保留一个空格 | INFO |
| COD_NAM_021 | CASE语句规范 | CASE语句必须包含ELSE子语 | WARN |
| COD_NAM_022 | 字段注释规范 | 字段注释紧跟在字段后面 | WARN |

### 2.2 性能优化检查

| 规则ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_PER_001 | 全表扫描预警 | 检测无WHERE条件的SELECT | BLOCK |
| COD_PER_002 | 笛卡尔积检测 | 检测笛卡尔积JOIN（JOIN前无ON条件） | BLOCK |
| COD_PER_003 | 大表LIMIT限制 | 大表查询未限制返回行数（LIMIT>10000或无LIMIT） | WARN |
| COD_PER_004 | COUNT优化 | 建议使用COUNT(*)或COUNT(1)而非COUNT(字段) | INFO |
| COD_PER_005 | 模糊查询前缀 | 避免左百分号的LIKE查询 | WARN |
| COD_PER_006 | 批量INSERT | 建议使用批量INSERT而非逐条INSERT | INFO |

### 2.3 SQL反模式检查

| 规则ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_ANT_001 | SELECT * | 禁止使用SELECT * | WARN |
| COD_ANT_002 | 隐式类型转换 | 避免字段类型隐式转换 | WARN |
| COD_ANT_003 | 负面查询 | NOT IN / NOT EXISTS性能差，建议改写 | WARN |
| COD_ANT_004 | OR条件优化 | OR条件建议改写为UNION ALL | WARN |
| COD_ANT_005 | 子查询嵌套 | 避免超过2层嵌套子查询 | WARN |
| COD_ANT_006 | 分页深度 | 避免大偏移量分页（OFFSET>10000） | INFO |

### 2.4 安全合规检查

| 规则ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_SEC_001 | 敏感字段脱敏 | 手机号、身份证必须脱敏 | BLOCK |
| COD_SEC_002 | 危险操作预警 | 避免直接DROP TABLE/TRUNCATE TABLE | BLOCK |
| COD_SEC_003 | 无限制DELETE | DELETE操作必须带WHERE条件 | BLOCK |
| COD_SEC_004 | 明文密码检测 | 禁止在SQL中出现明文密码 | BLOCK |
| COD_SEC_005 | 邮箱脱敏 | 邮箱地址应部分脱敏 | WARN |
| COD_SEC_006 | 银行账号脱敏 | 银行账号必须脱敏 | BLOCK |

### 2.5 分层原则检查

| 规则ID | 规则名称 | 检查内容 | 严重程度 |
|--------|---------|---------|---------|
| COD_LAY_001 | ODS层禁止聚合 | ODS层不应包含聚合计算 | BLOCK |
| COD_LAY_002 | DWD层禁止跨层引用 | DWD只引用ODS/DIM | BLOCK |
| COD_LAY_003 | DWS层单主题域 | DWS按主题域组织 | WARN |
| COD_LAY_004 | ADS层引用规范 | ADS只引用DWS/DIM | BLOCK |

---

## 三、评估流程

执行脚本：`Data-Governance/code_ckeck/py_scripts/code_checker.py`

### 步骤1：创建并清空原始表（执行 code_chk0.sql）

执行 `Data-Governance/code_ckeck/sql_scripts/chk_sql/code_chk0.sql`，创建并清空 `rdos_batch_task` 表。

```sql
-- 创建并清空原始表，用于存储任务信息
TRUNCATE TABLE `zhaogang_test`.`rdos_batch_task`;
```

### 步骤2：将数据写入原始表（执行 data_insert.py）
执行 `data_insert.py`，将 `task_info_data.xlsx` 文件中的数据写入 `rdos_batch_task` 表。

```python
python data_insert.py
```

### 步骤3：创建结果表（执行 code_chk1.sql）

执行 `Data-Governance/code_ckeck/sql_scripts/chk_sql/code_chk1.sql`，创建以下表：

`code_check_result` - 代码检查结果表

### 步骤4：查询核心字段检查

从 `rdos_batch_task` 表读取核心字段：

```sql
SELECT id, tenant_id, project_id, name, task_type, sql_text
FROM rdos_batch_task
WHERE is_deleted = 1
AND sql_text IS NOT NULL
AND sql_text != ''
ORDER BY tenant_id, project_id, name;
```
其中，`id` 为任务ID，`tenant_id` 为租户ID，`project_id` 为项目ID，`name` 为任务名称，`task_type` 为任务类型，`sql_text` 为SQL代码。

### 步骤5：执行规则检查

基于核心字段的查询情况，对每条SQL代码应用`Data-Governance/code_ckeck/configs/code_rules.md` 中的44条规则进行检查。

### 步骤6：保存检查结果

将检查结果写入 `code_check_result` 表：

```sql
CREATE TABLE `code_check_result` (
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
```

### 步骤7：计算代码评分

**评分公式：**

```
代码得分 = 100 - (BLOCK失败数 × 25) - (WARN失败数 × 10) - (INFO失败数 × 3)
```

**分层评分：**

```sql
SELECT 
    code_layer,
    AVG(score) as avg_score,
    COUNT(*) as total_code,
    SUM(CASE WHEN check_status='FAIL' AND rule_severity='BLOCK' THEN 1 ELSE 0 END) as block_issues,
    SUM(CASE WHEN check_status='FAIL' AND rule_severity='WARN' THEN 1 ELSE 0 END) as warn_issues
FROM (
    SELECT 
        code_id, code_name, code_layer,
        100 - COALESCE(SUM(CASE WHEN rule_severity='BLOCK' AND check_status='FAIL' THEN 25 ELSE 0 END),0)
            - COALESCE(SUM(CASE WHEN rule_severity='WARN' AND check_status='FAIL' THEN 10 ELSE 0 END),0)
            - COALESCE(SUM(CASE WHEN rule_severity='INFO' AND check_status='FAIL' THEN 3 ELSE 0 END),0) AS score
    FROM code_check_result
    WHERE check_time >= DATE_SUB(NOW(), INTERVAL 1 DAY)
    GROUP BY code_id, code_name, code_layer
) t
GROUP BY code_layer;
```

### 步骤8：检查结果输出

将检查结果输出为Markdown格式的报告
输出位置：Data-Governance/code_ckeck/outputs/docs/code_check_report.md 

同时，输出检查结果表（code_check_result）的Excel文档
输出位置：Data-Governance/code_ckeck/outputs/docs/code_check_report.xlsx。

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
| 四、TOP问题 | 问题代码排行 |
| 五、整改建议 | 修复建议 |
| 六、最佳实践 | 代码优化建议 |

### 5.2 报告示例

```markdown
# 数仓代码检查报告

## 开篇总结
本次检查覆盖X个代码，发现Y个问题...

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
python code_checker.py --all

# 指定分层检查
python code_checker.py --layers ods,dwd

# 指定代码检查
python code_checker.py --code_ids 1,2,3
```
---

## 七、注意事项

1. **安全第一**：敏感数据检查必须通过
2. **性能优先**：BLOCK级性能问题必须修复
3. **分层原则**：严格遵守数仓分层规范
4. **持续检查**：建议集成到CI/CD流程
