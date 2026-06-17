# 数仓代码检查报告

## 开篇总结
本次检查覆盖106个代码，共执行4664次规则检查，发现127个问题。

## 一、评估概览
| 分层 | 代码数 | 平均分 | BLOCK | WARN |
|------|--------|--------|-------|------|
| DWS | 4 | 56.2 | 5 | 5 |
| ODS | 89 | 87.5 | 15 | 74 |
| DWD | 13 | 61.2 | 15 | 13 |

## 二、问题分布
### 严重程度分布
- BLOCK: 35 个
- WARN: 92 个

### 问题类型分布
- 2.1 代码规范: 88 个
- 2.4 安全合规: 25 个
- 2.5 分层原则: 5 个
- 2.2 性能优化: 5 个
- 2.3 SQL反模式: 4 个

## 三、分层详情

### DWS层
| 任务名称 | 评分 | BLOCK问题 | WARN问题 |
|----------|------|-----------|----------|
| ads_engy_cost_vin_chrg_cycl_wide_metric_detl_df | 65 | 1 | 1 |
| ads_engy_cost_vin_redy_trip_wide_metric_detl_di | 65 | 1 | 1 |
| dws_car_drv_vin_mile_aggr_di | 65 | 1 | 1 |
| dws_engy_splm_vin_chrg_cycl_metric_detl_df | 30 | 2 | 2 |

### ODS层
| 任务名称 | 评分 | BLOCK问题 | WARN问题 |
|----------|------|-----------|----------|
| cust_data_compare | 65 | 1 | 1 |
| dcvp_custm_tag_day_drop_partition | 90 | 0 | 1 |
| dcvp_cutm_his_drop_partition | 90 | 0 | 1 |
| dcvp_cutm_tag_day | 90 | 0 | 1 |
| dcvp_cutm_tag_day_copy | 90 | 0 | 1 |

### DWD层
| 任务名称 | 评分 | BLOCK问题 | WARN问题 |
|----------|------|-----------|----------|
| dwd_track_app_record_detl_di | 90 | 0 | 1 |
| dwd_trip_chrg_cycl_detl_df | 65 | 1 | 1 |
| dwd_trip_chrg_trip_detl_di | 65 | 1 | 1 |
| dwd_trip_gb_trip_detl_di | 65 | 1 | 1 |
| dwd_trip_on_trip_detl_di | 65 | 1 | 1 |

## 四、TOP问题
| 任务名称 | 规则ID | 规则名称 | 严重程度 |
|----------|--------|---------|----------|
| ads_engy_cost_vin_chrg_cycl_wide_metric_detl_df | COD_NAM_001 | 命名规范 | WARN |
| ads_engy_cost_vin_redy_trip_wide_metric_detl_di | COD_NAM_001 | 命名规范 | WARN |
| cust_data_compare | COD_NAM_001 | 命名规范 | WARN |
| dcvp_custm_tag_day_drop_partition | COD_NAM_001 | 命名规范 | WARN |
| dcvp_cutm_his_drop_partition | COD_NAM_001 | 命名规范 | WARN |
| dcvp_cutm_tag_day | COD_NAM_001 | 命名规范 | WARN |
| dcvp_cutm_tag_day_copy | COD_NAM_001 | 命名规范 | WARN |
| dwd_sig_cutm_comm_detl_di | COD_NAM_001 | 命名规范 | WARN |
| dwd_sig_cutm_engy_detl_di | COD_NAM_001 | 命名规范 | WARN |
| dwd_sig_engy_detl_di_copy | COD_NAM_001 | 命名规范 | WARN |
## 五、整改建议
1. **安全第一**：优先修复BLOCK级别的安全问题
2. **性能优化**：解决全表扫描、笛卡尔积等性能问题  
3. **规范完善**：补充必要的注释和遵循命名规范
4. **分层原则**：确保各层代码符合数仓分层设计原则

## 六、最佳实践
- 使用明确的字段名替代SELECT *
- 为所有查询添加适当的WHERE条件
- 对敏感字段实施脱敏处理
- 遵循分层命名规范（ods_/dwd_/dws_/dim_/ads_）
