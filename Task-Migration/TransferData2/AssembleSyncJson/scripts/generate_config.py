#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AssembleSyncJson - 整合型数据同步任务配置生成脚本

将 MysqlReader、HdfsWriter、Parser、ParseSqlText、ParseScriptBase64 的功能整合，
直接从 Excel 配置文件生成完整的 DTStack 数据同步任务 JSON 配置。

重构说明：
- parser 配置构建逻辑重构
- 从 task_info 中源表类型和目标表类型判断 sourceMap 和 targetMap
- 根据表类型从 dataSource_info 中读取对应数据源配置进行填充
- 字段映射通过 task_info 解析，支持分区字段处理
- keymap 根据"是否映射"字段判断是否加入映射
- 支持从 taskSchedule_info 读取调度时间和调度类型，生成对应的 scheduleConf
"""

import zipfile
import xml.etree.ElementTree as ET
import json
import base64
import os
import random
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# 输入文件路径 — 统一从 TransferData2/输入文件/ 目录读取
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(SKILL_DIR, '..', '输入文件')
DATA_SOURCE_FILE = os.path.join(INPUT_DIR, 'dataSource_info.xlsx')
TASK_INFO_FILE = os.path.join(INPUT_DIR, 'task_info.xlsx')
TASK_SCHEDULE_FILE = os.path.join(INPUT_DIR, 'taskSchedule_info.xlsx')
PUBLIC_INFO_FILE = os.path.join(INPUT_DIR, 'public_info.xlsx')

# 参考文件路径 — 统一从 TransferData2/AssembleSyncJson/references/ 目录读取
REFERENCES_DIR = os.path.join(SKILL_DIR, 'references')
SCHEDULE_TEMPLATE_FILE = os.path.join(REFERENCES_DIR, 'schedule_info.json')
TASK_TYPE_FILE = os.path.join(REFERENCES_DIR, 'task_type.xlsx')

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resoult')

# 默认配置
DEFAULT_CONFIG = {
    'nodePid': 33357,
    'projectId': 695,
    'tenantId': 10719,
    'projectAlias': 'zy_test',
    'partition_value': '${bdp.system.bizdate}',
    'writeMode': 'overwrite',
}


class ExcelReader:
    """Excel 文件读取器（无需外部依赖）"""
    
    @staticmethod
    def get_sheet_names(filepath: str) -> List[str]:
        """获取 xlsx 文件中的所有 sheet 名称"""
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            wb_xml = zip_ref.read('xl/workbook.xml')
            root = ET.fromstring(wb_xml)
            
            ns = ''
            for elem in root.iter():
                if '}' in elem.tag:
                    ns = elem.tag.split('}')[0] + '}'
                    break
            
            sheets = []
            for sheet in root.iter(f'{ns}sheet'):
                name = sheet.get('name')
                if name:
                    sheets.append(name)
            return sheets
    
    @staticmethod
    def read_sheet_data(filepath: str, sheet_name: str) -> List[List[str]]:
        """读取指定 sheet 的数据"""
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            wb_xml = zip_ref.read('xl/workbook.xml')
            root = ET.fromstring(wb_xml)
            
            ns = ''
            for elem in root.iter():
                if '}' in elem.tag:
                    ns = elem.tag.split('}')[0] + '}'
                    break
            
            sheet_map = {}
            for sheet in root.iter(f'{ns}sheet'):
                name = sheet.get('name')
                rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                if name and rid:
                    sheet_map[name] = f'xl/worksheets/{rid.replace("rId", "sheet")}.xml'
            
            if sheet_name not in sheet_map:
                return []
            
            sheet_file = sheet_map[sheet_name]
            sheet_xml = zip_ref.read(sheet_file)
            root = ET.fromstring(sheet_xml)
            
            ns = ''
            for elem in root.iter():
                if '}' in elem.tag:
                    ns = elem.tag.split('}')[0] + '}'
                    break
            
            strings = {}
            try:
                st_xml = zip_ref.read('xl/sharedStrings.xml')
                st_root = ET.fromstring(st_xml)
                for i, si in enumerate(st_root.iter(f'{ns}si')):
                    text = ''
                    for t in si.iter(f'{ns}t'):
                        if t.text:
                            text += t.text
                    strings[i] = text
            except:
                pass
            
            rows = []
            for row in root.iter(f'{ns}row'):
                row_data = []
                cells = sorted(row.findall(f'{ns}c'), 
                              key=lambda c: int(c.get('r')[1:]) if c.get('r') and c.get('r')[1:].isdigit() else 0)
                for cell in cells:
                    cell_type = cell.get('t')
                    value_elem = cell.find(f'{ns}v')
                    value = value_elem.text if value_elem is not None else ''
                    
                    if cell_type == 's':
                        value = strings.get(int(value), value) if value else ''
                    
                    row_data.append(value if value else '')
                if row_data:
                    rows.append(row_data)
            
            return rows
    
    @staticmethod
    def read_to_dict(filepath: str, sheet_name: str) -> Dict[str, str]:
        """将 sheet 读取为键值对字典（第一列是 key，第二列是 value）"""
        data = ExcelReader.read_sheet_data(filepath, sheet_name)
        if not data:
            return {}
        return {row[0]: row[1] if len(row) > 1 else '' for row in data}


class PublicInfoConfig:
    """公共信息配置——从 public_info.xlsx 读取全局参数，动态注入 JSON"""
    
    def __init__(self):
        self._data: Dict[str, str] = {}
    
    def load_from_excel(self, filepath: str):
        """从 public_info.xlsx 读取 key-value 对（第一列 key，第二列 value）"""
        if not os.path.exists(filepath):
            print(f"  Warning: 公共信息文件不存在：{filepath}")
            return
        
        sheet_names = ExcelReader.get_sheet_names(filepath)
        for sheet_name in sheet_names:
            data = ExcelReader.read_sheet_data(filepath, sheet_name)
            for row in data:
                if len(row) >= 2 and row[0]:
                    self._data[row[0]] = row[1]
        
        print(f"  加载公共信息：{len(self._data)} 项 — {list(self._data.keys())}")
    
    def get(self, key: str, default: Any = None) -> str:
        """获取指定 key 的值"""
        return self._data.get(key, default)
    
    def to_dict(self) -> Dict[str, str]:
        """返回所有 key-value 的字典"""
        return dict(self._data)


class DataSourceConfig:
    """数据源配置管理"""
    
    def __init__(self):
        self.sources: Dict[str, Dict[str, Any]] = {}
    
    def load_from_excel(self, filepath: str):
        """从 dataSource_info.xlsx 加载数据源配置"""
        sheet_names = ExcelReader.get_sheet_names(filepath)
        
        for sheet_name in sheet_names:
            config = ExcelReader.read_to_dict(filepath, sheet_name)
            if config:
                source_type = config.get('数据源类型', '').lower()
                self.sources[sheet_name] = {
                    'sheet_name': sheet_name,
                    'name': config.get('dataSourceName', sheet_name),
                    'type': source_type,
                    'dataSourceType': int(config.get('dataSourceType', 0)),
                    'sourceIds': int(config.get('sourceIds', 0)),
                    'dtCenterSourceId': int(config.get('dtCenterSourceId', 0)),
                    'jdbc': config.get('jdbc', ''),
                    'username': config.get('username', ''),
                    'password': config.get('password', ''),
                    'path': config.get('path', ''),
                    'partition': config.get('partition', ''),
                    'hadoopConfig': config.get('hadoopConfig', ''),
                    'raw': config
                }
    
    def get_source_by_type(self, source_type: str) -> Optional[Dict[str, Any]]:
        """根据数据源类型获取配置（mysql/hdfs）"""
        for name, config in self.sources.items():
            if config['type'] == source_type.lower():
                return config
        return None
    
    def get_source_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据数据源名称获取配置"""
        for sheet_name, config in self.sources.items():
            if config['name'] == name or sheet_name == name:
                return config
        return None


