# 模型规范检查报告

**生成时间**: 2026-07-03 14:10:43

## 开篇总结

本次检查共覆盖 **5** 个数据表，整体平均得分 **89.8** 分。

## 一、评估概览

### 整体评分

| 分层 | 表数 | 平均分 | 最高分 | 最低分 |
|------|------|--------|--------|--------|
| ADS | 1 | 95.0 | 95 | 95 |
| DIM | 1 | 95.0 | 95 | 95 |
| DWD | 1 | 87.0 | 87 | 87 |
| DWS | 1 | 95.0 | 95 | 95 |
| ODS | 1 | 77.0 | 77 | 77 |

### 评分等级说明

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 模型质量优秀 |
| 75-89 | 良好 | 模型质量良好 |
| 60-74 | 一般 | 模型质量一般 |
| 40-59 | 较差 | 模型质量较差 |
| 0-39 | 危险 | 存在严重问题 |

## 二、问题分布

### 检查项扣分统计

| 检查项 | 总扣分 | 说明 |
|--------|--------|------|
| 表命名检查 | 0 | 表名规范 |
| 字段规范检查 | 24 | 字段命名、注释、类型 |
| 分区规范检查 | 2 | 分区设计 |
| 存储规范检查 | 25 | 存储格式、压缩配置 |

## 三、分层详情


### ADS层
| 表名 | 字段数 | 得分 | 主要问题 |
|------|--------|------|----------|
| ads_pr_proj_subcontract_process_settle_detail_df | 25 | 95 | 存储格式使用 ORC/Parquet 但未配置压缩格式 |

### DIM层
| 表名 | 字段数 | 得分 | 主要问题 |
|------|--------|------|----------|
| dim_pr_org_project_sub_company_info_df | 19 | 95 | 存储格式使用 ORC/Parquet 但未配置压缩格式 |

### DWD层
| 表名 | 字段数 | 得分 | 主要问题 |
|------|--------|------|----------|
| dwd_pr_subcontract_contracts_df | 121 | 87 | 4 个字段缺少注释：project_name, contra... |

### DWS层
| 表名 | 字段数 | 得分 | 主要问题 |
|------|--------|------|----------|
| dws_ct_contract_settlement_inventory_details_df | 29 | 95 | 存储格式使用 ORC/Parquet 但未配置压缩格式 |

### ODS层
| 表名 | 字段数 | 得分 | 主要问题 |
|------|--------|------|----------|
| ods_ztpc_xmglxt_ejc_proincome_ejc_income_contract_register_df | 101 | 77 | 7 个字段缺少注释：project_name, org_na... |

## 四、TOP 问题表

### 得分最低的 5 个表

| 表名 | 分层 | 得分 | 主要问题 |
|------|------|------|----------|
| ods_ztpc_xmglxt_ejc_proincome_ejc_income_contract_register_df | ODS | 77 | 7 个字段缺少注释：project_name, org_name, parent... |
| dwd_pr_subcontract_contracts_df | DWD | 87 | 4 个字段缺少注释：project_name, contract_name, o... |
| ads_pr_proj_subcontract_process_settle_detail_df | ADS | 95 | 存储格式使用 ORC/Parquet 但未配置压缩格式 |
| dws_ct_contract_settlement_inventory_details_df | DWS | 95 | 存储格式使用 ORC/Parquet 但未配置压缩格式 |
| dim_pr_org_project_sub_company_info_df | DIM | 95 | 存储格式使用 ORC/Parquet 但未配置压缩格式 |

## 五、整改建议

### 优先修复项

1. **字段注释补充**：为所有缺少注释的字段添加 COMMENT
2. **字段命名规范**：将驼峰命名改为下划线命名
3. **存储压缩配置**：为 ORC/Parquet 表添加压缩配置

### 建议配置

```sql
-- 推荐的存储配置
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY')
```

## 六、最佳实践

- 表名使用 `分层前缀_业务域_表名_增量标识` 格式
- 所有字段必须有 COMMENT 注释
- 分区字段统一使用 `dt` (日期)
- 使用 ORC 或 Parquet 列式存储
- 配置适当的压缩格式（SNAPPY/ZLIB）
