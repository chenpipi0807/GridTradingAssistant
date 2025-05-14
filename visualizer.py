"""
可视化模块 - 负责生成数据表格和图表
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from dash import html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta


class Visualizer:
    def __init__(self):
        """初始化可视化器"""
        pass
    
    def create_stock_table(self, df):
        """
        创建股票数据表格
        
        Parameters:
        -----------
        df : pd.DataFrame
            处理后的股票数据
            
        Returns:
        --------
        html.Div : Dash表格组件
        """
        if df.empty:
            return html.Div("无数据")
        
        # 选择要显示的列
        display_cols = [
            'date', 'high', 'low', 'close', 'mid_price', 
            'amplitude'
        ]
        
        # 添加资金流向列（如果存在）
        if 'main_net_inflow' in df.columns:
            display_cols.append('main_net_inflow')
        
        # 准备表格数据
        table_df = df[display_cols].copy()
        
        # 格式化数值
        format_cols = {
            'high': '¥{:.2f}',
            'low': '¥{:.2f}',
            'close': '¥{:.2f}',
            'mid_price': '¥{:.2f}',
            'amplitude': '{:.2f}%'
        }
        
        if 'main_net_inflow' in table_df.columns:
            format_cols['main_net_inflow'] = '{:,.2f}万'
            # 将资金流向转换为万元单位
            table_df['main_net_inflow'] = table_df['main_net_inflow'] / 10000
        
        for col, fmt in format_cols.items():
            if col in table_df.columns:
                table_df[col] = table_df[col].apply(lambda x: fmt.format(x) if pd.notna(x) else '-')
        
        # 重命名列
        rename_map = {
            'date': '日期',
            'high': '最高价',
            'low': '最低价',
            'close': '收盘价',
            'mid_price': '中间价',
            'amplitude': '振幅(%)',
            'main_net_inflow': '主力资金(万)'
        }
        table_df = table_df.rename(columns=rename_map)
        
        # 创建更大更醒目的表格
        table = dbc.Table.from_dataframe(
            table_df, 
            striped=True, 
            bordered=True, 
            hover=True,
            responsive=True,
            size="lg",  # 使用大尺寸表格
            className="stock-data-table",
            style={
                'fontSize': '16px',  # 更大的字体
                'width': '100%',     # 占满宽度
                'minWidth': '800px',  # 最小宽度
                'marginTop': '20px',
                'marginBottom': '30px',
                'border': '2px solid #dee2e6',  # 更醒目的边框
            }
        )
        
        return html.Div([
            html.H4("股票数据表格", style={'fontSize': '22px', 'marginBottom': '15px', 'fontWeight': 'bold'}),
            table
        ], style={'width': '100%', 'padding': '15px 0px'})
    
    def create_stock_chart(self, df, title=None):
        """
        创建中间价和振幅图表
        
        Parameters:
        -----------
        df : pd.DataFrame
            处理后的股票数据
        title : str, optional
            图表标题
            
        Returns:
        --------
        dcc.Graph : Dash图表组件
        """
        if df.empty:
            return html.Div("无图表数据")
            
        # 通过判断当前时间决定是否显示当天数据
        # 如果当前时间小于15:00，则不显示当天数据
        # 需要筛选非交易日的数据(周末和节假日)
        now = datetime.now()
        df['date'] = pd.to_datetime(df['date'])
        
        # 如果当前时间小于15:00，且数据中包含当天数据，则去除当天数据
        if now.hour < 15 and now.date() in df['date'].dt.date.values:
            df = df[df['date'].dt.date < now.date()]
        
        # 创建图表 - 增强振幅区域显示
        fig = make_subplots(
            rows=2, 
            cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.05,  # 减小空间
            row_heights=[0.6, 0.4],  # 增加振幅子图的高度比例
            subplot_titles=(
                "中间价走势 (最高价+最低价)/2", 
                "日振幅(%)"
            )
        )
        
        # 添加中间价曲线（醒目且连接所有点）
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['mid_price'],
                mode='lines+markers',  # 线条+标记点
                name="中间价",
                line=dict(color='#7D5BA6', width=2.5),  # 淡紫色，高级感更强
                marker=dict(size=6, color='#7D5BA6'),
                hovertemplate='%{x|%Y-%m-%d}<br>中间价: %{y:.2f}<extra></extra>',
            ),
            row=1, col=1
        )
        
        # 添加价格区间柱状图（最高价-最低价）- 增强可见性
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['high'] - df['low'],  # 柱状图高度是最高价和最低价之差
                base=df['low'],           # 柱状图从最低价开始
                name="最高-最低区间",
                marker_color='rgba(130, 160, 220, 0.95)',  # 显著增强饱和度和不透明度
                marker_line=dict(width=2.5, color="rgba(70, 90, 180, 0.9)"),  # 大幅加粗边框
                opacity=0.95,  # 提高不透明度
                hovertemplate='%{x|%Y-%m-%d}<br>最高: %{customdata[0]:.2f}<br>最低: %{customdata[1]:.2f}<br>区间: %{customdata[2]:.2f}<extra></extra>',
                customdata=[[h, l, h-l] for h, l in zip(df['high'], df['low'])],
                width=0.45,  # 减小宽度到一半
            ),
            row=1, col=1
        )
        
        # 增加价格线
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['close'],
                mode='lines',
                name="收盘价",
                line=dict(color='rgba(120, 120, 120, 0.65)', width=1.5, dash='dot'),
                hovertemplate='%{x|%Y-%m-%d}<br>收盘价: %{y:.2f}<extra></extra>',
            ),
            row=1, col=1
        )
        
        # 在振幅子图中添加柱状图，根据振幅比例使用高饱和度颜色
        colors = []
        symbols = []  # 为振幅添加箭头符号
        zero_line = np.zeros(len(df))
        
        # 计算振幅变化，添加趋势符号
        prev_amp = None
        for i, amp in enumerate(df['amplitude']):
            # 设置颜色
            if amp > 5:
                colors.append('#FF3B30')  # 非常饱和亮红色：振幅>5%
            elif amp > 3:
                colors.append('#FF9500')  # 酷炫橙色：振幅>3%
            elif amp < 1:
                colors.append('#34C759')  # 鲜艳绿色：振幅<1%
            else:
                colors.append('#007AFF')  # 亮蓝色：中等振幅
            
            # 添加箭头符号
            if prev_amp is not None:
                if amp > prev_amp:
                    symbols.append('triangle-up')
                elif amp < prev_amp:
                    symbols.append('triangle-down')
                else:
                    symbols.append('circle')
            else:
                symbols.append('circle')
            
            prev_amp = amp
        
        # 添加振幅变化趋势指示器
        # 添加指示振幅变化的箭头图标
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=[amp + 0.5 for amp in df['amplitude']],  # 将符号放在柱状图上方
                mode='markers',
                name="振幅趋势",
                marker=dict(
                    symbol=symbols,
                    size=10,
                    color=["green" if s == "triangle-up" else "red" if s == "triangle-down" else "gray" for s in symbols],
                    line=dict(width=1, color="#333")
                ),
                hoverinfo="none",
                showlegend=False
            ),
            row=2, col=1
        )
        
        # 添加振幅参考线（水平线） - 增加更多的参考线
        for level in [1, 3, 5, 10, 15, 20]:
            fig.add_shape(
                type="line",
                x0=df['date'].min(),
                y0=level,
                x1=df['date'].max(),
                y1=level,
                line=dict(color="rgba(0,0,0,0.2)", width=1, dash="dot"),
                row=2, col=1
            )
            # 添加参考线标签
            fig.add_annotation(
                x=df['date'].max(),
                y=level,
                text=f"{level}%",
                showarrow=False,
                xshift=10,
                font=dict(size=9, color="rgba(0,0,0,0.7)"),
                row=2, col=1
            )
        
        # 添加更加醒目的振幅柱状图 - 显著增强可视性
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['amplitude'],
                name="振幅(%)",
                marker_color=colors,
                marker_line=dict(width=3, color="rgba(40,40,40,0.6)"),  # 显著加粗边框
                hovertemplate='%{x|%Y-%m-%d}<br>振幅: %{y:.2f}%<extra></extra>',
                width=0.45,  # 减小宽度到一半
                opacity=1.0,  # 完全不透明
                text=[f"{amp:.1f}%" for amp in df['amplitude']],  # 添加振幅文字标签
                textposition='outside',  # 文字放在柱子上方
                textfont=dict(size=10, color='rgba(0,0,0,0.7)')  # 设置文字大小和颜色
            ),
            row=2, col=1
        )
        
        # 准备日期标签，只显示实际交易日的日期
        date_labels = df['date'].dt.strftime('%m-%d').tolist()
        
        # 设置图表布局 - 增大图表尺寸和可读性
        fig.update_layout(
            title={
                'text': title or "中间价与振幅分析",
                'font': dict(size=24, color='#444'),
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title=None,
            yaxis_title={
                'text': "价格(元)",
                'font': dict(size=16)
            },
            xaxis_rangeslider_visible=False,
            plot_bgcolor='white',  # 纯白背景
            paper_bgcolor='white',
            height=750,  # 显著增加高度
            margin=dict(l=50, r=30, t=100, b=50),  # 调整边距增加上部空间
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0.01,
                bgcolor="white",
                bordercolor="#f2f2f2",
                borderwidth=1,
                font=dict(size=14),  # 增大图例字体
            ),
            hovermode="x unified",
            font=dict(family="Arial, sans-serif", size=11, color="#444")
        )
        
        # 将X轴改为分类轴，只显示有交易数据的日期，无间隔连续显示
        fig.update_xaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='#f2f2f2',
            zeroline=False,
            type='category',  # 使用分类轴，连续显示交易日
            tickmode='array',
            tickvals=list(range(len(df))),
            ticktext=date_labels,
            tickangle=-30,  # 倾斜日期标签
            tickfont=dict(size=10),
        )
        
        # 添加网格线
        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='#f2f2f2',
            zeroline=False,
            row=1, col=1,
            title_font=dict(size=12),
            tickfont=dict(size=10),
        )
        
        # 振幅图的Y轴设置
        fig.update_yaxes(
            title_text="振幅(%)", 
            row=2, col=1,
            range=[0, 20],  # 固定范围为0-20%
            title_font=dict(size=12),
            tickfont=dict(size=10),
            showgrid=True,
            gridwidth=0.5,
            gridcolor='#f2f2f2',
        )
        
        return dcc.Graph(
            figure=fig, 
            id='stock-chart',
            config={
                'displayModeBar': False,  # 隐藏工具栏
                'displaylogo': False,
                'responsive': True,
            },
            style={"border": "1px solid #e0e0e0", "border-radius": "5px"}
        )
    
    def create_strategy_chart(self, df, strategy_results):
        """
        创建策略回测图表
        
        Parameters:
        -----------
        df : pd.DataFrame
            处理后的股票数据
        strategy_results : dict
            策略回测结果
            
        Returns:
        --------
        dcc.Graph : Dash图表组件
        """
        if df.empty or not strategy_results:
            return html.Div("无策略回测数据")
        
        trades = strategy_results.get('trades', [])
        if not trades:
            return html.Div("无交易记录")
        
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
        
        # 添加中间价通道
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['mid_upper'],
                mode='lines',
                name="卖出价(+1%)",
                line=dict(color='rgba(255, 0, 0, 0.5)', width=1)
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['mid_lower'],
                mode='lines',
                name="买入价(-1%)",
                line=dict(color='rgba(0, 255, 0, 0.5)', width=1)
            )
        )
        
        return dcc.Graph(figure=fig, id='strategy-chart')
    
    def create_summary_cards(self, df, strategy_results=None):
        """
        创建数据摘要卡片
        
        Parameters:
        -----------
        df : pd.DataFrame
            处理后的股票数据
        strategy_results : dict, optional
            策略回测结果
            
        Returns:
        --------
        html.Div : Dash卡片组件
        """
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
        latest_mid = latest_data['mid_price']
        latest_upper = latest_data['mid_upper']
        latest_lower = latest_data['mid_lower']
        
        cards.append(
            dbc.Card(
                dbc.CardBody([
                    html.H5("中间价通道", className="card-title"),
                    html.H3(f"¥{latest_mid:.2f}", className="card-text text-success"),
                    html.P([
                        "上轨: ",
                        html.Span(f"¥{latest_upper:.2f}", className="text-danger")
                    ], className="card-text"),
                    html.P([
                        "下轨: ",
                        html.Span(f"¥{latest_lower:.2f}", className="text-success")
                    ], className="card-text"),
                ]),
                className="m-2 shadow"
            )
        )
        
        # 如果有策略回测结果，添加策略卡片
        if strategy_results:
            total_return = strategy_results.get('total_return', 0)
            trade_count = len(strategy_results.get('trades', []))
            win_rate = strategy_results.get('win_rate', 0) * 100
            
            cards.append(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("策略回测", className="card-title"),
                        html.H3([
                            html.Span(
                                f"{total_return:.2f}%", 
                                className=f"text-{'success' if total_return >= 0 else 'danger'}"
                            )
                        ], className="card-text"),
                        html.P(f"交易次数: {trade_count}", className="card-text"),
                        html.P(f"胜率: {win_rate:.1f}%", className="card-text"),
                    ]),
                    className="m-2 shadow"
                )
            )
        
        # 将卡片排列成一行
        return html.Div(
            dbc.Row([dbc.Col(card, width=12//len(cards)) for card in cards]),
            className="mb-4"
        )
