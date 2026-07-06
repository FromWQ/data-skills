# 数仓数据质量校验规则集 v2

> 本文档定义了数仓各分层表的数据质量校验规则，包括通用规则和分层专属规则。

---

## 一、规则编号规范

| 前缀 | 说明 | 适用范围 |
|------|------|---------|
| COM | 通用规则 (Common) | 所有分层 |
| ODS | ODS 层规则 | ODS 层 |
| DWD | DWD 层规则 | DWD 层 |
| DWS | DWS 层规则 | DWS 层 |
| DIM | DIM 层规则 | DIM 层 |
| ADS | ADS 层规则 | ADS 层 |

---

## 二、通用规则 (COM_001 ~ COM_005)

### COM_001 分区连续无缺失

**规则名称**：分区连续无缺失检查

**严重程度**：BLOCK

**应用条件**：表有分区字段（pt/dt/partition_date）

**SQL 模板**：
```sql
SELECT 
    COUNT(DISTINCT {partition_field}) as partition_count,
    MIN({partition_field}) as min_partition,
    MAX({partition_field}) as max_partition
FROM {table_name}
WHERE {partition_field} >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
```

**校验标准**：分区数应接近 30（允许±3 天波动）

**异常判断**：分区数 < 27 或 分区数 > 33

---

### COM_002 数据量波动合理

**规则名称**：数据量波动检查

**严重程度**：WARN

**应用条件**：表有分区字段

**SQL 模板**：
```sql
SELECT 
    {partition_field} as pt,
    COUNT(*) as cnt
FROM {table_name}
WHERE {partition_field} >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY {partition_field}
ORDER BY {partition_field}
```

**校验标准**：相邻分区数据量波动不超过 50%

**异常判断**：波动率 > 50%

---

### COM_003 关键字段非空率

**规则名称**：关键字段非空检查

**严重程度**：BLOCK

**应用条件**：存在主键字段（id）或关键字段

**SQL 模板**：
```sql
SELECT 
    COUNT(*) as total_count,
    SUM(CASE WHEN {key_field} IS NULL OR {key_field} = '' THEN 1 ELSE 0 END) as null_count
FROM {table_name}
WHERE {partition_field} = CURDATE()
```

**校验标准**：null_count = 0

**异常判断**：null_count > 0

---

### COM_004 时间字段无异常

**规则名称**：时间字段合理性检查

**严重程度**：WARN

**应用条件**：存在时间字段（datetime/date 类型，或字段名/注释包含时间关键词）

**SQL 模板**：
```sql
SELECT 
    COUNT(*) as total_count,
    SUM(CASE WHEN create_time < '1970-01-01' OR create_time > NOW() THEN 1 ELSE 0 END) as invalid_count
FROM {table_name}
LIMIT 1000
```

**校验标准**：invalid_count = 0

**异常判断**：invalid_count > 0

---

### COM_005 脏数据/乱码检查

**规则名称**：脏数据乱码检查

**严重程度**：INFO

**应用条件**：存在 varchar/text 类型字段

**SQL 模板**：
```sql
SELECT 
    COUNT(*) as total_count,
    SUM(CASE WHEN memo IS NULL THEN 1 ELSE 0 END) as null_count
FROM {table_name}
LIMIT 1000
```

**校验标准**：null_count = 0

**异常判断**：null_count > 0

---

## 三、ODS 层专属规则 (ODS_001 ~ ODS_004)

### ODS_001 主键缺失检查

**规则名称**：主键缺失检查

**严重程度**：BLOCK

**应用条件**：存在主键字段（id）

**SQL 模板**：
```sql
SELECT COUNT(*) as null_pk_count
FROM {table_name}
WHERE id IS NULL
```

**校验标准**：null_pk_count = 0

---

### ODS_002 主键重复检查

**规则名称**：主键唯一性检查

**严重程度**：BLOCK

**应用条件**：存在主键字段（id）

**SQL 模板**：
```sql
SELECT COUNT(*) as duplicate_pk_count 
FROM (
    SELECT id, COUNT(*) AS cnt 
    FROM {table_name}
    WHERE {partition_field} = CURDATE()
    GROUP BY id 
    HAVING COUNT(*) > 1
) t
```