class TaskInfo:
    """任务信息管理"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.sql_tasks: Dict[str, str] = {}  # Store SQL content for non-data-sync tasks
    
    def load_from_excel(self, filepath: str):
        """从 task_info.xlsx 加载任务信息"""
        sheet_names = ExcelReader.get_sheet_names(filepath)
        
        for sheet_name in sheet_names:
            data = ExcelReader.read_sheet_data(filepath, sheet_name)
            if not data:
                continue
            
            # Check if this is a SQL task sheet (has sqlText column or doesn't have standard columns)
            headers = data[0] if data else []
            
            # If first row looks like SQL content (starts with -- or SELECT), treat as SQL task
            first_cell = data[0][0] if data and data[0] else ''
            if first_cell.startswith('--') or first_cell.upper().startswith('SELECT') or first_cell.upper().startswith('WITH') or first_cell.upper().startswith('INSERT') or first_cell.upper().startswith('UPDATE') or first_cell.upper().startswith('DELETE') or first_cell.upper().startswith('CREATE'):
                # This is a SQL task sheet, store the SQL content
                sql_content = '\n'.join([row[0] if row else '' for row in data])
                self.sql_tasks[sheet_name] = sql_content
                print(f"  [SQL Task] {sheet_name}: {len(sql_content)} chars")
                continue
            
            # Standard data sync task sheet
            # 检测新旧格式：新格式有 "源名称" 和 "目标名称" 列（11列），旧格式为9列
            is_new_format = ('源名称' in headers) if headers else False
            rows = data[1:] if len(data) > 1 else []
            
            fields = []
            partition_field = None
            source_table = None
            source_name = None
            source_type = None
            target_table = None
            target_name = None
            target_type = None
            
            for row in rows:
                if row[0] == '分区字段':
                    if is_new_format:
                        # 新格式分区行: ['分区字段', 'zy_test_HADOOP', 'hdfs', 'students', 'pt', 'string']
                        # col 1: 目标数据源名称, col 2: 类型, col 3: 表名, col 4: 分区字段名, col 5: 分区字段类型
                        partition_field = {
                            'name': row[4] if len(row) > 4 else 'pt',
                            'type': row[5] if len(row) > 5 else 'string',
                            'source_table': row[3] if len(row) > 3 else '',
                            'target_table': row[3] if len(row) > 3 else ''
                        }
                        if not target_name and len(row) > 1 and row[1] != '':
                            target_name = row[1]
                        if not target_type and len(row) > 2:
                            target_type = row[2]
                    else:
                        # 旧格式分区行: ['分区字段', 'students_zwq', 'hdfs', 'pt', 'string']
                        # col 1: 表名, col 2: 类型, col 3: 分区字段名, col 4: 分区字段类型
                        partition_field = {
                            'name': row[3] if len(row) > 3 else 'pt',
                            'type': row[4] if len(row) > 4 else 'string',
                            'source_table': row[1] if len(row) > 1 else '',
                            'target_table': row[1] if len(row) > 1 else ''
                        }
                        if not target_type and len(row) > 2:
                            target_type = row[2]
                    continue
                
                if is_new_format:
                    # 新格式: 源名称(0), 源表类型(1), 源表表名(2), 源表字段(3), 源表字段类型(4), 是否映射(5),
                    #         目标名称(6), 目标表类型(7), 目标表表名(8), 目标表字段(9), 目标表字段类型(10)
                    field = {
                        'source_name': row[0] if len(row) > 0 else '',
                        'source_type': row[1] if len(row) > 1 else '',
                        'source_table': row[2] if len(row) > 2 else '',
                        'source_field': row[3] if len(row) > 3 else None,
                        'source_field_type': row[4] if len(row) > 4 else '',
                        'is_mapped': row[5] if len(row) > 5 else '是',
                        'target_name': row[6] if len(row) > 6 else '',
                        'target_type': row[7] if len(row) > 7 else '',
                        'target_table': row[8] if len(row) > 8 else '',
                        'target_field': row[9] if len(row) > 9 else None,
                        'target_field_type': row[10] if len(row) > 10 else ''
                    }
                else:
                    # 旧格式: 源表表名(0), 源表类型(1), 源表字段(2), 源表字段类型(3), 是否映射(4),
                    #         目标表表名(5), 目标表类型(6), 目标表字段(7), 目标表字段类型(8)
                    field = {
                        'source_name': '',
                        'source_type': row[1] if len(row) > 1 else '',
                        'source_table': row[0] if len(row) > 0 else '',
                        'source_field': row[2] if len(row) > 2 else None,
                        'source_field_type': row[3] if len(row) > 3 else '',
                        'is_mapped': row[4] if len(row) > 4 else '是',
                        'target_name': '',
                        'target_type': row[6] if len(row) > 6 else '',
                        'target_table': row[5] if len(row) > 5 else '',
                        'target_field': row[7] if len(row) > 7 else None,
                        'target_field_type': row[8] if len(row) > 8 else ''
                    }
                fields.append(field)
                
                if not source_table and field['source_table']:
                    source_table = field['source_table']
                    source_type = field['source_type']
                    source_name = field.get('source_name', '')
                if not target_table and field['target_table']:
                    target_table = field['target_table']
                    target_type = field['target_type']
                    target_name = field.get('target_name', '')
            
            self.tasks[sheet_name] = {
                'fields': fields,
                'partition': partition_field,
                'source_table': source_table,
                'source_type': source_type,
                'source_name': source_name or '',
                'target_table': target_table,
                'target_type': target_type,
                'target_name': target_name or ''
            }
    
    def get_sql_content(self, task_name: str) -> str:
        """获取 SQL 任务的 SQL 内容"""
        return self.sql_tasks.get(task_name, '')


class TaskScheduleConfig:
    """任务调度配置管理"""
    
    def __init__(self):
        self.schedules: Dict[str, Dict[str, str]] = {}
        self.schedule_templates: Dict[str, Dict[str, Any]] = {}
    
    def load_schedule_templates(self, filepath: str):
        """加载调度类型模板"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                self.schedule_templates = json.load(f)
            print(f"  加载调度模板：{len(self.schedule_templates)} 种类型")
        else:
            print(f"  Warning: 调度模板文件不存在：{filepath}")
    
    def load_from_excel(self, filepath: str):
        """从 taskSchedule_info.xlsx 加载调度配置"""
        sheet_names = ExcelReader.get_sheet_names(filepath)
        
        for sheet_name in sheet_names:
            data = ExcelReader.read_sheet_data(filepath, sheet_name)
            if not data or len(data) < 2:
                continue
            
            for row in data[1:]:
                if len(row) >= 1:
                    task_name = row[0]
                    task_type = row[1] if len(row) > 1 else '数据同步'
                    dependency = row[2] if len(row) > 2 else '无'
                    schedule_time = row[3] if len(row) > 3 else '00:00'
                    schedule_type = row[4] if len(row) > 4 else '天'
                    
                    self.schedules[task_name] = {
                        'task_type': task_type,
                        'dependency': dependency,
                        'schedule_time': schedule_time,
                        'schedule_type': schedule_type
                    }
    
    def build_schedule_conf(self, task_name: str) -> Dict[str, Any]:
        """
        根据调度类型构建 scheduleConf
        
        Args:
            task_name: 任务名称
        
        Returns:
            scheduleConf 字典
        """
        schedule_info = self.schedules.get(task_name, {})
        schedule_type = schedule_info.get('schedule_type', '天')
        schedule_time = schedule_info.get('schedule_time', '00:00')
        
        # 获取对应调度类型的模板
        template = self.schedule_templates.get(schedule_type, self.schedule_templates.get('天', {}))
        
        # 根据调度类型填充具体值
        if schedule_type == '天':
            # 天调度：调度时间拆分为 hour 和 min
            hour, minute = self._parse_time(schedule_time)
            schedule_conf = template.copy()
            schedule_conf['hour'] = hour
            schedule_conf['min'] = minute
            schedule_conf['periodType'] = '2'
        
        elif schedule_type == '周':
            # 周调度：调度时间对应 weekDay，默认 00:00
            hour, minute = self._parse_time(schedule_time)
            schedule_conf = template.copy()
            schedule_conf['weekDay'] = schedule_time if schedule_time.isdigit() else '1'
            schedule_conf['hour'] = str(hour)
            schedule_conf['min'] = str(minute)
            schedule_conf['periodType'] = '3'
        
        elif schedule_type == '月':
            # 月调度：调度时间对应 day，默认 00:00
            hour, minute = self._parse_time(schedule_time)
            schedule_conf = template.copy()
            schedule_conf['day'] = schedule_time if schedule_time.isdigit() else '5'
            schedule_conf['hour'] = str(hour)
            schedule_conf['min'] = str(minute)
            schedule_conf['periodType'] = '4'
        
        elif schedule_type == '小时':
            # 小时调度：调度时间对应 gapHour
            schedule_conf = template.copy()
            gap_hour = schedule_time if schedule_time.isdigit() else '1'
            # 如果调度时间包含范围（如 "0-23"），则解析
            if '-' in schedule_time:
                parts = schedule_time.split('-')
                schedule_conf['beginHour'] = parts[0]
                schedule_conf['endHour'] = parts[1] if len(parts) > 1 else '23'
            schedule_conf['gapHour'] = gap_hour
            schedule_conf['periodType'] = '1'
        
        elif schedule_type == '分钟':
            # 分钟调度：调度时间对应 gapMin
            schedule_conf = template.copy()
            gap_min = schedule_time if schedule_time.isdigit() else '15'
            # 如果调度时间包含范围
            if '-' in schedule_time:
                parts = schedule_time.split('-')
                schedule_conf['beginHour'] = parts[0]
                schedule_conf['endHour'] = parts[1] if len(parts) > 1 else '23'
            schedule_conf['gapMin'] = gap_min
            schedule_conf['periodType'] = '0'
        
        elif schedule_type == 'corn 表达式' or schedule_type == 'cron':
            # cron 表达式调度
            schedule_conf = template.copy()
            schedule_conf['cron'] = schedule_time
            schedule_conf['periodType'] = '5'
        
        else:
            # 默认使用天调度模板
            hour, minute = self._parse_time(schedule_time)
            schedule_conf = self.schedule_templates.get('天', {}).copy()
            schedule_conf['hour'] = hour
            schedule_conf['min'] = minute
            schedule_conf['periodType'] = '2'
        
        return schedule_conf
    
    def _parse_time(self, time_str: str) -> Tuple[int, int]:
        """
        解析时间字符串为 hour 和 minute
        
        Args:
            time_str: 时间字符串，如 "00:00", "01:30"
        
        Returns:
            (hour, minute) 元组
        """
        if ':' in time_str:
            parts = time_str.split(':')
            try:
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            except:
                hour, minute = 0, 0
        else:
            try:
                hour = int(time_str)
                minute = 0
            except:
                hour, minute = 0, 0
        
        return hour, minute


