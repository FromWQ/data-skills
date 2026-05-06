#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TransferData2 - 统一流程控制器

根据 taskSchedule_info.xlsx 中的任务类型，自动调用对应的技能：
- 虚节点 + 数据同步任务 → AssembleSyncJson
- SQL 任务（SparkSql、FlinkSql 等）→ AssembleScriptJson
- 最后调用 AssembleSyncReleasePackage 组装发布包
"""

import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# 基础路径
WORKSPACE_DIR = Path("/home/shuofeng/.openclaw/workspace")
TRANSFER_DATA2_DIR = WORKSPACE_DIR / "skills" / "TransferData2"
LOCAL_INPUT_DIR = TRANSFER_DATA2_DIR / "输入文件"
REMOTE_INPUT_DIR = Path("/mnt/c/Users/67461/Desktop/sync_model/model")
INPUT_DIR = LOCAL_INPUT_DIR if LOCAL_INPUT_DIR.exists() else REMOTE_INPUT_DIR
TASK_SCHEDULE_FILE = INPUT_DIR / "taskSchedule_info.xlsx"

# 技能脚本路径
ASSEMBLE_SYNC_JSON_SCRIPT = TRANSFER_DATA2_DIR / "AssembleSyncJson" / "scripts" / "generate_config.py"
ASSEMBLE_SCRIPT_JSON_SCRIPT = TRANSFER_DATA2_DIR / "AssembleScriptJson" / "scripts" / "generate_sql_config.py"
ASSEMBLE_SYNC_RELEASE_PACKAGE_SCRIPT = TRANSFER_DATA2_DIR / "AssembleSyncReleasePackage" / "scripts" / "assemble_sync_package.py"


class TaskScheduleReader:
    """任务调度配置读取器"""
    
    @staticmethod
    def read_from_excel(filepath: Path) -> Dict[str, Dict[str, str]]:
        """
        从 taskSchedule_info.xlsx 读取任务调度配置
        
        Returns:
            {任务名：{task_type, dependency, schedule_time, schedule_type}} 字典
        """
        schedules = {}
        
        if not filepath.exists():
            print(f"  ✗ 错误：找不到调度配置文件 {filepath}")
            return {}
        
        try:
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                # 获取 workbook.xml
                wb_xml = zip_ref.read('xl/workbook.xml')
                root = ET.fromstring(wb_xml)
                
                # 查找命名空间
                ns = ''
                for elem in root.iter():
                    if '}' in elem.tag:
                        ns = elem.tag.split('}')[0] + '}'
                        break
                
                # 获取 sheet 映射
                sheet_map = {}
                for sheet in root.iter(f'{ns}sheet'):
                    name = sheet.get('name')
                    rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                    if name and rid:
                        sheet_map[name] = f'xl/worksheets/{rid.replace("rId", "sheet")}.xml'
                
                # 读取第一个 sheet
                if sheet_map:
                    first_sheet = list(sheet_map.values())[0]
                    sheet_xml = zip_ref.read(first_sheet)
                    sheet_root = ET.fromstring(sheet_xml)
                    
                    # 重新查找命名空间
                    ns = ''
                    for elem in sheet_root.iter():
                        if '}' in elem.tag:
                            ns = elem.tag.split('}')[0] + '}'
                            break
                    
                    # 读取共享字符串
                    strings = {}
                    try:
                        st_xml = zip_ref.read('xl/sharedStrings.xml')
                        st_root = ET.fromstring(st_xml)
                        for i, si in enumerate(st_root.iter(f'{ns}si')):
                            text = ''
                            for t in si.iter(f'{ns}t'):
                                text += t.text or ''
                            strings[i] = text
                    except:
                        pass
                    
                    # 读取数据
                    rows = []
                    for row in sheet_root.iter(f'{ns}row'):
                        row_data = []
                        for cell in row.iter(f'{ns}c'):
                            cell_type = cell.get('t')
                            value = ''
                            
                            if cell_type == 's':
                                for v in cell.iter(f'{ns}v'):
                                    if v.text:
                                        value = strings.get(int(v.text), '')
                            else:
                                for v in cell.iter(f'{ns}v'):
                                    value = v.text or ''
                            
                            row_data.append(value)
                        
                        if row_data:
                            rows.append(row_data)
                    
                    # 解析调度配置（跳过表头）
                    # 列：任务名称 | 任务类型 | 上游依赖 | 调度时间 | 调度类型
                    for row in rows[1:]:
                        if len(row) >= 1:
                            task_name = row[0].strip()
                            task_type = row[1].strip() if len(row) > 1 else '数据同步'
                            dependency = row[2].strip() if len(row) > 2 else '无'
                            schedule_time = row[3].strip() if len(row) > 3 else '00:00'
                            schedule_type = row[4].strip() if len(row) > 4 else '天'
                            
                            if task_name:
                                schedules[task_name] = {
                                    'task_type': task_type,
                                    'dependency': dependency,
                                    'schedule_time': schedule_time,
                                    'schedule_type': schedule_type
                                }
        
        except Exception as e:
            print(f"  ✗ 错误：读取调度配置失败：{e}")
        
        return schedules


def classify_tasks(schedules: Dict[str, Dict[str, str]]) -> Tuple[List[str], List[str]]:
    """
    根据任务类型分类任务
    
    Args:
        schedules: 任务调度配置字典
    
    Returns:
        (sync_tasks, sql_tasks) 元组
        - sync_tasks: 需要同步任务（虚节点 + 数据同步）
        - sql_tasks: 需要 SQL 任务（SparkSql、FlinkSql 等）
    """
    sync_tasks = []
    sql_tasks = []
    
    for task_name, config in schedules.items():
        task_type = config.get('task_type', '数据同步')
        task_type_lower = task_type.lower()
        
        # 判断是否为数据同步或虚节点
        if task_type in ['数据同步', '虚节点', '数据同步任务']:
            sync_tasks.append(task_name)
        # 判断是否为 SQL 任务类型
        elif any(kw in task_type_lower for kw in ['spark', 'flink', 'odps', 'hive', 'sql']):
            sql_tasks.append(task_name)
        else:
            # 未知类型，默认归为数据同步
            print(f"  ⚠ 未知任务类型 '{task_type}'，归类为数据同步任务")
            sync_tasks.append(task_name)
    
    return sync_tasks, sql_tasks


def run_script(script_path: Path, description: str) -> bool:
    """运行脚本并返回是否成功"""
    if not script_path.exists():
        print(f"  ✗ 错误：找不到脚本 {script_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"执行：{description}")
    print(f"脚本：{script_path}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(WORKSPACE_DIR),
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  ✗ 错误：执行失败：{e}")
        return False


def main():
    """主函数"""
    print("="*60)
    print("       TransferData2 - 统一流程控制器")
    print("="*60)
    print(f"\n开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 步骤 1: 读取任务调度配置
    print(f"\n{'='*60}")
    print("步骤 1: 读取任务调度配置")
    print(f"{'='*60}")
    print(f"配置文件：{TASK_SCHEDULE_FILE}")
    
    schedules = TaskScheduleReader.read_from_excel(TASK_SCHEDULE_FILE)
    
    if not schedules:
        print(f"  ✗ 错误：未读取到任何任务配置")
        return 1
    
    print(f"  找到 {len(schedules)} 个任务")
    for task_name, config in schedules.items():
        print(f"    - {task_name} (类型：{config['task_type']})")
    
    # 步骤 2: 根据任务类型分类
    print(f"\n{'='*60}")
    print("步骤 2: 根据任务类型分类")
    print(f"{'='*60}")
    
    sync_tasks, sql_tasks = classify_tasks(schedules)
    
    print(f"  数据同步任务 + 虚节点 ({len(sync_tasks)} 个):")
    for task in sync_tasks:
        print(f"    - {task}")
    
    print(f"\n  SQL 任务 ({len(sql_tasks)} 个):")
    for task in sql_tasks:
        print(f"    - {task}")
    
    # 步骤 3: 执行 AssembleSyncJson（如有数据同步任务）
    if sync_tasks:
        if not run_script(ASSEMBLE_SYNC_JSON_SCRIPT, "AssembleSyncJson - 生成数据同步任务 + 虚节点任务配置"):
            print(f"\n  ✗ AssembleSyncJson 执行失败，终止流程")
            return 1
    else:
        print(f"\n  ⚠ 无数据同步任务，跳过 AssembleSyncJson")
    
    # 步骤 4: 执行 AssembleScriptJson（如有 SQL 任务）
    if sql_tasks:
        if not run_script(ASSEMBLE_SCRIPT_JSON_SCRIPT, "AssembleScriptJson - 生成 SQL 任务配置"):
            print(f"\n  ✗ AssembleScriptJson 执行失败，终止流程")
            return 1
    else:
        print(f"\n  ⚠ 无 SQL 任务，跳过 AssembleScriptJson")
    
    # 步骤 5: 执行 AssembleSyncReleasePackage（组装发布包）
    print(f"\n{'='*60}")
    print("步骤 5: 组装发布包")
    print(f"{'='*60}")
    
    if not run_script(ASSEMBLE_SYNC_RELEASE_PACKAGE_SCRIPT, "AssembleSyncReleasePackage - 组装多任务发布包"):
        print(f"\n  ✗ AssembleSyncReleasePackage 执行失败")
        return 1
    
    # 完成
    print(f"\n{'='*60}")
    print("✅ TransferData2 流程执行完成!")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    exit(main())
