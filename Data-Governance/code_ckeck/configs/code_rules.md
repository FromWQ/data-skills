# SQL代码检查规则集

> 本规则集定义了数仓SQL代码的检查规则，用于自动化代码质量检查。

## 一、规则说明

| 严重程度 | 说明 | 处理建议 |
|---------|------|---------|
| BLOCK | 阻断级问题 | 必须修复，否则禁止发布 |
| WARN | 警告级问题 | 建议修复，影响评分 |
| INFO | 提示级问题 | 建议优化，不影响评分 |

---

## 二、检查规则详情

### 2.1 代码规范检查

| 规则ID | 规则名称 | 检查内容 | 严重程度 | 检测方式 |
|--------|---------|---------|---------|---------|
| COD_NAM_001 | 命名规范 | 表名、字段名使用下划线命名 | WARN | 正则：`^[a-z][a-z0-9_]*$` |
| COD_NAM_002 | 分层前缀规范 | 表名必须以分层前缀开头 | WARN | 正则：`^(ods\|dwd\|dws\|dim\|ads)_` |
| COD_NAM_003 | 注释规范 | 必须包含功能说明注释 | WARN | 正则：检查 COMMENT 或 -- 注释 |
| COD_NAM_004 | 别名规范 | 别名应有意义，避免单字母 | INFO | 正则：检测 ` as [a-z]$`, ` a `, ` b ` |
| COD_NAM_005 | 字段命名一致性 | 同类型字段命名一致 | WARN | 对比同表不同字段 |
| COD_NAM_006 | 时间字段规范 | 包含gmt_create/gmt_modified | WARN | 检测时间字段存在性 |
| COD_NAM_007 | 主键字段规范 | 主键使用id或{table}_id | INFO | 检测PRIMARY KEY定义 |
| COD_NAM_008 | 布尔字段规范 | 使用is_/has_/can_前缀 | INFO | 正则：`^(is\|has\|can)_` |
| COD_NAM_009 | 关联字段规范 | 外键使用{table}_id格式 | INFO | 正则：检测外键字段 |
| COD_NAM_010 | 禁用保留字 | 禁止SQL保留字 | WARN | 对比保留字列表 |
| COD_NAM_011 | 驼峰命名规范 | 禁用驼峰命名 | WARN | 正则：检测大小写混合 |
| COD_NAM_012 | 表名长度规范 | 表名长度3-50字符 | INFO | 字符串长度检查 |
| COD_NAM_013 | 字段长度规范 | VARCHAR明确长度 | INFO | 检测VARCHAR无长度 |
| COD_NAM_014 | 数字类型规范 | 金额使用DECIMAL | WARN | 检测FLOAT/DOUBLE用于金额 |
| COD_NAM_015 | 代码头部注释 | 包含主题/功能/创建者/日期 | WARN | 检测文件头注释块 |
| COD_NAM_016 | 修改日志注释 | 包含修改日志记录 | INFO | 检测修改日志格式 |
| COD_NAM_017 | 单行字段规范 | SELECT字段每行一个 | INFO | 检测多字段单行 |
| COD_NAM_018 | AS对齐规范 | AS对齐在同一列 | INFO | 检测AS位置一致性 |
| COD_NAM_019 | 子句换行规范 | FROM/WHERE等换行 | INFO | 检测子句不换行 |
| COD_NAM_020 | 运算符空格规范 | 运算符前后有空格 | INFO | 正则：检测无空格运算符 |
| COD_NAM_021 | CASE语句规范 | CASE必须包含ELSE | WARN | 检测无ELSE的CASE |
| COD_NAM_022 | 字段注释规范 | 字段后紧跟注释 | WARN | 检测字段注释格式 |

**SQL保留字列表：**
```sql
SELECT, FROM, WHERE, AND, OR, NOT, IN, LIKE, BETWEEN, 
IS, NULL, AS, ON, JOIN, LEFT, RIGHT, INNER, OUTER, 
GROUP, BY, ORDER, HAVING, LIMIT, OFFSET, UNION, ALL, 
INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, TABLE, DATABASE,
INDEX, VIEW, PRIMARY, KEY, FOREIGN, REFERENCES, CONSTRAINT,
DEFAULT, CHECK, UNIQUE, CASCADE, DISTINCT, EXISTS, CASE, 
WHEN, THEN, ELSE, END, SUM, COUNT, AVG, MAX, MIN, COALESCE
```

---

### 2.2 性能优化检查

