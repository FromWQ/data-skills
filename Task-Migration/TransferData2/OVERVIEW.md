# TransferData2 — 多任务批量同步发布框架

> 创建时间：2026-05-09 | 最后更新：2026-05-24

## 📋 概述

TransferData2 是一个从 **Excel 配置文件 → DTStack 发布包** 的一站式生成框架，涵盖数据同步任务、SQL 任务和虚节点任务的批量处理。

与 TransferData（单任务、多步骤手动）不同，TransferData2 支持：
- 一个 Excel 配置多个任务
- 自动匹配数据源
- 新旧格式兼容
- 一键生成可发布的 DTStack 导入包

---

## 🏗️ 架构总览

```
TransferData2/
├── 📄 OVERVIEW.md                        # 本文档
├── 📂 输入文件/                           # 本地输入文件（优先读取）
│   ├── dataSource_info.xlsx             # 数据源配置
│   ├── task_info.xlsx                   # 任务配置（含新旧格式）
│   ├── taskSchedule_info.xlsx           # 调度依赖配置
│   └── public_info.xlsx                 # 全局公共参数
│
├── 📂 AssembleSyncJson/                  # 🔧 技能1：数据同步 + 虚节点任务生成
│   ├── SKILL.md
│   ├── scripts/generate_config.py       # 主脚本
│   ├── references/
│   │   ├── mysql2hive_01.json           # 数据同步任务模板
│   │   ├── virtual_node_template.json   # 虚节点模板
│   │   ├── schedule_info.json           # 调度类型模板
│   │   ├── task_type.xlsx               # 任务类型映射表
│   │   └── sparksql_template.json       # SQL 参考（兼容）
│   └── resoult/                         # 输出目录
│
├── 📂 AssembleScriptJson/                # 🔧 技能2：SQL 任务生成
│   ├── SKILL.md
│   ├── scripts/generate_sql_config.py   # 主脚本
│   ├── references/
│   │   ├── sparksql_template.json       # SQL 任务模板
│   │   ├── schedule_info.json           # 调度类型模板
│   │   └── task_type.xlsx               # 任务类型映射表
│   └── resoult/                         # 输出目录
│
├── 📂 AssembleSyncReleasePackage/        # 🔧 技能3：发布包组装
│   ├── SKILL.md
│   ├── scripts/assemble_sync_package.py  # 主脚本
│   ├── references/
│   │   ├── package.json                 # 包结构模板
│   │   ├── task_catalogue.json          # 目录树模板
│   │   ├── task.xls                     # Excel 结构参考
│   │   └── tasks/                       # 参考任务 JSON
│   └── resoult/
│
├── 📂 scripts/
│   └── run_transfer_data2.py            # 一键执行入口
│
└── 📂 生成案例/                          # 示例发布包
```

---

## 🗺️ 完整数据流

