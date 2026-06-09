# AssembleScriptJson Skill

## Description

AssembleScriptJson 是一个专门用于**构建 SQL 任务配置**的技能。它从 Excel 配置文件中读取 SQL 任务信息，生成 DTStack 平台的 SQL 类型任务 JSON 配置（如 SparkSql、FlinkSql、ODPS SQL 等）。

此技能是从 `AssembleSyncJson` 分离出来的独立技能，专注于非数据同步类型的 SQL 脚本任务。

## Capabilities

- 读取 task_info.xlsx 中的 SQL 任务 sheet 页（包含 SQL 语句的任务）
- 读取 taskSchedule_info.xlsx 中的任务调度配置
- 支持多种 SQL 任务类型：SparkSql、FlinkSql、ODPS SQL、Hive SQL 等
- 构建完整的 taskInfo 配置（包含 sqlText、taskParams、scheduleConf 等）
- 构建 taskTaskInfo 调度依赖配置（支持多依赖）
- 输出独立的 SQL 任务 JSON 配置文件

## Input Files

### 1. task_info.xlsx

路径：`C:/Users/67461/Desktop/sync_model/model/task_info.xlsx`

**SQL 任务 sheet 页识别规则：**
- 如果 sheet 页的第一行第一列以 SQL 关键字开头（`--`, `SELECT`, `WITH`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`），则视为 SQL 任务
- SQL 任务 sheet 页的每一行第一列拼接成完整的 SQL 内容

**示例：sparksql_etl sheet 页**
```
| -- 数据清洗任务                                    |
| INSERT OVERWRITE TABLE target_table                |
| SELECT                                             |
|     id,                                            |
|     name,                                          |
|     age                                            |
| FROM source_table                                  |
| WHERE dt = '${bdp.system.bizdate}'                 |
```

### 2. taskSchedule_info.xlsx

路径：`C:/Users/67461/Desktop/sync_model/model/taskSchedule_info.xlsx`

任务调度配置：

| 字段 | 说明 | 示例 |
|------|------|------|
| 任务名称 | 任务名 | `sparksql_etl`, `flinksql_clean` |
| 任务类型 | SQL 引擎类型 | `SparkSql`, `FlinkSql`, `ODPS SQL` |
| 上游依赖 | 依赖的上游任务 | `无`, `root`, `mysql2hive_01` |
| 调度时间 | 调度执行时间 | `00:00`, `01:30` |
| 调度类型 | 调度频率 | `天`, `周`, `月`, `小时`, `分钟`, `cron` |

### 3. schedule_info.json（可选）

路径：`C:/Users/67461/Desktop/sync_model/model/schedule_info.json`

调度类型模板，定义不同调度类型的配置结构。

### 4. Reference Template

路径：`references/sparksql_template.json`

参考模板，提供 SQL 任务的默认配置格式。

## Output Format

### Generated JSON Structure

每个 SQL 任务生成一个独立的 JSON 文件：

```json
{
  "taskInfo": {
    "agentResourceId": 17,
    "appType": 1,
    "computeType": 1,
    "createUserId": 1,
    "dependOnSettings": 0,
    "dtuicTenantId": 0,
    "engineType": 1,
    "exeArgs": "",
    "flowId": 0,
    "id": 0,
    "isDeleted": 0,
    "isPublishToProduce": 0,
    "jobBuildType": 1,
    "mainClass": "",
    "name": "sparksql_etl",
    "nodePid": 33357,
    "ownerUserId": 1,
    "ownerUserName": "admin@dtstack.com",
    "periodType": 2,
    "projectId": 695,
    "projectScheduleStatus": 0,
    "scheduleConf": "{\"isFailRetry\":true,\"periodType\":\"2\",\"hour\":0,\"min\":0,...}",
    "scheduleStatus": 1,
    "sqlText": "-- 数据清洗任务\nINSERT OVERWRITE TABLE...",
    "submitStatus": 1,
    "taskDesc": "",
    "taskGroup": 0,
    "taskId": 0,
    "taskType": 0,
    "taskParams": "## Spark 配置参数\n# spark.driver.cores=1\n# spark.driver.memory=1g\n...",
    "tenantId": 10719,
    "yarnResourceName": "saas"
  },
  "taskTaskInfo": [
    {
      "customOffset": 0,
      "forwardDirection": 1,
      "isCurrentProject": true,
      "projectAlias": "zy_test",
      "taskName": "root",
      "taskType": 0,
      "upDownRelyType": 0
    }
  ],
  "updateEnvParam": false
}
```

### Output Files

```
skills/TransferData2/AssembleScriptJson/resoult/
├── sparksql_etl.json
├── flinksql_clean.json
└── ...
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              AssembleScriptJson 完整流程                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 task_info.xlsx                                              │
│       ├── mysql2hive_01 (数据同步任务，跳过)                     │
│       ├── sparksql_etl (SQL 任务) ←──┐                         │
│       └── flinksql_clean (SQL 任务) ←─┼─ 读取 SQL 内容           │
│                                        │                        │
│  📊 taskSchedule_info.xlsx               │                        │
│       └── Sheet1                         │                        │
│           ├── sparksql_etl ──────────────┤                        │
│           └── flinksql_clean ────────────┼─ 读取调度配置          │
│                                          │                        │
│       │                                  │                        │
│       ▼                                  │                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           AssembleScriptJson Skill                       │   │
│  │                                                          │   │
│  │  1. 读取 task_info.xlsx，识别 SQL 任务 sheet 页             │   │
│  │  2. 读取 taskSchedule_info.xlsx，获取调度配置              │   │
│  │  3. 对每个 SQL 任务：                                     │   │
│  │     - 拼接 SQL 内容                                        │   │
│  │     - 构建 scheduleConf（根据调度类型）                    │   │
│  │     - 构建 taskTaskInfo（调度依赖）                       │   │
│  │     - 构建 taskParams（SQL 引擎配置参数）                  │   │
│  │     - 生成完整 taskInfo                                   │   │
│  │  4. 输出 JSON 文件                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│       ▼                                                         │
│  📄 resoult/sparksql_etl.json                                   │
│  📄 resoult/flinksql_clean.json                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### 运行脚本

