# AssembleSyncJson Skill

## Description

AssembleSyncJson 是一个整合型技能，将 MysqlReader、HdfsWriter、Parser、ParseSqlText、ParseScriptBase64 的功能整合成一个完整流程。该技能直接从 Excel 配置文件中读取数据源信息、任务信息和调度信息，生成完整的 DTStack 数据同步任务 JSON 配置。

## Capabilities

- 读取 dataSource_info.xlsx 数据源配置（支持多个 sheet 页）
- 读取 task_info.xlsx 任务脚本信息（支持多个 sheet 页，生成多个 JSON 脚本）
- 读取 taskSchedule_info.xlsx 任务调度配置信息
- 根据 task_info 中的数据源类型自动匹配对应的数据源配置
- 处理字段映射关系（同行映射，"是否映射"为"是"则关联）
- 自动识别分区字段并配置分区值（如 dt=20260508）
- 生成完整的 taskInfo 和 taskTaskInfo 配置
- 输出 Base64 编码的任务脚本 JSON

## Input Files

### 1. dataSource_info.xlsx

路径：`C:\Users\67461\Desktop\sync_model\model\dataSource_info.xlsx`

包含多个 sheet 页，每个 sheet 页对应一个数据源配置：

| 字段 | 说明 | 示例 |
|------|------|------|
| 数据源类型 | 数据源类型标识 | `mysql`, `hdfs` |
| dataSourceName | 数据源名称 | `zy_test_MYSQL` |
| dataSourceType | 数据源类型 ID | `1` (MySQL), `45` (Hadoop) |
| jdbc | 连接字符串 | `jdbc:mysql://...` |
| username | 用户名 | `drpeco` |
| password | 密码 | `DT#passw0rd2024` |
| path | HDFS 路径（仅 HDFS） | `/user/hive/warehouse/...` |
| partition | 分区配置（仅 HDFS） | `pt=20260508` |
| hadoopConfig | Hadoop 配置（仅 HDFS） | JSON 字符串 |

### 2. task_info.xlsx

**本地路径**（优先）：`skills/TransferData2/输入文件/task_info.xlsx`  
**远程路径**（回退）：`C:\Users\67461\Desktop\sync_model\model\task_info.xlsx`

包含多个 sheet 页，每个 sheet 页对应一个任务。

**🆕 新格式**（11列，含 `源名称`/`目标名称`）：

| 字段 | 说明 | 示例 |
|------|------|------|
| 源名称 | 源数据源名称（匹配 dataSource_info 的 sheet 名/dataSourceName） | `zy_test_MYSQL` |
| 源表类型 | 源数据源类型 | `mysql` |
| 源表表名 | MySQL 源表名 | `students` |
| 源表字段 | 源字段名 | `age` |
| 源表字段类型 | 源字段类型 | `int` |
| 是否映射 | 是否进行字段映射 | `是`, `否` |
| 目标名称 | 目标数据源名称（匹配 dataSource_info 的 sheet 名/dataSourceName） | `zy_test_HADOOP` |
| 目标表类型 | 目标数据源类型 | `hdfs` |
| 目标表表名 | Hive 目标表名 | `students` |
| 目标表字段 | 目标字段名 | `id` |
| 目标表字段类型 | 目标字段类型 | `int` |

**🔙 旧格式**（9列，兼容格式，无 `源名称`/`目标名称`）：

| 字段 | 说明 | 示例 |
|------|------|------|
| 源表表名 | MySQL 源表名 | `student_sex` |
| 源表类型 | 源数据源类型（用于类型匹配查找 dataSource_info） | `mysql` |
| 源表字段 | 源字段名 | `id` |
| 源表字段类型 | 源字段类型 | `int` |
| 是否映射 | 是否进行字段映射 | `是`, `否` |
| 目标表表名 | Hive 目标表名 | `students_zwq` |
| 目标表类型 | 目标数据源类型（用于类型匹配查找 dataSource_info） | `hdfs` |
| 目标表字段 | 目标字段名 | `id` |
| 目标表字段类型 | 目标字段类型 | `int` |

**数据源匹配规则（新格式）**：
- 根据 `源名称` 列的值（如 `zy_test_MYSQL`）去 `dataSource_info.xlsx` 中查找对应 sheet 页名称或 `dataSourceName`
- 根据 `目标名称` 列的值（如 `zy_test_HADOOP`）去 `dataSource_info.xlsx` 中查找对应 sheet 页名称或 `dataSourceName`
- 如果未填写源名称/目标名称（旧格式），则回退到按数据源类型（`mysql`/`hdfs`）匹配