**校验标准**：duplicate_pk_count = 0

---

### ODS_003 完全重复检查

**规则名称**：完全重复记录检查

**严重程度**：WARN

**应用条件**：所有 ODS 表

**SQL 模板**：
```sql
SELECT COUNT(*) as duplicate_rows_count
FROM (
    SELECT id, COUNT(*) AS cnt 
    FROM {table_name}
    GROUP BY id
    HAVING COUNT(*) > 1
) t
```

**校验标准**：duplicate_rows_count = 0

---

### ODS_004 删除标识合法性

**规则名称**：删除标识检查

**严重程度**：WARN

**应用条件**：存在 dr 字段

**SQL 模板**：
```sql
SELECT 
    dr,
    COUNT(*) as cnt
FROM {table_name}
WHERE dr NOT IN (0, 1) OR dr IS NULL
```

**校验标准**：cnt = 0

**异常判断**：cnt > 0

---

## 四、DWD 层专属规则 (DWD_001 ~ DWD_003)

### DWD_001 指标非负检查

**规则名称**：明细指标非负检查

**严重程度**：BLOCK

**应用条件**：存在金额/数量类字段

**SQL 模板**：
```sql
SELECT 
    COUNT(*) as total_count,
    SUM(CASE WHEN {measure_field} < 0 THEN 1 ELSE 0 END) as negative_count
FROM {table_name}
WHERE {partition_field} = CURDATE()
```

**校验标准**：negative_count = 0

---

### DWD_002 外键关联检查

**规则名称**：外键关联完整性检查

**严重程度**：WARN

**应用条件**：存在外键字段（*_id 结尾）

**SQL 模板**：
```sql
SELECT COUNT(*) as orphan_count
FROM {table_name} t1
LEFT JOIN {ref_table} t2 ON t1.{fk_field} = t2.id
WHERE t1.{partition_field} = CURDATE()
AND t2.id IS NULL
```

**校验标准**：orphan_count = 0

---

### DWD_003 枚举值合法性

**规则名称**：明细枚举值检查

**严重程度**：WARN

**应用条件**：存在枚举字段

**SQL 模板**：同 COM_007

---

## 五、DWS 层专属规则 (DWS_001 ~ DWS_002)

### DWS_001 分组维度唯一

**规则名称**：汇总维度唯一性检查

**严重程度**：BLOCK

**应用条件**：存在维度字段（name/code 结尾）

**SQL 模板**：
```sql
SELECT COUNT(*) as duplicate_dim_count
FROM (
    SELECT {dim_field}, COUNT(*) AS cnt 
    FROM {table_name}
    WHERE {partition_field} = CURDATE()
    GROUP BY {dim_field}
    HAVING COUNT(*) > 1
) t
```

**校验标准**：duplicate_dim_count = 0

---

### DWS_002 汇总指标空值率

**规则名称**：汇总指标空值检查

**严重程度**：WARN

**应用条件**：存在金额字段

**SQL 模板**：
```sql
SELECT 
    COUNT(*) as total_count,
    SUM(CASE WHEN {amount_field} IS NULL THEN 1 ELSE 0 END) as null_count
FROM {table_name}
WHERE {partition_field} = CURDATE()
```

**校验标准**：null_rate < 5%

---

### DWS_003 数据量级合理性

**规则名称**：汇总数据量级检查

**严重程度**：INFO

**应用条件**：存在分区字段

**SQL 模板**：
```sql
SELECT 
    {partition_field} as pt,
    COUNT(*) as cnt
FROM {table_name}
WHERE {partition_field} >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY {partition_field}
ORDER BY cnt DESC
LIMIT 1
```

**校验标准**：单分区数据量不超过 1000 万

**异常判断**：cnt > 10000000

---

## 六、DIM 层专属规则 (DIM_001 ~ DIM_003)

### DIM_001 维度编码唯一

**规则名称**：维度编码唯一性检查

**严重程度**：BLOCK

**应用条件**：存在 code 字段

**SQL 模板**：
```sql
SELECT COUNT(*) as duplicate_code_count
FROM (
    SELECT {code_field}, COUNT(*) AS cnt 
    FROM {table_name}
    GROUP BY {code_field}
    HAVING COUNT(*) > 1
) t
```

