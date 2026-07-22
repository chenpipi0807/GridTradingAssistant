"""
工具函数模块 - 提供辅助功能
"""
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re


def load_favorite_stocks():
    """
    从文件加载常用股票列表

    Returns:
    --------
    list : 包含股票代码和名称的字典列表
    """
    try:
        file_path = os.path.join(os.getcwd(), 'favorite_stocks.json')
        if not os.path.exists(file_path):
            default_favorites = [
                {"code": "603019", "name": "中科曙光"},
                {"code": "600161", "name": "天坛生物"},
                {"code": "002261", "name": "拓维信息"},
                {"code": "000977", "name": "浪潮信息"},
                {"code": "300502", "name": "新易盛"}
            ]
            save_favorite_stocks(default_favorites)
            return default_favorites

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('favorites', [])
    except Exception as e:
        print(f'加载常用股票时出错: {str(e)}')
        return []


def save_favorite_stocks(favorites):
    """
    保存常用股票列表到文件

    Parameters:
    -----------
    favorites : list
        包含股票代码和名称的字典列表
    """
    try:
        file_path = os.path.join(os.getcwd(), 'favorite_stocks.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"favorites": favorites}, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f'保存常用股票时出错: {str(e)}')
        return False


def add_favorite_stock(code, name):
    """
    添加股票到收藏列表

    Parameters:
    -----------
    code : str
        股票代码
    name : str
        股票名称
    Returns:
    --------
    bool : 是否添加成功
    """
    favorites = load_favorite_stocks()
    # 检查是否已存在
    for stock in favorites:
        if stock["code"] == code:
            return True  # 已存在，不算失败
    favorites.append({"code": code, "name": name})
    return save_favorite_stocks(favorites)


def remove_favorite_stock(code):
    """
    从收藏列表中移除股票

    Parameters:
    -----------
    code : str
        股票代码
    Returns:
    --------
    bool : 是否移除成功
    """
    favorites = load_favorite_stocks()
    favorites = [stock for stock in favorites if stock["code"] != code]
    return save_favorite_stocks(favorites)


def is_favorite_stock(code):
    """
    检查股票是否已收藏

    Parameters:
    -----------
    code : str
        股票代码
    Returns:
    --------
    bool : 是否已收藏
    """
    favorites = load_favorite_stocks()
    for stock in favorites:
        if stock["code"] == code:
            return True
    return False


def get_temp_stock_files():
    """
    获取 temp/ 目录下所有可用的股票数据文件

    Returns:
    --------
    list : 每个元素包含 code, name, file_path, date_range
    """
    result = []
    temp_dir = os.path.join(os.getcwd(), 'temp')

    if not os.path.exists(temp_dir):
        return result

    # 收集所有 CSV 文件（排除 current_stock_data.csv，单独处理）
    current_file = os.path.join(temp_dir, 'current_stock_data.csv')
    if os.path.exists(current_file):
        # 读取 info 文件获取名称
        info_file = os.path.join(temp_dir, 'current_stock_info.json')
        name = "未知"
        code = "未知"
        date_range = ""
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    code = info.get('code', '未知')
                    name = info.get('name', '未知')
                    date_range = info.get('period', '')
            except:
                pass
        result.append({
            "code": code,
            "name": name,
            "label": f"📊 当前行情: {name}({code}) {date_range}",
            "file_path": current_file,
            "date_range": date_range
        })

    # 扫描其他 CSV 文件
    for fname in os.listdir(temp_dir):
        if fname == 'current_stock_data.csv' or not fname.endswith('.csv'):
            continue
        fpath = os.path.join(temp_dir, fname)
        # 从文件名解析: {code}_{start}_{end}.csv
        parts = fname.replace('.csv', '').split('_')
        code = parts[0] if len(parts) >= 1 else '未知'
        date_range = f"{parts[1]} 至 {parts[2]}" if len(parts) >= 3 else ""

        # 尝试从收藏列表中匹配名称
        name = code
        favorites = load_favorite_stocks()
        for fav in favorites:
            if fav["code"] == code:
                name = fav["name"]
                break

        label = f"{name}({code})"
        if date_range:
            label += f" [{date_range}]"

        result.append({
            "code": code,
            "name": name,
            "label": label,
            "file_path": fpath,
            "date_range": date_range
        })

    return result


def is_valid_stock_code(code):
    """
    验证股票代码格式是否正确
    
    Parameters:
    -----------
    code : str
        股票代码
        
    Returns:
    --------
    bool : 代码是否有效
    """
    code = str(code).strip()
    
    # 上海证券交易所股票代码规则
    sh_pattern = r'^(sh)?[6][0-9]{5}$'
    # 深圳证券交易所股票代码规则
    sz_pattern = r'^(sz)?[0123][0-9]{5}$'
    
    return bool(re.match(sh_pattern, code.lower()) or re.match(sz_pattern, code.lower()))


def format_stock_code(code):
    """
    格式化股票代码为标准格式
    
    Parameters:
    -----------
    code : str
        股票代码
        
    Returns:
    --------
    str : 格式化后的股票代码
    """
    code = str(code).strip()
    
    # 如果已经包含前缀，直接返回小写版本
    if code.lower().startswith(('sh', 'sz')):
        return code.lower()
    
    # 根据规则添加前缀
    if code.startswith('6'):
        return f"sh{code}"
    else:
        return f"sz{code}"


def parse_date_range(date_range_str):
    """
    解析日期范围字符串
    
    Parameters:
    -----------
    date_range_str : str
        日期范围字符串，格式如"2025-01-01至2025-05-14"或"2025-01-01 - 2025-05-14"
        
    Returns:
    --------
    tuple : (开始日期, 结束日期)
    """
    # 如果为空，返回默认值（过去30天）
    if not date_range_str:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        return start_date, end_date
    
    # 尝试各种分隔符
    for sep in ['至', ' - ', '到', '~', ',', ';']:
        if sep in date_range_str:
            parts = date_range_str.split(sep)
            if len(parts) == 2:
                start_date = parts[0].strip()
                end_date = parts[1].strip()
                return start_date, end_date
    
    # 如果只有一个日期，将其作为开始日期，今天作为结束日期
    try:
        pd.to_datetime(date_range_str)  # 验证是否为有效日期
        return date_range_str, datetime.now().strftime('%Y-%m-%d')
    except:
        # 返回默认值
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        return start_date, end_date


def format_currency(value, prefix='¥'):
    """
    格式化货币数值
    
    Parameters:
    -----------
    value : float
        数值
    prefix : str
        货币符号前缀
        
    Returns:
    --------
    str : 格式化后的货币字符串
    """
    if pd.isna(value):
        return '-'
    return f"{prefix}{value:.2f}"


def format_percent(value):
    """
    格式化百分比数值
    
    Parameters:
    -----------
    value : float
        数值（已乘以100的百分比）
        
    Returns:
    --------
    str : 格式化后的百分比字符串
    """
    if pd.isna(value):
        return '-'
    return f"{value:.2f}%"


def format_large_number(value):
    """
    格式化大数字（万、亿单位）
    
    Parameters:
    -----------
    value : float
        数值
        
    Returns:
    --------
    str : 格式化后的数字字符串
    """
    if pd.isna(value):
        return '-'
    
    abs_value = abs(value)
    sign = '-' if value < 0 else ''
    
    if abs_value >= 1e8:  # 亿
        return f"{sign}{abs_value/1e8:.2f}亿"
    elif abs_value >= 1e4:  # 万
        return f"{sign}{abs_value/1e4:.2f}万"
    else:
        return f"{sign}{abs_value:.2f}"


def generate_date_options(days=365):
    """
    生成日期范围选项
    
    Parameters:
    -----------
    days : int
        向前生成多少天的选项
        
    Returns:
    --------
    list : 日期范围选项列表
    """
    today = datetime.now()
    
    options = [
        {'label': '近7天', 'value': (today - timedelta(days=7)).strftime('%Y-%m-%d') + '至' + today.strftime('%Y-%m-%d')},
        {'label': '近30天', 'value': (today - timedelta(days=30)).strftime('%Y-%m-%d') + '至' + today.strftime('%Y-%m-%d')},
        {'label': '近60天', 'value': (today - timedelta(days=60)).strftime('%Y-%m-%d') + '至' + today.strftime('%Y-%m-%d')},
        {'label': '近90天', 'value': (today - timedelta(days=90)).strftime('%Y-%m-%d') + '至' + today.strftime('%Y-%m-%d')},
        {'label': '近120天', 'value': (today - timedelta(days=120)).strftime('%Y-%m-%d') + '至' + today.strftime('%Y-%m-%d')},
        {'label': '近180天', 'value': (today - timedelta(days=180)).strftime('%Y-%m-%d') + '至' + today.strftime('%Y-%m-%d')},
        {'label': '近一年', 'value': (today - timedelta(days=365)).strftime('%Y-%m-%d') + '至' + today.strftime('%Y-%m-%d')},
    ]
    
    # 添加当年、去年等选项
    current_year = today.year
    options.extend([
        {'label': f'{current_year}年', 'value': f'{current_year}-01-01至{current_year}-12-31'},
        {'label': f'{current_year-1}年', 'value': f'{current_year-1}-01-01至{current_year-1}-12-31'},
    ])
    
    return options


def parse_stock_input(input_text):
    """
    解析用户输入的股票代码或名称
    
    Parameters:
    -----------
    input_text : str
        用户输入，可能包含股票代码或名称
        
    Returns:
    --------
    tuple : (代码类型, 代码或名称)
    """
    input_text = str(input_text).strip()
    
    # 检查是否为股票代码格式
    if is_valid_stock_code(input_text):
        return 'code', format_stock_code(input_text)
    
    # 如果包含数字，也视为代码，但不做格式化
    if any(c.isdigit() for c in input_text):
        return 'code', input_text
    
    # 否则视为股票名称
    return 'name', input_text
