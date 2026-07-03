CREATE TABLE IF NOT EXISTS dim_pr_org_project_sub_company_info_df(
                         org_id           STRING COMMENT '组织ID', 
                         org_code STRING COMMENT '经理部项目编码',-- 经理部项目编码
                         org_name STRING COMMENT '经理部项目名称',-- 经理部项目名称
                         project_shortname STRING COMMENT '经理部项目简称',-- 经理部项目简称
                         project_state_name STRING COMMENT '经理部项目状态',-- 经理部项目状态
                         project_id STRING COMMENT '经理部项目id',-- 经理部项目id
                         project_code STRING COMMENT '项目部项目编码',-- 项目部项目编码
                         project_name STRING COMMENT '项目部项目名称',-- 项目部项目名称
                         cylx_category_code STRING COMMENT '项目部项目产业领域编码',-- 项目部项目产业领域编码
                         cylx_category_name STRING COMMENT '项目部项目产业领域编码',-- 项目部项目产业领域编码
                         national_name STRING COMMENT '项目部项目国家编码',-- 项目部项目国家编码
                         insert_time STRING COMMENT '插入时间',
                         establishment_time STRING COMMENT '项目成立时间',
                         completion_time STRING COMMENT '项目实际完工日期',
                         org_type STRING           COMMENT '公司类型',
                         `region_name` string COMMENT'区域名称',
                         `region_code` string COMMENT'区域编码',
                         inner_code    string COMMENT'内部编码'
)
COMMENT '项目域项目信息维表' -- 表的描述信息
PARTITIONED BY ( -- 按日期进行分区存储
                         dt STRING COMMENT '日期分区'
)
STORED AS ORC
 lifecycle 30;
