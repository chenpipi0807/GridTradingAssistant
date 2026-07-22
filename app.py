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
    external_stylesheets=[],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="网格交易大师V5",
    suppress_callback_exceptions=True  # 添加这个参数来抑制回调异常
)

# 创建标签页
tabs = dbc.Tabs(
    [
        dbc.Tab(label="行情分析", tab_id="market-tab", 
                labelClassName="fw-bold", activeLabelClassName="text-primary"),
        dbc.Tab(label="DeepSeek对话", tab_id="deepseek-tab", 
                labelClassName="fw-bold", activeLabelClassName="text-primary"),
        dbc.Tab(label="观测指标与技巧", tab_id="indicators-tab", 
                labelClassName="fw-bold", activeLabelClassName="text-primary"),
    ],
    id="tabs",
    active_tab="market-tab",
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
                    dbc.Col(dbc.NavbarBrand("网格交易大师V5", className="ms-2 fw-normal", style={"color": "#4D4B63"})),
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
        dcc.Store(id="favorites-store", data=utils.load_favorite_stocks()),
        
        # 页脚
        html.Footer([
            html.Hr(style={"margin": "10px 0", "border-top": "1px solid #f0f0f0"}),
            html.P(
                "网格交易大师 © 2025",
                className="text-center text-muted small",
                style={"margin-bottom": "8px"}
            ),
        ]),
    ], fluid=True, className="px-4 pb-2"),  # 减少容器内边距
], style={"background-color": "#fcfcfc"})  # 提高整体背景色亮度

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
    if active_tab == "market-tab":
        return get_market_layout()
    elif active_tab == "deepseek-tab":
        return deepseek_ui.get_deepseek_layout()
    elif active_tab == "indicators-tab":
        return get_indicators_layout()
    return html.P("未知标签页")

