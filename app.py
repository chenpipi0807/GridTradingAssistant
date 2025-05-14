"""网格交易大师 (Grid Trading Master) - 主应用"""
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import plotly.graph_objects as go
import os

from data_fetcher import DataFetcher
from data_processor import DataProcessor
from visualizer import Visualizer
from strategy import TradingStrategy
import utils

# 初始化组件
data_fetcher = DataFetcher(data_source="eastmoney")
data_processor = DataProcessor()
visualizer = Visualizer()
strategy = TradingStrategy()

# 创建Dash应用
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="网格交易大师V2"
)

# 定义布局
app.layout = html.Div([
    # 导航栏
    dbc.Navbar(
        dbc.Container([
            html.A(
                dbc.Row([
                    dbc.Col(html.Img(src="assets/logo.png", height="28px"), width="auto"),
                    dbc.Col(dbc.NavbarBrand("网格交易大师V2", className="ms-2 fw-normal", style={"color": "#4D4B63"})),
                ], align="center", className="g-0"),
                href="/",
                style={"textDecoration": "none"},
            ),
            dbc.Col(html.Span("基于中间价的股票观测工具", className="small", style={"color": "#8E7E64"}), width="auto"),
        ]),
        color="#F9F8FA",  # 低饱和度淡紫色背景
        dark=False, 
        className="py-2 border-bottom shadow-sm mb-3",  # 减小高度
        style={"height": "50px"},
    ),
    
    # 主体内容
    dbc.Container([
        dbc.Row([
            # 左侧控制面板
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        # 股票输入
                        dbc.Label("股票代码/名称", className="mb-1 small fw-bold", style={"color": "#4D4B63"}),
                        dbc.InputGroup([
                            dbc.Input(
                                id="stock-input",
                                placeholder="如：603019 / 中科曙光",
                                value="603019",
                                style={"height": "36px"},
                                className="border-light-subtle",
                            ),
                            dbc.Button("搜索", id="search-btn", color="light", size="sm", 
                                     style={"background": "#7D5BA6", "color": "white", "border": "none"}),
                        ], size="sm", className="mb-3"),
                        dbc.ListGroup(id="stock-search-results", className="mb-3 small"),
                        
                        # 日期范围
                        dbc.Label("日期范围", className="mb-1 small fw-bold", style={"color": "#4D4B63"}),
                        dcc.Dropdown(
                            id="date-range-dropdown",
                            options=utils.generate_date_options(),
                            value=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d') + '至' + datetime.now().strftime('%Y-%m-%d'),
                            className="mb-3 small",
                            style={"fontSize": "12px"},
                        ),
                        
                        # 数据源
                        html.Div([
                            html.P("数据源: 东方财富", 
                                   className="small fw-bold mb-3", 
                                   style={"color": "#4D4B63", "margin-bottom": "15px"}),
                            # 隐藏的数据源选择器(仅保留东方财富)
                            dbc.Input(
                                id="data-source-dropdown",
                                value="eastmoney", 
                                type="hidden"
                            ),
                        ], className="mb-3"),
                        
                        # 查询按钮
                        dbc.Button(
                            "获取数据",
                            id="query-btn",
                            color="light",
                            className="w-100 mt-2 mb-2",
                            size="sm",
                            style={"background": "#A65B56", "color": "white", "border": "none"},
                        ),
                        
                        # 预警消息
                        html.Div(id="alert-container", className="mt-3"),
                        
                        # 基本信息
                        html.Div(id="summary-cards", className="mt-3"),
                    ]),
                ], className="shadow-sm h-100", style={"border": "1px solid #EFEDF5", "background": "#FCFCFE"}),
            ], width=3, className="pe-0"),  # 左侧列去除右边距
            
            # 右侧主内容
            dbc.Col([
                # 加载指示器
                dcc.Loading(
                    id="loading",
                    type="circle",
                    children=[
                        # 主要图表容器
                        dbc.Card([
                            dbc.CardHeader([
                                html.Div([
                                    html.H6("中间价与振幅分析", className="mb-0 d-inline fw-bold", style={"color": "#4D4B63"}),
                                    html.Span(
                                        "(最高价+最低价)/2", 
                                        className="ms-2 small", style={"color": "#8E7E64"}
                                    ),
                                ], className="d-inline"),
                                # 添加交互控制按钮组
                                html.Div([
                                    dbc.ButtonGroup([
                                        dbc.Button("-", id="zoom-out-btn", color="light", className="mx-1 p-1", 
                                                  size="sm", style={"width": "30px", "height": "30px", "border-radius": "50%"}),
                                        dbc.Button("+", id="zoom-in-btn", color="light", className="mx-1 p-1", 
                                                  size="sm", style={"width": "30px", "height": "30px", "border-radius": "50%"}),
                                        dbc.Button("重置", id="reset-zoom-btn", color="light", className="mx-1 p-1", 
                                                  size="sm", style={"height": "30px", "font-size": "12px"}),
                                    ], className="float-end me-2"),
                                    # 添加K线图切换开关
                                    html.Div(
                                        dbc.Switch(
                                            id="kline-toggle",
                                            label="显示K线图",
                                            value=False,  # 默认关闭
                                            className="mt-0",
                                            style={"font-size": "12px"}
                                        ),
                                        className="float-end"
                                    )
                                ]),
                            ], className="py-2 border-bottom d-flex justify-content-between", style={"border-left": "3px solid #7D5BA6", "background": "#FCFCFE"}),
                            dbc.CardBody([
                                html.Div(id="stock-chart-container"),
                                # 添加缓存存储组件来记录图表交互状态
                                dcc.Store(id="chart-zoom-state", data={"range": None, "domain": None})
                            ], className="p-2", style={"background": "#FFFFFF"}),
                        ], className="mb-3 border shadow-sm", style={"border-radius": "3px", "border": "1px solid #EFEDF5"}),
                        
                        # 数据表格
                        dbc.Card([
                            dbc.CardHeader(html.H6("交易数据", className="mb-0 small fw-bold", style={"color": "#4D4B63"}), 
                                        className="py-2 border-bottom", 
                                        style={"border-left": "3px solid #A65B56", "background": "#FCFCFE"}),
                            dbc.CardBody([
                                html.Div(id="data-table-container", className="small")
                            ], className="p-2", style={"background": "#FFFFFF"}),
                        ], className="mb-3 border shadow-sm", style={"border-radius": "3px", "border": "1px solid #EFEDF5"}),
                    ],
                ),
            ], width=9, className="ps-3"),  # 右侧列去除左边距
        ]),
        
        # 存储组件
        dcc.Store(id="stock-data-store"),
        
        # 页脚
        html.Footer([
            html.Hr(style={"margin": "10px 0", "border-top": "1px solid #f0f0f0"}),
            html.P(
                "网格交易大师 v2.0 © 2025",
                className="text-center text-muted small",
                style={"margin-bottom": "8px"}
            ),
        ]),
    ], fluid=True, className="px-4 pb-2"),  # 减少容器内边距
], style={"background-color": "#fafafa"})  # 整体背景色