class AssembleSyncJson:
    """AssembleSyncJson 主类"""
    
    def __init__(self):
        self.data_source_config = DataSourceConfig()
        self.task_info = TaskInfo()
        self.task_schedule = TaskScheduleConfig()
        self.public_info = PublicInfoConfig()
        # 合并：默认配置为基础，public_info.xlsx 中的同名参数优先覆盖
        self.config = DEFAULT_CONFIG.copy()
        self._task_type_mapping: Dict[str, str] = {}  # description -> task type ID
    
    def load_task_type_mapping(self):
        """
        从 references/task_type.xlsx 读取任务类型映射
        返回: {描述: 任务类型ID} 字典
        """
        if not os.path.exists(TASK_TYPE_FILE):
            print(f"  Warning: 找不到任务类型文件 {TASK_TYPE_FILE}")
            return
        
        sheet_names = ExcelReader.get_sheet_names(TASK_TYPE_FILE)
        if not sheet_names:
            return
        
        data = ExcelReader.read_sheet_data(TASK_TYPE_FILE, sheet_names[0])
        if not data or len(data) < 2:
            return
        
        # 列：任务类型 ID | 描述
        for row in data[1:]:
            if len(row) >= 2:
                type_id = row[0].strip()
                description = row[1].strip()
                if type_id and description:
                    self._task_type_mapping[description] = type_id
        
        # 添加中文别名
        aliases = {'虚节点': 'VIRTUAL'}
        for cn, en in aliases.items():
            if en in self._task_type_mapping and cn not in self._task_type_mapping:
                self._task_type_mapping[cn] = self._task_type_mapping[en]
        
        print(f"  加载任务类型映射：{len(self._task_type_mapping)} 条")
    
    def get_task_type_id(self, task_type_desc: str) -> str:
        """
        根据任务类型描述获取任务类型 ID
        
        Args:
            task_type_desc: 任务类型描述（如 '数据同步', '虚节点', 'SparkSql'）
        
        Returns:
            任务类型 ID（如 '2', '-1', '0'）
        """
        if self._task_type_mapping:
            return self._task_type_mapping.get(task_type_desc, '2')
        # 回退到硬编码
        if task_type_desc in ['虚节点']:
            return '-1'
        elif task_type_desc in ['数据同步']:
            return '2'
        return '0'
    
    def load_all(self):
        """加载所有输入文件"""
        print(f"加载公共信息：{PUBLIC_INFO_FILE}")
        self.public_info.load_from_excel(PUBLIC_INFO_FILE)
        self.config.update(self.public_info.to_dict())  # public_info 的参数覆盖默认值
        
        print(f"加载数据源配置：{DATA_SOURCE_FILE}")
        self.data_source_config.load_from_excel(DATA_SOURCE_FILE)
        print(f"  找到 {len(self.data_source_config.sources)} 个数据源")
        
        print(f"加载任务信息：{TASK_INFO_FILE}")
        self.task_info.load_from_excel(TASK_INFO_FILE)
        print(f"  找到 {len(self.task_info.tasks)} 个任务")
        
        print(f"加载调度配置：{TASK_SCHEDULE_FILE}")
        self.task_schedule.load_from_excel(TASK_SCHEDULE_FILE)
        print(f"  找到 {len(self.task_schedule.schedules)} 条调度配置")
        
        print(f"加载调度模板：{SCHEDULE_TEMPLATE_FILE}")
        self.task_schedule.load_schedule_templates(SCHEDULE_TEMPLATE_FILE)
        
        print(f"加载任务类型映射：{TASK_TYPE_FILE}")
        self.load_task_type_mapping()
    
    def map_mysql_type_to_hive(self, mysql_type: str) -> str:
        """MySQL 类型映射到 Hive 类型"""
        mysql_type = mysql_type.upper().strip()
        
        type_mapping = {
            'INT': 'int',
            'INTEGER': 'int',
            'BIGINT': 'bigint',
            'SMALLINT': 'int',
            'TINYINT': 'int',
            'VARCHAR': 'string',
            'CHAR': 'string',
            'TEXT': 'string',
            'LONGTEXT': 'string',
            'MEDIUMTEXT': 'string',
            'DATETIME': 'string',
            'TIMESTAMP': 'string',
            'DATE': 'string',
            'TIME': 'string',
            'DECIMAL': 'decimal',
            'NUMERIC': 'decimal',
            'FLOAT': 'float',
            'DOUBLE': 'double',
            'BOOLEAN': 'boolean',
            'BOOL': 'boolean',
        }
        
        base_type = mysql_type.split('(')[0]
        return type_mapping.get(base_type, 'string')
    
    def _extract_schema(self, jdbc_url: str) -> str:
        """从 JDBC URL 中提取 schema/database 名称"""
        try:
            if '?' in jdbc_url:
                jdbc_url = jdbc_url.split('?')[0]
            parts = jdbc_url.rstrip('/').split('/')
            return parts[-1] if parts else 'default'
        except:
            return 'default'
    
    def _build_source_map(self, task_name: str, task_data: Dict[str, Any], 
                          source_config: Dict[str, Any]) -> Dict[str, Any]:
        """构建 sourceMap 配置"""
        fields = task_data.get('fields', [])
        source_table = task_data.get('source_table', 'unknown')
        source_type_str = task_data.get('source_type', 'mysql')
        
        source_type_str = source_config.get('type', task_data.get('source_type', 'mysql'))
        
        source_id = int(source_config['sourceIds'])
        type_type = int(source_config['dataSourceType'])
        
        source_columns = []
        for field in fields:
            source_field = field.get('source_field', '')
            source_field_type = field.get('source_field_type', '')
            
            if not source_field or source_field.lower() == 'null':
                continue
            
            source_col = {
                'part': False,
                'comment': '',
                'isPart': False,
                'type': source_field_type.upper() if source_field_type else 'VARCHAR',
                'key': source_field
            }
            
            if 'VARCHAR' in source_field_type.upper():
                try:
                    precision = int(source_field_type.split('(')[1].split(')')[0])
                    source_col['precision'] = precision
                except:
                    source_col['precision'] = 100
            
            source_columns.append(source_col)
        
        source_type_config = {
            'type': type_type,
            'table': [source_table]
        }
        
        partition_field = task_data.get('partition')
        if partition_field and source_type_str.lower() in ['hdfs', 'hive']:
            source_type_config['partition'] = f"{partition_field['name']}={self.config['partition_value']}"
            source_type_config['writeMode'] = self.config['writeMode']
        
        source_map = {
            'sourceId': source_id,
            'schema': self._extract_schema(source_config['jdbc']),
            'sourceList': [{
                'sourceId': source_id,
                'schema': self._extract_schema(source_config['jdbc']),
                'tables': [source_table],
                'name': source_config['name'],
                'type': type_type,
                'key': 'main'
            }],
            'name': source_config['name'],
            'column': source_columns,
            'type': source_type_config,
            'extralConfig': ''
        }
        
        return source_map
    
    def _build_target_map(self, task_name: str, task_data: Dict[str, Any],
                          target_config: Dict[str, Any]) -> Dict[str, Any]:
        """构建 targetMap 配置"""
        fields = task_data.get('fields', [])
        target_table = task_data.get('target_table', 'unknown')
        target_type_str = target_config.get('type', task_data.get('target_type', 'hdfs'))
        partition_field = task_data.get('partition')
        
        target_id = int(target_config['sourceIds'])
        target_type = int(target_config['dataSourceType'])
        
        target_columns = []
        for field in fields:
            target_field = field.get('target_field', '')
            target_field_type = field.get('target_field_type', '')
            
            if not target_field or target_field.lower() == 'null':
                continue
            
            target_col = {
                'part': False,
                'comment': '',
                'isPart': False,
                'type': target_field_type.lower() if target_field_type else 'string',
                'key': target_field
            }
            target_columns.append(target_col)
        
        if partition_field:
            partition_col = {
                'part': True,
                'comment': '',
                'isPart': True,
                'type': partition_field['type'],
                'key': partition_field['name']
            }
            target_columns.append(partition_col)
        
        target_type_config = {
            'type': target_type,
            'table': target_table
        }
        
        if partition_field and target_type_str.lower() in ['hdfs', 'hive']:
            target_type_config['partition'] = f"{partition_field['name']}={self.config['partition_value']}"
            target_type_config['writeMode'] = self.config['writeMode']
        
        target_map = {
            'sourceId': target_id,
            'name': target_config['name'],
            'column': target_columns,
            'schema': self._extract_schema(target_config['jdbc']),
            'type': target_type_config,
            'extralConfig': ''
        }
        
        return target_map
    
    def _build_keymap(self, task_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """构建 keymap 配置"""
        fields = task_data.get('fields', [])
        
        keymap_source = []
        keymap_target = []
        
        for field in fields:
            if field.get('is_mapped') != '是':
                continue
            
            source_field = field.get('source_field')
            target_field = field.get('target_field')
            
            if not source_field or not target_field:
                continue
            
            source_field_type = field.get('source_field_type', '')
            target_field_type = field.get('target_field_type', '')
            
            source_col = {
                'comment': '',
                'isPart': False,
                'type': source_field_type.upper() if source_field_type else 'VARCHAR',
                'key': source_field
            }
            
            if 'VARCHAR' in (source_field_type or '').upper():
                try:
                    precision = int(source_field_type.split('(')[1].split(')')[0])
                    source_col['precision'] = precision
                except:
                    source_col['precision'] = 100
            
            keymap_source.append(source_col)
            
            target_col = {
                'comment': '',
                'isPart': False,
                'type': target_field_type.lower() if target_field_type else 'string',
                'key': target_field
            }
            keymap_target.append(target_col)
        
        return {
            'source': keymap_source,
            'target': keymap_target
        }
    
    def _build_parser_config(self, task_name: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建 parser 配置"""
        source_name = task_data.get('source_name', '')
        target_name = task_data.get('target_name', '')
        source_type_str = task_data.get('source_type', 'mysql').lower()
        target_type_str = task_data.get('target_type', 'hdfs').lower()
        
        # 优先使用源名称/目标名称匹配 dataSource_info 的 sheet 页名称（dataSourceName）
        if source_name:
            source_config = self.data_source_config.get_source_by_name(source_name)
        else:
            source_config = self.data_source_config.get_source_by_type(source_type_str)
        
        if target_name:
            target_config = self.data_source_config.get_source_by_name(target_name)
        else:
            target_config = self.data_source_config.get_source_by_type(target_type_str)
        
        if not source_config:
            raise ValueError(f"任务 {task_name}: 找不到源数据源配置（名称：{source_name}，类型：{source_type_str}）")
        if not target_config:
            raise ValueError(f"任务 {task_name}: 找不到目标数据源配置（名称：{target_name}，类型：{target_type_str}）")
        
        source_map = self._build_source_map(task_name, task_data, source_config)
        target_map = self._build_target_map(task_name, task_data, target_config)
        keymap = self._build_keymap(task_data)
        
        parser_config = {
            'targetMap': target_map,
            'keymap': keymap,
            'sourceMap': source_map,
            'setting': {
                'readerChannel': 1,
                'init': False,
                'writerChannel': 1,
                'record': 100,
                'restoreColumnIndex': 0,
                'speed': '-1',
                'isSaveDirty': 0
            }
        }
        
        return parser_config
    
    def _build_job_config(self, task_name: str, task_data: Dict[str, Any],
                         parser_config: Dict[str, Any]) -> Dict[str, Any]:
        """构建 job 配置"""
        source_name = task_data.get('source_name', '')
        target_name = task_data.get('target_name', '')
        source_type_str = task_data.get('source_type', 'mysql').lower()
        target_type_str = task_data.get('target_type', 'hdfs').lower()
        
        # 优先使用源名称/目标名称匹配 dataSource_info 的 sheet 页名称
        if source_name:
            source_config = self.data_source_config.get_source_by_name(source_name)
        else:
            source_config = self.data_source_config.get_source_by_type(source_type_str)
        
        if target_name:
            target_config = self.data_source_config.get_source_by_name(target_name)
        else:
            target_config = self.data_source_config.get_source_by_type(target_type_str)
        
        source_table = task_data.get('source_table', 'unknown')
        target_table = task_data.get('target_table', 'unknown')
        partition_field = task_data.get('partition')
        partition_value = self.config['partition_value']
        
        keymap = parser_config.get('keymap', {})
        keymap_source = keymap.get('source', [])
        keymap_target = keymap.get('target', [])
        
        reader_columns = []
        for col in keymap_source:
            reader_col = {
                'customConverterType': col['type'].upper().split('(')[0],
                'name': col['key'],
                'isPart': False,
                'type': col['type'],
                'key': col['key']
            }
            reader_columns.append(reader_col)
        
        writer_columns = []
        for idx, col in enumerate(keymap_target):
            writer_col = {
                'customConverterType': col['type'].lower(),
                'name': col['key'],
                'index': idx,
                'isPart': False,
                'type': col['type'],
                'key': col['key']
            }
            writer_columns.append(writer_col)
        
        job_config = {
            'job': {
                'content': [{
                    'reader': {
                        'parameter': {
                            'password': source_config.get('password', ''),
                            'customSql': '',
                            'startLocation': '',
                            'dtCenterSourceId': source_config['dtCenterSourceId'],
                            'increColumn': '',
                            'column': reader_columns,
                            'dtCenterSourceIds': [int(source_config['dataSourceType'])],
                            'connection': [{
                                'schema': self._extract_schema(source_config['jdbc']),
                                'sourceId': int(source_config['sourceIds']),
                                'password': source_config.get('password', ''),
                                'jdbcUrl': [source_config['jdbc']],
                                'type': int(source_config['dataSourceType']),
                                'table': [source_table],
                                'username': source_config.get('username', '')
                            }],
                            'sourceIds': [int(source_config['sourceIds'])],
                            'username': source_config.get('username', ''),
                            'dataSourceInfo': {
                                'dataSourceName': source_config['name'],
                                'dataSourceType': int(source_config['dataSourceType'])
                            }
                        },
                        'name': 'mysqlreader'
                    },
                    'writer': {
                        'parameter': {
                            'schema': self._extract_schema(target_config['jdbc']),
                            'fileName': partition_value,
                            'dtCenterSourceId': target_config['dtCenterSourceId'],
                            'column': writer_columns,
                            'dtCenterSourceIds': [int(target_config['dataSourceType'])],
                            'writeMode': self.config['writeMode'],
                            'encoding': 'utf-8',
                            'fullColumnName': [col['key'] for col in keymap_target],
                            'dataSourceInfo': {
                                'dataSourceName': target_config['name'],
                                'dataSourceType': int(target_config['dataSourceType'])
                            },
                            'path': target_config.get('path', f'/user/hive/warehouse/{self._extract_schema(target_config["jdbc"])}.db/{target_table}'),
                            'password': target_config.get('password', ''),
                            'partition': partition_value,
                            'hadoopConfig': self._parse_hadoop_config(target_config.get('hadoopConfig', '')),
                            'defaultFS': 'hdfs://ns1',
                            'connection': [{
                                'jdbcUrl': target_config['jdbc'],
                                'table': [target_table]
                            }],
                            'table': target_table,
                            'fileType': 'orc',
                            'sourceIds': [int(target_config['sourceIds'])],
                            'username': target_config.get('username', ''),
                            'fullColumnType': [col['type'] for col in keymap_target]
                        },
                        'name': 'hdfswriter'
                    }
                }],
                'setting': {
                    'restore': {
                        'maxRowNumForCheckpoint': 0,
                        'isRestore': False,
                        'restoreColumnName': '',
                        'restoreColumnIndex': 0
                    },
                    'errorLimit': {
                        'record': 100
                    },
                    'speed': {
                        'readerChannel': 1,
                        'writerChannel': 1,
                        'bytes': 0,
                        'channel': 1
                    }
                }
            }
        }
        
        return job_config
    
    def _parse_hadoop_config(self, hadoop_config_str: str) -> Dict[str, str]:
        """解析 Hadoop 配置字符串为字典"""
        if not hadoop_config_str:
            return {
                'dfs.replication': '3',
                'yarn.resourcemanager.ha.enabled': 'true',
                'hive.exec.dynamic.partition': 'true',
                'hive.exec.dynamic.partition.mode': 'nonstrict'
            }
        
        try:
            return json.loads(hadoop_config_str)
        except:
            return {
                'dfs.replication': '3',
                'yarn.resourcemanager.ha.enabled': 'true',
                'hive.exec.dynamic.partition': 'true',
                'hive.exec.dynamic.partition.mode': 'nonstrict'
            }
    
    def _build_task_task_info(self, task_name: str, task_type: str = '数据同步') -> List[Dict[str, Any]]:
        """
        构建 taskTaskInfo 配置
        
        Args:
            task_name: 任务名称
            task_type: 任务类型，用于判断是否支持多依赖
        """
        task_task_info = []
        
        schedule_info = self.task_schedule.schedules.get(task_name, {})
        dependency = schedule_info.get('dependency', '无') if isinstance(schedule_info, dict) else schedule_info
        
        if not dependency or dependency == '无':
            task_info = {
                'customOffset': 0,
                'forwardDirection': 1,
                'isCurrentProject': True,
                'projectAlias': self.config['projectAlias'],
                'taskName': 'root',
                'taskType': int(self.get_task_type_id('虚节点')),
                'upDownRelyType': 0
            }
            task_task_info.append(task_info)
        else:
            # 支持多个依赖，按逗号分隔
            dependencies = [d.strip() for d in dependency.split(',')]
            
            for dep_task_name in dependencies:
                if not dep_task_name or dep_task_name == '无':
                    continue
                
                # 从 taskSchedule_info.xlsx 获取依赖任务的任务类型描述
                dep_schedule = self.task_schedule.schedules.get(dep_task_name, {})
                dep_task_type_desc = dep_schedule.get('task_type', '数据同步')
                
                # 从 task_type.xlsx 查询对应的任务类型 ID
                dep_task_type_id = int(self.get_task_type_id(dep_task_type_desc))
                
                task_info = {
                    'customOffset': 0,
                    'forwardDirection': 1,
                    'isCurrentProject': True,
                    'projectAlias': self.config['projectAlias'],
                    'taskName': dep_task_name,
                    'taskType': dep_task_type_id,
                    'upDownRelyType': 0
                }
                task_task_info.append(task_info)
        
        return task_task_info
    
    def _build_schedule_conf(self, task_name: str) -> Tuple[str, int]:
        """
        构建 scheduleConf JSON 字符串
        
        Args:
            task_name: 任务名称
        
        Returns:
            (scheduleConf JSON 字符串, periodType int 值)
        """
        schedule_conf = self.task_schedule.build_schedule_conf(task_name)
        period_type = int(schedule_conf.get('periodType', 2))
        return json.dumps(schedule_conf, ensure_ascii=False, separators=(',', ':')), period_type
    
    def build_virtual_node_config(self, task_name: str, schedule_info: Dict[str, str]) -> Dict[str, Any]:
        """构建虚节点任务配置"""
        schedule_conf_str, period_type = self._build_schedule_conf(task_name)
        
        virtual_node_config = {
            'taskInfo': {
                'appType': 1,
                'computeType': 1,
                'createUserId': 1,
                'dependOnSettings': 0,
                'dtuicTenantId': 0,
                'engineType': 1,
                'exeArgs': '',
                'flowId': 0,
                'id': 0,
                'isDeleted': 0,
                'isPublishToProduce': 0,
                'jobBuildType': 1,
                'mainClass': '',
                'name': task_name,
                'nodePid': int(self.config['nodePid']),
                'ownerUserId': 1,
                'ownerUserName': 'admin@dtstack.com',
                'periodType': period_type,
                'projectId': int(self.config['projectId']),
                'projectScheduleStatus': 0,
                'scheduleConf': schedule_conf_str,
                'scheduleStatus': 1,
                'sqlText': '',
                'submitStatus': 1,
                'taskDesc': '',
                'taskGroup': 0,
                'taskId': random.randint(1000000, 9999999),
                'taskType': int(self.get_task_type_id('虚节点')),
                'taskParams': '',
                'tenantId': int(self.config['tenantId']),
                'yarnResourceName': self.config.get('yarnResourceName', 'saas')
            },
            'updateEnvParam': False
        }
        
        return virtual_node_config
    

    def build_task_config(self, task_name: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建单个任务的完整配置"""
        parser_config = self._build_parser_config(task_name, task_data)
        job_config = self._build_job_config(task_name, task_data, parser_config)
        
        sql_text_dict = {
            'parser': json.dumps(parser_config, ensure_ascii=False, separators=(',', ':')),
            'syncModel': 0,
            'createModel': 0,
            'job': json.dumps(job_config, ensure_ascii=False, separators=(',', ':'))
        }
        sql_text = json.dumps(sql_text_dict, ensure_ascii=False, separators=(',', ':'))
        sql_text_base64 = base64.b64encode(sql_text.encode('utf-8')).decode('utf-8')
        
        task_task_info = self._build_task_task_info(task_name)
        
        schedule_conf_str, period_type = self._build_schedule_conf(task_name)
        
        # taskType 动态查询：taskSchedule_info → task_type_desc → task_type.xlsx
        sync_task_type = self.task_schedule.schedules.get(task_name, {}).get('task_type', '数据同步')

        task_info = {
            'agentResourceId': 17,
            'appType': 1,
            'computeType': 1,
            'createUserId': 1,
            'dependOnSettings': 0,
            'dtuicTenantId': 0,
            'engineType': 0,
            'exeArgs': '',
            'flowId': 0,
            'id': 0,
            'isDeleted': 0,
            'isPublishToProduce': 0,
            'jobBuildType': 1,
            'mainClass': '',
            'name': task_name,
            'nodePid': int(self.config['nodePid']),
            'ownerUserId': 1,
            'ownerUserName': 'admin@dtstack.com',
            'periodType': period_type,
            'projectId': int(self.config['projectId']),
            'projectScheduleStatus': 0,
            'scheduleConf': schedule_conf_str,
            'scheduleStatus': 1,
            'sqlText': sql_text_base64,
            'submitStatus': 1,
            'taskDesc': '',
            'taskGroup': 0,
            'taskId': random.randint(1000000, 9999999),
            'taskType': int(self.get_task_type_id(sync_task_type)),
            'tenantId': int(self.config['tenantId']),
            'yarnResourceName': self.config.get('yarnResourceName', 'saas'),
            'taskParams': '''## 任务运行方式：
## per_job:单独为任务创建 flink yarn session，适用于低频率，大数据量同步
## session：多个任务共用一个 flink yarn session，适用于高频率、小数据量同步，默认 session
## flinkTaskRunMode=per_job
## per_job 模式下 jobManager 配置的内存大小，默认 1024（单位 M)
## jobmanager.memory.mb=1024
## per_job 模式下 taskManager 配置的内存大小，默认 1024（单位 M）
## taskmanager.memory.mb=1024
## per_job 模式下每个 taskManager 对应 slot 的数量
## slots=1

## checkpoint 保存时间间隔
## flink.checkpoint.interval=300000
## 任务优先级，范围:1-1000
## 
pipeline.operator-chaining = false'''
        }
        
        return {
            'taskInfo': task_info,
            'taskTaskInfo': task_task_info,
            'updateEnvParam': False
        }
    
    def generate_all(self):
        """生成所有任务的配置文件"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        generated_tasks = set()
        
        # 处理 taskSchedule_info 中的所有任务
        for task_name, schedule_info in self.task_schedule.schedules.items():
            task_type = schedule_info.get('task_type', '数据同步')
            
            if task_name in generated_tasks:
                continue
            
            print(f"\n生成任务配置：{task_name} (类型：{task_type})")
            
            try:
                if task_type == '虚节点':
                    # 虚节点配置
                    config = self.build_virtual_node_config(task_name, schedule_info)
                
                elif task_type == '数据同步':
                    # 数据同步任务配置
                    if task_name not in self.task_info.tasks:
                        print(f"  ✗ 错误：找不到任务 {task_name} 的配置信息")
                        continue
                    task_data = self.task_info.tasks[task_name]
                    config = self.build_task_config(task_name, task_data)
                
                else:
                    # SQL 类任务（SparkSql、FlinkSql 等）已转由 AssembleScriptJson 独立处理
                    print(f"  ⊘ 跳过 SQL 任务（请使用 AssembleScriptJson 技能处理）")
                    continue
                
                output_file = os.path.join(OUTPUT_DIR, f'{task_name}.json')
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                
                print(f"  ✓ 输出：{output_file}")
                generated_tasks.add(task_name)
            
            except Exception as e:
                print(f"  ✗ 错误：{e}")
                raise
        
        print(f"\n{'='*60}")
        print(f"完成！共生成 {len(generated_tasks)} 个任务配置文件")
        print(f"输出目录：{OUTPUT_DIR}")
        print(f"{'='*60}")


def main():
    """主函数"""
    print("="*60)
    print("       AssembleSyncJson - 数据同步任务配置生成")
    print("="*60)
    
    assembler = AssembleSyncJson()
    assembler.load_all()
    assembler.generate_all()


if __name__ == '__main__':
    main()