```
                             ┌──────────────────────────────────────────┐
                             │           输入文件（本地优先）              │
                             ├──────────────────────────────────────────┤
                             │  📊 dataSource_info.xlsx                │
                             │     ├── zy_test_MYSQL  (mysql, type=1)  │
                             │     └── zy_test_HADOOP (hdfs, type=45)  │
                             │                                          │
                             │  📊 task_info.xlsx                      │
                             │     ├── mysql2hive_01  (新格式 11列)      │
                             │     ├── mysql2hive_02  (旧格式 9列)       │
                             │     └── test_sparksql  (SQL key-value)   │
                             │                                          │
                             │  📊 taskSchedule_info.xlsx              │
                             │     ├── root (虚节点, 无依赖)             │
                             │     ├── mysql2hive_01 (天调度, 依赖root)  │
                             │     ├── mysql2hive_02 (小时调度, 依赖root)│
                             │     └── test_sparksql (天调度, 双依赖)    │
                             │                                          │
                             │  📊 public_info.xlsx                    │
                             │     ├── tenantId=10719                  │
                             │     ├── projectId=695                   │
                             │     ├── nodePid=33357                   │
                             │     └── yarnResourceName=saas           │
                             └──────────────────────────────────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    │                              │                              │
                    ▼                              ▼                              │
         ┌──────────────────┐          ┌──────────────────┐                      │
         │ 🔧 AssembleSync  │          │ 🔧 AssembleScript│                      │
         │    Json          │          │    Json          │                      │
         ├──────────────────┤          ├──────────────────┤                      │
         │                  │          │                  │                      │
         │ 1. 读取3个Excel   │          │ 1. 读取 Excel    │                      │
         │ 2. 匹配数据源     │          │ 2. 识别 SQL 任务 │                      │
         │ 3. 字段映射       │          │ 3. 生成 sqlText  │                      │
         │ 4. 构建 parser    │          │ 4. 追加 taskParams│                      │
         │ 5. 构建 job       │          │ 5. 构建调度依赖  │                      │
         │ 6. Base64编码     │          │                  │                      │
         │ 7. 调度依赖       │          │                  │                      │
         │                  │          │                  │                      │
         │ 📤 输出:          │          │ 📤 输出:          │                      │
         │   root.json       │          │   test_sparksql   │                      │
         │   mysql2hive_01   │          │   .json           │                      │
         │   mysql2hive_02   │          │                  │                      │
         │   test_sparksql   │          │                  │                      │
         └──────────────────┘          └──────────────────┘                      │
                    │                              │                              │
                    └──────────────┬───────────────┘                              │
                                   │                                              │
                                   ▼                                              │
                    ┌──────────────────────────────┐                              │
                    │ 🔧 AssembleSyncReleasePackage│                              │
                    ├──────────────────────────────┤                              │
                    │                              │                              │
                    │ 1. 汇总所有任务 JSON           │                              │
                    │ 2. 提取数据源信息（去重）       │                              │
                    │ 3. 生成 package.json          │                              │
                    │ 4. 生成 task_catalogue.json   │                              │
                    │ 5. 生成 task.xls              │                              │
                    │ 6. 复制任务脚本到 tasks/       │                              │
                    │                              │                              │
                    │ 📤 输出:                      │                              │
                    │   sync_package_YYYYMMDD_HHMMSS│                              │
                    └──────────────────────────────┘                              │
                                   │                                              │
                                   ▼                                              │
                    ┌──────────────────────────────┐                              │
                    │       📤 导入 DTStack 平台     │                              │
                    └──────────────────────────────┘                              │
```

---

## 📥 输入文件详解

### 1. dataSource_info.xlsx — 数据源配置

| 表名 | sheet 名 | dataSourceName | dataSourceType | 连接信息 |
|------|---------|----------------|----------------|----------|
| MySQL 数据源 | `zy_test_MYSQL` | zy_test_MYSQL | 1 | jdbc:mysql://172.16.114.43:3306/zy_test |
| HDFS/Hive 数据源 | `zy_test_HADOOP` | zy_test_HADOOP | 45 | hdfs://ns1 + jdbc:hive2://... |

**字段结构**（key-value 格式，每个 sheet 内）：

| Key | MySQL 示例 | HDFS 示例 |
|-----|-----------|----------|
| 数据源类型 | `mysql` | `hdfs` |
| dataSourceName | `zy_test_MYSQL` | `zy_test_HADOOP` |
| dataSourceType | `1` | `45` |
| jdbc | `jdbc:mysql://...` | `jdbc:hive2://...` |
| username | `drpeco` | `admin@dtstack.com` |
| password | *** | *** |
| dtCenterSourceId | `4013` | `4007` |
| sourceIds | `2579` | `2573` |
| path | — | `hdfs://ns1/...` |
| fileType | — | `orc` |
| hadoopConfig | — | JSON 配置块 |

### 2. task_info.xlsx — 任务配置信息

包含三种 sheet 类型：

#### 🆕 新格式（数据同步任务，11 列）