| 规则ID | 规则名称 | 检查内容 | 严重程度 | 检测方式 |
|--------|---------|---------|---------|---------|
| COD_PER_001 | 全表扫描预警 | 无WHERE条件的SELECT | BLOCK | 正则：`SELECT.*FROM.*WHERE`缺失 |
| COD_PER_002 | 笛卡尔积检测 | JOIN前无ON条件 | BLOCK | 正则：检测无ON的JOIN |
| COD_PER_003 | 大表LIMIT限制 | 无LIMIT或LIMIT>10000 | WARN | 正则：检测LIMIT值 |
| COD_PER_004 | COUNT优化 | 使用COUNT(*)或COUNT(1) | INFO | 检测COUNT(字段名) |
| COD_PER_005 | 模糊查询前缀 | 左百分号LIKE查询 | WARN | 正则：`LIKE '%...'` |
| COD_PER_006 | 批量INSERT | 建议批量INSERT | INFO | 检测逐条INSERT |

**检测SQL示例：**

```sql
-- COD_PER_001: 全表扫描检测
SELECT 'COD_PER_001' as rule_id,
       '全表扫描预警' as rule_name,
       CASE 
           WHEN UPPER(sql_content) NOT REGEXP 'WHERE' THEN 'FAIL'
           ELSE 'PASS'
       END as check_status
FROM code_repository
WHERE sql_type = 'SQL';

-- COD_PER_002: 笛卡尔积检测  
SELECT 'COD_PER_002' as rule_id,
       '笛卡尔积检测' as rule_name,
       CASE
           WHEN UPPER(sql_content) REGEXP 'JOIN[ A-Z]+\s+ON\s+' THEN 'PASS'
           ELSE 'FAIL'
       END as check_status
FROM code_repository;

-- COD_PER_003: LIMIT检测
SELECT 'COD_PER_003' as rule_id,
       '大表LIMIT限制' as rule_name,
       CASE
           WHEN sql_content NOT REGEXP 'LIMIT[ ]+[0-9]+' THEN 'FAIL'
           WHEN sql_content REGEXP 'LIMIT[ ]+[0-9]{5,}' THEN 'FAIL'
           ELSE 'PASS'
       END as check_status
FROM code_repository;
```

---

### 2.3 SQL反模式检查

| 规则ID | 规则名称 | 检查内容 | 严重程度 | 检测方式 |
|--------|---------|---------|---------|---------|
| COD_ANT_001 | SELECT * | 禁止SELECT * | WARN | 正则：`SELECT\s+\*` |
| COD_ANT_002 | 隐式类型转换 | 避免隐式类型转换 | WARN | 检测类型不匹配JOIN |
| COD_ANT_003 | 负面查询 | NOT IN/NOT EXISTS性能差 | WARN | 正则：`NOT\s+IN\|NOT\s+EXISTS` |
| COD_ANT_004 | OR条件优化 | OR改写为UNION ALL | WARN | 正则：`\bOR\b` |
| COD_ANT_005 | 子查询嵌套 | 避免超过2层嵌套 | WARN | 嵌套深度检测 |
| COD_ANT_006 | 分页深度 | 避免大偏移量分页 | INFO | 正则：`OFFSET[ ]+[0-9]{5,}` |

**检测SQL示例：**

```sql
-- COD_ANT_001: SELECT * 检测
SELECT 'COD_ANT_001' as rule_id,
       'SELECT *' as rule_name,
       CASE
           WHEN UPPER(sql_content) REGEXP 'SELECT\\s+\\*\\s+FROM' THEN 'FAIL'
           ELSE 'PASS'
       END as check_status
FROM code_repository;

-- COD_ANT_003: 负面查询检测
SELECT 'COD_ANT_003' as rule_id,
       '负面查询' as rule_name,
       CASE
           WHEN UPPER(sql_content) REGEXP 'NOT\\s+IN|NOT\\s+EXISTS' THEN 'FAIL'
           ELSE 'PASS'
       END as check_status
FROM code_repository;
```

---

### 2.4 安全合规检查

| 规则ID | 规则名称 | 检查内容 | 严重程度 | 检测方式 |
|--------|---------|---------|---------|---------|
| COD_SEC_001 | 敏感字段脱敏 | 手机号/身份证必须脱敏 | BLOCK | 检测未脱敏敏感字段 |
| COD_SEC_002 | 危险操作预警 | 禁止DROP/TRUNCATE | BLOCK | 正则：`DROP\\s+TABLE\|TRUNCATE` |
| COD_SEC_003 | 无限制DELETE | DELETE必须带WHERE | BLOCK | 正则：`DELETE.*WHERE`缺失 |
| COD_SEC_004 | 明文密码检测 | 禁止明文密码 | BLOCK | 正则：检测password= |
| COD_SEC_005 | 邮箱脱敏 | 邮箱地址部分脱敏 | WARN | 检测未脱敏邮箱 |
| COD_SEC_006 | 银行账号脱敏 | 银行账号必须脱敏 | BLOCK | 检测未脱敏银行账号 |