**校验标准**：duplicate_code_count = 0

---

### DIM_002 维度层级完整

**规则名称**：维度层级完整性检查

**严重程度**：INFO

**应用条件**：存在 parent_id 或 level 字段

**SQL 模板**：
```sql
SELECT 
    COUNT(*) as total_count,
    SUM(CASE WHEN parent_id IS NULL AND level > 1 THEN 1 ELSE 0 END) as missing_parent_count
FROM {table_name}
```

**校验标准**：missing_parent_count = 0

---

### DIM_003 核心属性非空

**规则名称**：维度核心属性非空检查

**严重程度**：BLOCK

**应用条件**：存在 name 字段

**SQL 模板**：
```sql
SELECT 
    COUNT(*) as total_count,
    SUM(CASE WHEN name IS NULL OR name = '' THEN 1 ELSE 0 END) as null_count
FROM {table_name}
```

**校验标准**：null_count = 0

---

## 七、ADS 层专属规则 (ADS_001 ~ ADS_002)

### ADS_001 分组维度唯一

**规则名称**：ADS 维度唯一性检查

**严重程度**：BLOCK

**应用条件**：存在维度字段

**SQL 模板**：同 DWS_001

---

### ADS_002 关键指标非空

**规则名称**：ADS 关键指标非空检查

**严重程度**：BLOCK

**应用条件**：存在金额字段

**SQL 模板**：
```sql
SELECT 
    COUNT(*) as total_count,
    SUM(CASE WHEN project_code IS NULL OR project_code = '' THEN 1 ELSE 0 END) as null_count
FROM {table_name}
```

**校验标准**：null_count = 0

---

### ADS_003 报表一致性检查

**规则名称**：报表数据一致性检查

**严重程度**：WARN

**应用条件**：存在关联的 DWS 层表

**SQL 模板**：
```sql
SELECT 
    'skip' as result
FROM dual
```

**校验标准**：跳过（需要手动配置关联表）

**异常判断**：无

---

## 八、规则应用逻辑

### 8.1 规则匹配流程

```
1. 获取表所属分层 (table_layer)
   ↓
2. 加载通用规则 (COM_001 ~ COM_007)
   ↓
3. 加载分层专属规则 (ODS_*/DWD_*/DWS_*/DIM_*/ADS_*)
   ↓
4. 检查字段是否满足规则应用条件
   ↓
5. 生成最终适用规则列表
```

### 8.2 字段类型识别

| 字段类型 | 识别规则 |
|---------|---------|
| **DIMENSION** | 字段名包含/结尾：name, code, type, status, flag, org, dept, region, date, time |
| **MEASURE** | 字段名包含：mny, amount, price, cost, qty, count, rate, percent；或 decimal/double/float 类型 |
| **ATTRIBUTE** | 不符合上述规则的普通字段 |

### 8.3 特殊字段识别

| 字段类型 | 识别规则 |
|---------|---------|
| **主键** | 字段名 = 'id' 或 is_pk = 1 |
| **分区字段** | 字段名 IN ('dt', 'pt', 'partition_date') 或 is_partition = 1 |
| **时间字段** | 类型为 datetime/date/timestamp，或字段名/注释包含"时间"/"日期" |
| **金额字段** | 字段名包含 mny/amount/cost/fee/price，或注释包含"金额"/"费用" |
| **枚举字段** | 字段名包含 state/status/type/flag，或注释包含"状态"/"类型" |

---

## 九、评分标准

### 9.1 单表评分

```
单表得分 = 100 - (BLOCK 失败数 × 25) - (WARN 失败数 × 10) - (INFO 失败数 × 3)
最低分为 0 分
```

### 9.2 评分等级

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 数据质量优秀，可放心使用 |
| 75-89 | 良好 | 数据质量良好，存在轻微问题 |
| 60-74 | 一般 | 数据质量一般，需要关注 |
| 40-59 | 较差 | 数据质量较差，需要尽快修复 |
| 0-39 | 危险 | 数据质量严重问题，必须立即处理 |

---

## 十、版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v2.0 | 2026-01-01 | 初始版本，包含通用规则 7 条，分层规则 15 条 |