def get_indicators_layout():
    """获取观测指标与技巧标签页的布局"""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H4("观测指标与技巧", className="text-primary mb-3"),
                
                # 振幅指标说明
                html.H5("振幅指标", className="text-success mt-4 mb-2"),
                dbc.Card(dbc.CardBody([
                    html.P([
                        "振幅是股票价格在特定时间段内的波动范围，计算方式为：",
                        html.Code("振幅 = (最高价 - 最低价) / 最低价 * 100%")
                    ]),
                    html.P([
                        "观测技巧：",
                        html.Ul([
                            html.Li("高振幅通常意味着市场情绪波动较大，可能伴随着重要信息的发布或市场不确定性"),
                            html.Li("将当日振幅与历史分位数比较，可以判断当前市场活跃程度"),
                            html.Li("持续的高振幅可能预示着价格趋势的转变或市场情绪的极端化")
                        ])
                    ])
                ])),
                
                # 中间价与开盘价差值说明
                html.H5("中间价与开盘价差值", className="text-success mt-4 mb-2"),
                dbc.Card(dbc.CardBody([
                    html.P([
                        "中间价与开盘价差值反映了股票当天价格运行的中心位置与开盘位置的关系：",
                        html.Code("差值 = (中间价 - 开盘价) / 中间价 * 100%")
                    ]),
                    html.P([
                        "观测技巧：",
                        html.Ul([
                            html.Li("正差值意味着中间价高于开盘价，表示价格中心在上移"),
                            html.Li("负差值意味着中间价低于开盘价，表示价格中心在下移"),
                            html.Li("差值的绝对值越大，表示价格偏离开盘的程度越大"),
                            html.Li("连续多日的同向差值可能表示趋势正在形成")
                        ])
                    ])
                ])),
                
                # ATR指标说明
                html.H5("ATR指标 (Average True Range)", className="text-success mt-4 mb-2"),
                dbc.Card(dbc.CardBody([
                    html.P("ATR指标是衡量市场波动性的重要指标，由Welles Wilder开发。它计算最近N天的真实范围(True Range)的平均值。"),
                    html.P([
                        "真实范围(True Range)的计算方法为以下三个值中的最大值：",
                        html.Ol([
                            html.Li("当日最高价 - 当日最低价"),
                            html.Li("|当日最高价 - 前一日收盘价|"),
                            html.Li("|当日最低价 - 前一日收盘价|")
                        ])
                    ]),
                    html.P("ATR = 过去N天TR值的指数移动平均(默认N=14)"),
                    html.P([
                        "ATR观测技巧：",
                        html.Ul([
                            html.Li("ATR值越高，表示市场波动越大；ATR值越低，表示市场波动越小"),
                            html.Li("ATR的变化趋势比绝对值更重要：上升的ATR表示波动性增强，下降的ATR表示波动性减弱"),
                            html.Li("ATR常用于确定止损位置：例如设置止损在当前价格减去1.5倍ATR"),
                            html.Li("ATR也用于判断市场趋势强度：在趋势形成初期，ATR往往会增大"),
                            html.Li("ATR不能判断价格方向，只能判断波动程度"),
                        ])
                    ])
                ])),
                
                # ATR应用场景
                html.H5("ATR在交易中的应用", className="text-success mt-4 mb-2"),
                dbc.Card(dbc.CardBody([
                    html.P([
                        "1. 波动突破策略：",
                        html.Ul([
                            html.Li("当价格突破上一交易日收盘价上方X倍ATR时买入"),
                            html.Li("当价格跌破上一交易日收盘价下方X倍ATR时卖出"),
                        ])
                    ]),
                    html.P([
                        "2. 通道突破策略：",
                        html.Ul([
                            html.Li("上轨 = 移动平均线 + 2*ATR"),
                            html.Li("下轨 = 移动平均线 - 2*ATR"),
                            html.Li("价格突破上轨买入，跌破下轨卖出")
                        ])
                    ]),
                    html.P([
                        "3. 组合指标应用：",
                        html.Ul([
                            html.Li("ATR与振幅结合：先用振幅判断市场活跃度，再用ATR判断趋势强度"),
                            html.Li("ATR与中间价差值结合：中间价差值判断方向，ATR判断力度")
                        ])
                    ])
                ])),
                
                # MPMI指标说明
                html.H5("MPMI指标 (Mid-Price Momentum Indicator)", className="text-success mt-4 mb-2"),
                dbc.Card(dbc.CardBody([
                    html.P("MPMI指标是基于中间价的动量指标，类似于MACD指标，但使用中间价而非收盘价计算。"),
                    html.P([
                        "MPMI指标的计算方法为：",
                        html.Ol([
                            html.Li("EMA短线 = 中间价的12日指数移动平均"),
                            html.Li("EMA长线 = 中间价的26日指数移动平均"),
                            html.Li("MPMI线 = EMA短线 - EMA长线"),
                            html.Li("MPMI信号线 = MPMI线的9日指数移动平均"),
                            html.Li("MPMI柱状图 = MPMI线 - MPMI信号线")
                        ])
                    ]),
                    html.P([
                        "MPMI指标观测技巧：",
                        html.Ul([
                            html.Li("MPMI线从下连续上穿信号线，形成金叉，是买入信号"),
                            html.Li("MPMI线从上连续下穿信号线，形成死叉，是卖出信号"),
                            html.Li("MPMI柱状图趋势由负转正且柱状图高度升高，说明上涨动能增强"),
                            html.Li("MPMI柱状图趋势由正转负且柱状图进一步走低，说明下跌动能增强"),
                            html.Li("MPMI指标并非绝对准确，建议结合其他指标如振幅、ATR等进行分析")
                        ])
                    ])
                ])),
                
                # MPMI应用场景
                html.H5("MPMI在交易中的应用", className="text-success mt-4 mb-2"),
                dbc.Card(dbc.CardBody([
                    html.P([
                        "1. 动能转化判断：",
                        html.Ul([
                            html.Li("MPMI柱状图由负转正，且MPMI线向上穿过信号线时，可能将出现上涨动能"),
                            html.Li("MPMI柱状图由正转负，且MPMI线向下穿过信号线时，可能将出现下跌动能")
                        ])
                    ]),
                    html.P([
                        "2. 网格交易中的应用：",
                        html.Ul([
                            html.Li("上轨和下轨定位：当MPMI金叉形成时，可作为设置网格交易上轨的使用参考"),
                            html.Li("交易方向确认：当中间价趋势和MPMI信号方向一致时，可增强交易信心")
                        ])
                    ]),
                    html.P([
                        "3. 组合指标应用：",
                        html.Ul([
                            html.Li("MPMI与振幅结合：金叉信号出现的同时振幅增大，可能意味着更强的趋势信号"),
                            html.Li("MPMI与ATR结合：ATR增大时的MPMI金叉信号可能有更高的可靠性"),
                            html.Li("MPMI与中间价-开盘价差值结合：差值和MPMI方向一致时，信号可靠性增强")
                        ])
                    ])
                ])),
                
                # 星星指标说明 - 新增
                html.H5("星星指标", className="text-success mt-4 mb-2"),
                dbc.Card(dbc.CardBody([
                    html.P("星星指标是用于识别特定市场形态的观测工具，当满足以下两个条件时会在振幅图上显示星星标记："),
                    html.P([
                        html.Strong("触发条件："),
                        html.Ol([
                            html.Li("振幅连续三天缩小（第一天振幅 > 第二天振幅 > 第三天振幅）"),
                            html.Li("第二天和第三天的最高价和最低价都在第一天的最高价和最低价区间内")
                        ])
                    ]),
                    html.P([
                        html.Strong("星星颜色含义："),
                        html.Ul([
                            html.Li([html.Span("🔴 红色星星", style={"color": "red", "fontWeight": "bold"}), ": 三天中间价持续上涨"]),
                            html.Li([html.Span("🟢 绿色星星", style={"color": "green", "fontWeight": "bold"}), ": 三天中间价持续下跌"]),
                            html.Li([html.Span("🟡 黄色星星", style={"color": "gold", "fontWeight": "bold"}), ": 三天中间价持平或波动"])
                        ])
                    ]),
                ])),
                
                # DeepSeek使用说明 - 新增
                html.H5("DeepSeek使用说明", className="text-success mt-4 mb-2"),
                dbc.Card(dbc.CardBody([
                    html.P("DeepSeek是强大的AI助手，可以帮助您分析股票数据和网格交易策略。以下是使用说明："),
                    html.P([
                        html.Strong("1. 获取API密钥："),
                        html.Ul([
                            html.Li("访问DeepSeek官方网站注册账户"),
                            html.Li("在个人账户中申请并获取API密钥"),
                            html.Li("API密钥是您访问DeepSeek服务的唯一凭证，请妥善保管")
                        ])
                    ]),
                    html.P([
                        html.Strong("2. 在应用中使用："),
                        html.Ul([
                            html.Li("切换到DeepSeek标签页"),
                            html.Li("在左侧控制面板中输入您的API密钥并点击保存"),
                            html.Li("选择合适的模型（推荐使用DeepSeek V4 Pro以获得更好的分析能力）"),
                            html.Li("可以上传当前股票数据以便AI分析"),
                            html.Li("使用预设问题或输入自定义问题进行交流")
                        ])
                    ]),
                    html.P([
                        "项目源码和更多信息：",
                        html.A("https://github.com/chenpipi0807/GridTradingAssistant", 
                               href="https://github.com/chenpipi0807/GridTradingAssistant", 
                               target="_blank",
                               className="text-decoration-none")
                    ]),
                    html.P("关于网格交易的技术交流可以在GitHub项目页面给我留言。", className="mb-3"),
                    html.Div([
                        html.P("或者扫描下方二维码添加微信，一起交流量化交易心得：", className="text-center mb-2"),
                        html.Img(
                            src="/assets/aboutme.png",
                            alt="微信二维码",
                            style={"maxWidth": "200px", "display": "block", "margin": "0 auto"}
                        )
                    ], className="text-center")
                ])),
                
                # 作者赞赏
                html.H5("赞赏作者", className="text-success mt-4 mb-2"),
                dbc.Card(dbc.CardBody([
                    html.P("如果本工具对您的交易有所帮助，欢迎请我喝杯咖啡 ☕", className="text-center mb-3"),
                    html.Div([
                        html.Img(
                            src="/assets/pipchen.png",
                            alt="赞赏码",
                            style={"maxWidth": "200px", "display": "block", "margin": "0 auto"}
                        )
                    ], className="text-center"),
                    html.P("感谢您的支持！更多功能持续开发中...", className="text-center mt-3 text-muted small")
                ])),
            ], width=10, className="mx-auto")
        ])
    ], className="py-3")