**敏感字段识别规则：**

| 字段类型 | 识别方式 | 脱敏要求 |
|---------|---------|---------|
| 手机号 | 字段名包含phone/mobile/tel | 脱敏中间4位 |
| 身份证 | 字段名包含idcard/id_no | 脱敏出生日期 |
| 银行卡 | 字段名包含bank/card_no | 脱敏后4位 |
| 邮箱 | 字段名包含email | 脱敏@前部分 |
| 密码 | 字段名包含password/passwd | 禁止明文 |

**检测SQL示例：**

```sql
-- COD_SEC_001: 敏感字段脱敏检测
SELECT 'COD_SEC_001' as rule_id,
       '敏感字段脱敏' as rule_name,
       CASE
           WHEN sql_content REGEXP 'CONCAT|SUBSTR' THEN 'PASS'
           WHEN table_column IN ('phone', 'mobile', 'id_card', 'id_no') THEN 'FAIL'
           ELSE 'PASS'
       END as check_status
FROM code_repository;

-- COD_SEC_002: 危险操作检测
SELECT 'COD_SEC_002' as rule_id,
       '危险操作预警' as rule_name,
       CASE
           WHEN UPPER(sql_content) REGEXP 'DROP\\s+(TABLE|DATABASE)' THEN 'FAIL'
           WHEN UPPER(sql_content) REGEXP 'TRUNCATE' THEN 'FAIL'
           ELSE 'PASS'
       END as check_status
FROM code_repository;

-- COD_SEC_003: 无限制DELETE检测
SELECT 'COD_SEC_003' as rule_id,
       '无限制DELETE' as rule_name,
       CASE
           WHEN UPPER(sql_content) REGEXP 'DELETE\\s+FROM' 
                AND sql_content NOT REGEXP 'WHERE' THEN 'FAIL'
           ELSE 'PASS'
       END as check_status
FROM code_repository;
```

---

### 2.5 分层原则检查

| 规则ID | 规则名称 | 检查内容 | 严重程度 | 检测方式 |
|--------|---------|---------|---------|---------|
| COD_LAY_001 | ODS层禁止聚合 | ODS不应包含聚合 | BLOCK | 检测ODS层SUM/COUNT/AVG |
| COD_LAY_002 | DWD层禁止跨层引用 | DWD只引用ODS/DIM | BLOCK | 检测DWD引用DWS/ADS |
| COD_LAY_003 | DWS层单主题域 | DWS按主题域组织 | WARN | 检测跨主题JOIN |
| COD_LAY_004 | ADS层引用规范 | ADS只引用DWS/DIM | BLOCK | 检测ADS引用ODS/DWD |

**分层识别规则：**

| 分层 | 表名前缀 | 特征 |
|------|---------|------|
| ODS | ods_ | 原始数据，无加工 |
| DIM | dim_ | 维度表 |
| DWD | dwd_ | 明细宽表 |
| DWS | dws_ | 汇总表 |
| ADS | ads_ | 应用表 |

**检测SQL示例：**

```sql
-- COD_LAY_001: ODS层禁止聚合检测
SELECT 'COD_LAY_001' as rule_id,
       'ODS层禁止聚合' as rule_name,
       CASE
           WHEN table_name LIKE 'ods_%' 
                AND sql_content REGEXP 'GROUP\\s+BY|SUM\\(|COUNT\\(|AVG\\(' THEN 'FAIL'
           ELSE 'PASS'
       END as check_status
FROM code_repository;

-- COD_LAY_002: DWD层禁止跨层引用检测
SELECT 'COD_LAY_002' as rule_id,
       'DWD层禁止跨层引用' as rule_name,
       CASE
           WHEN table_name LIKE 'dwd_%' 
                AND (sql_content LIKE '%dws_%' OR sql_content LIKE '%ads_%') THEN 'FAIL'
           ELSE 'PASS'
       END as check_status
FROM code_repository;
```

---

## 三、规则执行优先级

| 优先级 | 规则类型 | 执行顺序 |
|--------|---------|---------|
| 1 | 安全合规检查 | BLOCK级优先执行 |
| 2 | 性能优化检查 | 阻断级性能问题 |
| 3 | 分层原则检查 | 确保分层规范 |
| 4 | SQL反模式检查 | 代码质量优化 |
| 5 | 代码规范检查 | 编码风格统一 |

---

## 四、问题处理时效

| 严重程度 | 处理时限 | 责任人 |
|---------|---------|--------|
| BLOCK | 立即处理 | 开发人员 |
| WARN | 24小时内 | 开发人员 |
| INFO | 下周迭代 | 开发人员 |

---

## 五、规则更新记录

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2026-04-23 | v1.0 | 初始版本，包含5大类62条规则 |