**字段映射规则**：
- 同行映射：源字段和目标字段在同一行
- "是否映射"为"是"：两个字段进行关联
- "是否映射"为"否"：不进行关联（字段忽略）
- 分区字段：单独一行，第一列为"分区字段"

### 3. taskSchedule_info.xlsx

路径：`C:\Users\67461\Desktop\sync_model\model\taskSchedule_info.xlsx`

任务调度配置信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| 任务名称 | 任务名 | `mysql2hive_01`, `root` |
| 上游依赖 | 依赖的上游任务 | `无`, `root` |

### 4. Reference Template

路径：`references/mysql2hive_01.json`

参考模板，提供输出格式和默认值。

## Output Format

### Generated JSON Structure

每个任务生成一个独立的 JSON 文件：

```json
{
  "taskInfo": {
    "name": "mysql2hive_01",
    "taskType": 2,
    "nodePid": 33357,
    "projectId": 695,
    "tenantId": 10719,
    "scheduleConf": "{\"isFailRetry\":true,\"periodType\":\"2\",\"maxRetryNum\":\"3\"}",
    "sqlText": "{...Base64 编码的任务配置...}",
    "taskParams": "## 任务运行方式配置..."
  },
  "taskTaskInfo": [
    {
      "customOffset": 0,
      "forwardDirection": 1,
      "isCurrentProject": true,
      "projectAlias": "zy_test",
      "taskName": "root",  // 根据 taskSchedule_info 配置，无依赖时为 root
      "taskType": 2,       // 有依赖时为 2（数据同步任务类型）
      "upDownRelyType": 0
    }
  ],
  "updateEnvParam": false
}
```

### Output Files

