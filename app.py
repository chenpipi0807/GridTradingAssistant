"""网格交易大师 (Grid Trading Master) - 主应用"""
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import plotly.graph_objects as go
import os
import json

from data_fetcher import DataFetcher
from data_processor import DataProcessor
from visualizer import Visualizer
from strategy import TradingStrategy
import utils
import deepseek_ui

# 初始化组件
data_fetcher = DataFetcher(data_source="eastmoney")
data_processor = DataProcessor()
visualizer = Visualizer()
strategy = TradingStrategy()

# 创建Dash应用
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, "https://use.fontawesome.com/releases/v5.15.4/css/all.css"],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="网格交易大师V3",
    suppress_callback_exceptions=True  # 添加这个参数来抑制回调异常
)

# 创建标签页
tabs = dbc.Tabs(
    [
        dbc.Tab(label="行情分析", tab_id="tab-market", 
                labelClassName="fw-bold", activeLabelClassName="text-primary"),
        dbc.Tab(label="DeepSeek对话", tab_id="tab-deepseek", 
                labelClassName="fw-bold", activeLabelClassName="text-primary"),
    ],
    id="tabs",
    active_tab="tab-market",
    className="mb-3"
)

# 定义布局
app.layout = html.Div([
    # 全局错误通知
    dbc.Alert(id="error-notification", is_open=False, dismissable=True, duration=4000),
    # 隐藏的触发器组件
    html.Div(id="_dummy-input", style={"display": "none"}),
    
    # 导航栏
    dbc.Navbar(
        dbc.Container([
            html.A(
                dbc.Row([
                    dbc.Col(html.Img(src="assets/logo.png", height="28px"), width="auto"),
                    dbc.Col(dbc.NavbarBrand("网格交易大师V3", className="ms-2 fw-normal", style={"color": "#4D4B63"})),
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
        # 标签页
        tabs,
        
        # 标签页内容
        html.Div(id="tab-content"),
        
        # 存储组件 - 添加所有需要的存储组件
        dcc.Store(id="stock-data-store"),
        dcc.Store(id="chat-session-store", data={"session_id": "", "messages": []}),
        dcc.Store(id="uploaded-files-store", data=[]),
        dcc.Store(id="selected-file-store", data={}),
        dcc.Store(id="chart-data-store", data={}),
        # 新增消息处理存储组件
        dcc.Store(id="message-processing-store", storage_type="memory"),
        dcc.Store(id="request-state-store", storage_type="memory", data=False),
        
        # 页脚
        html.Footer([
            html.Hr(style={"margin": "10px 0", "border-top": "1px solid #f0f0f0"}),
            html.P(
                "网格交易大师 V3.0 © 2025",
                className="text-center text-muted small",
                style={"margin-bottom": "8px"}
            ),
        ]),
    ], fluid=True, className="px-4 pb-2"),  # 减少容器内边距
], style={"background-color": "#fafafa"})  # 整体背景色

# 创建资产目录
if not os.path.exists("assets"):
    os.makedirs("assets")

# 创建临时目录
if not os.path.exists("temp"):
    os.makedirs("temp")

# 创建聊天历史目录
if not os.path.exists("chattemp"):
    os.makedirs("chattemp")

# 标签页切换回调
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab")
)
def render_tab_content(active_tab):
    """根据选中的标签页渲染内容"""
    if active_tab == "tab-market":
        return get_market_layout()
    elif active_tab == "tab-deepseek":
        return deepseek_ui.get_deepseek_layout()
    return html.P("未知标签页")

def get_market_layout():
    """获取行情分析标签页的布局"""
    return html.Div([
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
                                placeholder="如：301536 / 中科曙光",
                                value="301536",
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
                            value=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d') + '至' + datetime.now().strftime('%Y-%m-%d'),
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
                                    # 只保留K线图切换开关
                                    html.Div([
                                        dbc.Switch(
                                            id="kline-toggle",
                                            label="显示K线图",
                                            value=False,  # 默认关闭
                                            className="mt-0",
                                            style={"font-size": "12px"}
                                        )
                                    ], className="float-end d-flex")
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
    ])

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
        
        # 创建新的图表，传递K线图和MPMI指标显示状态
        chart = visualizer.create_stock_chart(
            df, 
            f"{stock_name} ({stock_code}) 中间价与振幅分析",
            show_kline=kline_toggle  # 根据开关状态决定是否显示K线图
            # MPMI指标始终显示，不需要开关控制
        )
        fig = chart.figure
        
        # 从存储的状态中获取当前缩放状态，如果有的话
        if 'y_scale_factor' in stored_data:
            y_scale_factor = stored_data['y_scale_factor']
        
        # 处理缩放操作
        if triggered_id == "zoom-in-btn":
            # 放大 - 减小Y轴范围
            y_scale_factor *= (1 - zoom_factor)
        elif triggered_id == "zoom-out-btn":
            # 缩小 - 增加Y轴范围
            y_scale_factor *= (1 + zoom_factor)
        elif triggered_id == "reset-zoom-btn":
            # 重置缩放
            y_scale_factor = 1.0
        
        # 应用缩放
        if y_scale_factor != 1.0:
            # 获取当前Y轴范围
            y_range = fig.layout.yaxis.range
            if y_range:
                # 计算中点
                mid_point = (y_range[0] + y_range[1]) / 2
                # 计算新范围
                half_range = (y_range[1] - y_range[0]) / 2 * y_scale_factor
                # 设置新范围
                fig.update_layout(yaxis=dict(range=[mid_point - half_range, mid_point + half_range]))
        
        # 更新调试信息
        debug_info.children[0].children = f"当前缩放状态: 比例因子 = {y_scale_factor:.2f}"
        
        # 更新存储数据中的缩放状态
        stored_data['y_scale_factor'] = y_scale_factor
        
        # 返回更新后的图表和保持其他输出不变
        return stored_data, dash.no_update, dash.no_update, dcc.Graph(figure=fig), dash.no_update
    
    # 查询功能 - 如果是查询按钮
    elif triggered_id == "query-btn":
        # 验证输入
        if not stock_code:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dbc.Alert("请输入股票代码或名称", color="warning", dismissable=True)
        
        # 解析股票输入
        input_type, value = utils.parse_stock_input(stock_code)
        
        # 解析日期范围
        start_date, end_date = utils.parse_date_range(date_range)
        
        try:
            # 获取股票数据
            df, stock_info = data_fetcher.get_stock_data(value, start_date, end_date, data_source)
            
            if df.empty:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dbc.Alert("未找到股票数据", color="warning", dismissable=True)
            
            # 处理数据
            df = data_processor.process_stock_data(df)
            
            # 保存数据到临时文件 - 使用原始文件名
            original_temp_file = os.path.join("temp", f"{stock_code}_{start_date}_{end_date}.csv")
            df.to_csv(original_temp_file, index=False)
            
            # 同时保存一份作为当前股票数据的文件，固定名称
            current_file = os.path.join("temp", "current_stock_data.csv")
            df.to_csv(current_file, index=False)
            
            # 同时保存股票信息到JSON文件中，便于显示
            stock_info_file = os.path.join("temp", "current_stock_info.json")
            with open(stock_info_file, "w", encoding="utf-8") as f:
                json.dump({
                    "code": stock_info["code"],
                    "name": stock_info["name"],
                    "period": f"{start_date} 至 {end_date}",
                    "data_source": data_source
                }, f, ensure_ascii=False)
            
            # 创建图表 - MPMI指标始终显示
            chart = visualizer.create_stock_chart(
                df, 
                f"{stock_info['name']} ({stock_info['code']}) 中间价与振幅分析",
                show_kline=kline_toggle
            )
            
            # 创建数据表格
            table = visualizer.create_stock_table(df)
            
            # 创建摘要卡片
            summary = visualizer.create_summary_cards(df)
            
            # 生成交易预警
            alerts = []
            warning_items = strategy.generate_alerts(df)
            if warning_items:
                for item in warning_items:
                    # generate_alerts返回的是字典，包含message和level字段
                    message = item['message']
                    level = item.get('level', 'warning')
                    alerts.append(
                        dbc.Alert(
                            message,
                            color="info" if level == "info" else "warning",
                            dismissable=True,
                            className="mb-2 py-2 small"
                        )
                    )
            
            # 存储数据
            stored_data = {
                'data': df.to_dict('records'),
                'stock_code': stock_info['code'],
                'stock_name': stock_info['name'],
                'y_scale_factor': 1.0  # 初始缩放因子
            }
            
            return stored_data, table, summary, dcc.Graph(figure=chart.figure), html.Div(alerts)
            
        except Exception as e:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dbc.Alert(f"获取数据时出错: {str(e)}", color="danger", dismissable=True)
    
    # 默认返回
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# 添加全局错误处理
@app.callback(
    Output("error-notification", "is_open", allow_duplicate=True),
    Output("error-notification", "children", allow_duplicate=True),
    Output("error-notification", "color", allow_duplicate=True),
    Input("_dummy-input", "n_clicks"),
    prevent_initial_call=True
)
def handle_global_errors(n_clicks):
    return False, "", "danger"

# 我们已经有了标签页切换回调，不需要这个额外的回调

# 注册DeepSeek UI模块的回调函数
deepseek_ui.register_callbacks(app)

# 运行应用
if __name__ == '__main__':
    app.run(debug=True, dev_tools_silence_routes_logging=False, host='0.0.0.0')