**识别条件**：表头含 `源名称` 列

| 列 | 字段名 | 说明 | mysql2hive_01 示例 |
|----|--------|------|-------------------|
| 0 | 源名称 | 源数据源名称 → 匹配 dataSource_info 的 sheet 名 | `zy_test_MYSQL` |
| 1 | 源表类型 | 源数据源类型 | `mysql` |
| 2 | 源表表名 | 源数据库表名 | `students` |
| 3 | 源表字段 | 源字段名 | `age` |
| 4 | 源表字段类型 | 源字段类型 | `int` |
| 5 | 是否映射 | `是`=建立关联, `否`=忽略 | `是` |
| 6 | 目标名称 | 目标数据源名称 → 匹配 dataSource_info 的 sheet 名 | `zy_test_HADOOP` |
| 7 | 目标表类型 | 目标数据源类型 | `hdfs` |
| 8 | 目标表表名 | 目标表名（Hive） | `students` |
| 9 | 目标表字段 | 目标字段名 | `id` |
| 10 | 目标表字段类型 | 目标字段类型 | `int` |

**数据源匹配规则**：
- 优先用 `源名称`/`目标名称` 调用 `get_source_by_name()` 匹配 dataSource_info 的 **sheet 名** 或 **dataSourceName** 字段
- 若无名称（旧格式），回退到按 `源表类型`/`目标表类型`（`mysql`/`hdfs`）进行类型匹配

#### 🔙 旧格式（数据同步任务，9 列，向后兼容）

| 列 | 字段名 | 说明 |
|----|--------|------|
| 0 | 源表表名 | `student_sex` |
| 1 | 源表类型 | `mysql` → 类型匹配 |
| 2–4 | … | … |
| 5 | 目标表表名 | `students_zwq` |
| 6 | 目标表类型 | `hdfs` → 类型匹配 |
| 7–8 | … | … |

#### 📝 SQL 任务格式（key-value）

**识别条件**：首行第一列为 `sqlText`

| 行 | 列0 | 列1 |
|----|-----|-----|
| 0 | `sqlText` | SQL 语句（直接覆盖 JSON 对应字段） |
| 1 | `taskParams` | 自定义参数（直接追加到默认值后） |

**示例**（test_sparksql）：
```
Row 0: ['sqlText', 'select * from students']
Row 1: ['taskParams', 'spark.executor.cores=2\nspark.executor.memory=2g']
```

#### 分区字段行

所有数据同步 sheet 的末行，第一列为 `分区字段`：

```
['分区字段', 'zy_test_HADOOP', 'hdfs', 'students', 'pt', 'string']
                ↑目标名称       ↑类型   ↑表名      ↑分区名 ↑分区类型
```

### 3. taskSchedule_info.xlsx — 调度依赖配置

| 列 | 字段名 | 说明 |
|----|--------|------|
| 0 | 任务名称 | 对应 task_info 的 sheet 名 |
| 1 | 任务类型 | `虚节点` / `数据同步` / `SparkSql` / `FlinkSql` 等 |
| 2 | 上游依赖 | `无` / `root` / `task1,task2`（多依赖逗号分隔） |
| 3 | 调度时间 | `00:00` / `01:30` / `1hour` |
| 4 | 调度类型 | `天` / `小时` / `周` / `月` / `分钟` / `cron` |

**当前任务调度表**：

| 任务名称 | 任务类型 | 上游依赖 | 调度时间 | 调度类型 |
|----------|----------|----------|----------|----------|
| root | 虚节点 | 无 | 00:00 | 天 |
| mysql2hive_01 | 数据同步 | root | 01:30 | 天 |
| mysql2hive_02 | 数据同步 | root | 1hour | 小时 |
| test_sparksql | SparkSql | mysql2hive_01,mysql2hive_02 | 05:00 | 天 |

### 4. public_info.xlsx — 公共全局参数

