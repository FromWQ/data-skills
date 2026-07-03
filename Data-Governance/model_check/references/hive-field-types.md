# Hive字段类型最佳实践

## Hive数据类型分类

### 数值类型

| 类型 | 范围 | 存储大小 | 适用场景 |
|-----|-----|---------|---------|
| TINYINT | -128 ~ 127 | 1字节 | 状态码、小范围枚举 |
| SMALLINT | -32,768 ~ 32,767 | 2字节 | 端口、中等范围数值 |
| INT | -21亿 ~ 21亿 | 4字节 | 常规整数、数量 |
| BIGINT | -922亿亿 ~ 922亿亿 | 8字节 | ID、大数值 |
| FLOAT | 6-7位精度 | 4字节 | 科学计算 |
| DOUBLE | 15-16位精度 | 8字节 | 科学计算 |
| DECIMAL(p,s) | 精确数值 | 可变 | 金额、财务数据 |

### 字符串类型

| 类型 | 最大长度 | 适用场景 |
|-----|---------|---------|
| STRING | 2GB | 不定长文本、JSON |
| VARCHAR(n) | n字符 | 定长字符串(≤100) |
| CHAR(n) | n字符 | 固定长度字符串 |

### 日期时间类型

| 类型 | 格式 | 适用场景 |
|-----|-----|---------|
| DATE | yyyy-MM-dd | 日期 |
| TIMESTAMP | yyyy-MM-dd HH:mm:ss | 时间戳 |
| INTERVAL | - | 时间间隔 |

### 复杂类型

| 类型 | 说明 | 适用场景 |
|-----|-----|---------|
| ARRAY | 有序数组 | 标签列表 |
| MAP | 键值对 | 属性映射 |
| STRUCT | 结构体 | 嵌套数据 |

## 类型选择决策树

```
开始
├── 是数值吗？
│   ├── 是
│   │   ├── 需要小数吗？
│   │   │   ├── 是 → DECIMAL(p,s)
│   │   │   └── 否
│   │   │       ├── 范围 -128~127 → TINYINT
│   │   │       ├── 范围 -32768~32767 → SMALLINT
│   │   │       ├── 范围 -21亿~21亿 → INT
│   │   │       └── 超过21亿 → BIGINT
│   └── 否
│       ├── 是日期吗？
│       │   ├── 是
│       │   │   ├── 只需要日期 → DATE
│       │   │   └── 需要时间 → TIMESTAMP
│       │   └── 否
│           ├── 是布尔值吗？ → BOOLEAN
│           ├── 长度固定且≤100 → VARCHAR(n)
│           └── 其他 → STRING
```

## 类型选择最佳实践

### ID字段

| ID类型 | 推荐类型 | 说明 |
|-------|---------|-----|
| 自增ID | BIGINT | 支持大范围 |
| UUID | STRING(36) | 36字符标准格式 |
| 业务ID | STRING | 保持原始格式 |
| 雪花ID | BIGINT | 19位数字 |

### 金额字段

```sql
-- 正确: 使用DECIMAL
amount DECIMAL(18,2) COMMENT '金额(元)'

-- 错误: 使用DOUBLE
amount DOUBLE COMMENT '金额(元)'  -- 可能丢失精度
```

**金额字段规范:**
- 使用DECIMAL(p,s)
- p: 总位数，考虑业务规模
- s: 小数位数，通常2位

### 日期字段

| 场景 | 推荐类型 | 格式 |
|-----|---------|-----|
| 日期 | DATE | yyyy-MM-dd |
| 日期时间 | TIMESTAMP | yyyy-MM-dd HH:mm:ss |
| 分区字段 | STRING | yyyyMMdd |
| 年月 | STRING | yyyyMM |

### 状态字段

| 状态数量 | 推荐类型 | 示例 |
|---------|---------|-----|
| 2个状态 | BOOLEAN | is_active |
| 少量枚举 | TINYINT | status(0,1,2,3) |
| 较多枚举 | SMALLINT | type_code |
| 文本状态 | STRING | status_name |

### 字符串字段

| 长度范围 | 推荐类型 | 说明 |
|---------|---------|-----|
| 固定长度 | CHAR(n) | 如手机号、身份证 |
| ≤100字符 | VARCHAR(n) | 如姓名、标题 |
| >100字符 | STRING | 如描述、内容 |
| JSON/XML | STRING | 复杂结构数据 |

## 常见类型选择错误

### 错误1: 全部使用STRING

```sql
-- 错误示例
CREATE TABLE bad_example (
    id STRING,           -- 应使用BIGINT
    amount STRING,       -- 应使用DECIMAL
    create_time STRING,  -- 应使用TIMESTAMP
    status STRING        -- 应使用TINYINT
);
```

**问题:**
- 无法进行数值计算
- 存储空间浪费
- 查询性能下降

### 错误2: 使用DOUBLE存储金额

```sql
-- 错误示例
price DOUBLE COMMENT '价格'

-- 正确示例
price DECIMAL(10,2) COMMENT '价格'
```

**原因:** DOUBLE存在精度丢失问题

### 错误3: 混用VARCHAR和STRING

```sql
-- 不推荐: 混用类型
CREATE TABLE mixed_types (
    name VARCHAR(50),
    description STRING
);

-- 推荐: 统一使用STRING
CREATE TABLE unified_types (
    name STRING,
    description STRING
);
```

### 错误4: 使用错误的时间类型

```sql
-- 错误: 用STRING存储时间戳
event_time STRING COMMENT '事件时间'

-- 正确: 使用TIMESTAMP
event_time TIMESTAMP COMMENT '事件时间'
```

## 类型转换

### 显式转换

```sql
-- 字符串转数值
CAST('123' AS INT)

-- 数值转字符串
CAST(123 AS STRING)

-- 字符串转日期
CAST('2024-01-01' AS DATE)
```

### 隐式转换规则

| 转换方向 | 是否支持 |
|---------|---------|
| 小类型 → 大类型 | 支持 |
| 大类型 → 小类型 | 不支持(需显式) |
| 字符串 → 数值 | 支持 |
| 数值 → 字符串 | 支持 |

## 字段命名规范

### 命名规则

1. 使用小写字母
2. 单词间用下划线分隔
3. 长度不超过32字符
4. 见名知意

### 常见字段命名

| 含义 | 推荐命名 | 类型 |
|-----|---------|-----|
| 主键ID | id / {entity}_id | BIGINT/STRING |
| 名称 | {entity}_name | STRING |
| 编码 | {entity}_code | STRING |
| 状态 | status / {entity}_status | TINYINT |
| 创建时间 | create_time / created_at | TIMESTAMP |
| 更新时间 | update_time / updated_at | TIMESTAMP |
| 创建人 | create_by / created_by | STRING |
| 是否删除 | is_deleted | BOOLEAN |
| 开始日期 | start_date | DATE |
| 结束日期 | end_date | DATE |