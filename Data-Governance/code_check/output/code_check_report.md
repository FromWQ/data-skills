# 数仓代码检查报告

**生成时间**: 2026-07-06 19:14:07

## 开篇总结

本次检查覆盖 **106** 个代码任务，共执行 **4770** 次规则检查。

- **通过**: 4627 项
- **失败**: 143 项

## 一、评估概览

### 整体评分

| 分层 | 代码数 | 平均分 | BLOCK | WARN | INFO |
|------|--------|--------|-------|------|------|
| ADS | 2 | 65.0 | 2 | 2 | 0 |
| DWD | 13 | 52.3 | 20 | 13 | 0 |
| DWS | 8 | 32.5 | 18 | 9 | 0 |
| ODS | 83 | 88.5 | 11 | 68 | 0 |

### 评分等级说明

| 分数范围 | 等级 | 说明 |
|---------|------|------|
| 90-100 | 优秀 | 代码质量优秀 |
| 75-89 | 良好 | 代码质量良好 |
| 60-74 | 一般 | 代码质量一般 |
| 40-59 | 较差 | 代码质量较差 |
| 0-39 | 危险 | 存在严重问题 |

## 二、问题分布

### 严重程度分布

- **BLOCK**: 51 个
- **WARN**: 92 个

### 问题类型分布

- **代码规范检查**: 88 个
- **安全合规检查**: 25 个
- **分层原则检查**: 21 个
- **性能优化检查**: 5 个
- **SQL 反模式检查**: 4 个

## 三、分层详情


### ADS层
| 任务名称 | 评分 | BLOCK 问题 | WARN 问题 | INFO 问题 |
|----------|------|-----------|----------|----------|
| ads_engy_cost_vin_redy_trip_wide_metric_detl_di | 65 | 1 | 1 | 0 |
| ads_engy_cost_vin_chrg_cycl_wide_metric_detl_df | 65 | 1 | 1 | 0 |

### DWD层
| 任务名称 | 评分 | BLOCK 问题 | WARN 问题 | INFO 问题 |
|----------|------|-----------|----------|----------|
| dwd_sig_exd_engy_detl_di | 0 | 4 | 1 | 0 |
| dwd_sig_engy_detl_di_copy | 15 | 3 | 1 | 0 |
| dwd_sig_cutm_comm_detl_di | 40 | 2 | 1 | 0 |
| dwd_sig_gb_detl_di | 40 | 2 | 1 | 0 |
| dwd_sig_cutm_engy_detl_di | 40 | 2 | 1 | 0 |

### DWS层
| 任务名称 | 评分 | BLOCK 问题 | WARN 问题 | INFO 问题 |
|----------|------|-----------|----------|----------|
| dws_car_drv_vin_redy_trip_metric_detl_di | 15 | 3 | 1 | 0 |
| dws_car_drv_vin_stall_trip_metric_detl_di | 15 | 3 | 1 | 0 |
| dws_car_drv_vin_state_df | 15 | 3 | 1 | 0 |
| dws_engy_splm_vin_chrg_cycl_metric_detl_df | 30 | 2 | 2 | 0 |
| dws_engy_cost_vin_ready_trip_metric_detl_di | 40 | 2 | 1 | 0 |

### ODS层
| 任务名称 | 评分 | BLOCK 问题 | WARN 问题 | INFO 问题 |
|----------|------|-----------|----------|----------|
| test_sd | 40 | 2 | 1 | 0 |
| testsssxccc | 40 | 2 | 1 | 0 |
| spark35 | 40 | 2 | 1 | 0 |
| ods_track_tsp_t_log_ontm_di | 65 | 1 | 1 | 0 |
| ods_track_tsp_t_log_drft_di | 65 | 1 | 1 | 0 |

## 四、TOP 问题

### 问题代码排行（按问题数量）

| 任务名称 | 所属分层 | 评分 | BLOCK | WARN | INFO |
|----------|----------|------|-------|------|------|
| dwd_sig_exd_engy_detl_di | DWD | 0 | 4 | 1 | 0 |
| dws_car_drv_vin_redy_trip_metric_detl_di | DWS | 15 | 3 | 1 | 0 |
| dwd_sig_engy_detl_di_copy | DWD | 15 | 3 | 1 | 0 |
| dws_car_drv_vin_stall_trip_metric_detl_di | DWS | 15 | 3 | 1 | 0 |
| dws_engy_splm_vin_chrg_cycl_metric_detl_df | DWS | 30 | 2 | 2 | 0 |
| dws_car_drv_vin_state_df | DWS | 15 | 3 | 1 | 0 |
| test_sd | ODS | 40 | 2 | 1 | 0 |
| testsssxccc | ODS | 40 | 2 | 1 | 0 |
| dwd_sig_cutm_comm_detl_di | DWD | 40 | 2 | 1 | 0 |
| dws_engy_cost_vin_ready_trip_metric_detl_di | DWS | 40 | 2 | 1 | 0 |

## 五、整改建议

### 优先级建议

1. **立即处理（BLOCK 级）**：
   - [test_sd] ODS 层禁止聚合: ODS 不应包含聚合
   - [test_sd] ADS 层引用规范: ADS 只引用 DWS/DIM
   - [ods_gb_car_login_all_view] ODS 层禁止聚合: ODS 不应包含聚合
   - [ods_track_tsp_t_log_ontm_di] 危险操作预警: 禁止 DROP/TRUNCATE
   - [ods_track_tsp_t_log_drft_di] 危险操作预警: 禁止 DROP/TRUNCATE

2. **建议修复（WARN 级）**：
   - 完善代码注释和命名规范
   - 优化查询性能，避免全表扫描
   - 遵循分层设计原则

3. **持续优化（INFO 级）**：
   - 改进代码格式和可读性
   - 统一编码风格

## 六、最佳实践

- 使用明确的字段名替代 `SELECT *`
- 为所有查询添加适当的 `WHERE` 条件
- 对敏感字段实施脱敏处理
- 遵循分层命名规范（ods_/dwd_/dws_/dim_/ads_）
- 定期执行代码检查，持续改进代码质量