| Key | Value | 注入位置 |
|-----|-------|----------|
| tenantId | `10719` | `taskInfo.tenantId` |
| projectId | `695` | `taskInfo.projectId` |
| nodePid | `33357` | `taskInfo.nodePid` |
| yarnResourceName | `saas` | `taskInfo.yarnResourceName` |

**加载机制**：`PublicInfoConfig.load_from_excel()` 读取所有 key-value → `self.config.update(public_info.to_dict())`，新增行自动注入无需改动代码。

---

## 🔧 技能模块详解

### 技能1：AssembleSyncJson — 数据同步 + 虚节点

**定位**：处理所有 **数据同步任务**（MySQL→Hive）和 **虚节点任务**，生成完整的 DTStack 任务 JSON。

**处理流程**：

```
Excel 读取
  ├── dataSource_info.xlsx → DataSourceConfig（按 sheet 名/type 索引）
  ├── task_info.xlsx       → TaskInfo（新旧格式自动检测）
  ├── taskSchedule_info.xlsx → TaskScheduleConfig
  └── public_info.xlsx     → PublicInfoConfig → self.config

逐任务生成：
  ├── 虚节点 → build_virtual_node_config()
  │     └── sqlText='', taskType=虚节点ID, yarnResourceName=来自 public_info
  │
  ├── 数据同步 → build_task_config()
  │     ├── _build_parser_config()
  │     │   ├── 名称优先 → get_source_by_name(source_name)
  │     │   ├── 类型回退 → get_source_by_type(source_type)
  │     │   ├── _build_source_map() → 源表 columns + partition
  │     │   ├── _build_target_map() → 目标表 columns + partition
  │     │   └── _build_keymap() → 字段映射（is_mapped=是）
  │     ├── _build_job_config() → reader + writer + 分区值
  │     ├── Base64编码 → sqlText
  │     ├── _build_task_task_info() → 调度依赖
  │     └── _build_schedule_conf() → 调度策略
  │
  └── SQL任务 → build_sql_task_config()
        └── 与 AssembleScriptJson 逻辑对齐

输出到 resoult/：
  ├── root.json
  ├── mysql2hive_01.json
  ├── mysql2hive_02.json
  └── test_sparksql.json
```

**关键技术点**：

| 特性 | 实现 |
|------|------|
| 数据源匹配 | `get_source_by_name()` 优先（sheet名/dataSourceName），`get_source_by_type()` 回退 |
| 新旧格式兼容 | 检测表头是否有 `源名称` 列自动切换解析模式 |
| 分区字段 | 根据 dataSource_info 中实际类型（mysql/hdfs）判断是否添加 partition |
| 字段映射 | `是否映射=是` → 加入 keymap，同行对应 source/target |
| 调度模板 | 加载 schedule_info.json，根据调度类型匹配对应模板 |

---

### 技能2：AssembleScriptJson — SQL 任务

**定位**：专门处理 **SQL 类型任务**（SparkSql、FlinkSql 等），生成 DTStack SQL 任务 JSON。

**处理流程**：

```
Excel 读取
  ├── task_info.xlsx       → SqlTaskInfo（只处理 SQL 格式 sheet）
  ├── taskSchedule_info.xlsx → 调度配置
  └── public_info.xlsx     → 公共参数

SQL sheet 处理（_load_new_format）：
  ├── data[0][1] → sqlText（第一行第二列，直接覆盖）
  └── data[1][1] → taskParams（第二行第二列，追加到默认值后）

逐任务生成 → build_sql_task_config()：
  ├── sqlText = Excel 内容（直接覆盖 JSON 对应字段）
  ├── taskParams = 默认参数 + '\n' + Excel 自定义参数（直接追加）
  ├── scheduleConf = 根据调度类型生成
  └── taskTaskInfo = 调度依赖（支持多依赖）

跳过非 SQL 任务（数据同步、虚节点）
```

**默认 taskParams 模板**（按任务类型）：

