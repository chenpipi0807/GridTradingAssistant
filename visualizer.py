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
        创建股票图表，包含中间价、振幅和成交量，始终显示MPMI指标
        
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
        
        # 所有情况下始终都显示成交量和MPMI指标
        # 根据参数决定子图行数及高度
        # MPMI始终显示为第二行
        # 新增开盘价与中间价差值图表
        if show_kline:
            rows = 5  # K线图+中间价重叠, MPMI指标, 开盘价与中间价差值, 振幅, 成交量
            row_heights = [0.4, 0.15, 0.15, 0.15, 0.15]  
            subplot_titles = ("", "中间价动量指标(MPMI)", "开盘价与中间价差值(%)", "", "")  
        else:
            rows = 5  # 中间价, MPMI指标, 开盘价与中间价差值, 振幅, 成交量
            row_heights = [0.4, 0.15, 0.15, 0.15, 0.15]  
            subplot_titles = ("", "中间价动量指标(MPMI)", "开盘价与中间价差值(%)", "", "")  
        
        # 定义show_mpmi变量为True，保证MPMI始终显示
        show_mpmi = True
        
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
        
        # 初始化行索引，根据子图数量调整行号
        price_row = 1      # 第一行始终显示股价(中间价或K线图+中间价)
        
        # 根据是否显示MPMI来调整其他行
        if show_mpmi:
            mpmi_row = 2       # 如果显示MPMI，它在第二行
            open_mid_diff_row = 3  # 开盘价与中间价差值在第三行
            amplitude_row = 4   # 振幅移到第四行
            volume_row = 5      # 成交量移到第五行
        else:
            open_mid_diff_row = 2  # 开盘价与中间价差值在第二行
            amplitude_row = 3   # 振幅在第三行
            volume_row = 4      # 成交量在第四行
        
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
        
        # 2.5 如果启用MPMI指标，添加MPMI指标图表
        if show_mpmi and 'mpmi' in df.columns and 'mpmi_signal' in df.columns and 'mpmi_hist' in df.columns:
            # 添加MPMI线(类似MACD的DIF线)
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['mpmi'],
                    mode='lines',
                    name="MPMI线",
                    line=dict(width=3.0, color='rgb(0, 255, 0)'),  # 荧光绿
                    hoverinfo='text',
                    hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>MPMI线: {v:.4f}" 
                              for d, v in zip(df['display_date'], df['mpmi'])],
                ),
                row=mpmi_row, col=1
            )
            
            # 添加信号线(类似MACD的DEA线)
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['mpmi_signal'],
                    mode='lines',
                    name="信号线",
                    line=dict(width=3.0, color='rgb(255, 255, 0)'),  # 荧光黄
                    hoverinfo='text',
                    hovertext=[f"日期: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}<br>信号线: {v:.4f}" 
                              for d, v in zip(df['display_date'], df['mpmi_signal'])],
                ),
                row=mpmi_row, col=1
            )
            
            # 添加柱状图 - 使用红绿颜色区分正负值
            colors = []
            for val in df['mpmi_hist']:
                if val >= 0:
                    colors.append('rgba(255, 99, 71, 0.7)')  # 红色为正值
                else:
                    colors.append('rgba(50, 205, 50, 0.7)')  # 绿色为负值
                    
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['mpmi_hist'],
                    name="MPMI柱状图",
                    marker_color=colors,
                    opacity=0.7,
                ),
                row=mpmi_row, col=1
            )
            
            # 添加金叉和银叉标记
            golden_cross_dates = df[df['mpmi_golden_cross'] == True]['date']
            golden_cross_values = df.loc[df['mpmi_golden_cross'] == True, 'mpmi']
            
            death_cross_dates = df[df['mpmi_death_cross'] == True]['date']
            death_cross_values = df.loc[df['mpmi_death_cross'] == True, 'mpmi']
            
            # 添加金叉标记(上穿)
            if not golden_cross_dates.empty:
                fig.add_trace(
                    go.Scatter(
                        x=golden_cross_dates,
                        y=golden_cross_values,
                        mode='markers',
                        name="金叉",
                        marker=dict(symbol='star', size=10, color='gold', line=dict(width=1, color='black')),
                        hoverinfo='text',
                        hovertext=[f"金叉: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}" 
                                  for d in df.loc[df['mpmi_golden_cross'] == True, 'display_date']],
                    ),
                    row=mpmi_row, col=1
                )
            
            # 添加银叉标记(下穿)
            if not death_cross_dates.empty:
                fig.add_trace(
                    go.Scatter(
                        x=death_cross_dates,
                        y=death_cross_values,
                        mode='markers',
                        name="银叉",
                        marker=dict(symbol='cross', size=10, color='silver', line=dict(width=1, color='black')),
                        hoverinfo='text',
                        hovertext=[f"银叉: {d.strftime('%Y-%m-%d') if isinstance(d, pd.Timestamp) else d}" 
                                  for d in df.loc[df['mpmi_death_cross'] == True, 'display_date']],
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
        
        # 3. 添加开盘价与中间价差值图表
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
                    name="开盘价与中间价差值(%)",
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
            
            # 设置图表Y轴标题
            fig.update_yaxes(
                title_text="差值(%)",
                title_standoff=0,
                title_font=dict(size=14),
                side="left",
                row=open_mid_diff_row, col=1
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
            title={
                'text': title or "股票价格分析",
                'font': dict(size=18),
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title=None,
            yaxis_title="价格(元)",
            xaxis_rangeslider_visible=False,  # 隐藏K线图下方的滑动条
            plot_bgcolor='white',  # 白色背景
            paper_bgcolor='white',
            height=800,  # 增加高度以容纳所有子图
            margin=dict(l=80, r=50, t=100, b=50),  # 增加左侧边距以容纳标签
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
        """创建数据摘要卡片"""
        if df.empty:
            return html.Div("无数据摘要")
        
        cards = []
        
        # 最新价格卡片
        latest_data = df.iloc[-1]
        latest_price = latest_data['close']
        latest_date = latest_data['date']
        
        cards.append(
            dbc.Card(
                dbc.CardBody([
                    html.H5("最新价格", className="card-title"),
                    html.H3(f"¥{latest_price:.2f}", className="card-text text-primary"),
                    html.P(f"日期: {latest_date}", className="card-text text-muted"),
                ]),
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
                    html.H5("振幅统计", className="card-title"),
                    html.H3(f"{avg_amplitude:.2f}%", className="card-text text-info"),
                    html.P(f"平均振幅", className="card-text text-muted"),
                    html.P([
                        f"最大振幅: {max_amplitude:.2f}% (",
                        html.Span(f"{max_amplitude_date}", className="font-weight-bold"),
                        ")"
                    ], className="card-text"),
                ]),
                className="m-2 shadow"
            )
        )
        
        # 中间价通道卡片
        if 'mid_price' in df.columns:
            latest_mid = latest_data['mid_price']
            cards.append(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("中间价", className="card-title"),
                        html.H3(f"¥{latest_mid:.2f}", className="card-text text-success"),
                    ]),
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
                        html.H5("开盘价与中间价差值", className="card-title"),
                        html.H3(f"{diff_sign}{latest_open_mid_diff:.2f}%", className=f"card-text {diff_color}"),
                        html.P(f"平均差值: {avg_open_mid_diff:.2f}%", className="card-text text-muted"),
                    ]),
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
