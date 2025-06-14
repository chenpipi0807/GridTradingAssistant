"""
数据获取模块 - 负责从各种数据源获取股票数据
"""
import pandas as pd
import requests
import json
import time
from datetime import datetime
import tushare as ts

class DataFetcher:
    def __init__(self, data_source="eastmoney"):
        """
        初始化数据获取器
        
        Parameters:
        -----------
        data_source : str
            数据源名称，支持 'eastmoney' 或 'tushare'
        """
        self.data_source = data_source
        self.tushare_token = None  # 需要用户提供Tushare Token
        
        if data_source == "tushare" and self.tushare_token:
            ts.set_token(self.tushare_token)
            self.pro = ts.pro_api()
    
    def set_tushare_token(self, token):
        """设置Tushare API token"""
        self.tushare_token = token
        ts.set_token(token)
        self.pro = ts.pro_api()
    
    def normalize_stock_code(self, code):
        """标准化股票代码格式"""
        code = str(code).strip()
        # 如果是纯数字代码，根据规则添加前缀
        if code.isdigit():
            if code.startswith('6'):
                return f"sh{code}"
            else:
                return f"sz{code}"
        # 如果已经包含前缀，直接返回
        elif code.lower().startswith(('sh', 'sz')):
            return code.lower()
        return code
    
    def get_stock_data(self, code, start_date, end_date=None, data_source=None):
        """
        获取指定时间范围内的股票数据
        
        Parameters:
        -----------
        code : str
            股票代码，如 '603019' 或 'sh603019'
        start_date : str
            开始日期，格式 'YYYY-MM-DD'
        end_date : str, optional
            结束日期，格式 'YYYY-MM-DD'，默认为当前日期
        data_source : str, optional
            数据源名称，可选择性覆盖实例化时设置的数据源
            
        Returns:
        --------
        pd.DataFrame : 包含股票数据的DataFrame
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # 使用传入的data_source（如果有），否则使用实例变量
        source = data_source if data_source else self.data_source
            
        if source == "eastmoney":
            df, stock_info = self._get_from_eastmoney(code, start_date, end_date)
            return df, stock_info
        elif source == "tushare":
            df = self._get_from_tushare(code, start_date, end_date)
            # 对于tushare，暂时构造一个简单的stock_info
            stock_info = {"code": code, "name": code, "market": ""}
            return df, stock_info
        else:
            raise ValueError(f"不支持的数据源: {source}")
    
    def _get_from_eastmoney(self, code, start_date, end_date):
        """从东方财富获取数据"""
        normalized_code = self.normalize_stock_code(code)
        
        # 去掉开头的sh或sz以适应东方财富API
        secid = normalized_code
        market = ""
        stock_code = normalized_code
        
        if normalized_code.startswith('sh'):
            secid = f"1.{normalized_code[2:]}"
            market = "上海"
            stock_code = normalized_code[2:]
        elif normalized_code.startswith('sz'):
            secid = f"0.{normalized_code[2:]}"
            market = "深圳"
            stock_code = normalized_code[2:]
        
        # 转换日期格式
        start_timestamp = int(time.mktime(time.strptime(start_date, '%Y-%m-%d'))) * 1000
        end_timestamp = int(time.mktime(time.strptime(end_date, '%Y-%m-%d'))) * 1000 + 86399000  # 加上一天的毫秒数减1
        
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            'klt': '101',  # 日K线
            'fqt': '1',    # 前复权
            'secid': secid,
            'beg': start_date.replace('-', ''),
            'end': end_date.replace('-', ''),
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'data' not in data or data['data'] is None or 'klines' not in data['data']:
                return pd.DataFrame(), {}
                
            stock_data = []
            for kline in data['data']['klines']:
                parts = kline.split(',')
                if len(parts) >= 7:
                    stock_data.append({
                        'date': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': float(parts[5]),
                        'amount': float(parts[6]),
                        'amplitude': (float(parts[3]) - float(parts[4])) / float(parts[1]) * 100 if float(parts[1]) > 0 else 0  # 振幅
                    })
            
            df = pd.DataFrame(stock_data)
            df['code'] = code
            
            # 获取股票名称和其他信息
            stock_name = ""
            if 'data' in data and 'name' in data['data']:
                stock_name = data['data']['name']
            
            stock_info = {
                "code": normalized_code,
                "name": stock_name,
                "market": market
            }
            
            return df, stock_info
        
        except Exception as e:
            print(f"从东方财富获取数据时出错: {e}")
            return pd.DataFrame(), {}
    
    def _get_from_tushare(self, code, start_date, end_date):
        """从Tushare获取数据"""
        if not self.tushare_token:
            raise ValueError("使用Tushare数据源需要设置token")
        
        # 处理股票代码格式
        code_clean = code.replace('sh', '').replace('sz', '')
        
        try:
            df = ts.pro_bar(
                ts_code=code_clean,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adj='qfq'  # 前复权
            )
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 重命名列以保持一致性
            df = df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume',
                'amount': 'amount'
            })
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df['code'] = code
            
            return df.sort_values('date')
        
        except Exception as e:
            print(f"从Tushare获取数据时出错: {e}")
            return pd.DataFrame()
    
    def search_stock_by_name(self, name):
        """根据股票名称搜索股票代码"""
        if self.data_source == "tushare" and self.tushare_token:
            try:
                df = self.pro.stock_basic(
                    exchange='',
                    list_status='L',
                    fields='ts_code,symbol,name,area,industry,list_date'
                )
                result = df[df['name'].str.contains(name)]
                return result[['ts_code', 'symbol', 'name']]
            except Exception as e:
                print(f"搜索股票名称时出错: {e}")
                return pd.DataFrame()
        else:
            # 东方财富股票搜索API
            url = "https://searchapi.eastmoney.com/api/suggest/get"
            params = {
                'input': name,
                'type': '14',
                'token': 'D43BF722C8E33BDC906FB84D85E326E8',
                'count': '10'
            }
            
            try:
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'QuotationCodeTable' not in data or 'Data' not in data['QuotationCodeTable']:
                    return pd.DataFrame()
                
                stocks = []
                for item in data['QuotationCodeTable']['Data']:
                    if 'Code' in item and 'Name' in item:
                        stocks.append({
                            'symbol': item['Code'],
                            'name': item['Name'],
                            'market': item.get('SecurityTypeName', '')
                        })
                
                return pd.DataFrame(stocks)
            except Exception as e:
                print(f"搜索股票名称时出错: {e}")
                return pd.DataFrame()
    
    def get_fund_flow_data(self, code, start_date, end_date=None):
        """获取资金流向数据"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        normalized_code = self.normalize_stock_code(code)
        
        # 东方财富资金流向API
        try:
            # 处理代码格式
            if normalized_code.startswith('sh'):
                market = 1
                code_num = normalized_code[2:]
            else:  # sz
                market = 0
                code_num = normalized_code[2:]
                
            url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
            params = {
                'lmt': '100',
                'klt': '101',
                'secid': f"{market}.{code_num}",
                'fields1': 'f1,f2,f3,f7',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63',
                'ut': 'b2884a393a59ad64002292a3e90d46a5',
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'data' not in data or data['data'] is None or 'klines' not in data['data']:
                return pd.DataFrame()
                
            flow_data = []
            for kline in data['data']['klines']:
                parts = kline.split(',')
                if len(parts) >= 5:
                    flow_data.append({
                        'date': parts[0],
                        'main_net_inflow': float(parts[1]),  # 主力净流入
                        'retail_net_inflow': float(parts[2]),  # 散户净流入
                        'net_amount': float(parts[3]),  # 净额
                        'total_amount': float(parts[4]),  # 总额
                    })
            
            df = pd.DataFrame(flow_data)
            
            # 过滤日期范围
            df['date'] = pd.to_datetime(df['date'])
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            df = df[(df['date'] >= start) & (df['date'] <= end)]
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            
            df['code'] = code
            return df
            
        except Exception as e:
            print(f"获取资金流向数据时出错: {e}")
            return pd.DataFrame()
