CREATE TABLE IF NOT EXISTS ads_pr_proj_subcontract_process_settle_detail_df(
    org_code STRING COMMENT '行政单位编码', 
    org_name STRING COMMENT '行政单位名称', 
    project_shortname STRING COMMENT '项目名称全称',
    project_state_name STRING COMMENT '项目状态',
    org_type STRING COMMENT '组织类型',
    contract_id STRING COMMENT '合同id',
    contract_code STRING COMMENT '企业合同编码', 
    contract_name STRING COMMENT '合同名称',
    category_name STRING COMMENT '合同类型',  
    sign_date STRING COMMENT '合同签订日期', 
    contract_tax_mny STRING COMMENT '分包合同金额', 
    sing_contract_tax_mny STRING COMMENT '分包合同签订金额',
    payment_stage_scale STRING COMMENT '支付比例',
    change_cn  STRING COMMENT '补充协议次数',
    change_mny  STRING COMMENT '补充协议总金额',
    supplier_name STRING COMMENT '分包商名称', 
    charge_name STRING COMMENT '分包单位负责人', 
    settle_date STRING COMMENT '结算日期', 
    settle_date_year STRING COMMENT '结算日期年', 
    settle_date_month STRING COMMENT '结算日期月', 
    settle_date_quarter STRING COMMENT '结算日期季度', 
    settle_mny STRING COMMENT '本次结算金额', 
    pay_amount_apply decimal(32,8)  COMMENT '付款金额（拨付单）', 
    pay_amount_finance decimal(32,8)  COMMENT '付款金额（财务收付款）', 
    insert_time STRING COMMENT '数据插入时间 ',
    inner_code  STRING COMMENT '内部编码'
)
COMMENT '工程定案_分包过程结算明细' -- 表的描述信息
PARTITIONED BY ( -- 按日期进行分区存储
    dt STRING COMMENT '日期分区'
)
STORED AS ORC
 lifecycle 30;