| 任务类型 | 默认参数 |
|----------|----------|
| SparkSql | spark.driver.cores, spark.executor.memory, spark.sql.shuffle.partitions 等 |
| FlinkSql | flinkTaskRunMode, jobmanager.memory.mb, taskmanager.memory.mb 等 |

**自定义 taskParams 追加规则**：
- Excel 中的 `taskParams` 行内容以 `\n` 追加在默认参数之后
- 无 `## 自定义参数` 等额外标题，直接追加
- Excel 单元格中的 `\n` 换行符被正确保留

---

### 技能3：AssembleSyncReleasePackage — 发布包组装

**定位**：汇总 AssembleSyncJson 生成的所有任务 JSON，组装成 DTStack 可直接导入的发布包。

**处理流程**：

```
1. 扫描 AssembleSyncJson/resoult/*.json
   ├── root.json
   ├── mysql2hive_01.json
   ├── mysql2hive_02.json
   └── test_sparksql.json

2. 解析所有任务的 sqlText 中的 parser.job 配置
   ├── 提取 dataSourceName + dataSourceType（去重）
   └── 提取 schema 信息

3. 生成 package.json
   ├── dataSourceList → 所有数据源（合并去重）
   ├── engineList → 引擎 + schema
   └── packageName, createTime 等元信息

4. 生成 task_catalogue.json
   └── 目录树结构（周期任务 → 任务开发 → 测试）

5. 读取 taskSchedule_info.xlsx → 生成 task.xls

6. 复制所有任务 JSON → tasks/ 目录

7. 创建空 error.log

输出到 Windows Desktop：
  C:/Users/67461/Desktop/sync_package_YYYYMMDD_HHMMSS/
```

---

## 📤 输出产物

### resoult/ 输出（技能1+2）

```
AssembleSyncJson/resoult/
├── root.json                # 虚节点（根节点，sqlText 为空）
├── mysql2hive_01.json       # students → students（新格式，名称匹配）
├── mysql2hive_02.json       # student_sex → students_zwq（旧格式，类型匹配）
└── test_sparksql.json       # SELECT SQL 任务

AssembleScriptJson/resoult/
└── test_sparksql.json       # SQL 任务（独立生成）
```

### 发布包输出（技能3）

```
C:/Users/67461/Desktop/sync_package_20260524_123820/
├── package.json              # 包配置（dataSourceList 合并去重）
├── task_catalogue.json       # 任务目录层级
├── task.xls                  # 从 taskSchedule_info.xlsx 生成
├── error.log                 # 空日志
└── tasks/
    ├── root.json
    ├── mysql2hive_01.json
    ├── mysql2hive_02.json
    └── test_sparksql.json
```

### taskInfo 字段对照表

| 字段 | 虚节点 | 数据同步 | SQL 任务 | 来源 |
|------|--------|----------|----------|------|
| name | root | mysql2hive_01 | test_sparksql | sheet 名 |
| taskType | 虚节点ID | 2 | SQL ID | task_type.xlsx 查表 |
| sqlText | `''` | Base64(parser+job) | SQL 语句 | Excel / 拼接编码 |
| taskParams | `''` | Flink 默认参数 | 引擎默认+自定义 | _get_task_params() |
| nodePid | | | | public_info |
| projectId | | | | public_info |
| tenantId | | | | public_info |
| yarnResourceName | | | | public_info |
| scheduleConf | | | | taskSchedule_info |
| taskTaskInfo | | | | taskSchedule_info（依赖） |

---

## 🚀 快速执行

### 一键运行

```bash
cd /home/shuofeng/.openclaw/workspace
python3 skills/TransferData2/scripts/run_transfer_data2.py
```

### 分步执行

```bash
# 步骤 1: 生成数据同步 + 虚节点 + SQL 任务配置
python3 skills/TransferData2/AssembleSyncJson/scripts/generate_config.py

# 步骤 2 (可选): 独立生成 SQL 任务配置
python3 skills/TransferData2/AssembleScriptJson/scripts/generate_sql_config.py

# 步骤 3: 组装发布包
python3 skills/TransferData2/AssembleSyncReleasePackage/scripts/assemble_sync_package.py
```

