#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AssembleScriptJson - SQL 任务配置生成脚本

专门用于生成 SQL 类型任务（SparkSql、FlinkSql、ODPS SQL 等）的 DTStack 配置。
此脚本是从 AssembleSyncJson 分离出来的独立功能。

功能：
- 从 task_info.xlsx 读取 SQL 任务内容
- 从 taskSchedule_info.xlsx 读取调度配置
- 生成完整的 SQL 任务 JSON 配置
"""

import zipfile
import xml.etree.ElementTree as ET
import json
import os
import random
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# 输入文件路径 — 统一从 TransferData2/输入文件/ 目录读取
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(SKILL_DIR, '..', '输入文件')
TASK_INFO_FILE = os.path.join(INPUT_DIR, 'task_info.xlsx')
TASK_SCHEDULE_FILE = os.path.join(INPUT_DIR, 'taskSchedule_info.xlsx')
DATA_SOURCE_FILE = os.path.join(INPUT_DIR, 'dataSource_info.xlsx')
PUBLIC_INFO_FILE = os.path.join(INPUT_DIR, 'public_info.xlsx')

# 调度模板文件
# 参考文件路径
REFERENCES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'references')
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


class SqlTaskInfo:
    """SQL 任务信息管理"""
    
    def __init__(self):
        self.sql_tasks: Dict[str, str] = {}
        self.task_params: Dict[str, str] = {}  # 从 Excel 读取的自定义 taskParams
    
    def load_from_excel(self, filepath: str):
        """从 task_info.xlsx 加载 SQL 任务信息"""
        sheet_names = ExcelReader.get_sheet_names(filepath)
        
        for sheet_name in sheet_names:
            data = ExcelReader.read_sheet_data(filepath, sheet_name)
            if not data:
                continue
            
            # 判断是否为 SQL 任务 sheet 页
            first_cell = data[0][0] if data and data[0] else ''
            
            # 新格式：key-value 对（首行第一列为 'sqlText' 标记）
            if first_cell == 'sqlText':
                self._load_new_format(sheet_name, data)
            # 旧格式：每行第一列为 SQL 文本
            elif self._is_sql_content(first_cell):
                sql_content = '\n'.join([row[0] if row else '' for row in data])
                self.sql_tasks[sheet_name] = sql_content
                print(f"  [SQL Task] {sheet_name}: {len(sql_content)} chars (旧格式)")

    def _load_new_format(self, sheet_name: str, data: List[List[str]]):
        """加载新格式（key-value 对）的 SQL 任务 sheet
        
        格式约定：
          第一行: ['sqlText', sql内容]
          第二行: ['taskParams', 自定义参数内容]
        """
        # 第一行第一列是 sqlText 标记，第一行第二列是 sql 内容
        if len(data) > 0 and len(data[0]) > 1 and data[0][0].strip() == 'sqlText':
            sql_text = data[0][1]
            self.sql_tasks[sheet_name] = sql_text
            print(f"  [SQL Task] {sheet_name}: sqlText={len(sql_text)} chars (新格式)")
        
        # 第二行第一列是 taskParams 标记，第二行第二列是自定义参数
        if len(data) > 1 and len(data[1]) > 1 and data[1][0].strip() == 'taskParams':
            task_params = data[1][1]
            self.task_params[sheet_name] = task_params
            print(f"            taskParams={len(task_params)} chars (自定义追加)")
    
    def _is_sql_content(self, text: str) -> bool:
        """判断文本是否为 SQL 内容"""
        if not text:
            return False
        
        text_upper = text.upper().strip()
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'WITH', 'ALTER', 'DROP', 'TRUNCATE']
        
        # 检查是否以 SQL 关键字开头或为注释
        if text.startswith('--'):
            return True
        
        for keyword in sql_keywords:
            if text_upper.startswith(keyword):
                return True
        
        return False
    
    def get_sql_content(self, task_name: str) -> str:
        """获取 SQL 任务的 SQL 内容"""
        return self.sql_tasks.get(task_name, '')
    
    def get_task_params(self, task_name: str) -> str:
        """获取 Excel 中自定义的 taskParams 内容（仅新格式支持）"""
        return self.task_params.get(task_name, '')


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
                    task_type = row[1] if len(row) > 1 else 'SparkSql'
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
        """构建 scheduleConf"""
        schedule_info = self.schedules.get(task_name, {})
        schedule_type = schedule_info.get('schedule_type', '天')
        schedule_time = schedule_info.get('schedule_time', '00:00')
        
        template = self.schedule_templates.get(schedule_type, self.schedule_templates.get('天', {}))
        
        if schedule_type == '天':
            hour, minute = self._parse_time(schedule_time)
            schedule_conf = template.copy()
            schedule_conf['hour'] = hour
            schedule_conf['min'] = minute
            schedule_conf['periodType'] = '2'
        
        elif schedule_type == '周':
            hour, minute = self._parse_time(schedule_time)
            schedule_conf = template.copy()
            schedule_conf['weekDay'] = schedule_time if schedule_time.isdigit() else '1'
            schedule_conf['hour'] = str(hour)
            schedule_conf['min'] = str(minute)
            schedule_conf['periodType'] = '3'
        
        elif schedule_type == '月':
            hour, minute = self._parse_time(schedule_time)
            schedule_conf = template.copy()
            schedule_conf['day'] = schedule_time if schedule_time.isdigit() else '5'
            schedule_conf['hour'] = str(hour)
            schedule_conf['min'] = str(minute)
            schedule_conf['periodType'] = '4'
        
        elif schedule_type == '小时':
            schedule_conf = template.copy()
            gap_hour = schedule_time if schedule_time.isdigit() else '1'
            if '-' in schedule_time:
                parts = schedule_time.split('-')
                schedule_conf['beginHour'] = parts[0]
                schedule_conf['endHour'] = parts[1] if len(parts) > 1 else '23'
            schedule_conf['gapHour'] = gap_hour
            schedule_conf['periodType'] = '1'
        
        elif schedule_type == '分钟':
            schedule_conf = template.copy()
            gap_min = schedule_time if schedule_time.isdigit() else '15'
            if '-' in schedule_time:
                parts = schedule_time.split('-')
                schedule_conf['beginHour'] = parts[0]
                schedule_conf['endHour'] = parts[1] if len(parts) > 1 else '23'
            schedule_conf['gapMin'] = gap_min
            schedule_conf['periodType'] = '0'
        
        elif schedule_type in ['corn 表达式', 'cron']:
            schedule_conf = template.copy()
            schedule_conf['cron'] = schedule_time
            schedule_conf['periodType'] = '5'
        
        else:
            hour, minute = self._parse_time(schedule_time)
            schedule_conf = self.schedule_templates.get('天', {}).copy()
            schedule_conf['hour'] = hour
            schedule_conf['min'] = minute
            schedule_conf['periodType'] = '2'
        
        return schedule_conf
    
    def _parse_time(self, time_str: str) -> Tuple[int, int]:
        """解析时间字符串为 hour 和 minute"""
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


class AssembleScriptJson:
    """AssembleScriptJson 主类 - 专门处理 SQL 任务配置"""
    
    def __init__(self):
        self.sql_task_info = SqlTaskInfo()
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
            task_type_desc: 任务类型描述（如 'SparkSql', 'FlinkSql' 等）
        
        Returns:
            任务类型 ID（如 '0', '31' 等）
        """
        if self._task_type_mapping:
            return self._task_type_mapping.get(task_type_desc, '0')
        # 回退到硬编码
        if 'spark' in task_type_desc.lower():
            return '0'
        elif 'flink' in task_type_desc.lower():
            return '39'
        return '0'
    
    def load_all(self):
        """加载所有输入文件"""
        print(f"加载公共信息：{PUBLIC_INFO_FILE}")
        self.public_info.load_from_excel(PUBLIC_INFO_FILE)
        self.config.update(self.public_info.to_dict())  # public_info 的参数覆盖默认值
        
        print(f"加载 SQL 任务信息：{TASK_INFO_FILE}")
        self.sql_task_info.load_from_excel(TASK_INFO_FILE)
        print(f"  找到 {len(self.sql_task_info.sql_tasks)} 个 SQL 任务")
        
        print(f"加载调度配置：{TASK_SCHEDULE_FILE}")
        self.task_schedule.load_from_excel(TASK_SCHEDULE_FILE)
        print(f"  找到 {len(self.task_schedule.schedules)} 条调度配置")
        
        print(f"加载调度模板：{SCHEDULE_TEMPLATE_FILE}")
        self.task_schedule.load_schedule_templates(SCHEDULE_TEMPLATE_FILE)
        
        print(f"加载任务类型映射：{TASK_TYPE_FILE}")
        self.load_task_type_mapping()
    
    def _build_task_task_info(self, task_name: str, task_type: str) -> List[Dict[str, Any]]:
        """构建 taskTaskInfo 配置"""
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
    
    def _build_schedule_conf_str(self, task_name: str) -> Tuple[str, str]:
        """
        构建 scheduleConf JSON 字符串
        
        Returns:
            (scheduleConf JSON 字符串, periodType 值)
        """
        schedule_conf = self.task_schedule.build_schedule_conf(task_name)
        period_type = str(schedule_conf.get('periodType', '2'))
        return json.dumps(schedule_conf, ensure_ascii=False, separators=(',', ':')), period_type
    
    def _get_task_params(self, task_type: str) -> str:
        """根据任务类型获取 taskParams 配置"""
        task_type_lower = task_type.lower()
        
        if 'spark' in task_type_lower:
            return '''## Driver 程序使用的 CPU 核数，默认为 1
# spark.driver.cores=1

## Driver 程序使用内存大小，默认 1g
# spark.driver.memory=1g

## 对 Spark 每个 action 结果集大小的限制，最少是 1M，若设为 0 则不限制大小。
## 若 Job 结果超过限制则会异常退出，若结果集限制过大也可能造成 OOM 问题，默认 1g
# spark.driver.maxResultSize=1g

## 启动的 executor 的数量，默认为 1
# spark.executor.instances=1

## 每个 executor 使用的 CPU 核数，默认为 1
# spark.executor.cores=1

## 每个 executor 内存大小，默认 1g
# spark.executor.memory=1g

## 任务优先级，值越小，优先级越高，范围:1-1000


## spark 日志级别可选 ALL, DEBUG, ERROR, FATAL, INFO, OFF, TRACE, WARN
# logLevel = INFO

## spark 中所有网络交互的最大超时时间
# spark.network.timeout=120s

## executor 的 OffHeap 内存，和 spark.executor.memory 配置使用
# spark.yarn.executor.memoryOverhead=

## 设置 spark sql shuffle 分区数，默认 200
# spark.sql.shuffle.partitions=200

## 开启 spark 推测行为，默认 false
# spark.speculation=false'''
        
        elif 'flink' in task_type_lower:
            return '''## 任务运行方式：
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
        
        else:
            # 默认返回 Spark 配置
            return '''## Driver 程序使用的 CPU 核数，默认为 1