```
skills/TransferData/AssembleSyncJson/resoult/
├── mysql2hive_01.json
├── mysql2hive_02.json
└── ...
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              AssembleSyncJson 完整流程                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 dataSource_info.xlsx                                        │
│       ├── zy_test_MYSQL (sheet)                                 │
│       └── zy_test_HADOOP (sheet)                                │
│                                                                 │
│  📊 task_info.xlsx                   ← 优先读取 输入文件/ 本地副本│
│       ├── mysql2hive_01 (sheet, 新格式)                          │
│       │   源名称→zy_test_MYSQL, 目标名称→zy_test_HADOOP          │
│       ├── mysql2hive_02 (sheet, 旧格式兼容)                      │
│       └── test_sparksql (SQL任务)                                │
│                                                                 │
│  📊 taskSchedule_info.xlsx                                      │
│       └── Sheet1                                                │
│                                                                 │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              AssembleSyncJson Skill                      │   │
│  │                                                          │   │
│  │  1. 读取数据源配置 → 构建 dataSourceMap                  │   │
│  │  2. 读取任务信息 → 按 sheet 分组处理                     │   │
│  │     🔑 新格式: 根据 源名称/目标名称 匹配 dataSource_info │   │
│  │                的 sheet 页（dataSourceName）              │   │
│  │     🔙 旧格式: 回退到按数据源类型（mysql/hdfs）匹配       │   │
│  │  3. 读取调度配置 → 构建 taskScheduleMap                  │   │
│  │  4. 对每个任务：                                         │   │
│  │     - 解析字段映射关系                                   │   │
│  │     - 识别分区字段                                       │   │
│  │     - 构建 parser 配置                                   │   │
│  │     - 构建 job 配置（reader + writer）                    │   │
│  │     - Base64 编码 sqlText                                │   │
│  │     - 构建 taskTaskInfo（调度依赖）                      │   │
│  │  5. 输出 JSON 文件                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│       ▼                                                         │
│  📄 resoult/mysql2hive_01.json                                  │
│  📄 resoult/mysql2hive_02.json                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### 运行脚本

```bash
cd /home/shuofeng/.openclaw/workspace
python3 skills/TransferData/AssembleSyncJson/scripts/generate_config.py
```

### 输出位置

```
skills/TransferData/AssembleSyncJson/resoult/
```

## Column Mapping Rules

### 字段映射逻辑

1. **同行映射**: 源字段和目标字段在同一行
2. **是否映射="是"**: 建立字段关联，加入 keymap
3. **是否映射="否"**: 忽略该字段，不加入映射
4. **分区字段**: 第一列为"分区字段"的行，标记为分区字段

### 分区字段处理

- 在 targetMap.column 中标记 `isPart: true`
- 在 keymap.target 中排除分区字段
- 自动添加分区值，如 `pt=20260508`

### 类型映射

| MySQL Type | HDFS/Hive Type |
|------------|----------------|
| INT | int |
| VARCHAR | string |
| BIGINT | bigint |
| DATETIME | string |
| TEXT | string |
| DECIMAL | decimal |

## Task Schedule Configuration

### taskTaskInfo 结构

每个任务生成 **一个** taskTaskInfo 条目，根据 taskSchedule_info 配置决定内容：

```json
"taskTaskInfo": [
  {
    "customOffset": 0,
    "forwardDirection": 1,
    "isCurrentProject": true,
    "projectAlias": "zy_test",
    "taskName": "root",  // 或依赖的任务名
    "taskType": -1,      // 无依赖时为 -1，有依赖时为 2
    "upDownRelyType": 0
  }
]
```

### 调度依赖规则

| 上游依赖 | taskName | taskType | 说明 |
|----------|----------|----------|------|
| 无 | root | -1 | 根节点任务 |
| root | root | 2 | 依赖 root 任务 |
| 其他任务名 | 对应任务名 | 2 | 依赖指定任务 |

## Related Skills

此技能整合了以下技能的功能：

| 技能 | 作用 | 整合方式 |
|------|------|----------|
| [MysqlReader](../MysqlReader/SKILL.md) | MySQL 读取配置 | 直接从 dataSource_info 读取 |
| [HdfsWriter](../HdfsWriter/SKILL.md) | HDFS 写入配置 | 直接从 dataSource_info 读取 |
| [Parser](../Parser/SKILL.md) | 字段映射整合 | 从 task_info 解析映射关系 |
| [ParseSqlText](../ParseSqlText/SKILL.md) | 配置拼接 | 内部构建完整 job 配置 |
| [ParseScriptBase64](../ParseScriptBase64/SKILL.md) | Base64 编码 | 内部进行 Base64 编码 |

## Example

### 输入：task_info.xlsx (mysql2hive_01 sheet)

| 源表表名 | 源表类型 | 源表字段 | 源表字段类型 | 是否映射 | 目标表表名 | 目标表类型 | 目标表字段 | 目标表字段类型 |
|----------|----------|----------|--------------|----------|------------|------------|------------|----------------|
| students | mysql | age | int | 是 | students | hdfs | id | int |
| students | mysql | name | varchar(100) | 是 | students | hdfs | name | string |
| students | mysql | id | int | 是 | students | hdfs | age | int |
| 分区字段 | students | hdfs | pt | string | | | | |

### 输出：mysql2hive_01.json

- taskInfo.name: `mysql2hive_01`
- sourceMap.column: [age, name, id]
- targetMap.column: [id, name, age, pt] (包含分区字段)
- keymap.target: [id, name, age] (排除分区字段)
- partition: `pt=20260508`
- taskTaskInfo: 根据 taskSchedule_info 配置依赖关系

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| 找不到输入文件 | Excel 文件路径错误 | 优先将 task_info.xlsx 放入 `输入文件/`；确认远程文件在 `C:\Users\67461\Desktop\sync_model\model\` |
| 数据源匹配失败（新格式） | `源名称`/`目标名称` 与 dataSource_info 的 sheet 名或 dataSourceName 不一致 | 检查名称拼写，确保与 dataSource_info 中的值一致 |
| 数据源匹配失败（旧格式） | task_info 中的数据源类型与 dataSource_info 不一致 | 检查数据源类型标识（mysql/hdfs）或改用新格式的 源名称/目标名称 |
| 字段映射错误 | "是否映射"列值不是"是"或"否" | 确保使用中文"是"或"否" |
| 分区字段未识别 | 分区字段行第一列不是"分区字段" | 确保第一列为"分区字段" |
| 调度依赖缺失 | taskSchedule_info 中缺少任务名 | 在 taskSchedule_info 中添加对应任务 |

## Files

- `SKILL.md` - This file
- `references/mysql2hive_01.json` - 参考配置模板
- `references/task_type.xlsx` - 任务类型映射表
- `scripts/generate_config.py` - 配置生成脚本
- `resoult/` - 输出目录
- `../输入文件/task_info.xlsx` - 本地任务配置文件（优先读取）

## Complete TransferData Flow Comparison

### 原流程（6 步）

```
1️⃣  MysqlReader       → mysql_reader_config.json
2️⃣  HdfsWriter        → hdfs_writer_config.json
3️⃣  Parser            → parser.json
4️⃣  ParseSqlText      → sql_text.json
5️⃣  ParseScriptBase64 → mysql2hive_script.json
6️⃣  AssembleModel     → package_YYYYMMDD_HHMMSS/
```

### AssembleSyncJson 流程（1 步）

```
📊 dataSource_info.xlsx  ──┐
📊 task_info.xlsx     ────┼──→ AssembleSyncJson ──→ resoult/*.json
📊 taskSchedule_info.xlsx─┘
```

---

*最后更新：2026-05-24*
