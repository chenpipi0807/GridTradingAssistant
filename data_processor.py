"""
数据处理模块 - 负责处理股票数据，计算中间价、振幅等指标
"""
import pandas as pd
import numpy as np


class DataProcessor:
    def __init__(self):
        """初始化数据处理器"""
        pass
    
    def process_stock_data(self, df):
        """
        处理股票数据，计算中间价、振幅等指标
        
        Parameters:
        -----------
        df : pd.DataFrame
            包含股票数据的DataFrame，需包含'high'和'low'列
            
        Returns:
        --------
        pd.DataFrame : 添加了计算指标的DataFrame
        """
        if df.empty:
            return df
        
        # 确保日期格式一致
        df['date'] = pd.to_datetime(df['date'])
        
        # 计算中间价：（当日最高价 + 当日最低价）/ 2
        df['mid_price'] = (df['high'] + df['low']) / 2
        
        # 计算基础振幅：(最高价 - 最低价) / 最低价 × 100%
        df['amplitude'] = (df['high'] - df['low']) / df['low'] * 100
        
        # 计算相对振幅：(最高价 - 最低价) / 前日收盘价 × 100%
        df['rel_amplitude'] = np.nan
        for i in range(1, len(df)):
            if i > 0:
                df.loc[df.index[i], 'rel_amplitude'] = (
                    (df.loc[df.index[i], 'high'] - df.loc[df.index[i], 'low']) / 
                    df.loc[df.index[i-1], 'close'] * 100
                )
        
        # 计算中间价通道上下轨
        df['mid_upper'] = df['mid_price'] * 1.01  # 上轨：中间价+1%
        df['mid_lower'] = df['mid_price'] * 0.99  # 下轨：中间价-1%
        
        # 添加历史区间突破标记
        df = self.mark_breakouts(df)
        
        # 确保所有列的数据类型正确
        numeric_cols = ['open', 'high', 'low', 'close', 'mid_price', 
                        'amplitude', 'rel_amplitude', 'mid_upper', 'mid_lower']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def mark_breakouts(self, df, window=5, threshold=0.02):
        """
        标记价格突破历史区间的情况
        
        Parameters:
        -----------
        df : pd.DataFrame
            股票数据
        window : int
            回溯的天数窗口
        threshold : float
            突破阈值，默认为2%
            
        Returns:
        --------
        pd.DataFrame : 添加了突破标记的DataFrame
        """
        if len(df) < window:
            df['price_breakout'] = False
            return df
            
        df['price_breakout'] = False
        
        for i in range(window, len(df)):
            # 获取过去window天的最高价和最低价
            hist_high = df.iloc[i-window:i]['high'].max()
            hist_low = df.iloc[i-window:i]['low'].min()
            
            # 当前价格
            current_close = df.iloc[i]['close']
            
            # 判断是否突破上轨或下轨
            upper_breakout = current_close > hist_high * (1 + threshold)
            lower_breakout = current_close < hist_low * (1 - threshold)
            
            df.loc[df.index[i], 'price_breakout'] = upper_breakout or lower_breakout
        
        return df
    
    def merge_stock_and_fund_data(self, stock_df, fund_df):
        """
        合并股票价格数据和资金流向数据
        
        Parameters:
        -----------
        stock_df : pd.DataFrame
            股票价格数据
        fund_df : pd.DataFrame
            资金流向数据
            
        Returns:
        --------
        pd.DataFrame : 合并后的DataFrame
        """
        if stock_df.empty or fund_df.empty:
            return stock_df
            
        # 确保日期格式一致
        stock_df['date'] = pd.to_datetime(stock_df['date'])
        fund_df['date'] = pd.to_datetime(fund_df['date'])
        
        # 通过日期合并
        merged_df = pd.merge(
            stock_df, 
            fund_df, 
            on=['date', 'code'], 
            how='left'
        )
        
        return merged_df
    
    def calculate_historic_percentiles(self, df, column='amplitude', window=20):
        """
        计算历史数据的百分位数
        
        Parameters:
        -----------
        df : pd.DataFrame
            股票数据
        column : str
            要计算百分位数的列名
        window : int
            计算窗口大小
            
        Returns:
        --------
        pd.DataFrame : 添加了百分位数列的DataFrame
        """
        if len(df) < window or column not in df.columns:
            return df
            
        # 添加百分位数列
        percentile_col = f'{column}_percentile'
        df[percentile_col] = np.nan
        
        for i in range(window, len(df)):
            # 获取历史窗口数据
            hist_values = df.iloc[i-window:i][column].dropna()
            
            if len(hist_values) > 0:
                # 计算当前值在历史数据中的百分位
                current_value = df.iloc[i][column]
                percentile = (hist_values < current_value).mean() * 100
                df.loc[df.index[i], percentile_col] = percentile
                
        return df
    
    def detect_abnormal_amplitude(self, df, threshold_percentile=90):
        """
        检测异常振幅
        
        Parameters:
        -----------
        df : pd.DataFrame
            股票数据，需包含amplitude_percentile列
        threshold_percentile : float
            认为是异常的振幅百分位阈值
            
        Returns:
        --------
        pd.DataFrame : 添加了异常振幅标记的DataFrame
        """
        if 'amplitude_percentile' not in df.columns:
            df = self.calculate_historic_percentiles(df, 'amplitude')
            
        if 'amplitude_percentile' in df.columns:
            df['abnormal_amplitude'] = df['amplitude_percentile'] > threshold_percentile
        else:
            df['abnormal_amplitude'] = False
            
        return df