```bash
cd /home/shuofeng/.openclaw/workspace
python3 skills/TransferData2/AssembleScriptJson/scripts/generate_sql_config.py
```

### 输出位置

```
skills/TransferData2/AssembleScriptJson/resoult/
```

## SQL Task Type Mapping

| 任务类型 | taskType 值 | 说明 |
|----------|-------------|------|
| SparkSql | 0 | Spark SQL 任务 |
| FlinkSql | 0 | Flink SQL 任务 |
| ODPS SQL | 0 | 阿里云 ODPS SQL 任务 |
| Hive SQL | 0 | Hive SQL 任务 |
| 其他 SQL | 0 | 其他 SQL 类型任务 |

## Task Parameters by Type

### SparkSql 任务参数

```
## Driver 程序使用的 CPU 核数，默认为 1
# spark.driver.cores=1

## Driver 程序使用内存大小，默认 1g
# spark.driver.memory=1g

## 对 Spark 每个 action 结果集大小的限制
# spark.driver.maxResultSize=1g

## 启动的 executor 的数量，默认为 1
# spark.executor.instances=1

## 每个 executor 使用的 CPU 核数，默认为 1
# spark.executor.cores=1

## 每个 executor 内存大小，默认 1g
# spark.executor.memory=1g

## 任务优先级，值越小，优先级越高，范围:1-1000

## spark 日志级别
# logLevel = INFO

## spark 中所有网络交互的最大超时时间
# spark.network.timeout=120s

## 设置 spark sql shuffle 分区数，默认 200
# spark.sql.shuffle.partitions=200
```

### FlinkSql 任务参数

```
## 任务运行方式：
## per_job:单独为任务创建 flink yarn session
## session：多个任务共用一个 flink yarn session，默认 session
## flinkTaskRunMode=per_job

## jobManager 配置的内存大小，默认 1024（单位 M)
# jobmanager.memory.mb=1024

## taskManager 配置的内存大小，默认 1024（单位 M）
# taskmanager.memory.mb=1024

## checkpoint 保存时间间隔
# flink.checkpoint.interval=300000

## 任务优先级，范围:1-1000
# pipeline.operator-chaining = false
```

## Task Schedule Configuration

### taskTaskInfo 结构

```json
"taskTaskInfo": [
  {
    "customOffset": 0,
    "forwardDirection": 1,
    "isCurrentProject": true,
    "projectAlias": "zy_test",
    "taskName": "root",  // 或依赖的任务名
    "taskType": 0,       // SQL 任务固定为 0
    "upDownRelyType": 0
  }
]
```

