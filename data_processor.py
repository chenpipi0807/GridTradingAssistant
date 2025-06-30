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
        
        # 计算开盘价与中间价差值百分比：(中间价 - 开盘价) / 中间价 × 100%
        # 当中间价高于开盘价时，差值为正；当中间价低于开盘价时，差值为负
        df['open_mid_diff'] = (df['mid_price'] - df['open']) / df['mid_price'] * 100
        
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
        
        # 计算增强振幅指标
        df = self.calculate_enhanced_amplitude(df)
        
        # 计算增强中间价-开盘价差值指标
        df = self.calculate_enhanced_open_mid_diff(df)
        
        # 计算MPMI (中间价动量指标)
        df = self.calculate_mpmi(df)
        
        # 计算星星指标
        df = self.calculate_star_indicator(df)
        
        # 确保所有列的数据类型正确
        numeric_cols = ['open', 'high', 'low', 'close', 'mid_price', 
                        'amplitude', 'rel_amplitude', 'mid_upper', 'mid_lower',
                        'amplitude_ma', 'amplitude_percentile', 'open_mid_diff',
                        'open_mid_diff_ma', 'open_mid_diff_percentile', 
                        'MPMI_Line', 'MPMI_Signal', 'MPMI_Hist']
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
        
    def calculate_enhanced_amplitude(self, df, ma_period=10, window=20, percentiles=[20, 50, 80]):
        """
        计算增强振幅指标，包括振幅的移动平均和历史百分位数
        
        Parameters:
        -----------
        df : pd.DataFrame
            股票数据，需包含'amplitude'列
        ma_period : int
            移动平均的周期，默认10
        window : int
            历史百分位计算的窗口大小，默认20
        percentiles : list
            要计算的百分位数，默认[20, 50, 80]
            
        Returns:
        --------
        pd.DataFrame : 添加了增强振幅指标的DataFrame
        """
        if 'amplitude' not in df.columns or df.empty:
            return df
        
        # 计算振幅的移动平均
        df['amplitude_ma'] = df['amplitude'].rolling(window=ma_period).mean()
        
        # 计算ATR (Average True Range)
        # 定义真实范围
        df['true_range'] = 0.0
        for i in range(1, len(df)):
            true_range = max(
                df['high'].iloc[i] - df['low'].iloc[i],  # 当日高低差
                abs(df['high'].iloc[i] - df['close'].iloc[i-1]),  # 当日最高与前日收盘差
                abs(df['low'].iloc[i] - df['close'].iloc[i-1])   # 当日最低与前日收盘差
            )
            df.loc[df.index[i], 'true_range'] = true_range
        
        # 计算ATR（使用简单移动平均）
        df['atr'] = df['true_range'].rolling(window=ma_period).mean()
        
        # 计算ATR变化率
        df['atr_change'] = df['atr'].pct_change() * 100
        
        # 计算振幅的历史百分位
        df = self.calculate_historic_percentiles(df, 'amplitude', window)
        
        # 计算各百分位线
        for percentile in percentiles:
            col_name = f'amplitude_p{percentile}'
            df[col_name] = np.nan
            
            for i in range(window, len(df)):
                hist_values = df['amplitude'].iloc[i-window:i].dropna()
                if len(hist_values) > 0:
                    df.loc[df.index[i], col_name] = np.percentile(hist_values, percentile)
        
        # 计算振幅Z分数
        df['amplitude_zscore'] = np.nan
        for i in range(window, len(df)):
            hist_values = df['amplitude'].iloc[i-window:i].dropna()
            if len(hist_values) > 0:
                mean = hist_values.mean()
                std = hist_values.std()
                if std > 0:  # 避免除零
                    current_value = df['amplitude'].iloc[i]
                    df.loc[df.index[i], 'amplitude_zscore'] = (current_value - mean) / std
        
        return df
        
    def calculate_enhanced_open_mid_diff(self, df, ma_period=5, window=20, percentiles=[20, 50, 80]):
        """
        计算增强的中间价与开盘价差值指标，包括移动平均和历史百分位数
        
        Parameters:
        -----------
        df : pd.DataFrame
            股票数据，需包含'open_mid_diff'列
        ma_period : int
            移动平均的周期，默认5
        window : int
            历史百分位计算的窗口大小，默认20
        percentiles : list
            要计算的百分位数，默认[20, 50, 80]
            
        Returns:
        --------
        pd.DataFrame : 添加了增强中间价与开盘价差值指标的DataFrame
        """
        if 'open_mid_diff' not in df.columns or df.empty:
            return df
        
        # 计算差值的移动平均
        df['open_mid_diff_ma'] = df['open_mid_diff'].rolling(window=ma_period).mean()
        
        # 计算差值的累积和（近N日）
        df['open_mid_diff_cum'] = df['open_mid_diff'].rolling(window=ma_period).sum()
        
        # 计算差值的历史百分位
        df = self.calculate_historic_percentiles(df, 'open_mid_diff', window)
        
        # 计算各百分位线
        for percentile in percentiles:
            col_name = f'open_mid_diff_p{percentile}'
            df[col_name] = np.nan
            
            for i in range(window, len(df)):
                hist_values = df['open_mid_diff'].iloc[i-window:i].dropna()
                if len(hist_values) > 0:
                    df.loc[df.index[i], col_name] = np.percentile(hist_values, percentile)
        
        # 计算差值Z分数
        df['open_mid_diff_zscore'] = np.nan
        for i in range(window, len(df)):
            hist_values = df['open_mid_diff'].iloc[i-window:i].dropna()
            if len(hist_values) > 0:
                mean = hist_values.mean()
                std = hist_values.std()
                if std > 0:  # 避免除零
                    current_value = df['open_mid_diff'].iloc[i]
                    df.loc[df.index[i], 'open_mid_diff_zscore'] = (current_value - mean) / std
        
        return df
        
    def calculate_mpmi(self, df):
        """
        计算中间价动量指标(MPMI, Mid-Price Momentum Indicator)
        类似MACD但以中间价为基础计算
        
        Parameters:
        -----------
        df : pd.DataFrame
            股票数据，需包含'mid_price'列
            
        Returns:
        --------
        pd.DataFrame : 添加了MPMI指标的DataFrame
        """
        if 'mid_price' not in df.columns or df.empty:
            return df
            
        # 计算EMA短期线 (span=12)
        df['ema_short'] = df['mid_price'].ewm(span=12, adjust=False).mean()
        
        # 计算EMA长期线 (span=26)
        df['ema_long'] = df['mid_price'].ewm(span=26, adjust=False).mean()
        
        # 计算MPMI线 (类似MACD线)
        df['MPMI_Line'] = df['ema_short'] - df['ema_long']
        
        # 计算信号线 (9日MPMI的EMA)
        df['MPMI_Signal'] = df['MPMI_Line'].ewm(span=9, adjust=False).mean()
        
        # 计算柱状图 (MPMI线-信号线)
        df['MPMI_Hist'] = df['MPMI_Line'] - df['MPMI_Signal']
        
        # 标记金叉和死叉
        df['MPMI_GoldenCross'] = (df['MPMI_Line'] > df['MPMI_Signal']) & (df['MPMI_Line'].shift(1) <= df['MPMI_Signal'].shift(1))
        df['MPMI_DeathCross'] = (df['MPMI_Line'] < df['MPMI_Signal']) & (df['MPMI_Line'].shift(1) >= df['MPMI_Signal'].shift(1))
        
        return df

    def calculate_star_indicator(self, df):
        """
        计算星星指标：连续三天振幅缩小且第二天和第三天的高低价都在第一天的高低价区间内
        星星颜色根据中间价走势确定：
        - 红色星星：三天中间价持续上涨
        - 绿色星星：三天中间价持续下跌  
        - 黄色星星：三天中间价持平或上下波动
        
        Parameters:
        -----------
        df : pd.DataFrame
            股票数据，需包含'amplitude', 'high', 'low', 'mid_price'列
            
        Returns:
        --------
        pd.DataFrame : 添加了星星指标的DataFrame
        """
        if df.empty or len(df) < 3:
            df['star_indicator'] = None
            return df
            
        # 检查必需的列是否存在
        required_cols = ['amplitude', 'high', 'low', 'mid_price']
        if not all(col in df.columns for col in required_cols):
            df['star_indicator'] = None
            return df
        
        # 初始化星星指标列
        df['star_indicator'] = None
        
        # 从第三天开始检查（需要前两天的数据）
        for i in range(2, len(df)):
            # 获取连续三天的数据
            day1_idx = i - 2
            day2_idx = i - 1  
            day3_idx = i
            
            # 检查条件1：振幅连续三天缩小
            amp1 = df.iloc[day1_idx]['amplitude']
            amp2 = df.iloc[day2_idx]['amplitude']
            amp3 = df.iloc[day3_idx]['amplitude']
            
            amplitude_shrinking = amp1 > amp2 > amp3
            
            # 检查条件2：第二天和第三天的最高价和最低价都在第一天的最高价和最低价区间内
            high1 = df.iloc[day1_idx]['high']
            low1 = df.iloc[day1_idx]['low']
            
            high2 = df.iloc[day2_idx]['high']
            low2 = df.iloc[day2_idx]['low']
            high3 = df.iloc[day3_idx]['high']
            low3 = df.iloc[day3_idx]['low']
            
            day2_in_range = low1 <= low2 <= high1 and low1 <= high2 <= high1
            day3_in_range = low1 <= low3 <= high1 and low1 <= high3 <= high1
            
            price_in_range = day2_in_range and day3_in_range
            
            # 如果满足两个条件，确定星星颜色
            if amplitude_shrinking and price_in_range:
                mid1 = df.iloc[day1_idx]['mid_price']
                mid2 = df.iloc[day2_idx]['mid_price']
                mid3 = df.iloc[day3_idx]['mid_price']
                
                # 判断中间价走势
                if mid1 < mid2 < mid3:  # 持续上涨
                    star_color = 'red'
                elif mid1 > mid2 > mid3:  # 持续下跌
                    star_color = 'green'
                else:  # 持平或波动
                    star_color = 'yellow'
                
                # 将星星标记在第三天（当前检查的这一天）
                df.loc[df.index[day3_idx], 'star_indicator'] = star_color
        
        return df
