#!/usr/bin/env python3
"""
数据库连接工具模块
提供数据库连接、查询、元数据同步等功能
"""

import json
import os
import pymysql
from datetime import datetime
from typing import List, Dict, Any, Optional


class DbConnector:
    """数据库连接工具类"""

    def __init__(self, config_path: str = None):
        """
        初始化数据库连接

        Args:
            config_path: 配置文件路径，默认为 input/db_config.json
        """
        if config_path is None:
            # 使用当前脚本所在目录的父目录作为基准路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(script_dir)
            config_path = os.path.join(base_dir, 'input', 'db_config.json')

        self.config = self._load_config(config_path)
        self.connection = None

    def _load_config(self, config_path: str) -> Dict:
        """加载数据库配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ 数据库配置加载成功：{config.get('name', '未知')}")
            return config
        except FileNotFoundError:
            print(f"❌ 配置文件不存在：{config_path}")
            raise
        except json.JSONDecodeError as e:
            print(f"❌ 配置文件解析失败：{e}")
            raise

    def connect(self) -> pymysql.Connection:
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 3306),
                user=self.config.get('user', 'root'),
                password=self.config.get('password', ''),
                database=self.config.get('database', ''),
                charset=self.config.get('charset', 'utf8mb4'),
                cursorclass=pymysql.cursors.DictCursor
            )
            print(f"✅ 数据库连接成功：{self.config.get('host')}:{self.config.get('port')}/{self.config.get('database')}")
            return self.connection
        except pymysql.Error as e:
            print(f"❌ 数据库连接失败：{e}")
            raise

    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("✅ 数据库连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

    def query_data(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        执行查询 SQL

        Args:
            sql: SQL 语句
            params: SQL 参数元组

        Returns:
            查询结果列表
        """
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                return result if result else []
        except pymysql.Error as e:
            print(f"❌ 查询执行失败：{sql[:100]}...")
            print(f"   错误信息：{e}")
            raise

    def execute_sql(self, sql: str, params: tuple = None) -> int:
        """
        执行更新 SQL（INSERT/UPDATE/DELETE）

        Args:
            sql: SQL 语句
            params: SQL 参数元组

        Returns:
            受影响的行数
        """
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                self.connection.commit()
                return affected_rows
        except pymysql.Error as e:
            print(f"❌ SQL 执行失败：{sql[:100]}...")
            print(f"   错误信息：{e}")
            self.connection.rollback()
            raise

    def get_table_list(self, table_prefixes: List[str] = None) -> List[str]:
        """
        获取数据库表列表

        Args:
            table_prefixes: 表名前缀列表，如 ['ods_', 'dwd_', 'dws_', 'ads_', 'dim_']

        Returns:
            表名列表
        """
        if table_prefixes is None:
            table_prefixes = ['ods_', 'dwd_', 'dws_', 'ads_', 'dim_']

        prefix_condition = ' OR '.join([f"table_name LIKE '{p}%'" for p in table_prefixes])
        sql = f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = '{self.config.get('database')}'
            AND ({prefix_condition})
            ORDER BY table_name
        """

        result = self.query_data(sql)
        return [row['table_name'] for row in result]

    def get_table_columns(self, table_name: str) -> List[Dict]:
        """
        获取表的字段信息

        Args:
            table_name: 表名

        Returns:
            字段信息列表
        """
        sql = f"""
            SELECT
                column_name,
                column_type,
                column_comment,
                column_key,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = '{self.config.get('database')}'
            AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """

        return self.query_data(sql)

    def get_table_count(self, table_name: str, partition_field: str = None, partition_value: str = None) -> int:
        """
        获取表记录数

        Args:
            table_name: 表名
            partition_field: 分区字段
            partition_value: 分区值

        Returns:
            记录数
        """
        if partition_field and partition_value:
            sql = f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {partition_field} = '{partition_value}'"
        else:
            sql = f"SELECT COUNT(*) as cnt FROM {table_name}"

        result = self.query_data(sql)
        return result[0]['cnt'] if result else 0

    def sync_table_metadata(self, target_table: str = 'meta_table_column') -> Dict:
        """
        同步表元数据到 meta_table_column 表

        Args:
            target_table: 目标元数据表名

        Returns:
            同步统计信息
        """
        print("\n" + "=" * 60)
        print("🔄 开始同步表元数据...")
        print("=" * 60)

        # 获取所有数仓表
        table_list = self.get_table_list()
        print(f"📊 发现 {len(table_list)} 个数仓表")

        stats = {
            'total_tables': len(table_list),
            'total_columns': 0,
            'inserted': 0,
            'updated': 0,
            'failed': 0
        }

        for table_name in table_list:
            # 识别表分层
            table_layer = self._identify_layer(table_name)

            # 获取表注释
            table_comment = self._get_table_comment(table_name)

            # 获取字段信息
            columns = self.get_table_columns(table_name)

            for col in columns:
                # 识别字段标签
                column_tag = self._identify_column_tag(col)

                # 识别是否主键
                is_pk = 1 if col.get('column_key') == 'PRI' else 0

                # 识别是否分区字段
                is_partition = 1 if col['column_name'].lower() in ['dt', 'pt', 'partition_date'] else 0

                # 构建 SQL
                sql = f"""
                    INSERT INTO {target_table}
                    (table_name, table_comment, table_layer, column_name, column_type,
                     column_comment, column_tag, is_pk, is_partition)
                    VALUES (
                        '{table_name}', '{table_comment}', '{table_layer}',
                        '{col['column_name']}', '{col['column_type']}',
                        '{col.get('column_comment') or ''}', '{column_tag}',
                        {is_pk}, {is_partition}
                    )
                    ON DUPLICATE KEY UPDATE
                        table_comment = VALUES(table_comment),
                        table_layer = VALUES(table_layer),
                        column_type = VALUES(column_type),
                        column_comment = VALUES(column_comment),
                        column_tag = VALUES(column_tag),
                        is_pk = VALUES(is_pk),
                        is_partition = VALUES(is_partition),
                        updated_at = NOW()
                """

                try:
                    result = self.execute_sql(sql)
                    if result == 1:
                        stats['inserted'] += 1
                    else:
                        stats['updated'] += result
                    stats['total_columns'] += 1
                except Exception as e:
                    print(f"   ⚠️  同步字段 {table_name}.{col['column_name']} 失败：{e}")
                    stats['failed'] += 1

        print("\n" + "=" * 60)
        print("✅ 元数据同步完成!")
        print(f"   表数量：{stats['total_tables']}")
        print(f"   字段总数：{stats['total_columns']}")
        print(f"   新增：{stats['inserted']}")
        print(f"   更新：{stats['updated']}")
        print(f"   失败：{stats['failed']}")
        print("=" * 60)

        return stats

    def _identify_layer(self, table_name: str) -> str:
        """识别表所属分层"""
        prefix = table_name.lower().split('_')[0]
        layer_map = {
            'ods': 'ODS',
            'dwd': 'DWD',
            'dws': 'DWS',
            'dim': 'DIM',
            'ads': 'ADS'
        }
        return layer_map.get(prefix, 'UNKNOWN')

    def _get_table_comment(self, table_name: str) -> str:
        """获取表注释"""
        sql = f"""
            SELECT table_comment
            FROM information_schema.tables
            WHERE table_schema = '{self.config.get('database')}'
            AND table_name = '{table_name}'
        """
        result = self.query_data(sql)
        return result[0]['table_comment'] if result and result[0]['table_comment'] else ''

    def _identify_column_tag(self, col: Dict) -> str:
        """
        识别字段标签
        """
        col_name = col['column_name'].lower()
        col_type = col['column_type'].lower()
        col_comment = (col.get('column_comment') or '').lower()

        # 维度字段关键词
        dim_keywords = ['name', 'code', 'type', 'status', 'flag', 'org', 'dept', 'region', 'date', 'time',
                        '名称', '编码', '类型', '状态', '部门', '地区', '日期', '时间']

        # 指标字段关键词
        measure_keywords = ['mny', 'amount', 'price', 'cost', 'fee', 'qty', 'count', 'rate', 'percent',
                           '金额', '价格', '成本', '费用', '数量', '比率']

        # 检查维度字段
        if any(kw in col_name or kw in col_comment for kw in dim_keywords):
            return 'DIMENSION'

        # 检查指标字段
        if any(kw in col_name or kw in col_comment for kw in measure_keywords):
            return 'MEASURE'

        # 检查数值类型（非_id 结尾）
        if any(t in col_type for t in ['decimal', 'double', 'float', 'int', 'bigint']):
            if not col_name.endswith('_id'):
                return 'MEASURE'

        return 'ATTRIBUTE'


def main():
    """主函数：同步元数据"""
    connector = DbConnector()
    try:
        connector.sync_table_metadata()
    finally:
        connector.disconnect()


if __name__ == '__main__':
    main()