# 创建资产目录
if not os.path.exists("assets"):
    os.makedirs("assets")

# 回调函数：搜索股票
@app.callback(
    Output("stock-search-results", "children"),
    Input("search-btn", "n_clicks"),
    State("stock-input", "value"),
    prevent_initial_call=True
)
def search_stock(n_clicks, stock_input):
    if not stock_input:
        return []
    
    input_type, value = utils.parse_stock_input(stock_input)
    
    if input_type == 'code':
        # 如果输入的是有效股票代码，不需要搜索
        return []
    
    # 搜索股票
    search_results = data_fetcher.search_stock_by_name(value)
    
    if search_results.empty:
        return dbc.ListGroupItem("未找到相关股票")
    
    # 生成搜索结果列表
    result_items = []
    for _, row in search_results.iterrows():
        result_items.append(
            dbc.ListGroupItem(
                f"{row['name']} ({row['symbol']})",
                id={"type": "search-result", "index": row['symbol']},
                action=True
            )
        )
    
    return result_items

# 回调函数：点击搜索结果
@app.callback(
    Output("stock-input", "value"),
    Input({"type": "search-result", "index": dash.dependencies.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def select_search_result(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    # 获取点击的搜索结果ID
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    selected_code = eval(triggered_id)['index']
    
    return selected_code

# 创建摘要卡片函数
def create_summary_cards(df):
    """创建股票数据摘要卡片"""
    if df.empty:
        return None
    
    # 计算关键指标
    latest = df.iloc[-1]
    latest_price = latest['close']
    latest_date = latest['date'].strftime('%Y-%m-%d') if isinstance(latest['date'], pd.Timestamp) else latest['date']
    mid_price = round((latest['high'] + latest['low']) / 2, 2)
    avg_amplitude = round(df['amplitude'].mean(), 2) if 'amplitude' in df.columns else 0
    max_amplitude = round(df['amplitude'].max(), 2) if 'amplitude' in df.columns else 0
    min_amplitude = round(df['amplitude'].min(), 2) if 'amplitude' in df.columns else 0
    
    # 创建卡片
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("最新价", className="card-subtitle text-muted small mb-1"),
                        html.H5(f"¥{latest_price:.2f}", className="card-title mb-0 text-primary"),
                        html.P(latest_date, className="card-text small text-muted mt-1 mb-0"),
                    ], className="p-2"),
                ], className="mb-2 border shadow-sm"),
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("中间价", className="card-subtitle text-muted small mb-1"),
                        html.H5(f"¥{mid_price:.2f}", className="card-title mb-0 text-success"),
                        html.P("(最高+最低)/2", className="card-text small text-muted mt-1 mb-0"),
                    ], className="p-2"),
                ], className="mb-2 border shadow-sm"),
            ], width=6),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("平均振幅", className="card-subtitle text-muted small mb-1"),
                        html.H5(f"{avg_amplitude}%", className="card-title mb-0"),
                        html.P("区间平均值", className="card-text small text-muted mt-1 mb-0"),
                    ], className="p-2"),
                ], className="mb-2 border shadow-sm"),
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("最大振幅", className="card-subtitle text-muted small mb-1"),
                        html.H5(f"{max_amplitude}%", className="card-title mb-0 text-danger"),
                        html.P(f"最小: {min_amplitude}%", className="card-text small text-muted mt-1 mb-0"),
                    ], className="p-2"),
                ], className="mb-2 border shadow-sm"),
            ], width=6),
        ]),
    ])