### 调度依赖规则

| 上游依赖 | taskName | taskType | 说明 |
|----------|----------|----------|------|
| 无 | root | 0 | 根节点任务 |
| 其他任务名 | 对应任务名 | 0 | 依赖指定任务 |

## Related Skills

| 技能 | 作用 | 输出 |
|------|------|------|
| [AssembleSyncJson](../AssembleSyncJson/SKILL.md) | 数据同步任务 + 虚节点任务配置 | `resoult/*.json` |
| **AssembleScriptJson** | **SQL 任务配置** | **`resoult/*.json`** |
| [AssembleSyncReleasePackage](../AssembleSyncReleasePackage/SKILL.md) | 多任务发布包组装 | `sync_package_*/` |

## TransferData2 技能分工

```
┌─────────────────────────────────────────────────────────────┐
│              TransferData2 技能分工                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AssembleSyncJson          AssembleScriptJson               │
│  ┌─────────────────┐       ┌─────────────────┐             │
│  │ 数据同步任务     │       │ SQL 任务           │             │
│  │ - MySQL→Hive    │       │ - SparkSql      │             │
│  │ - MySQL→HDFS    │       │ - FlinkSql      │             │
│  │ - HDFS→Hive     │       │ - ODPS SQL      │             │
│  │                 │       │ - Hive SQL      │             │
│  │ 虚节点任务       │       │                 │             │
│  │ - 根节点         │       │                 │             │
│  │ - 依赖节点       │       │                 │             │
│  └─────────────────┘       └─────────────────┘             │
│           │                          │                      │
│           └──────────┬───────────────┘                      │
│                      │                                      │
│                      ▼                                      │
│         AssembleSyncReleasePackage                          │
│         ┌─────────────────────────┐                         │
│         │ 多任务发布包组装         │                         │
│         │ 读取所有任务 JSON         │                         │
│         │ 生成 sync_package_*/    │                         │
│         └─────────────────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Example

### 输入：task_info.xlsx (sparksql_etl sheet)

```
| -- 数据清洗任务                                    |
| INSERT OVERWRITE TABLE target_table                |
| SELECT                                             |
|     id,                                            |
|     name,                                          |
|     age                                            |
| FROM source_table                                  |
| WHERE dt = '${bdp.system.bizdate}'                 |
```

### 输入：taskSchedule_info.xlsx

| 任务名称 | 任务类型 | 上游依赖 | 调度时间 | 调度类型 |
|----------|----------|----------|----------|----------|
| sparksql_etl | SparkSql | mysql2hive_01 | 01:00 | 天 |

### 输出：sparksql_etl.json

- taskInfo.name: `sparksql_etl`
- taskInfo.taskType: `0` (SQL 任务)
- taskInfo.sqlText: 完整的 SQL 语句
- taskInfo.taskParams: Spark 配置参数
- taskTaskInfo[0].taskName: `mysql2hive_01` (依赖上游)
- taskTaskInfo[0].taskType: `0` (SQL 任务依赖)

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| 找不到 SQL 任务 | task_info.xlsx 中 SQL 内容格式不正确 | 确保第一行以 SQL 关键字开头 |
| 调度配置缺失 | taskSchedule_info.xlsx 中缺少任务名 | 在 taskSchedule_info 中添加对应任务 |
| SQL 内容为空 | sheet 页识别失败 | 检查第一行是否以 `--` 或 SQL 关键字开头 |
| 依赖任务不存在 | taskTaskInfo 引用的任务未生成 | 先运行 AssembleSyncJson 生成依赖任务 |

## Files

- `SKILL.md` - This file
- `references/sparksql_template.json` - SparkSql 参考模板
- `scripts/generate_sql_config.py` - SQL 任务配置生成脚本
- `resoult/` - 输出目录

## Quick Start

```bash
cd /home/shuofeng/.openclaw/workspace

# 生成 SQL 任务配置
python3 skills/TransferData2/AssembleScriptJson/scripts/generate_sql_config.py

# 输出位置：
# skills/TransferData2/AssembleScriptJson/resoult/*.json
```

---

*Created: 2026-05-17*
*Separated from AssembleSyncJson to provide dedicated SQL task configuration generation*