def get_market_layout():
    """获取行情分析标签页的布局"""
    return html.Div([
        dbc.Row([
            # 左侧控制面板
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        # 股票输入 - 紧凑搜索框
                        dbc.Label("股票代码/名称", className="mb-1 small fw-bold", style={"color": "#4D4B63", "fontSize": "11px"}),
                        dbc.InputGroup([
                            dbc.Input(
                                id="stock-input",
                                placeholder="输入代码后按回车",
                                value="300502",
                                style={"height": "32px", "fontSize": "11px"},
                                className="border-light-subtle",
                            ),
                            dbc.Button("搜索", id="search-btn", color="light", size="sm",
                                     style={"background": "#7D5BA6", "color": "white", "border": "none"}),
                        ], size="sm", className="mb-2"),
                        dbc.ListGroup(id="stock-search-results", className="mb-3 small"),

                        # 常用股票
                        dbc.Label("常用股票", className="mb-1 small fw-bold", style={"color": "#4D4B63", "fontSize": "11px"}),
                        html.Div(id="favorite-stocks-container", className="mb-2"),

                        # 日期范围
                        dbc.Label("日期范围", className="mb-1 small fw-bold", style={"color": "#4D4B63", "fontSize": "10px"}),
                        dcc.Dropdown(
                            id="date-range-dropdown",
                            options=utils.generate_date_options(),
                            value=(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d') + '至' + datetime.now().strftime('%Y-%m-%d'),
                            className="mb-2 small",
                            style={"fontSize": "10px"},
                        ),

                        # 数据源
                        html.Div([
                            html.P("数据源: 东方财富",
                                   className="small fw-bold mb-3",
                                   style={"color": "#4D4B63", "margin-bottom": "15px"}),
                            dbc.Input(
                                id="data-source-dropdown",
                                value="eastmoney",
                                type="hidden"
                            ),
                        ], className="mb-3"),

                        # 预警消息
                        html.Div(id="alert-container", className="mt-3"),

                        # 基本信息
                        html.Div(id="summary-cards", className="mt-3"),
                    ]),
                ], className="shadow-sm h-100", style={"border": "1px solid #EFEDF5", "background": "#FFFFFF"}),
            ], width=2, className="pe-0"),

            # 右侧主内容
            dbc.Col([
                # 加载指示器
                dcc.Loading(
                    id="loading",
                    type="circle",
                    color="#7D5BA6",
                    children=[
                        # 主要图表容器
                        dbc.Card([
                            dbc.CardHeader([
                                html.Div([
                                    html.H6(id="chart-title", className="mb-0 d-inline fw-bold", style={"color": "#4D4B63"}),
                                    html.Span(
                                        "(最高价+最低价)/2",
                                        className="ms-2 small", style={"color": "#8E7E64"}
                                    ),
                                ], className="d-inline"),
                                # 操作按钮组：更新数据、收藏、K线切换
                                html.Div([
                                    html.Button(
                                        "⟳ 更新",
                                        id="refresh-data-btn",
                                        title="刷新当前股票数据",
                                        style={
                                            "fontSize": "11px",
                                            "background": "none",
                                            "border": "none",
                                            "cursor": "pointer",
                                            "color": "#7D5BA6",
                                            "padding": "0 4px",
                                        }
                                    ),
                                    html.Button(
                                        "☆",
                                        id="chart-favorite-btn",
                                        title="收藏/取消收藏",
                                        style={
                                            "fontSize": "15px",
                                            "background": "none",
                                            "border": "none",
                                            "cursor": "pointer",
                                            "color": "#4D4B63",
                                            "padding": "0 6px",
                                            "lineHeight": "1",
                                        }
                                    ),
                                    dbc.Switch(
                                        id="kline-toggle",
                                        label="K线",
                                        value=False,
                                        className="mt-0",
                                        style={"font-size": "12px"}
                                    )
                                ], className="float-end d-flex align-items-center")
                            ], className="py-2 border-bottom d-flex justify-content-between", style={"border-left": "3px solid #7D5BA6", "background": "#FCFCFE"}),
                            dbc.CardBody([
                                html.Div(id="stock-chart-container"),
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
            ], width=10, className="ps-3"),
        ])
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
    
    # 创建卡片 - 使用更小的字体和更紧凑的布局
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div("最新价", className="text-muted small mb-0", style={'fontSize': '0.7rem'}),
                        html.Div(f"¥{latest_price:.2f}", className="text-primary", style={'fontSize': '0.9rem', 'fontWeight': 'bold'}),
                        html.Div(latest_date, className="text-muted", style={'fontSize': '0.65rem'}),
                    ], className="p-1"),
                ], className="mb-1 border shadow-sm"),
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div("中间价", className="text-muted small mb-0", style={'fontSize': '0.7rem'}),
                        html.Div(f"¥{mid_price:.2f}", className="text-success", style={'fontSize': '0.9rem', 'fontWeight': 'bold'}),
                        html.Div("(最高+最低)/2", className="text-muted", style={'fontSize': '0.65rem'}),
                    ], className="p-1"),
                ], className="mb-1 border shadow-sm"),
            ], width=6),
        ], className="g-1"),  # 减少行间距
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div("平均振幅", className="text-muted small mb-0", style={'fontSize': '0.7rem'}),
                        html.Div(f"{avg_amplitude}%", style={'fontSize': '0.9rem', 'fontWeight': 'bold'}),
                        html.Div("区间平均值", className="text-muted", style={'fontSize': '0.65rem'}),
                    ], className="p-1"),
                ], className="mb-1 border shadow-sm"),
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div("最大振幅", className="text-muted small mb-0", style={'fontSize': '0.7rem'}),
                        html.Div(f"{max_amplitude}%", className="text-danger", style={'fontSize': '0.9rem', 'fontWeight': 'bold'}),
                        html.Div(f"最小: {min_amplitude}%", className="text-muted", style={'fontSize': '0.65rem'}),
                    ], className="p-1"),
                ], className="mb-1 border shadow-sm"),
            ], width=6),
        ], className="g-1"),  # 减少行间距
    ])