# 整合查询和缩放功能的回调函数
@app.callback(
    [
        Output("stock-data-store", "data"),
        Output("data-table-container", "children"),
        Output("summary-cards", "children"),
        Output("stock-chart-container", "children"),
        Output("alert-container", "children"),
    ],
    [
        Input("query-btn", "n_clicks"),
        Input("zoom-in-btn", "n_clicks"),
        Input("zoom-out-btn", "n_clicks"),
        Input("reset-zoom-btn", "n_clicks"),
        Input('kline-toggle', 'value'),  # 添加K线图切换输入
    ],
    [
        State("stock-input", "value"),
        State("date-range-dropdown", "value"),
        State("data-source-dropdown", "value"),
        State("stock-data-store", "data"),
    ],
    prevent_initial_call=True
)
def update_chart(query_clicks, zoom_in_clicks, zoom_out_clicks, reset_clicks, kline_toggle, 
                 stock_code, date_range, data_source, stored_data):
    """整合的回调函数，处理查询和缩放功能"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    # 获取触发回调的按钮 ID
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # 缩放功能 - 如果是缩放按钮且有存储数据
    if triggered_id in ["zoom-in-btn", "zoom-out-btn", "reset-zoom-btn", "kline-toggle"] and stored_data:
        # 检查数据结构
        if not isinstance(stored_data, dict) or 'data' not in stored_data:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        # 将存储的数据转换为DataFrame
        df = pd.DataFrame(stored_data['data'])
        
        # 确保日期列是日期类型
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        
        # 获取股票信息
        stock_code = stored_data.get('stock_code', '')
        stock_name = stored_data.get('stock_name', '')
        
        # 创建调试信息区
        debug_info = html.Div(
            id="debug-info",
            children=[
                html.Pre(
                    id="zoom-debug-info",
                    children=f"当前缩放状态: 原始状态",
                    style={
                        "margin": "5px",
                        "padding": "5px",
                        "backgroundColor": "#f8f9fa",
                        "border": "1px solid #ddd",
                        "borderRadius": "3px",
                        "fontSize": "12px"
                    }
                )
            ],
            style={"marginBottom": "10px"}
        )
        
        # Y轴缩放因子(上下方向)
        zoom_factor = 0.2
        
        # 存储当前缩放状态
        y_scale_factor = 1.0  # 默认比例
        
        # 创建新的图表，传递K线图显示状态
        chart = visualizer.create_stock_chart(
            df, 
            f"{stock_name} ({stock_code}) 中间价与振幅分析",
            show_kline=kline_toggle  # 根据开关状态决定是否显示K线图
        )
        fig = chart.figure
        
        # 从存储的状态中获取当前缩放状态，如果有的话
        if 'y_scale_factor' in stored_data:
            y_scale_factor = stored_data.get('y_scale_factor', 1.0)
        
        # 获取K线图和振幅图的当前数据范围
        price_min = df['low'].min() * 0.98
        price_max = df['high'].max() * 1.02
        amp_min = 0  # 振幅最小值通常是0
        amp_max = df['amplitude'].max() * 1.2  # 问留一些余量
        
        debug_msg = ""
        
        if triggered_id == "zoom-in-btn":
            # 放大Y轴 - 缩小显示范围
            y_scale_factor *= (1 + zoom_factor)  # 增加缩放因子，使图表垂直方向放大
            
            # 计算新的Y轴范围
            price_range = price_max - price_min
            price_mid = (price_max + price_min) / 2
            new_price_range = price_range / y_scale_factor
            
            amp_range = amp_max - amp_min
            amp_mid = (amp_max + amp_min) / 2
            new_amp_range = amp_range / y_scale_factor
            
            # 更新图表垂直方向范围
            fig.update_layout(
                yaxis=dict(
                    range=[price_mid - new_price_range/2, price_mid + new_price_range/2]
                ),
                yaxis2=dict(
                    range=[amp_mid - new_amp_range/2, amp_mid + new_amp_range/2]
                )
            )
            
            debug_msg = f"放大Y轴: 缩放因子 = {y_scale_factor:.2f}\n"
            debug_msg += f"K线图范围: {price_mid - new_price_range/2:.2f} ~ {price_mid + new_price_range/2:.2f}\n"
            debug_msg += f"振幅图范围: {amp_mid - new_amp_range/2:.2f} ~ {amp_mid + new_amp_range/2:.2f}"
            
            # 更新调试信息
            debug_info.children[0].children = debug_msg
            
        elif triggered_id == "zoom-out-btn":
            # 缩小 Y 轴 - 扩大显示范围
            y_scale_factor /= (1 + zoom_factor)  # 减小缩放因子，使图表垂直方向缩小
            
            # 防止过度缩小
            if y_scale_factor < 0.3:
                y_scale_factor = 0.3
            
            # 计算新的Y轴范围
            price_range = price_max - price_min
            price_mid = (price_max + price_min) / 2
            new_price_range = price_range / y_scale_factor
            
            amp_range = amp_max - amp_min
            amp_mid = (amp_max + amp_min) / 2
            new_amp_range = amp_range / y_scale_factor
            
            # 更新图表垂直方向范围
            fig.update_layout(
                yaxis=dict(
                    range=[price_mid - new_price_range/2, price_mid + new_price_range/2]
                ),
                yaxis2=dict(
                    range=[amp_mid - new_amp_range/2, amp_mid + new_amp_range/2]
                )
            )
            
            debug_msg = f"缩小 Y 轴: 缩放因子 = {y_scale_factor:.2f}\n"
            debug_msg += f"K线图范围: {price_mid - new_price_range/2:.2f} ~ {price_mid + new_price_range/2:.2f}\n"
            debug_msg += f"振幅图范围: {amp_mid - new_amp_range/2:.2f} ~ {amp_mid + new_amp_range/2:.2f}"
            
            # 更新调试信息
            debug_info.children[0].children = debug_msg
        
        # 如果是重置按钮，重置所有缩放设置
        elif triggered_id == "reset-zoom-btn":
            # 重置缩放因子
            y_scale_factor = 1.0
            
            # 重置图表到原始状态，但保持K线图显示状态
            chart = visualizer.create_stock_chart(
                df, 
                f"{stock_name} ({stock_code}) 中间价与振幅分析",
                show_kline=kline_toggle
            )
            fig = chart.figure
            
            debug_msg = f"重置缩放 - 恢复原始状态\n"
            if kline_toggle:
                debug_msg += f"K线图显示已开启"
            else:
                debug_msg += f"K线图显示已关闭"
            
            # 更新调试信息
            debug_info.children[0].children = debug_msg
            
        # 如果是K线图切换开关
        elif triggered_id == "kline-toggle":
            import traceback
            import io
            try:
                # 打印当前数据和状态信息，帮助调试
                print(f"\n\n[DEBUG] K线图切换: {kline_toggle}")
                print(f"[DEBUG] 数据列: {df.columns.tolist()}")
                print(f"[DEBUG] 数据行数: {len(df)}")
                
                # 重新创建图表，并传递新的K线图显示状态
                chart = visualizer.create_stock_chart(
                    df, 
                    f"{stock_name} ({stock_code}) 中间价与振幅分析",
                    show_kline=kline_toggle
                )
                fig = chart.figure
                
                # 保持当前的缩放状态
                # 获取K线图和振幅图的当前数据范围
                price_min = df['low'].min() * 0.98
                price_max = df['high'].max() * 1.02
                amp_min = 0  # 振幅最小值通常是0
                amp_max = df['amplitude'].max() * 1.2
                
                # 计算当前缩放的Y轴范围
                price_range = price_max - price_min
                price_mid = (price_max + price_min) / 2
                new_price_range = price_range / y_scale_factor
                
                amp_range = amp_max - amp_min
                amp_mid = (amp_max + amp_min) / 2
                new_amp_range = amp_range / y_scale_factor
                
                # 应用当前的缩放状态
                fig.update_layout(
                    yaxis=dict(
                        range=[price_mid - new_price_range/2, price_mid + new_price_range/2]
                    ),
                    yaxis2=dict(
                        range=[amp_mid - new_amp_range/2, amp_mid + new_amp_range/2]
                    )
                )
                
                debug_msg = f"K线图显示已{'开启' if kline_toggle else '关闭'}\n"
                debug_msg += f"当前缩放因子 = {y_scale_factor:.2f}"
                
                # 更新调试信息
                debug_info.children[0].children = debug_msg
            except Exception as e:
                # 获取完整的错误信息
                error_buffer = io.StringIO()
                traceback.print_exc(file=error_buffer)
                full_error = error_buffer.getvalue()
                print(f"\n\n[ERROR] K线图切换时错误:\n{full_error}")
                
                # 在UI上显示错误
                debug_msg = f"\n*** 错误信息 ***\n"
                debug_msg += f"类型: {type(e).__name__}\n"
                debug_msg += f"内容: {str(e)}\n"
                debug_msg += f"请查看控制台以获取完整错误信息"
                
                # 更新调试信息
                debug_info.children[0].children = debug_msg
                
                # 创建一个空图表以避免崩溃
                if 'fig' not in locals():
                    fig = go.Figure()
                    fig.add_annotation(text="出错了，请查看上方的调试信息",
                                    xref="paper", yref="paper",
                                    x=0.5, y=0.5, showarrow=False,
                                    font=dict(color="red", size=20))
        
        # 更新存储数据中的缩放因子
        if isinstance(stored_data, dict):
            stored_data['y_scale_factor'] = y_scale_factor
        
        # 创建最终图表，包含调试信息
        final_chart = html.Div([
            debug_info,  # 添加调试信息区
            dcc.Graph(
                figure=fig,
                id="stock-chart",
                config={
                    'displayModeBar': False,
                    'displaylogo': False,
                    'responsive': True,
                }
            )
        ])
        
        # 更新存储数据和图表，其他保持不变
        return stored_data, dash.no_update, dash.no_update, final_chart, dash.no_update
    
    # 查询功能 - 如果是查询按钮
    elif triggered_id == "query-btn":
        if not stock_code:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # 解析日期范围
        dates = date_range.split('至')
        start_date = dates[0]
        end_date = dates[1] if len(dates) > 1 else datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 创建数据获取器 - 只使用东方财富数据源
            data_fetcher = DataFetcher(data_source="eastmoney")
            
            # 获取股票数据
            df = data_fetcher.get_stock_data(stock_code, start_date, end_date)
            
            # 打印调试信息，查看数据结构
            print("\n\n数据列名:", df.columns.tolist())
            if not df.empty and 'open' in df.columns:
                print("开盘价样本:", df['open'].head(3).tolist())
            else:
                print("数据中没有open列")
            
            if df.empty:
                alert = dbc.Alert("未查询到股票数据，请检查股票代码或日期范围", color="warning")
                return None, None, None, None, alert
            
            # 确保日期是日期时间格式以便排序
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 添加中间价和振幅指标
            df['mid_price'] = (df['high'] + df['low']) / 2
            df['amplitude'] = round((df['high'] - df['low']) / df['close'].shift(1) * 100, 2)
            
            # 获取股票名称
            try:
                stock_name = utils.get_stock_name(stock_code)
            except:
                stock_name = stock_code
            
            # 创建可视化对象，K线图初始不显示
            chart = visualizer.create_stock_chart(
                df, 
                f"{stock_name} ({stock_code}) 中间价与振幅分析",
                show_kline=kline_toggle
            )
            data_table = visualizer.create_stock_table(df)
            
            # 创建摘要卡片
            summary = create_summary_cards(df)
            
            # 检测异常振幅
            df = data_processor.detect_abnormal_amplitude(df)
            
            # 存储数据，包含初始缩放状态
            store_data = {
                'data': df.to_dict('records'),
                'stock_code': stock_code,
                'stock_name': stock_name,
                'y_scale_factor': 1.0  # 查询时重置缩放状态
            }
            
            return store_data, data_table, summary, chart, None
        
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print("=== 详细错误信息 ===")
            print(error_trace)
            print("====================")
            
            alert = dbc.Alert([
                html.H6(f"错误类型: {type(e).__name__}", className="alert-heading mb-1"),
                html.P(f"错误消息: {str(e)}", className="mb-2"),
                html.Hr(className="my-2"),
                html.Pre(error_trace, style={"whiteSpace": "pre-wrap", "fontSize": "11px", "backgroundColor": "#f8f9fa", "padding": "10px", "borderRadius": "5px"})
            ], color="danger")
            
            return None, None, None, None, alert
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# 运行应用
if __name__ == "__main__":
    app.run(debug=True, port=8050)
