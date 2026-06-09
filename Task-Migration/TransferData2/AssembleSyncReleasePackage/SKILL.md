# AssembleSyncReleasePackage Skill

## Description

DTStack 多任务同步发布包组装技能。读取 AssembleSyncJson 生成的多个任务脚本，组装成 DTStack 平台可发布的完整目录结构。

与 [AssembleModel](../AssembleModel/SKILL.md) 类似，但支持多任务批量发布。

**更新：** task.xls 现在通过 `taskSchedule_info.xlsx` 动态生成，references 目录使用 `C:\Users\67461\Desktop\sync_model\多任务模板\` 下的最新内容作为参考。

## Capabilities

- 读取 AssembleSyncJson/resoult/ 下的所有 JSON 任务文件
- 自动提取所有任务中的数据源信息（去重）
- 读取 `taskSchedule_info.xlsx` 生成 task.xls
- 生成 package.json 包配置
- 生成 task_catalogue.json 任务目录配置
- 创建 tasks 子目录并放置所有任务脚本
- 输出到 Windows Desktop，文件夹命名：sync_package_时间戳

## Input/Output Structure

### Input

**主要输入:**
- `AssembleSyncJson/resoult/*.json` - AssembleSyncJson 生成的多个任务 JSON 文件

**调度配置:**
- `C:/Users/67461/Desktop/sync_model/model/taskSchedule_info.xlsx` - 任务调度依赖配置

**参考模板:**
- `references/package.json` - 包配置模板
- `references/task_catalogue.json` - 任务目录模板
- `references/task.xls` - 任务 Excel 模板（用于结构参考）
- `references/tasks/` - 参考任务 JSON 文件

### Output

```
C:/Users/67461/Desktop/sync_package_YYYYMMDD_HHMMSS/
├── package.json           # 包配置
├── task_catalogue.json    # 任务目录结构
├── task.xls              # 任务 Excel (从 taskSchedule_info.xlsx 生成)
├── error.log             # 错误日志 (空)
└── tasks/
    ├── mysql2hive_01.json  # 任务脚本 1
    ├── mysql2hive_02.json  # 任务脚本 2
    └── ...
```

## Package Structure

### 目录结构说明

| 文件/目录 | 说明 | 来源 |
|-----------|------|------|
| `package.json` | 包配置信息（数据源、引擎、项目等） | 动态生成 |
| `task_catalogue.json` | 任务目录树结构 | 动态生成 |
| `task.xls` | 任务信息 Excel | **从 taskSchedule_info.xlsx 生成** |
| `error.log` | 错误日志文件 | 创建空文件 |
| `tasks/` | 任务脚本目录 | 创建 |
| `tasks/*.json` | 所有任务脚本 | 从 AssembleSyncJson 复制 |

### package.json 结构

```json
{
  "createTime": "2026-05-09 09:29:06",
  "createUser": "admin@dtstack.com",
  "dataSourceList": [
    {"dataSourceName": "zy_test_MYSQL", "dataSourceType": 1},
    {"dataSourceName": "zy_test_HADOOP", "dataSourceType": 45}
  ],
  "engineList": [
    {"engineType": 1, "schema": "zy_test"}
  ],
  "packageDesc": "多任务同步发布包",
  "packageName": "sync_package_20260509_092906",
  "projectName": "zy_test",
  "tenantName": "培训演示",
  "userNameList": []
}
```

### task_catalogue.json 结构

```json
{
  "0": [{
    "nodeName": "周期任务",
    "level": 0,
    "nodePid": 0,
    "id": 31153
  }],
  "1": [{
    "nodeName": "任务开发",
    "level": 1,
    "nodePid": 31153,
    "id": 31155
  }],
  "2": [{
    "nodeName": "测试",
    "level": 2,
    "nodePid": 31155,
    "id": 33357
  }]
}
```

## Usage

### 运行脚本

```bash
python3 skills/TransferData2/AssembleSyncReleasePackage/scripts/assemble_sync_package.py
```

### 输出位置

```
C:/Users/67461/Desktop/sync_package_YYYYMMDD_HHMMSS/
```

### 文件夹命名规则

```
sync_package_当前时间戳
```

示例：`sync_package_20260509_092906`

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│         AssembleSyncReleasePackage 工作流程                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 读取 AssembleSyncJson/resoult/*.json                    │
│     - mysql2hive_01.json                                    │
│     - mysql2hive_02.json                                    │
│     - ...                                                   │
│                                                             │
│  2. 解析所有任务脚本中的数据源信息（去重）                   │
│     - dataSourceName                                        │
│     - dataSourceType                                        │
│     - schema                                                │
│                                                             │
│  3. 生成 package.json                                       │
│     - createTime                                            │
│     - packageName (sync_package_时间戳)                     │
│     - dataSourceList (合并去重)                             │
│     - engineList                                            │
│                                                             │
│  4. 生成 task_catalogue.json                                │
│     - 周期任务 (level 0)                                    │
│     - 任务开发 (level 1)                                    │
│     - 测试 (level 2)                                        │
│                                                             │
│  5. 读取 taskSchedule_info.xlsx                             │
│     - 解析任务调度依赖关系                                   │
│     - 生成 task.xls                                         │
│                                                             │
│  6. 创建 tasks/ 目录并放置所有任务脚本                       │
│                                                             │
│  7. 创建空 error.log 文件                                   │
│                                                             │
│  8. 输出到 C:/Users/67461/Desktop/sync_package_时间戳/       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Example

### 输入文件

**AssembleSyncJson/resoult/:**
```
mysql2hive_01.json
mysql2hive_02.json
```

**taskSchedule_info.xlsx:**
```
| 任务名称      | 上游依赖 |
|--------------|----------|
| mysql2hive_01 | 无       |
| mysql2hive_02 | root     |
```

### 输出目录

```
C:/Users/67461/Desktop/sync_package_20260509_092906/
├── package.json
├── task_catalogue.json
├── task.xls (从 taskSchedule_info.xlsx 生成)
├── error.log
└── tasks/
    ├── mysql2hive_01.json
    └── mysql2hive_02.json
```

## Related Skills

| Skill | 作用 | 输出 |
|-------|------|------|
| [AssembleSyncJson](../AssembleSyncJson/SKILL.md) | 多任务配置生成 | *.json |
| [AssembleModel](../AssembleModel/SKILL.md) | 单任务发布包组装 | package_时间戳/ |
| **AssembleSyncReleasePackage** | **多任务发布包组装** | **sync_package_时间戳/** |

## Files

- `SKILL.md` - This file
- `references/package.json` - 包配置模板
- `references/task_catalogue.json` - 任务目录模板
- `references/task.xls` - 任务 Excel 模板（参考）
- `references/tasks/` - 参考任务 JSON 文件
- `scripts/assemble_sync_package.py` - 组装脚本
- `resoult/` - 临时输出目录（可选）

## Complete TransferData Flow

### 原流程（单任务）

```
┌─────────────────────────────────────────────────────────────┐
│              单任务流程 (AssembleModel)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1️⃣  MysqlReader                                            │
│      mysql_info.xlsx → mysql_reader_config.json             │
│                                                             │
│  2️⃣  HdfsWriter                                             │
│      hdfs_info.xlsx → hdfs_writer_config.json               │
│                                                             │
│  3️⃣  ParseSqlText                                           │
│      拼接 → sql_text.json                                   │
│                                                             │
│  4️⃣  ParseScript / ParseScriptBase64                        │
│      Base64 编码 → mysql2hive_script.json                   │
│                                                             │
│  5️⃣  AssembleModel                                          │
│      组装发布包 → package_时间戳/                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 新流程（多任务）

```
┌─────────────────────────────────────────────────────────────┐
│              多任务流程 (AssembleSyncJson + Release)         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 dataSource_info.xlsx  ──┐                              │
│  📊 task_info.xlsx     ────┼──→ AssembleSyncJson           │
│  📊 taskSchedule_info.xlsx─┘     ↓                          │
│                              resoult/*.json                 │
│                                     ↓                       │
│  1️⃣  AssembleSyncJson                                      │
│      多任务配置生成 → resoult/mysql2hive_01.json, ...       │
│                                                             │
│  2️⃣  AssembleSyncReleasePackage                            │
│      读取 taskSchedule_info.xlsx                            │
│      生成 task.xls                                          │
│      多任务发布包组装 → sync_package_时间戳/                │
│                                                             │
│  3️⃣  在 DTStack 平台导入发布包                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Comparison: AssembleModel vs AssembleSyncReleasePackage

| Feature | AssembleModel | AssembleSyncReleasePackage |
|---------|---------------|---------------------------|
| 输入来源 | ParseScriptBase64 / ParseScript | AssembleSyncJson |
| 任务数量 | 单任务 | 多任务 |
| 输入文件 | mysql2hive_script.json | *.json (多个) |
| 输出目录 | package_时间戳/ | sync_package_时间戳/ |
| task.xls 来源 | 静态模板复制 | **taskSchedule_info.xlsx 动态生成** |
| 适用场景 | 独立 SQL 任务 / 单数据同步任务 | 多任务批量发布 |
| 数据源提取 | 从单个任务提取 | 从所有任务合并去重 |

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| 找不到任务脚本 | AssembleSyncJson 未运行 | 先运行 AssembleSyncJson 脚本 |
| 输出目录无法创建 | Windows 路径权限问题 | 检查 C 盘访问权限 |
| 数据源解析失败 | sqlText 解码错误 | 检查 JSON 格式是否有效 |
| 空任务列表 | resoult/ 目录为空 | 确认 AssembleSyncJson 生成了 JSON 文件 |
| task.xls 生成失败 | taskSchedule_info.xlsx 格式错误 | 检查 Excel 文件格式和列结构 |

## Quick Start

```bash
# 1. 生成多任务配置
cd /home/shuofeng/.openclaw/workspace
python3 skills/TransferData2/AssembleSyncJson/scripts/generate_config.py

# 2. 组装发布包（自动从 taskSchedule_info.xlsx 生成 task.xls）
python3 skills/TransferData2/AssembleSyncReleasePackage/scripts/assemble_sync_package.py

# 3. 在 C 盘查看输出
# C:/Users/67461/Desktop/sync_package_YYYYMMDD_HHMMSS/
```

---

*Created: 2026-05-09*
*Updated: 2026-05-09 - 更新 references 内容，task.xls 从 taskSchedule_info.xlsx 动态生成*