# 整合查询和缩放功能的回调函数
@app.callback(
    [
        Output("stock-data-store", "data"),
        Output("data-table-container", "children"),
        Output("summary-cards", "children"),
        Output("stock-chart-container", "children"),
        Output("alert-container", "children"),
        Output("chart-title", "children"),
    ],
    [
        Input("stock-input", "n_submit"),
        Input("search-btn", "n_clicks"),
        Input("refresh-data-btn", "n_clicks"),
        Input('kline-toggle', 'value'),
    ],
    [
        State("stock-input", "value"),
        State("date-range-dropdown", "value"),
        State("data-source-dropdown", "value"),
        State("stock-data-store", "data"),
    ],
    prevent_initial_call=True
)
def update_chart(enter_press, search_clicks, refresh_clicks, kline_toggle, stock_code, date_range, data_source, stored_data):
    """整合的回调函数：搜索/Enter/刷新 获取数据 / K线切换"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # 获取触发回调的按钮 ID
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # 如果是K线图切换且有存储数据
    if triggered_id == "kline-toggle" and stored_data:
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
        
        # 移除旧的调试信息区
        
        # Y轴缩放因子(上下方向)
        zoom_factor = 0.2
        
        # 存储当前缩放状态
        y_scale_factor = 1.0  # 默认比例
        
        # 创建新的图表，传递K线图显示状态，标题留空（由CardHeader显示）
        chart = visualizer.create_stock_chart(
            df, 
            None,  # 不再在图表中显示标题，改为在CardHeader中显示
            show_kline=kline_toggle  # 根据开关状态决定是否显示K线图
        )
        fig = chart.figure
        
        # 更新存储的数据，我们不再需要缩放状态
        if 'y_scale_factor' in stored_data:
            del stored_data['y_scale_factor']
        
        # 创建图表标题（股票名称 + 中间价与振幅分析）
        chart_title = f"{stock_name} 中间价与振幅分析"
        
        # 返回结果 - 不再返回debug_info，改为保持alert不变
        return stored_data, visualizer.create_data_table(df), create_summary_cards(df), dcc.Graph(
            id='stock-chart', 
            figure=fig, 
            config={'displayModeBar': False}
        ), dash.no_update, chart_title
    
    # 数据查询/刷新 - Enter键 / 搜索按钮 / 更新按钮
    elif triggered_id in ("stock-input", "search-btn", "refresh-data-btn"):
        # 如果是刷新按钮，使用已存储的股票代码
        if triggered_id == "refresh-data-btn":
            if stored_data and isinstance(stored_data, dict):
                stock_code = stored_data.get('stock_code', stock_code)
            if not stock_code:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dbc.Alert("请先搜索一只股票", color="warning", dismissable=True), dash.no_update

        # 验证输入
        if not stock_code:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dbc.Alert("请输入股票代码或名称", color="warning", dismissable=True), dash.no_update

        # 解析股票输入
        input_type, value = utils.parse_stock_input(stock_code)

        # 如果是名称而非代码，不处理（由搜索回调处理）
        if input_type == 'name':
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # 解析日期范围
        start_date, end_date = utils.parse_date_range(date_range)

        try:
            # 获取股票数据
            df, stock_info = data_fetcher.get_stock_data(value, start_date, end_date, data_source)
            
            if df.empty:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dbc.Alert("未找到股票数据", color="warning", dismissable=True), dash.no_update
            
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
            table = visualizer.create_data_table(df)
            
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
            
            # 创建图表标题
            chart_title = f"{stock_info['name']} 中间价与振幅分析"
            
            return stored_data, table, create_summary_cards(df), dcc.Graph(
                id='stock-chart',
                figure=chart.figure,
                config={'displayModeBar': False}
            ), html.Div(alerts), chart_title
            
        except Exception as e:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dbc.Alert(f"获取数据时出错: {str(e)}", color="danger", dismissable=True)
    
    # 默认返回
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# 加载常用股票列表并显示在界面上
@app.callback(
    Output("favorite-stocks-container", "children"),
    Input("favorites-store", "data")
)
def load_favorite_stocks_ui(favorites_data):
    if not favorites_data:
        return html.Div("暂无收藏股票", className="small text-muted")

    # 创建常用股票按钮（带删除X）- 使用 Button 而非 Span 确保点击事件可靠
    buttons = []
    for stock in favorites_data:
        buttons.append(
            html.Span(
                [
                    html.Button(
                        stock["name"],
                        id={"type": "favorite-stock-btn", "index": stock["code"]},
                        style={
                            "fontSize": "10px",
                            "padding": "1px 5px",
                            "backgroundColor": "#f0f0f5",
                            "color": "#4D4B63",
                            "border": "1px solid #e0e0eb",
                            "borderRight": "none",
                            "borderRadius": "4px 0 0 4px",
                            "cursor": "pointer",
                            "lineHeight": "18px",
                        },
                        title=f"点击加载 {stock['name']}"
                    ),
                    html.Button(
                        "×",
                        id={"type": "remove-fav-btn", "index": stock["code"]},
                        style={
                            "fontSize": "12px",
                            "padding": "1px 5px",
                            "backgroundColor": "#f0f0f5",
                            "color": "#999",
                            "border": "1px solid #e0e0eb",
                            "borderLeft": "none",
                            "borderRadius": "0 4px 4px 0",
                            "cursor": "pointer",
                            "lineHeight": "18px",
                            "fontWeight": "bold",
                        },
                        title=f"取消收藏 {stock['name']}"
                    ),
                ],
                className="d-inline-block me-1 mb-1"
            )
        )

    return html.Div(buttons, className="d-flex flex-wrap")

# 图表标题栏收藏按钮 - 点击切换收藏状态（只更新数据，图标由下方回调自动刷新）
@app.callback(
    Output("favorites-store", "data", allow_duplicate=True),
    Input("chart-favorite-btn", "n_clicks"),
    State("stock-data-store", "data"),
    State("favorites-store", "data"),
    prevent_initial_call=True
)
def toggle_chart_favorite(n_clicks, stock_data, favorites_data):
    if not stock_data:
        return dash.no_update

    stock_code = stock_data.get('stock_code', '')
    stock_name = stock_data.get('stock_name', '')
    if not stock_code:
        return dash.no_update

    # 修复: favorites_data 可能为 None（初始状态）
    favorites = list(favorites_data) if favorites_data else []

    found = None
    for i, fav in enumerate(favorites):
        if fav["code"] == stock_code:
            found = i
            break
        # 兼容纯数字代码匹配
        pure_code = stock_code[-6:] if len(stock_code) >= 6 else stock_code
        if fav["code"] == pure_code:
            found = i
            break

    if found is not None:
        utils.remove_favorite_stock(favorites[found]["code"])
        favorites.pop(found)
    else:
        utils.add_favorite_stock(stock_code, stock_name or stock_code)
        favorites.append({"code": stock_code, "name": stock_name or stock_code})

    return favorites

# 当股票数据或收藏列表变化时，自动更新星标图标显示
@app.callback(
    Output("chart-favorite-btn", "children"),
    Input("stock-data-store", "data"),
    Input("favorites-store", "data"),
)
def update_chart_favorite_star(stock_data, favorites_data):
    """根据当前股票是否在收藏中，显示 ★ 或 ☆"""
    if not stock_data or not favorites_data:
        return "☆"

    stock_code = stock_data.get('stock_code', '')
    if not stock_code:
        return "☆"

    for fav in favorites_data:
        if fav["code"] == stock_code:
            return "★"
        pure_code = stock_code[-6:] if len(stock_code) >= 6 else stock_code
        if fav["code"] == pure_code:
            return "★"
    return "☆"

# 处理点击常用股票按钮的回调
@app.callback(
    Output("stock-input", "value", allow_duplicate=True),
    Input({"type": "favorite-stock-btn", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def on_favorite_stock_click(n_clicks):
    # 获取触发回调的按钮
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    # 获取按钮ID
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    stock_code = json.loads(button_id)["index"]

    # 返回股票代码填充到输入框
    return stock_code

# 处理点击删除收藏按钮
@app.callback(
    Output("favorites-store", "data", allow_duplicate=True),
    Input({"type": "remove-fav-btn", "index": dash.ALL}, "n_clicks"),
    State("favorites-store", "data"),
    prevent_initial_call=True
)
def on_remove_favorite_click(n_clicks, favorites_data):
    ctx = dash.callback_context
    if not ctx.triggered or not favorites_data:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    stock_code = json.loads(button_id)["index"]

    utils.remove_favorite_stock(stock_code)
    favorites = [fav for fav in favorites_data if fav["code"] != stock_code]
    return favorites

# 查询成功后更新收藏列表中的股票名称
@app.callback(
    Output("favorites-store", "data", allow_duplicate=True),
    Input("stock-data-store", "data"),
    State("favorites-store", "data"),
    prevent_initial_call=True
)
def update_favorite_name_on_query(stock_data, favorites_data):
    """当查询股票后，如果该股票在收藏中但名称为代码，则更新为真实名称"""
    if not stock_data or not favorites_data:
        return dash.no_update

    stock_code = stock_data.get('stock_code', '')
    stock_name = stock_data.get('stock_name', '')

    if not stock_code or not stock_name:
        return dash.no_update

    updated = False
    new_favorites = list(favorites_data)
    for fav in new_favorites:
        # 如果收藏中的名称就是代码本身，更新为真实名称
        if fav["code"] == stock_code and fav["name"] == stock_code and stock_name != stock_code:
            fav["name"] = stock_name
            updated = True
        # 同时也检查不带前缀的匹配
        if len(stock_code) >= 6:
            pure_code = stock_code[-6:] if len(stock_code) > 6 else stock_code
            if fav["code"] == pure_code and fav["name"] == pure_code and stock_name != pure_code:
                fav["name"] = stock_name
                updated = True

    if updated:
        utils.save_favorite_stocks(new_favorites)
        return new_favorites
    return dash.no_update

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