### 输出位置

```
步骤 1 → skills/TransferData2/AssembleSyncJson/resoult/*.json
步骤 2 → skills/TransferData2/AssembleScriptJson/resoult/*.json
步骤 3 → C:/Users/67461/Desktop/sync_package_YYYYMMDD_HHMMSS/
```

---

## 📐 关键设计决策

### 1. 文件读取优先级

| 文件 | 优先路径 | 回退路径 |
|------|----------|----------|
| task_info.xlsx | `输入文件/task_info.xlsx` | `C:\...\sync_model\model\task_info.xlsx` |
| public_info.xlsx | `输入文件/public_info.xlsx` | （本地固定） |
| dataSource_info.xlsx | — | `C:\...\sync_model\model\dataSource_info.xlsx` |
| taskSchedule_info.xlsx | — | `C:\...\sync_model\model\taskSchedule_info.xlsx` |

### 2. 数据源匹配策略

```
新格式 task_info（含 源名称/目标名称）:
  source_name='zy_test_MYSQL' → get_source_by_name() → dataSource_info sheet 'zy_test_MYSQL'
  target_name='zy_test_HADOOP' → get_source_by_name() → dataSource_info sheet 'zy_test_HADOOP'

旧格式 task_info（无名称列）:
  source_type='mysql' → get_source_by_type('mysql') → dataSource_info 中 type='mysql' 的 sheet
  target_type='hdfs' → get_source_by_type('hdfs') → dataSource_info 中 type='hdfs' 的 sheet
```

### 3. 公共参数注入

`public_info.xlsx` 中的任意 key-value 对在加载时自动注入 `self.config`，任何代码通过 `self.config.get(key, default)` 即可取值，新增参数无需修改加载逻辑。

### 4. 新旧格式兼容

`task_info.xlsx` 的 sheet 格式通过表头自动检测：
- 含 `源名称` → 11 列新格式
- 首行第一列为 `sqlText` → SQL key-value 格式
- 其他 → 9 列旧格式

### 5. taskParams 处理

| 任务类型 | taskParams 构成 |
|----------|----------------|
| 虚节点 | 空字符串 `''` |
| 数据同步 | Flink 运行方式配置（固定默认值） |
| SQL 任务 | `默认引擎参数 + '\n' + Excel 自定义参数` |

---

## 🔗 与 TransferData 的关系

| 维度 | TransferData | TransferData2 |
|------|--------------|---------------|
| 任务数量 | 单任务 | 多任务批量 |
| 配置方式 | 6 步离散执行 | Excel 配置 → 一键生成 |
| 任务类型 | 数据同步 | 数据同步 + 虚节点 + SQL |
| 输出 | `package_时间戳/` | `sync_package_时间戳/` |
| 数据源配置 | 分步手动 | Excel sheet 自动匹配 |
| 公共参数 | 硬编码 | public_info.xlsx 动态注入 |

TransferData 主框架：`skills/TransferData/`

---

## 🎯 发布后操作

1. 登录 DTStack 数据开发平台
2. 进入「包管理」或「任务管理」
3. 选择「导入包」
4. 选择生成的 `sync_package_YYYYMMDD_HHMMSS/` 目录
5. 确认导入
6. 在任务列表中查看执行：

| 任务 | 类型 | 执行顺序 | 调度 |
|------|------|----------|------|
| root | 虚节点 | 1 | 每天 00:00 |
| mysql2hive_01 | 数据同步 | 2（依赖 root） | 每天 01:30 |
| mysql2hive_02 | 数据同步 | 2（依赖 root） | 每小时 |
| test_sparksql | SparkSql | 3（依赖 01+02） | 每天 05:00 |

---

*最后更新：2026-05-24*
