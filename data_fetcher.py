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
    def __init__(self, data_source="tencent"):
        """
        初始化数据获取器

        Parameters:
        -----------
        data_source : str
            数据源名称，支持 'tencent'（腾讯财经，默认）、'eastmoney'（东方财富）或 'tushare'
        """
        self.data_source = data_source
        self.tushare_token = None  # 需要用户提供Tushare Token

        # 创建带浏览器伪装头的 Session
        self.session = requests.Session()
        self.session.trust_env = False  # 绕过系统代理，避免代理干扰HTTPS连接
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

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
            
        if source == "tencent":
            return self._get_from_tencent(code, start_date, end_date)
        elif source == "eastmoney":
            return self._get_from_eastmoney(code, start_date, end_date)
        elif source == "tushare":
            df = self._get_from_tushare(code, start_date, end_date)
            stock_info = {"code": code, "name": code, "market": ""}
            return df, stock_info
        else:
            raise ValueError(f"不支持的数据源: {source}")
    
    def _get_from_tencent(self, code, start_date, end_date):
        """从腾讯财经获取K线数据（前复权日线）

        腾讯API的日期参数过滤不可靠，所以请求足够多的数据后在本地按日期过滤。
        """
        normalized_code = self.normalize_stock_code(code)

        market = "上海" if normalized_code.startswith('sh') else "深圳"

        # 腾讯财经前复权K线 API（请求最多640条日线数据，覆盖约2.5年）
        url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {
            'param': f'{normalized_code},day,,,640,qfq',
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('code') != 0 or 'data' not in data:
                return pd.DataFrame(), {}

            stock_data_entry = data['data'].get(normalized_code)
            if not stock_data_entry:
                return pd.DataFrame(), {}

            # 腾讯返回的 K 线 key 可能是 'qfqday' 或 'day'，兼容两者
            klines = stock_data_entry.get('qfqday') or stock_data_entry.get('day') or []

            # 提取股票名称（从 qt 字段）
            stock_name = ""
            qt = stock_data_entry.get('qt', {})
            if isinstance(qt, dict):
                qt_fields = qt.get(normalized_code, [])
                if isinstance(qt_fields, list) and len(qt_fields) > 1:
                    stock_name = qt_fields[1]

            stock_data = []
            for row in klines:
                if len(row) >= 6:
                    date_str = row[0]

                    # 按日期范围过滤
                    if date_str < start_date or date_str > end_date:
                        continue

                    open_price = float(row[1])
                    close_price = float(row[2])
                    high_price = float(row[3])
                    low_price = float(row[4])
                    volume = float(row[5])  # 成交量（手）

                    # 成交额估算: 成交量(手) * 收盘价 * 100
                    amount = volume * close_price * 100

                    # 振幅
                    amplitude = (high_price - low_price) / open_price * 100 if open_price > 0 else 0

                    stock_data.append({
                        'date': date_str,
                        'open': open_price,
                        'close': close_price,
                        'high': high_price,
                        'low': low_price,
                        'volume': volume,
                        'amount': amount,
                        'amplitude': amplitude,
                    })

            df = pd.DataFrame(stock_data)
            if not df.empty:
                df['code'] = code

            stock_info = {
                "code": normalized_code,
                "name": stock_name,
                "market": market,
            }

            return df, stock_info

        except Exception as e:
            print(f"从腾讯财经获取数据时出错: {e}")
            return pd.DataFrame(), {}

    def _get_from_eastmoney(self, code, start_date, end_date):
        """从东方财富获取数据（可能因TLS指纹检测而失败）"""
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
            response = self.session.get(url, params=params, timeout=10)
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
                response = self.session.get(url, params=params, timeout=10)
                raw = response.text

                # 东方财富搜索API返回的是JSONP格式（jQuery...({...})），需要提取JSON部分
                json_start = raw.find('(')
                json_end = raw.rfind(')')
                if json_start != -1 and json_end != -1:
                    raw = raw[json_start + 1:json_end]
                data = json.loads(raw)

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
            
            response = self.session.get(url, params=params, timeout=10)
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
