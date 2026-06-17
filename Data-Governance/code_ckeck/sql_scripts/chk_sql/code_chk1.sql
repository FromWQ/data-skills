-- SQL 检查文件
-- 生成时间: 2026-04-09 18:33:25
-- 需求描述: 创建代码检查结果表
-- ========================================

-- DROP TABLE IF EXISTS `zhaogang_test`.`task_code_text`;
-- CREATE TABLE IF NOT EXISTS `zhaogang_test`.`task_code_text` (
--     `id`                INT             NOT NULL AUTO_INCREMENT COMMENT '主键ID',
--     `tenant_id`         INT             DEFAULT NULL COMMENT '租户ID',
--     `project_id`        INT             DEFAULT NULL COMMENT '项目ID',
--     `task_name`         VARCHAR(255)    DEFAULT NULL COMMENT '任务名称',
--     `task_type`         TINYINT         DEFAULT NULL COMMENT '任务类型',
--     `sql_text`          TEXT            DEFAULT NULL COMMENT 'SQL文本',
--     `is_deleted`        TINYINT(1)      DEFAULT 0 COMMENT '是否删除：0-否，1-是',
--     `gmt_create`        DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
--     `gmt_modified`      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
--     PRIMARY KEY (`id`),
--     KEY `idx_project_id` (`project_id`),
--     KEY `idx_task_name` (`task_name`)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务代码文本';

DROP TABLE IF EXISTS `zhaogang_test`.`code_check_result`;
CREATE TABLE IF NOT EXISTS `zhaogang_test`.`code_check_result` (
    `id`                BIGINT          NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `code_id`           BIGINT          NOT NULL COMMENT '代码ID',
    `task_name`         VARCHAR(255)    NOT NULL COMMENT '任务名称',
    `code_layer`        VARCHAR(16)     NOT NULL COMMENT '所属分层',
    `rule_id`           VARCHAR(16)     NOT NULL COMMENT '规则ID',
    `rule_name`         VARCHAR(64)     NOT NULL COMMENT '规则名称',
    `rule_severity`     VARCHAR(16)     NOT NULL COMMENT '严重程度',
    `check_status`      VARCHAR(16)     NOT NULL COMMENT '检查结果：PASS/FAIL',
    `issue_location`    VARCHAR(256)    DEFAULT NULL COMMENT '问题位置',
    `issue_desc`        TEXT            DEFAULT NULL COMMENT '问题描述',
    `suggestion`        TEXT            DEFAULT NULL COMMENT '整改建议',
    `check_time`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_code_id` (`code_id`),
    KEY `idx_rule_id` (`rule_id`),
    KEY `idx_task_name` (`task_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='代码检查结果表';
