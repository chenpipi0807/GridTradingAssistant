import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
from datetime import datetime
import dash_bootstrap_components as dbc
from dash import html, dcc
import numpy as np

class Visualizer:
    def __init__(self):
        """初始化可视化器"""
        pass
        
    def create_stock_chart(self, df, title=None, show_kline=False):
        """
        创建股票图表，包含中间价、振幅和成交量，显示增强振幅指标和中间价-开盘价差值指标
        
        Args:
            df: 股票数据框架
            title: 图表标题
            show_kline: 是否显示K线图（默认为否）
        
        Returns:
            plotly图表对象
        """
        # 检查是否有数据
        if df is None or df.empty:
            return go.Figure()
            
        # 过滤非交易日的数据
        df = df[df['volume'] > 0].copy()
        
        # 通过判断当前时间决定是否显示当天数据
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        
        # 确保日期列是日期格式
        if 'date' in df.columns and isinstance(df['date'].iloc[0], str):
            df['date'] = pd.to_datetime(df['date'])
        
        # 如果当前时间小于15:00，且数据中包含当天数据，则去除当天数据
        if now.hour < 15 and current_date in df['date'].dt.strftime("%Y-%m-%d").values:
            df = df[df['date'].dt.strftime("%Y-%m-%d") < current_date]
            
        # 重要优化：将真实日期保存为显示用途，但在X轴上使用序号，这样日期之间不会有空隙
        df['display_date'] = df['date']  # 保存真实日期用于显示
        df['date'] = range(len(df))  # 将日期列替换为序号，确保连续性
        
        # 所有情况下始终都显示成交量、增强振幅指标、中间价-开盘价差值指标和MPMI指标
        # 根据参数决定子图行数及高度
        if show_kline:
            rows = 6  # K线图+中间价重叠, 增强振幅指标, 中间价-开盘价差值, ATR, MPMI, 成交量
            row_heights = [0.36, 0.13, 0.13, 0.13, 0.13, 0.12]  
            subplot_titles = ("", "增强振幅指标(%)", "中间价-开盘价差值(%)", "ATR指标", "MPMI指标", "")  
        else:
            rows = 6  # 中间价, 增强振幅指标, 中间价-开盘价差值, ATR, MPMI, 成交量
            row_heights = [0.36, 0.13, 0.13, 0.13, 0.13, 0.12]  
            subplot_titles = ("", "增强振幅指标(%)", "中间价-开盘价差值(%)", "ATR指标", "MPMI指标", "")
        
        # 创建子图规格，确保每行都支持secondary_y
        specs = []
        for _ in range(rows):
            specs.append([{"secondary_y": True}])
            
        # 创建图表
        fig = make_subplots(
            rows=rows, 
            cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=row_heights,
            subplot_titles=subplot_titles,
            specs=specs
        )
        # 移除主标题，因为我们已经在卡片标题中显示了股票名称和分析类型
        fig.update_layout(title=None)
        
        # 初始化行索引，固定行号分配
        price_row = 1       # 第一行始终显示股价(中间价或K线图+中间价)
        amplitude_row = 2    # 第二行显示振幅指标
        open_mid_diff_row = 3  # 第三行显示中间价-开盘价差值
        atr_row = 4         # 第四行显示ATR指标
        mpmi_row = 5        # 第五行显示MPMI指标
        volume_row = 6      # 第六行显示成交量
        
        # 1. 绘制K线图和中间价在同一行显示
        
        # 添加最高价和最低价曲线作为上下轨
        # 上轨线 - 使用半透明红色表示最高价
        upper_color = 'rgba(255, 99, 71, 0.6)'  # 半透明红色
        # 下轨线 - 使用半透明绿色表示最低价
        lower_color = 'rgba(50, 205, 50, 0.6)'  # 半透明绿色
        
        # 添加最高价上轨线
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['high'],
                mode='lines',
                name="最高价",
                line=dict(width=1.5, color=upper_color, dash='dot'),
                hoverinfo='text',
                hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>最高价: {h:.2f}" 
                          for d, h in zip(df['display_date'], df['high'])],
            ),
            row=price_row, col=1
        )
        
        # 添加最低价下轨线
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['low'],
                mode='lines',
                name="最低价",
                line=dict(width=1.5, color=lower_color, dash='dot'),
                hoverinfo='text',
                hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>最低价: {l:.2f}" 
                          for d, l in zip(df['display_date'], df['low'])],
            ),
            row=price_row, col=1
        )
        
        # 中间价始终使用蓝色，不再根据是否显示K线图而变化
        mid_price_color = 'rgba(30, 144, 255, 0.9)'  # 半透明蓝色
        mid_price_width = 1.5 if show_kline else 2  # K线图模式线条稍细
        
        # 添加中间价线
        hover_data = []
        for i in range(len(df)):
            date_str = df.iloc[i]['display_date'].strftime('%Y-%m-%d')
            mid_price = df.iloc[i]['mid_price']
            open_price = df.iloc[i].get('open', 0)
            close_price = df.iloc[i].get('close', 0)
            high_price = df.iloc[i].get('high', 0)
            low_price = df.iloc[i].get('low', 0)
            amplitude = df.iloc[i].get('amplitude', 0)
            volume = df.iloc[i].get('volume', 0)
            hover_data.append([date_str, mid_price, open_price, close_price, high_price, low_price, amplitude, volume])
        
        hover_template = """
        <b>%{customdata[0]}</b><br>
        中间价: %{customdata[1]:.2f}<br>
        开盘价: %{customdata[2]:.2f}<br>
        收盘价: %{customdata[3]:.2f}<br>
        最高价: %{customdata[4]:.2f}<br>
        最低价: %{customdata[5]:.2f}<br>
        振幅: %{customdata[6]:.2f}%<br>
        成交量: %{customdata[7]:,}
        """
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['mid_price'],
                mode='lines',
                name="中间价",
                line=dict(width=mid_price_width, color=mid_price_color),
                customdata=hover_data,
                hovertemplate=hover_template,
            ),
            row=price_row, col=1
        )      
        # 根据是否启用K线图，添加不同形式的K线图
        # 无论是否启用K线图，都确保有所有必要的列
        required_columns = ['open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in df.columns:
                if col == 'open':
                    df['open'] = df['close']
                elif col == 'high':
                    df['high'] = df['close'] * 1.001
                elif col == 'low':
                    df['low'] = df['close'] * 0.999
                print(f"警告: {col}列不存在，使用计算值替代")
        
        # 处理缺失值
        for col in required_columns:
            if df[col].isna().any():
                df[col] = df[col].fillna(method='ffill').fillna(method='bfill').fillna(0)
                
        # 根据是否显示K线图选择不同的显示方式
        if show_kline:
            # 启用K线图时显示标准蜡烛图
            try:
                fig.add_trace(
                    go.Candlestick(
                        x=df['date'],
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name="K线",
                        increasing=dict(line=dict(color='#E01F54'), fillcolor='rgba(224,31,84,0.6)'),  # 红色上涨半透明
                        decreasing=dict(line=dict(color='#0A8043'), fillcolor='rgba(10,128,67,0.6)'),  # 绿色下跌半透明
                    ),
                    row=price_row, col=1
                )
            except Exception as e:
                print(f"K线图显示错误: {e}")
                # 出错时显示一个简单的线图
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['close'],
                        mode='lines',
                        name="收盘价",
                        line=dict(width=2, color='red'),
                    ),
                    row=price_row, col=1
                )
        else:
            # 默认视图下只显示简单的高低价蓝色柱状图
            # 为每个交易日加入高低价柱状图
            for i in range(len(df)):
                # 为每日数据添加一个简单的高低价柱状图
                fig.add_trace(
                    go.Scatter(
                        x=[df.iloc[i]['date'], df.iloc[i]['date']],
                        y=[df.iloc[i]['low'], df.iloc[i]['high']],
                        mode='lines',
                        line=dict(width=3, color='rgba(30, 144, 255, 0.8)'),
                        showlegend=(i==0),  # 只有第一个在图例中显示
                        name="高低价" if i==0 else None
                    ),
                    row=price_row, col=1
                )
        
        # 中间价已经在前面绘制完成，这里不再重复绘制
        
        # 2.5 添加增强振幅指标图表
        if 'amplitude' in df.columns and 'amplitude_ma' in df.columns:
            # 添加厚线条形图显示原始振幅数据
            colors = []
            for val in df['amplitude']:
                if val >= 0:
                    colors.append('rgba(255, 99, 71, 0.7)')  # 红色为正值
                else:
                    colors.append('rgba(50, 205, 50, 0.7)')  # 绿色为负值
            
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['amplitude'],
                    name="振幅(%)",
                    marker_color=colors,
                    opacity=0.7,
                    customdata=hover_data,
                    hovertemplate="<b>%{customdata[0]}</b><br>"
                                 "振幅: %{y:.2f}%<br>"
                ),
                row=amplitude_row, col=1
            )
            
            # 添加振幅移动平均线
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['amplitude_ma'],
                    mode='lines',
                    name="振幅移动平均",
                    line=dict(width=2, color='rgba(30, 144, 255, 0.8)'),
                    hoverinfo='text',
                    hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>振幅MA: {v:.2f}%" 
                              for d, v in zip(df['display_date'], df['amplitude_ma'])],
                ),
                row=amplitude_row, col=1
            )
            
            # 如果有振幅百分位等级数据，添加百分位线
            if 'amplitude_p75' in df.columns and 'amplitude_p90' in df.columns:
                # 添加P75百分位线
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['amplitude_p75'],
                        mode='lines',
                        name="75百分位",
                        line=dict(width=1.5, color='rgba(255, 165, 0, 0.6)', dash='dot'),
                    ),
                    row=amplitude_row, col=1
                )
                
                # 添加P90百分位线
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['amplitude_p90'],
                        mode='lines',
                        name="90百分位",
                        line=dict(width=1.5, color='rgba(255, 0, 0, 0.6)', dash='dot'),
                    ),
                    row=amplitude_row, col=1
                )
            
            # 添加异常振幅标记（如果有异常数据）
            if 'amplitude_zscore' in df.columns:
                abnormal_dates = df[df['amplitude_zscore'] > 2]['date']  # Z分数超过2的点作为异常点
                abnormal_values = df.loc[df['amplitude_zscore'] > 2, 'amplitude']
                
                if not abnormal_dates.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=abnormal_dates,
                            y=abnormal_values,
                            mode='markers',
                            name="异常振幅",
                            marker=dict(symbol='circle', size=9, color='purple', line=dict(width=1, color='black')),
                            hoverinfo='text',
                            hovertext=[f"异常振幅: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>"
                                      f"振幅: {v:.2f}%<br>Z分数: {z:.2f}" 
                                     for d, v, z in zip(df.loc[df['amplitude_zscore'] > 2, 'display_date'], 
                                                     abnormal_values, 
                                                     df.loc[df['amplitude_zscore'] > 2, 'amplitude_zscore'])],
                        ),
                        row=amplitude_row, col=1
                    )
            
            # 添加星星指标（振幅缩小且价格区间收窄的标记）
            if 'star_indicator' in df.columns:
                # 分别处理红色、绿色和黄色星星
                for star_color in ['red', 'green', 'yellow']:
                    star_data = df[df['star_indicator'] == star_color]
                    if not star_data.empty:
                        # 确定星星的颜色和名称
                        if star_color == 'red':
                            marker_color = 'red'
                            star_name = '红色星星（中间价上涨）'
                        elif star_color == 'green':
                            marker_color = 'green'
                            star_name = '绿色星星（中间价下跌）'
                        else:  # yellow
                            marker_color = 'gold'
                            star_name = '黄色星星（中间价持平）'
                        
                        # 添加星星标记到振幅图上
                        fig.add_trace(
                            go.Scatter(
                                x=star_data['date'],
                                y=star_data['amplitude'],
                                mode='markers',
                                name=star_name,
                                marker=dict(
                                    symbol='star',
                                    size=12,
                                    color=marker_color,
                                    line=dict(width=1, color='black')
                                ),
                                hoverinfo='text',
                                hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>"
                                          f"振幅: {a:.2f}%<br>"
                                          f"星星类型: {star_name}<br>"
                                          f"说明: 连续3天振幅缩小且价格区间收窄" 
                                         for d, a in zip(star_data['display_date'], star_data['amplitude'])],
                            ),
                            row=amplitude_row, col=1
                        )
            
            # 设置振幅图表Y轴标题
            fig.update_yaxes(
                title_text="振幅(%)",
                title_standoff=0,
                title_font=dict(size=14),
                side="left",
                row=amplitude_row, col=1
            )
        
        # 3. 添加中间价-开盘价差值图表 (增强版)
        if 'open_mid_diff' in df.columns:
            # 为差值百分比创建柱状图，使用红绿颜色区分正负值
            colors = []
            for val in df['open_mid_diff']:
                if val >= 0:
                    colors.append('rgba(255, 99, 71, 0.7)')  # 红色为正值（开盘价高于中间价）
                else:
                    colors.append('rgba(50, 205, 50, 0.7)')  # 绿色为负值（开盘价低于中间价）
            
            # 添加柱状图
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['open_mid_diff'],
                    name="中间价-开盘价差值(%)",
                    marker_color=colors,
                    opacity=0.9,
                    customdata=hover_data,
                    hovertemplate="<b>%{customdata[0]}</b><br>"
                                 "开盘价: %{customdata[2]:.2f}<br>"
                                 "中间价: %{customdata[1]:.2f}<br>"
                                 "差值: %{y:.2f}%<br>"
                ),
                row=open_mid_diff_row, col=1
            )
            
            # 添加移动平均线 (如果存在)
            if 'open_mid_diff_ma' in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['open_mid_diff_ma'],
                        mode='lines',
                        name="差值移动平均",
                        line=dict(width=2, color='rgba(30, 144, 255, 0.8)'),
                        hoverinfo='text',
                        hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>差值 MA: {v:.2f}%" 
                                  for d, v in zip(df['display_date'], df['open_mid_diff_ma'])],
                    ),
                    row=open_mid_diff_row, col=1
                )
            
            # 添加百分位线 (如果存在)
            if 'open_mid_diff_p25' in df.columns and 'open_mid_diff_p75' in df.columns:
                # 添加P25百分位线
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['open_mid_diff_p25'],
                        mode='lines',
                        name="25百分位",
                        line=dict(width=1.5, color='rgba(0, 128, 0, 0.6)', dash='dot'),
                    ),
                    row=open_mid_diff_row, col=1
                )
                
                # 添加P75百分位线
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['open_mid_diff_p75'],
                        mode='lines',
                        name="75百分位",
                        line=dict(width=1.5, color='rgba(255, 165, 0, 0.6)', dash='dot'),
                    ),
                    row=open_mid_diff_row, col=1
                )
            
            # 添加异常差值标记（如果有Z分数列）
            if 'open_mid_diff_zscore' in df.columns:
                # 正向异常（正Z分数超过2）
                pos_abnormal_dates = df[df['open_mid_diff_zscore'] > 2]['date']
                pos_abnormal_values = df.loc[df['open_mid_diff_zscore'] > 2, 'open_mid_diff']
                
                # 负向异常（负Z分数超过2）
                neg_abnormal_dates = df[df['open_mid_diff_zscore'] < -2]['date']
                neg_abnormal_values = df.loc[df['open_mid_diff_zscore'] < -2, 'open_mid_diff']
                
                if not pos_abnormal_dates.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=pos_abnormal_dates,
                            y=pos_abnormal_values,
                            mode='markers',
                            name="正向异常差值",
                            marker=dict(symbol='triangle-up', size=9, color='red', line=dict(width=1, color='black')),
                            hoverinfo='text',
                            hovertext=[f"正向异常: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>"
                                      f"差值: {v:.2f}%<br>Z分数: {z:.2f}" 
                                      for d, v, z in zip(df.loc[df['open_mid_diff_zscore'] > 2, 'display_date'], 
                                                      pos_abnormal_values, 
                                                      df.loc[df['open_mid_diff_zscore'] > 2, 'open_mid_diff_zscore'])],
                        ),
                        row=open_mid_diff_row, col=1
                    )
                
                if not neg_abnormal_dates.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=neg_abnormal_dates,
                            y=neg_abnormal_values,
                            mode='markers',
                            name="负向异常差值",
                            marker=dict(symbol='triangle-down', size=9, color='green', line=dict(width=1, color='black')),
                            hoverinfo='text',
                            hovertext=[f"负向异常: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>"
                                      f"差值: {v:.2f}%<br>Z分数: {z:.2f}" 
                                      for d, v, z in zip(df.loc[df['open_mid_diff_zscore'] < -2, 'display_date'], 
                                                      neg_abnormal_values, 
                                                      df.loc[df['open_mid_diff_zscore'] < -2, 'open_mid_diff_zscore'])],
                        ),
                        row=open_mid_diff_row, col=1
                    )
            
            # 添加零线参考线
            fig.add_shape(
                type="line",
                x0=df['date'].min(),
                y0=0,
                x1=df['date'].max(),
                y1=0,
                line=dict(color="rgba(0,0,0,0.3)", width=1, dash="dash"),
                row=open_mid_diff_row, col=1
            )
            
        # 4. 添加ATR指标图表
        if 'atr' in df.columns:
            # 添加ATR线
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['atr'],
                    mode='lines',
                    name="ATR",
                    line=dict(width=2, color='rgba(255, 140, 0, 0.8)'),  # 深橙色
                    hoverinfo='text',
                    hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>ATR: {v:.4f}" 
                              for d, v in zip(df['display_date'], df['atr'])],
                ),
                row=atr_row, col=1
            )
            
            # 添加ATR变化率（如果存在）
            if 'atr_change_rate' in df.columns:
                # 为ATR变化率创建柱状图，使用红绿颜色区分正负值
                colors = []
                for val in df['atr_change_rate']:
                    if val >= 0:
                        colors.append('rgba(255, 99, 71, 0.7)')  # 红色为正值（ATR增加）
                    else:
                        colors.append('rgba(50, 205, 50, 0.7)')  # 绿色为负值（ATR减少）
                
                fig.add_trace(
                    go.Bar(
                        x=df['date'],
                        y=df['atr_change_rate'],
                        name="ATR变化率(%)",
                        marker_color=colors,
                        opacity=0.7,
                        hoverinfo='text',
                        hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>ATR变化率: {v:.2f}%" 
                                  for d, v in zip(df['display_date'], df['atr_change_rate'])],
                    ),
                    row=atr_row, col=1,
                    secondary_y=True
                )
                
                # 设置次坐标轴标题
                fig.update_yaxes(
                    title_text="ATR变化率(%)",
                    title_standoff=0,
                    title_font=dict(size=14),
                    side="right",
                    row=atr_row, col=1,
                    secondary_y=True
                )
            
            # 设置ATR图表Y轴标题
            fig.update_yaxes(
                title_text="ATR",
                title_standoff=0,
                title_font=dict(size=14),
                side="left",
                row=atr_row, col=1
            )
            
            # 设置图表Y轴标题
            fig.update_yaxes(
                title_text="差值(%)",
                title_standoff=0,
                title_font=dict(size=14),
                side="left",
                row=open_mid_diff_row, col=1
            )
        
        # 5. 添加MPMI指标图表
        if 'MPMI_Line' in df.columns and 'MPMI_Signal' in df.columns and 'MPMI_Hist' in df.columns:
            # MPMI柱状图 (类似MACD)
            colors = []
            for val in df['MPMI_Hist']:
                if val >= 0:
                    colors.append('rgba(255, 99, 71, 0.7)')  # 红色为正值
                else:
                    colors.append('rgba(50, 205, 50, 0.7)')  # 绿色为负值
            
            # 添加MPMI柱状图
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['MPMI_Hist'],
                    name="MPMI柱状图",
                    marker_color=colors,
                    opacity=0.7,
                    hoverinfo='text',
                    hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>MPMI柱状图: {v:.4f}" 
                             for d, v in zip(df['display_date'], df['MPMI_Hist'])],
                ),
                row=mpmi_row, col=1
            )
            
            # 添加MPMI线
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['MPMI_Line'],
                    mode='lines',
                    name="MPMI线",
                    line=dict(width=2, color='rgba(30, 144, 255, 0.8)'),  # 蓝色
                    hoverinfo='text',
                    hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>MPMI线: {v:.4f}" 
                              for d, v in zip(df['display_date'], df['MPMI_Line'])],
                ),
                row=mpmi_row, col=1
            )
            
            # 添加信号线
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['MPMI_Signal'],
                    mode='lines',
                    name="MPMI信号线",
                    line=dict(width=2, color='rgba(255, 165, 0, 0.8)'),  # 橙色
                    hoverinfo='text',
                    hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>MPMI信号线: {v:.4f}" 
                              for d, v in zip(df['display_date'], df['MPMI_Signal'])],
                ),
                row=mpmi_row, col=1
            )
            
            # 标记金叉和死叉
            if 'MPMI_GoldenCross' in df.columns and 'MPMI_DeathCross' in df.columns:
                # 添加金叉标记
                golden_cross_dates = df[df['MPMI_GoldenCross']]['date']
                golden_cross_values = df.loc[df['MPMI_GoldenCross'], 'MPMI_Line']
                
                if not golden_cross_dates.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=golden_cross_dates,
                            y=golden_cross_values,
                            mode='markers',
                            name="MPMI金叉",
                            marker=dict(symbol='triangle-up', size=12, color='gold', line=dict(width=1, color='black')),
                            hoverinfo='text',
                            hovertext=[f"金叉信号: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>MPMI线: {v:.4f}" 
                                     for d, v in zip(df.loc[df['MPMI_GoldenCross'], 'display_date'], golden_cross_values)],
                        ),
                        row=mpmi_row, col=1
                    )
                
                # 添加死叉标记
                death_cross_dates = df[df['MPMI_DeathCross']]['date']
                death_cross_values = df.loc[df['MPMI_DeathCross'], 'MPMI_Line']
                
                if not death_cross_dates.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=death_cross_dates,
                            y=death_cross_values,
                            mode='markers',
                            name="MPMI死叉",
                            marker=dict(symbol='triangle-down', size=12, color='black', line=dict(width=1, color='white')),
                            hoverinfo='text',
                            hovertext=[f"死叉信号: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>MPMI线: {v:.4f}" 
                                     for d, v in zip(df.loc[df['MPMI_DeathCross'], 'display_date'], death_cross_values)],
                        ),
                        row=mpmi_row, col=1
                    )
            
            # 添加零线参考线
            fig.add_shape(
                type="line",
                x0=df['date'].min(),
                y0=0,
                x1=df['date'].max(),
                y1=0,
                line=dict(color="rgba(0,0,0,0.3)", width=1, dash="dash"),
                row=mpmi_row, col=1
            )
            
            # 设置MPMI图表Y轴标题
            fig.update_yaxes(
                title_text="MPMI",
                title_standoff=0,
                title_font=dict(size=14),
                side="left",
                row=mpmi_row, col=1
            )
        
        # 3. 添加振幅图表 - 统一使用半透明蓝色
        if 'amplitude' in df.columns:
            # 所有情况下都使用半透明蓝色
            colors = ['rgba(30, 144, 255, 0.6)'] * len(df)  # 半透明蓝色
            
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['amplitude'],
                    name="日振幅(%)",  # 恢复图例标签
                    marker_color=colors,
                    opacity=0.9 if show_kline else 1,  # K线图模式下的透明度
                    customdata=hover_data,
                    hovertemplate=hover_template,
                ),
                row=amplitude_row, col=1
            )
        
        # 4. 添加成交量图表
        if 'volume' in df.columns:
            # 计算涨跌颜色
            if 'open' in df.columns and 'close' in df.columns:
                vol_colors = ['#E01F54' if row['close'] >= row['open'] else '#0A8043' for _, row in df.iterrows()]
            else:
                vol_colors = ['#7D5BA6'] * len(df)  # 默认紫色
            
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['volume'],
                    name="成交量",  # 恢复成交量图例标签
                    marker_color=vol_colors,
                    customdata=hover_data,
                    hovertemplate=hover_template,
                ),
                row=volume_row, col=1
            )
        
        # 优化图表布局
        fig.update_layout(
            title=None,  # 移除标题，因为我们已经在卡片标题中显示了股票名称和分析类型
            xaxis_title=None,
            yaxis_title="价格(元)",
            xaxis_rangeslider_visible=False,  # 隐藏K线图下方的滑动条
            plot_bgcolor='white',  # 白色背景
            paper_bgcolor='white',
            height=900,  # 增加高度以容纳所有子图包括MPMI
            margin=dict(l=80, r=50, t=30, b=50),  # 减小顶部间距
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # 给振幅和成交量图表添加左侧标题
        fig.update_yaxes(
            title_text="振幅(%)",
            title_standoff=0,  # 标题距离轴的距离
            title_font=dict(size=14),
            side="left",  # 将标题放在左侧
            row=amplitude_row, col=1
        )
        
        fig.update_yaxes(
            title_text="成交量",  # 恢复成交量标签
            title_standoff=0,
            title_font=dict(size=14),
            side="left",
            row=volume_row, col=1
        )
        
        # 优化X轴日期显示 - 使用统一序号做坐标，但显示真实日期标签
        
        # 添加鼠标悬停显示详情的功能
        # 为所有图表元素设置悬停显示格式
        hover_template = """
        <b>%{customdata[0]}</b><br>
        中间价: %{customdata[1]:.2f}<br>
        开盘价: %{customdata[2]:.2f}<br>
        收盘价: %{customdata[3]:.2f}<br>
        最高价: %{customdata[4]:.2f}<br>
        最低价: %{customdata[5]:.2f}<br>
        振幅: %{customdata[6]:.2f}%<br>
        成交量: %{customdata[7]:,}
        """
        
        # 准备悬停显示数据
        hover_data = []
        for i in range(len(df)):
            date_str = df.iloc[i]['display_date'].strftime('%Y-%m-%d')
            mid_price = df.iloc[i]['mid_price']
            open_price = df.iloc[i].get('open', 0)
            close_price = df.iloc[i].get('close', 0)
            high_price = df.iloc[i].get('high', 0)
            low_price = df.iloc[i].get('low', 0)
            amplitude = df.iloc[i].get('amplitude', 0)
            volume = df.iloc[i].get('volume', 0)
            open_mid_diff = df.iloc[i].get('open_mid_diff', 0)
            hover_data.append([date_str, mid_price, open_price, close_price, high_price, low_price, amplitude, volume, open_mid_diff])
        
        # 对于前两个子图，显示较少日期
        few_dates_step = max(1, len(df) // 8)  # 每8个数据点显示一个日期
        few_tick_texts = []
        few_tick_values = []
        
        # 使用序号做坐标位置，但显示真实日期
        for i in range(len(df)):
            if i % few_dates_step == 0 or i == len(df) - 1:
                few_tick_texts.append(df.iloc[i]['display_date'].strftime('%m-%d'))
                few_tick_values.append(i)  # 使用序号作为坐标值
        
        # 对于最后一个子图（底部），显示更多日期
        many_dates_step = max(1, len(df) // 20)  # 每4个数据点显示一个日期
        many_tick_texts = []
        many_tick_values = []
        
        for i in range(len(df)):
            if i % many_dates_step == 0 or i == len(df) - 1:
                many_tick_texts.append(df.iloc[i]['display_date'].strftime('%m-%d'))
                many_tick_values.append(i)  # 使用序号作为坐标值
        
        # 对非底部子图应用较少的日期
        for i in range(1, rows):
            fig.update_xaxes(
                tickangle=30,  # 倾斜标签
                tickmode='array',
                tickvals=few_tick_values,  # 序号做坐标
                ticktext=few_tick_texts,   # 真实日期做标签
                row=i, col=1,
                showticklabels=(i==rows-1)  # 只在最后一个子图上显示标签
            )
        
        # 对底部子图应用更多的日期
        fig.update_xaxes(
            tickangle=30,
            tickmode='array',
            tickvals=many_tick_values,  # 序号做坐标
            ticktext=many_tick_texts,   # 真实日期做标签
            row=rows, col=1
        )
        
        # 设置Y轴格式
        fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)', row=price_row, col=1)  # 中间价/K线图Y轴
        fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)', row=amplitude_row, col=1)  # 振幅Y轴
        
        # 添加振幅参考线
        for level in [2, 4, 6, 8]:
            fig.add_shape(
                type="line",
                x0=df['date'].min(),
                y0=level,
                x1=df['date'].max(),
                y1=level,
                line=dict(color="rgba(0,0,0,0.2)", width=1, dash="dot"),
                row=amplitude_row, col=1
            )
        
        # 创建图表组件
        return dcc.Graph(
            figure=fig,
            id="stock-chart",
            config={
                'displayModeBar': True,
                'scrollZoom': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d']
            }
        )
        
    def create_data_table(self, df):
        """创建展示数据的表格"""
        if df.empty:
            return html.Div("无数据表格")
        
        # 选择并格式化要显示的列
        display_cols = [
            'date', 'open', 'high', 'low', 'close', 'mid_price', 'open_mid_diff',
            'volume', 'amplitude', 'MPMI_Signal', 'MPMI_Line'
        ]
        
        # 确保所有列都存在
        display_cols = [col for col in display_cols if col in df.columns]
        
        # 选择最后30行数据
        df_display = df.tail(30).copy()
        
        # 创建数据表格
        df_display = df_display[display_cols]
        
        # 格式化日期
        df_display['date'] = df_display['date'].astype(str)
        
        # 格式化数值列
        for col in df_display.columns:
            if col != 'date' and col not in ['MPMI_Signal']:
                df_display[col] = df_display[col].round(2)
                
        # 更新列名
        column_names = {
            'date': '日期',
            'open': '开盘价',
            'high': '最高价',
            'low': '最低价',
            'close': '收盘价',
            'mid_price': '中间价',
            'open_mid_diff': '开盘价与中间价差值(%)',
            'volume': '成交量',
            'amplitude': '振幅(%)',
            'MPMI_Signal': '信号',
            'MPMI_Line': 'MPMI线'
        }
        
        # 过滤存在的列
        cols_to_show = [col for col in display_cols if col in df.columns]
        
        # 创建一个新的DataFrame，只包含要显示的列
        table_df = df[cols_to_show].copy()
        
        # 重命名列
        table_df.columns = [column_names.get(col, col) for col in cols_to_show]
        
        # 格式化数值
        for col in table_df.columns:
            if col == '日期':
                continue  # 跳过日期列
            elif col == '成交量':
                # 成交量显示为整数
                table_df[col] = table_df[col].apply(lambda x: f"{int(x):,}")
            elif col == '成交额':
                # 成交额保留两位小数并加上千位分隔符
                table_df[col] = table_df[col].apply(lambda x: f"{x:,.2f}")
            else:
                # 其他数值保留两位小数
                table_df[col] = table_df[col].round(2)
        
        # 限制显示的行数，避免表格过长
        table_df = table_df.tail(30)  # 显示最近的30行数据
        
        # 创建表格组件
        table = dbc.Table.from_dataframe(
            table_df, 
            striped=True, 
            bordered=True,
            hover=True,
            responsive=True,
            className="table-sm"
        )
        
        return html.Div([
            html.H5("近期数据", className="text-center my-3"),
            table,
            self.create_summary_cards(df)  # 创建摘要卡片
        ])
    
    def create_summary_cards(self, df, strategy_results=None):
        """创建数据摘要卡片、使用较小字体和紧凑布局"""
        if df.empty:
            return html.Div("无数据摘要")
        
        cards = []
        
        # 最新价格卡片
        latest_data = df.iloc[-1]
        latest_price = latest_data['close']
        latest_date = latest_data['date']
        # 如果存在前一天数据，计算价格变化
        if len(df) > 1:
            prev_data = df.iloc[-2]
            price_change = latest_price - prev_data['close']
            price_change_percent = price_change / prev_data['close'] * 100
            price_color = "text-danger" if price_change >= 0 else "text-success"
            diff_sign = "+" if price_change > 0 else ""
        else:
            price_change = 0
            price_change_percent = 0
            price_color = "text-primary"
            diff_sign = ""

        cards.append(
            dbc.Card(
                dbc.CardBody([
                    html.H5("最新价格", className="card-title small fw-bold mb-1", style={"fontSize": "12px"}),
                    html.H3(f"¥{latest_price:.2f}", className=f"card-text {price_color} my-1", style={"fontSize": "18px"}),
                    html.P([
                        f"{diff_sign}{price_change:.2f} ({diff_sign}{price_change_percent:.2f}%)", 
                        html.Span(" vs 昨收盘", className="ms-1 small text-muted")
                    ], className=f"card-text {price_color} mb-1 small", style={"fontSize": "11px"}),
                    html.P(["日期: ", html.Strong(f"{latest_date}")], className="card-text text-muted mb-0 small", style={"fontSize": "10px"}),
                ], className="p-2"),
                className="m-2 shadow"
            )
        )
        
        # 振幅统计卡片
        avg_amplitude = df['amplitude'].mean()
        max_amplitude_idx = df['amplitude'].idxmax()
        max_amplitude = df.loc[max_amplitude_idx, 'amplitude']
        max_amplitude_date = df.loc[max_amplitude_idx, 'date']
        
        cards.append(
            dbc.Card(
                dbc.CardBody([
                    html.H5("振幅统计", className="card-title small fw-bold mb-1", style={"fontSize": "12px"}),
                    html.H3(f"{avg_amplitude:.2f}%", className="card-text text-info my-1", style={"fontSize": "18px"}),
                    html.P(f"平均振幅", className="card-text text-muted mb-1 small", style={"fontSize": "11px"}),
                    html.P([
                        f"最大振幅: {max_amplitude:.2f}% (",
                        html.Span(f"{max_amplitude_date}", className="font-weight-bold"),
                        ")"
                    ], className="card-text mb-0 small", style={"fontSize": "10px"}),
                ], className="p-2"),
                className="m-2 shadow"
            )
        )
        
        # 中间价通道卡片
        if 'mid_price' in df.columns:
            latest_mid = latest_data['mid_price']
            cards.append(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("中间价", className="card-title small fw-bold mb-1", style={"fontSize": "12px"}),
                        html.H3(f"¥{latest_mid:.2f}", className="card-text text-success my-1", style={"fontSize": "18px"}),
                    ], className="p-2"),
                    className="m-2 shadow"
                )
            )
        
        # 开盘价与中间价差值卡片
        if 'open_mid_diff' in df.columns:
            latest_open_mid_diff = latest_data['open_mid_diff']
            avg_open_mid_diff = df['open_mid_diff'].mean()
            
            # 确定颜色：正值为红色，负值为绿色
            diff_color = "text-danger" if latest_open_mid_diff >= 0 else "text-success"
            diff_sign = "+" if latest_open_mid_diff > 0 else ""
            
            cards.append(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("开盘价与中间价差值", className="card-title small fw-bold mb-1", style={"fontSize": "12px"}),
                        html.H3(f"{diff_sign}{latest_open_mid_diff:.2f}%", className=f"card-text {diff_color} my-1", style={"fontSize": "18px"}),
                        html.P(f"平均差值: {avg_open_mid_diff:.2f}%", className="card-text text-muted mb-0 small", style={"fontSize": "10px"}),
                    ], className="p-2"),
                    className="m-2 shadow"
                )
            )
        
        # 将卡片排列成一行
        return html.Div(
            dbc.Row([dbc.Col(card, width=12//len(cards)) for card in cards]),
            className="mb-4"
        )
    
    def create_strategy_chart(self, df, strategy_results):
        """创建策略回测图表"""
        if df.empty:
            return html.Div("无回测数据")
        
        # 创建图表
        fig = go.Figure()
        
        # 添加价格曲线
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['close'],
                mode='lines',
                name="收盘价",
                line=dict(color='rgba(100, 100, 100, 0.8)', width=2)
            )
        )
        
        # 添加策略相关内容
        if strategy_results:
            # 这里可以添加策略特定的可视化
            pass
        
        return dcc.Graph(figure=fig, id='strategy-chart')