# spark.driver.cores=1

## Driver 程序使用内存大小，默认 1g
# spark.driver.memory=1g

## 启动的 executor 的数量，默认为 1
# spark.executor.instances=1

## 每个 executor 使用的 CPU 核数，默认为 1
# spark.executor.cores=1

## 每个 executor 内存大小，默认 1g
# spark.executor.memory=1g

## 任务优先级，值越小，优先级越高，范围:1-1000'''
    
    def _get_chosen_database(self, task_type: str) -> str:
        """
        根据任务类型动态获取 chosenDatabase 值
        
        规则：
          - SparkSql: 读取 dataSource_info.xlsx 中数据源类型为 hdfs 的 jdbc，
            截取 URL 末尾 schema 作为 chosenDatabase
          - 其他类型: 默认返回 'zy_test'（待后续补充）
        """
        if 'spark' in task_type.lower():
            # 读取 dataSource_info.xlsx，查找 hdfs 类型数据源
            if not os.path.exists(DATA_SOURCE_FILE):
                return 'zy_test'
            try:
                sheet_names = ExcelReader.get_sheet_names(DATA_SOURCE_FILE)
                for sheet_name in sheet_names:
                    config = ExcelReader.read_to_dict(DATA_SOURCE_FILE, sheet_name)
                    source_type = config.get('数据源类型', '').lower()
                    if source_type == 'hdfs':
                        jdbc = config.get('jdbc', '')
                        if jdbc:
                            # JDBC URL: jdbc:hive2://172.16.124.9:8191/zy_test → zy_test
                            # 取最后一个 / 之后的部分，去掉可能的参数
                            schema = jdbc.rstrip('/').rsplit('/', 1)[-1]
                            # 去掉可能的 ? 参数
                            if '?' in schema:
                                schema = schema.split('?')[0]
                            if schema:
                                return schema
            except Exception:
                pass
        return 'zy_test'
    
    def build_sql_task_config(self, task_name: str, task_type: str) -> Dict[str, Any]:
        """构建 SQL 任务配置"""
        schedule_conf_str, period_type = self._build_schedule_conf_str(task_name)
        
        sql_text = self.sql_task_info.get_sql_content(task_name)
        if not sql_text:
            sql_text = f'-- {task_name}\nSELECT 1'
        
        task_task_info = self._build_task_task_info(task_name, task_type)
        
        # 获取默认 taskParams，如果 Excel 中有自定义 taskParams 则直接追加
        default_params = self._get_task_params(task_type)
        extra_params = self.sql_task_info.get_task_params(task_name)
        if extra_params:
            task_params = default_params + '\n' + extra_params
        else:
            task_params = default_params
        
        # 动态获取 chosenDatabase
        chosen_database = self._get_chosen_database(task_type)
        
        sql_task_config = {
            'taskInfo': {
                'agentResourceId': 17,
                'appType': 1,
                'chosenDatabase': chosen_database,
                'componentVersion': '3.2',
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
                'periodType': int(period_type),
                'projectId': int(self.config['projectId']),
                'projectScheduleStatus': 0,
                'scheduleConf': schedule_conf_str,
                'scheduleStatus': 1,
                'sqlText': sql_text,
                'submitStatus': 1,
                'taskDesc': '',
                'taskGroup': 0,
                'taskId': random.randint(1000000, 9999999),
                'taskType': int(self.get_task_type_id(task_type)),
                'taskParams': task_params,
                'tenantId': int(self.config['tenantId']),
                'yarnResourceName': self.config.get('yarnResourceName', 'saas')
            },
            'taskTaskInfo': task_task_info,
            'updateEnvParam': False
        }
        
        return sql_task_config
    
    def generate_all(self):
        """生成所有 SQL 任务的配置文件"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        generated_tasks = set()
        
        for task_name, schedule_info in self.task_schedule.schedules.items():
            task_type = schedule_info.get('task_type', 'SparkSql')
            
            # 只处理 SQL 类型任务
            sql_keywords = ['spark', 'flink', 'odps', 'hive', 'sql']
            is_sql_task = any(kw in task_type.lower() for kw in sql_keywords)
            
            if not is_sql_task:
                print(f"\n跳过非 SQL 任务：{task_name} (类型：{task_type})")
                continue
            
            if task_name in generated_tasks:
                continue
            
            print(f"\n生成 SQL 任务配置：{task_name} (类型：{task_type})")
            
            try:
                config = self.build_sql_task_config(task_name, task_type)
                
                output_file = os.path.join(OUTPUT_DIR, f'{task_name}.json')
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                
                print(f"  ✓ 输出：{output_file}")
                generated_tasks.add(task_name)
            
            except Exception as e:
                print(f"  ✗ 错误：{e}")
                raise
        
        print(f"\n{'='*60}")
        print(f"完成！共生成 {len(generated_tasks)} 个 SQL 任务配置文件")
        print(f"输出目录：{OUTPUT_DIR}")
        print(f"{'='*60}")


def main():
    """主函数"""
    print("="*60)
    print("       AssembleScriptJson - SQL 任务配置生成")
    print("="*60)
    
    assembler = AssembleScriptJson()
    assembler.load_all()
    assembler.generate_all()


if __name__ == '__main__':
    main()
