# 数仓数据质量评估系统

> 一键执行数仓各分层表的数据质量健康评估，生成量化评分报告。

---

## 📁 文件清单

| 文件 | 说明 |
|------|------|
| `db_config.json` | 数据库配置文件（需修改） |
| `db_connector.py` | 数据库连接工具模块 |
| `rule_v2.md` | 质量校验规则集 |
| `dq_quality_checker.py` | 主执行脚本 |
| `README.md` | 本文档 |

---

## 🚀 快速开始

### 1. 配置数据库连接

编辑 `Data-Governance/quality_check/input/db_config.json`：

```json
{
    "name": "数仓质量评估数据库配置",
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "warehouse_test",
    "charset": "utf8mb4"
}
```

**字段说明：**

| 字段 | 类型 | 含义 | 示例 |
|------|------|------|------|
| name | string | 连接标识名 | moxi |
| host | string | MySQL 主机地址 | rm-bp1k3s08d9qmdk4t3to.mysql.rds.aliyuncs.com |
| port | int | 端口号 | 3306 |
| user | string | 用户名 | yummy |
| password | string | 密码 | yf45464@123 |
| database | string | 数据库名 | fengji |
| charset | string | 字符集 | utf8mb4 |

### 2. 安装依赖

```bash
pip install pymysql
```

### 3. 执行评估

```bash
cd Data-Governance/quality_check/py_scripts

# 方式一：执行完整流程（推荐）
python dq_quality_checker.py --all

# 方式二：分步执行
python dq_quality_checker.py --init    # 阶段 0：初始化环境
python dq_quality_checker.py --sync    # 阶段 1：同步元数据
python dq_quality_checker.py --check   # 阶段 2：执行质量检查
python dq_quality_checker.py --report  # 阶段 3：生成评估报告
```

---

## 📊 评估规则

### 通用规则 (COM_001 ~ COM_005)

| 规则 ID | 规则名称 | 严重程度 |
|--------|---------|---------|
| COM_001 | 分区连续无缺失 | BLOCK |
| COM_002 | 数据量波动合理 | WARN |
| COM_003 | 关键字段非空率 | BLOCK |
| COM_004 | 时间字段无异常 | WARN |
| COM_005 | 脏数据/乱码检查 | INFO |

### 分层专属规则

| 分层 | 规则 ID | 规则名称 | 数量 |
|------|--------|---------|------|
| ODS | ODS_001 ~ ODS_004 | 主键缺失、主键重复、完全重复、删除标识检查 | 4 条 |
| DWD | DWD_001 ~ DWD_003 | 指标非负、外键关联、枚举值检查 | 3 条 |
| DWS | DWS_001 ~ DWS_003 | 分组维度唯一、汇总指标空值率、数据量级合理性 | 3 条 |
| DIM | DIM_001 ~ DIM_003 | 维度编码唯一、维度层级完整、核心属性非空 | 3 条 |
| ADS | ADS_001 ~ ADS_003 | 分组维度唯一、关键指标非空、报表一致性检查 | 3 条 |

---

## 📈 评分体系

### 单表评分

```
单表得分 = 100 - (BLOCK 失败数 × 25) - (WARN 失败数 × 10) - (INFO 失败数 × 3)
最低分为 0 分
```

### 评分等级

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 数据质量优秀，可放心使用 |
| 75-89 | 良好 | 数据质量良好，存在轻微问题 |
| 60-74 | 一般 | 数据质量一般，需要关注 |
| 40-59 | 较差 | 数据质量较差，需要尽快修复 |
| 0-39 | 危险 | 数据质量严重问题，必须立即处理 |

### 分层权重

| 分层 | 权重 |
|------|------|
| ODS | 15% |
| DWD | 25% |
| DWS | 25% |
| DIM | 20% |
| ADS | 15% |

---

## 📂 输出说明

### 数据库表

| 表名 | 说明 |
|------|------|
| `meta_table_column` | 表字段元数据表 |
| `dq_check_result` | 质量校验结果表 |

### 评估报告

位置：`Data-Governance/quality_check/output/质量评估报告_{YYYYMMDD_HHmmss}.md`

报告包含：
- 开篇总结
- 一、评估概览（整体评分、规则通过率、分层评分）
- 二、问题分布（严重程度、TOP10 排行）
- 三、问题明细
- 四、问题处理建议
- 五、趋势对比
- 六、附录

---

## 🔄 执行流程

```
前置材料
├── db_config.json        ──→ 连接参数
├── rule_v2.md            ──→ 规则库+SQL 模板
├── 数仓表数据 (ods/dwd...)──→ 校验对象
└── dq_quality_checker.py ──→ 执行载体

        ↓ 阶段 0：环境初始化

中间产物 (结构)
├── meta_table_column 表结构
└── dq_check_result 表结构

        ↓ 阶段 1：元数据同步

中间产物 (数据)
├── meta_table_column 记录 ──→ 每表每字段的元数据

        ↓ 阶段 2：规则校验

中间产物 (数据)
├── dq_check_result 记录   ──→ 每表每规则的校验结果

        ↓ 阶段 3：报告生成

交付成果
├── 质量评估报告.md       ──→ 最终交付，可直接阅读
├── dq_check_result 数据   ──→ 供历史对比分析
└── meta_table_column 数据 ──→ 供后续评估复用
```

---

## ⚙️ 高级配置

### 修改分层权重

编辑 `dq_quality_checker.py` 中的 `LAYER_WEIGHTS`：

```python
LAYER_WEIGHTS = {
    'ODS': 0.15,
    'DWD': 0.25,
    'DWS': 0.25,
    'DIM': 0.20,
    'ADS': 0.15
}
```

### 修改评分扣分

编辑 `SEVERITY_SCORES`：

```python
SEVERITY_SCORES = {
    'BLOCK': 25,
    'WARN': 10,
    'INFO': 3
}
```

### 添加自定义规则

编辑 `rule_v2.md`，按格式添加新规则。

---

## 🔧 常见问题

### Q1: 提示"配置文件不存在"

确保 `db_config.json` 文件存在于 `Data-Governance/quality_check/input` 目录，或修改代码中的配置路径。

### Q2: 数据库连接失败

检查：
1. 数据库地址、端口是否正确
2. 用户名密码是否正确
3. 数据库是否存在
4. 防火墙是否放行

### Q3: 检查时间过长

对于大表（>1000 万行），建议：
1. 使用采样查询
2. 按分区检查
3. 设置超时时间

---

## 📝 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-04-23 | 初始版本，包含通用规则 5 条，分层规则 16 条 |

---

## 📞 技术支持

如有问题，请查看日志或联系数据管理员。
