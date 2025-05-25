"""DeepSeek UI 模块 - 提供DeepSeek对话界面的Dash组件"""
import dash
from dash import dcc, html, Input, Output, State, callback, ALL, MATCH, ctx, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import os
import uuid
import json
import base64
import traceback
import re
import types
import inspect
from datetime import datetime
import pandas as pd

from deepseek_api import DeepSeekAPI

# 创建缓存目录
temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
chat_temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chattemp")
os.makedirs(temp_dir, exist_ok=True)
os.makedirs(chat_temp_dir, exist_ok=True)

# 初始化DeepSeek API
deepseek_api = DeepSeekAPI()

def get_available_stock_files():
    """获取temp目录下的当前股票数据文件"""
    stock_files = []
    try:
        # 检查temp目录是否存在
        if not os.path.exists("temp"):
            os.makedirs("temp")
            return stock_files
        
        # 只检查固定名称的当前股票数据文件
        current_file = os.path.join("temp", "current_stock_data.csv")
        if os.path.exists(current_file):
            # 读取股票信息文件以获取股票代码、名称和日期范围
            stock_info_file = os.path.join("temp", "current_stock_info.json")
            stock_code = "未知"
            stock_name = "未知"
            date_range = ""
            
            if os.path.exists(stock_info_file):
                try:
                    with open(stock_info_file, "r", encoding="utf-8") as f:
                        stock_info = json.load(f)
                        stock_code = stock_info.get("code", "未知")
                        stock_name = stock_info.get("name", "未知")
                        date_range = stock_info.get("period", "")
                except Exception as e:
                    print(f"读取股票信息文件时出错: {e}")
            
            # 尝试读取文件的第一行获取数据列
            headers = []
            try:
                with open(current_file, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    headers = first_line.split(",")
            except Exception as e:
                print(f"读取文件头时出错: {e}")
            
            # 添加到文件列表
            stock_files.append({
                "path": current_file,
                "name": "current_stock_data.csv",
                "stock_code": stock_code,
                "stock_name": stock_name,
                "date_range": date_range,
                "headers": headers,
                "size": os.path.getsize(current_file)
            })
    except Exception as e:
        print(f"获取股票文件列表时出错: {e}")
    
    return stock_files

def get_deepseek_layout():
    """获取DeepSeek对话标签页的布局"""
    
    # 初始化存储组件，确保它们在回调运行前已存在
    initial_chat_messages = []
    initial_session_data = {"session_id": str(uuid.uuid4()), "messages": []}
    initial_uploaded_files = []
    
    # 获取可用模型列表
    try:
        models = deepseek_api.get_available_models()
        model_options = [{"label": model["name"], "value": model["id"]} for model in models]
    except Exception as e:
        print(f"无法获取模型列表: {e}")
        model_options = [
            {"label": "DeepSeek-R1 (推理增强)", "value": "deepseek-reasoner"},
            {"label": "DeepSeek Chat (通用对话)", "value": "deepseek-chat"},
            {"label": "DeepSeek Coder (代码专家)", "value": "deepseek-coder"}
        ]
    
    # 移除历史会话相关功能
    
    # 构建布局
    layout = html.Div([
        # 只保留在app.py中没有定义的存储组件
        # 这些组件在app.py的主布局中已经定义，所以这里只需要添加新增的
        dcc.Store(id="message-processing-store", storage_type="memory"),
        dcc.Store(id="request-state-store", storage_type="memory", data=False),
        
        # 我们将样式移到assets/custom.css中，这里不再使用html.Style
        html.Div(id="chat-messages-container", children=initial_chat_messages, style={"display": "block"}),
        html.Div(id="session-list-container", style={"display": "block"}),
        html.Div(id="file-upload-list-container", style={"display": "block"}),
        dbc.Row([
            # 左侧控制面板
            dbc.Col([
                # API密钥设置
                dbc.Card([
                    dbc.CardHeader(html.H6("DeepSeek API设置", className="mb-0 small fw-bold", style={"color": "#4D4B63"})),
                    dbc.CardBody([
                        dbc.InputGroup([
                            dbc.Input(
                                id="api-key-input",
                                placeholder="输入DeepSeek API密钥",
                                type="password",
                                value=deepseek_api.api_key or "",
                                className="border-light-subtle",
                            ),
                            dbc.Button(
                                "保存", 
                                id="save-api-key-btn", 
                                color="light", 
                                size="sm",
                                style={"background": "#7D5BA6", "color": "white", "border": "none"}
                            ),
                        ], size="sm", className="mb-3"),
                        
                        # 模型选择
                        dbc.Label("选择模型", className="mb-1 small fw-bold", style={"color": "#4D4B63"}),
                        dcc.Dropdown(
                            id="model-dropdown",
                            options=model_options,
                            value="deepseek-reasoner",  # 默认选择DeepSeek-R1
                            className="mb-3 small",
                            style={"fontSize": "12px"},
                        ),
                        
                        # 文件上传
                        dbc.Label("当前股票数据", className="mb-1 small fw-bold", style={"color": "#4D4B63"}),
                        html.Div([
                            # 当前可用的股票数据文件
                            html.Div(id="available-stock-files", className="border rounded p-2 mb-2"),
                            
                            # 上传股票数据按钮
                            dbc.Button(
                                [
                                    html.I(className="fas fa-file-upload me-1"),
                                    "上传当前股票数据到对话"
                                ],
                                id="upload-stock-data-btn",
                                color="light",
                                size="sm",
                                className="mb-3 mt-1"
                            ),
                            
                            # 隐藏的上传组件 - 保留ID以避免回调错误
                            html.Div([
                                dcc.Upload(
                                    id="upload-data",
                                    children=html.Div([]),
                                    style={"display": "none"}
                                ),
                                html.Div(id="uploaded-files-list", style={"display": "none"})
                            ], style={"display": "none"}),
                            
                        ], className="mb-3"),
                        
                        # 移除新建会话按钮和历史会话列表
                    ]),
                ], className="shadow-sm mb-3", style={"border": "1px solid #EFEDF5", "background": "#FCFCFE"}),
                
                # 策略提示
                dbc.Card([
                    dbc.CardHeader(html.H6("策略提示", className="mb-0 small fw-bold", style={"color": "#4D4B63"})),
                    dbc.CardBody([
                        html.P("枢轴点策略是一种技术分析方法，用于确定市场趋势和潜在的支撑/阻力位。", className="small mb-2"),
                        html.P("常见的枢轴点计算公式:", className="small mb-2"),
                        html.Pre(
                            "枢轴点(P) = (高点 + 低点 + 收盘价) / 3\n"
                            "支撑位1(S1) = (2 × P) - 高点\n"
                            "支撑位2(S2) = P - (高点 - 低点)\n"
                            "阻力位1(R1) = (2 × P) - 低点\n"
                            "阻力位2(R2) = P + (高点 - 低点)",
                            className="small bg-light p-2 rounded"
                        ),
                        html.P("您可以询问AI关于如何利用枢轴点进行网格交易策略制定。", className="small mt-2"),
                    ]),
                ], className="shadow-sm", style={"border": "1px solid #EFEDF5", "background": "#FCFCFE"}),
            ], width=3, className="pe-0"),  # 左侧列去除右边距
            
            # 右侧对话区域
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.H6("DeepSeek AI 对话", className="mb-0 d-inline fw-bold", style={"color": "#4D4B63"}),
                            html.Span(
                                id="current-model-display",
                                className="ms-2 small",
                                style={"color": "#8E7E64"}
                            ),
                        ], className="d-inline"),
                    ], className="py-2 border-bottom", style={"border-left": "3px solid #7D5BA6", "background": "#FCFCFE"}),
                    
                    # 对话内容区域
                    dbc.CardBody([
                        html.Div(
                            id="chat-messages-container",
                            className="chat-container mb-3",
                            style={
                                "height": "calc(100vh - 250px)",
                                "overflowY": "auto",
                                "padding": "10px"
                            }
                        ),
                        
                        # 常用问题快捷选项
                        html.Div([
                            html.P("常用问题", className="mb-1 small fw-bold"),
                            dbc.ButtonGroup(
                                [
                                    dbc.Button("分析这支股票的走势", id="quick-q1", color="light", size="sm", className="me-1 mb-1"),
                                    dbc.Button("计算最佳网格交易区间", id="quick-q2", color="light", size="sm", className="me-1 mb-1"),
                                    dbc.Button("这支股票适合网格交易吗", id="quick-q3", color="light", size="sm", className="me-1 mb-1"),
                                    dbc.Button("解读这些数据的含义", id="quick-q4", color="light", size="sm", className="me-1 mb-1"),
                                    dbc.Button("分析振幅和中间价趋势", id="quick-q5", color="light", size="sm", className="me-1 mb-1"),
                                ],
                                className="flex-wrap"
                            ),
                        ], className="mb-3 mt-2"),
                        
                        # 当前分析的股票信息
                        html.Div([
                            html.P("当前分析的股票数据", className="mb-1 small fw-bold"),
                            html.Div(id="current-stock-info", className="small text-muted")
                        ], className="mb-3"),
                        
                        # 输入区域
                        dbc.InputGroup([
                            dbc.Textarea(
                                id="chat-input",
                                placeholder="在此输入问题...",
                                style={"resize": "none", "height": "80px"},
                                className="rounded-start"
                            ),
                            dbc.Button(
                                html.I(className="fas fa-paper-plane"), 
                                id="send-message-btn", 
                                color="primary",
                                className="rounded-end"
                            ),
                        ], className="mt-3"),
                        
                        # 加载状态指示器
                        dbc.Spinner(
                            id="loading-spinner",
                            color="primary",
                            size="sm",
                            children=[
                                html.Div(
                                    id="loading-message",
                                    children="",
                                    className="small text-muted mt-2 text-center",
                                    style={"display": "none"}
                                )
                            ],
                            fullscreen=False,
                            fullscreen_style={"backgroundColor": "rgba(0, 0, 0, 0.3)"},
                            spinner_style={"width": "1.5rem", "height": "1.5rem"},
                            show_initially=False
                        ),
                        
                        # 状态提示
                        dbc.Alert(
                            "请先设置API密钥",
                            id="chat-status-alert",
                            color="warning",
                            dismissable=True,
                            is_open=not deepseek_api.api_key,
                            className="mb-0 py-2 small"
                        ),
                    ], className="p-3", style={"background": "#FFFFFF"}),
                ], className="shadow-sm h-100", style={"border": "1px solid #EFEDF5"}),
            ], width=9, className="ps-3"),  # 右侧列去除左边距
        ]),
        
        # 存储组件
        dcc.Store(id="chat-session-store", data={"session_id": str(uuid.uuid4()), "messages": []}),
        dcc.Store(id="uploaded-files-store", data=[]),
    ])
    
    return layout

def parse_contents(contents, filename):
    """解析上传的文件内容"""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        # 保存文件到临时目录
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(decoded)
        
        # 返回文件信息
        return {
            "name": filename,
            "path": file_path,
            "size": len(decoded),
            "type": content_type
        }
    except Exception as e:
        print(f"处理文件时出错: {e}")
        return None

def format_ai_message(message):
    """格式化AI返回的消息，简化版本，主要处理换行和空格"""
    # 在处理文本时，我们采用更简单的方法，主要处理换行
    # 将文本中的可能的Markdown格式保留，让浏览器自然显示
    
    # 确保我们有文本可处理
    if not message:
        return ""
    
    # 去除多余的空行，保留格式
    lines = message.split("\n")
    formatted_lines = []
    for i, line in enumerate(lines):
        if i > 0 and not line.strip() and not lines[i-1].strip():
            continue  # 跳过连续的空行
        formatted_lines.append(line)
    
    # 重新组合文本
    formatted = "\n".join(formatted_lines)
    
    # 处理代码块，保留格式
    # 在这里不做过多处理，保留原始格式，让浏览器显示
    
    return formatted

def register_callbacks(app):
    """注册DeepSeek UI相关的回调函数"""
    
    def safe_callback_wrapper(func):
        """包装回调函数，提供全局错误处理和防止ID not found错误"""
        def wrapper(*args, **kwargs):
            # 首先确定输出数量
            output_count = 2  # 默认值
            try:
                # 检查装饰器来获取输出数量
                func_name = func.__name__
                wrapper_func = getattr(register_callbacks, func_name, None)
                if wrapper_func:
                    # 查找装饰器源代码
                    source = inspect.getsource(wrapper_func)
                    callback_line = re.search(r'@app\.callback\([^)]*\)', source)
                    if callback_line:
                        # 计算Output函数的数量
                        output_count = source.count('Output(')
            except Exception as e:
                print(f"无法确定回调函数的输出数量: {e}")
                # 查找关键函数的输出数量
                if func_name == "create_new_session" or func_name == "load_session":
                    output_count = 2
                elif func_name == "send_message":
                    output_count = 3

            try:
                # 检查所有输入是否为空或无效
                if not ctx.triggered or all(arg is None or (isinstance(arg, (list, dict)) and not arg) for arg in args):
                    # 如果没有触发器或所有输入都是空的，返回no_update
                    return tuple(dash.no_update for _ in range(output_count))
                
                # 正常执行函数
                result = func(*args, **kwargs)
                
                # 检查结果类型
                if result is None:
                    return tuple(dash.no_update for _ in range(output_count))
                elif not isinstance(result, tuple):
                    # 如果不是元组，包装成元组
                    return (result,) + tuple(dash.no_update for _ in range(output_count - 1))
                elif len(result) < output_count:
                    # 如果元组长度小于预期输出数量，补充no_update
                    return result + tuple(dash.no_update for _ in range(output_count - len(result)))
                return result
                
            except dash.exceptions.PreventUpdate:
                # 让PreventUpdate正常抛出
                raise
            except Exception as e:
                # 捕获并记录所有其他异常
                print(f"回调错误: {str(e)}")
                print(traceback.format_exc())
                
                # 返回适当的错误信息或no_update
                return tuple(dash.no_update for _ in range(output_count))
        return wrapper

    # 获取并显示股票文件列表
    @app.callback(
        Output("available-stock-files", "children"),
        Input("tabs", "active_tab")
    )
    def update_stock_files_list(active_tab):
        if active_tab != "tab-deepseek":
            return dash.no_update
        
        stock_files = get_available_stock_files()
        if not stock_files:
            return html.Div("暂无当前股票数据", className="text-center text-muted py-2")
        
        # 只显示当前股票数据文件
        file = stock_files[0]  # 现在列表中只有一个文件
        
        return html.Div([
            html.Div(
                [
                    html.Div([
                        html.Span("当前股票", className="fw-bold"),
                        html.Span(f": {file['stock_code']} ", className="fw-bold"),
                        html.Span(f"({file['stock_name']})", className="text-muted")
                    ], className="mb-1"),
                    html.Div(f"时间范围: {file['date_range']}", className="small text-muted mb-1"),
                ],
                className="p-2 bg-light rounded"
            )
        ])
    
    # 显示当前分析的股票信息
    @app.callback(
        Output("current-stock-info", "children"),
        Input("stock-data-store", "data")
    )
    def update_current_stock_info(stock_data):
        if not stock_data:
            return "未选择股票数据"
        
        try:
            return [
                html.Div(f"股票代码: {stock_data.get('stock_code', '未知')}"),
                html.Div(f"股票名称: {stock_data.get('stock_name', '未知')}"),
                html.Div(f"分析时间范围: {stock_data.get('period', '全部可用数据')}")
            ]
        except Exception as e:
            print(f"更新股票信息时出错: {e}")
            return "无法显示股票信息"
    
    # 上传当前股票数据文件到对话
    @app.callback(
        [Output("uploaded-files-store", "data", allow_duplicate=True),
         Output("uploaded-files-list", "children", allow_duplicate=True),
         Output("chat-status-alert", "is_open", allow_duplicate=True),
         Output("chat-status-alert", "children", allow_duplicate=True),
         Output("chat-status-alert", "color", allow_duplicate=True)],
        Input("upload-stock-data-btn", "n_clicks"),
        State("uploaded-files-store", "data"),
        prevent_initial_call=True
    )
    @safe_callback_wrapper
    def upload_current_stock_data(n_clicks, current_files):
        # 获取当前股票数据文件
        current_file_path = os.path.join("temp", "current_stock_data.csv")
        stock_info_file = os.path.join("temp", "current_stock_info.json")
        
        # 检查当前股票数据文件是否存在
        if not os.path.exists(current_file_path):
            return current_files, dash.no_update, True, "没有可用的股票数据文件", "warning"
        
        # 从股票信息文件中获取股票代码、名称和日期范围
        stock_code = "未知"
        stock_name = "未知"
        date_range = ""
        
        if os.path.exists(stock_info_file):
            try:
                with open(stock_info_file, "r", encoding="utf-8") as f:
                    stock_info = json.load(f)
                    stock_code = stock_info.get("code", "未知")
                    stock_name = stock_info.get("name", "未知")
                    date_range = stock_info.get("period", "")
            except Exception as e:
                print(f"读取股票信息文件时出错: {e}")
        
        # 上传到chattemp目录
        try:
            # 在chattemp目录中使用固定名称
            chat_file_path = os.path.join("chattemp", "current_stock_data.csv")
            
            # 复制文件
            with open(current_file_path, "r", encoding="utf-8") as src_file:
                content = src_file.read()
                with open(chat_file_path, "w", encoding="utf-8") as dst_file:
                    dst_file.write(content)
            
            # 创建新文件信息
            new_file = {
                "path": chat_file_path,
                "type": "csv",
                "name": "current_stock_data.csv",
                "stock_code": stock_code,
                "stock_name": stock_name,
                "date_range": date_range
            }
            
            # 将当前股票数据设置为唯一文件
            current_files = [new_file]
            
            # 显示提示信息
            file_items = [
                dbc.ListGroupItem(
                    [
                        html.Div(
                            [
                                html.Span(f"{stock_name} ({stock_code})", className="fw-bold"),
                                html.Div(f"时间范围: {date_range}", className="small text-muted"),
                            ],
                            className="d-flex flex-column"
                        ),
                    ],
                    className="py-2 small"
                )
            ]
            
            return current_files, dbc.ListGroup(file_items), True, f"已成功上传股票数据: {stock_code} ({stock_name})", "success"
            
        except Exception as e:
            print(f"上传股票数据文件时出错: {e}")
            return current_files, dash.no_update, True, f"上传文件失败: {str(e)}", "danger"
    
    # 快捷问题按钮回调
    @app.callback(
        Output("chat-input", "value", allow_duplicate=True),
        [Input("quick-q1", "n_clicks"),
         Input("quick-q2", "n_clicks"),
         Input("quick-q3", "n_clicks"),
         Input("quick-q4", "n_clicks"),
         Input("quick-q5", "n_clicks")],
        prevent_initial_call=True
    )
    def set_quick_question(q1, q2, q3, q4, q5):
        if not ctx.triggered:
            return dash.no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        questions = {
            "quick-q1": "请分析这支股票的价格走势和交易特点",
            "quick-q2": "根据上传的数据，计算这支股票的最佳网格交易区间和网格数量",
            "quick-q3": "分析这支股票是否适合进行网格交易，给出详细理由",
            "quick-q4": "请分析解读数据中的中间价、相对振幅等指标的含义和投资价值",
            "quick-q5": "根据振幅和中间价趋势，判断这支股票的市场状况和未来走势"
        }
        
        return questions.get(trigger_id, "")
    
        # 保存API密钥回调
# 保存API密钥回调
    @app.callback(
        [Output("chat-status-alert", "is_open"),
         Output("chat-status-alert", "children"),
         Output("chat-status-alert", "color")],
        Input("save-api-key-btn", "n_clicks"),
        State("api-key-input", "value"),
        prevent_initial_call=True
    )
    def save_api_key(n_clicks, api_key):
        if not api_key:
            return True, "API密钥不能为空", "warning"
        
        success = deepseek_api.save_api_key(api_key)
        if success:
            return True, "API密钥保存成功", "success"
        else:
            return True, "API密钥保存失败", "danger"
    
    # 上传文件回调
    @app.callback(
        [Output("uploaded-files-list", "children"),
         Output("uploaded-files-store", "data")],
        Input("upload-data", "contents"),
        [State("upload-data", "filename"),
         State("uploaded-files-store", "data")],
        prevent_initial_call=True
    )
    @safe_callback_wrapper
    def update_uploaded_files(contents, filenames, current_files):
        if not contents:
            return dash.no_update, dash.no_update
        
        # 解析新上传的文件
        new_files = []
        for content, filename in zip(contents, filenames):
            file_info = parse_contents(content, filename)
            if file_info:
                new_files.append(file_info)
        
        # 更新文件列表
        updated_files = current_files + new_files
        
        # 创建文件列表UI
        file_items = []
        for i, file in enumerate(updated_files):
            file_items.append(
                dbc.ListGroupItem(
                    [
                        html.Div(
                            [
                                html.I(className="fas fa-file me-2"),
                                html.Span(file["name"], className="text-truncate", style={"maxWidth": "150px"}),
                                html.Small(f"{file['size'] // 1024} KB", className="text-muted ms-2"),
                            ],
                            className="d-flex align-items-center"
                        ),
                        html.Div(
                            dbc.Button(
                                "删除",
                                id={"type": "remove-file", "index": i},
                                color="danger",
                                size="sm",
                                className="py-0 px-2"
                            ),
                            className="ms-auto"
                        )
                    ],
                    className="d-flex justify-content-between align-items-center py-1 px-2"
                )
            )
        
        if not file_items:
            file_items = [dbc.ListGroupItem("暂无上传文件", className="text-center text-muted py-2")]
        
        return dbc.ListGroup(file_items, className="small"), updated_files
    
    # 删除上传文件回调
    @app.callback(
        [Output("uploaded-files-list", "children", allow_duplicate=True),
         Output("uploaded-files-store", "data", allow_duplicate=True)],
        Input({"type": "remove-file", "index": ALL}, "n_clicks"),
        State("uploaded-files-store", "data"),
        prevent_initial_call=True
    )
    def remove_file(n_clicks, files):
        # 获取触发回调的按钮索引
        if not ctx.triggered:
            return dash.no_update, dash.no_update
        
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        file_index = json.loads(button_id)["index"]
        
        # 删除文件
        if 0 <= file_index < len(files):
            # 尝试从磁盘删除文件
            try:
                os.remove(files[file_index]["path"])
            except:
                pass
            
            # 从列表中删除
            files.pop(file_index)
        
        # 更新文件列表UI
        file_items = []
        for i, file in enumerate(files):
            file_items.append(
                dbc.ListGroupItem(
                    [
                        html.Div(
                            [
                                html.I(className="fas fa-file me-2"),
                                html.Span(file["name"], className="text-truncate", style={"maxWidth": "150px"}),
                                html.Small(f"{file['size'] // 1024} KB", className="text-muted ms-2"),
                            ],
                            className="d-flex align-items-center"
                        ),
                        html.Div(
                            dbc.Button(
                                "删除",
                                id={"type": "remove-file", "index": i},
                                color="danger",
                                size="sm",
                                className="py-0 px-2"
                            ),
                            className="ms-auto"
                        )
                    ],
                    className="d-flex justify-content-between align-items-center py-1 px-2"
                )
            )
        
        if not file_items:
            file_items = [dbc.ListGroupItem("暂无上传文件", className="text-center text-muted py-2")]
        
        return dbc.ListGroup(file_items, className="small"), files
    
    # 已移除历史会话相关功能
    
    # 添加一个请求状态存储，用于跟踪消息发送状态
    app.clientside_callback(
        """
        function(n_clicks, n_submit) {
            // 如果按钮被点击或回车键被按下，显示加载状态
            var triggered = window.dash_clientside.callback_context.triggered.map(t => t.prop_id);
            if (triggered.includes('send-message-btn.n_clicks') || triggered.includes('chat-input.n_submit')) {
                // 显示发送按钮的加载状态
                document.getElementById('send-message-btn').classList.add('btn-sending');
                document.getElementById('send-message-btn').disabled = true;
                return true;
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("request-state-store", "data"),
        Input("send-message-btn", "n_clicks"),
        Input("chat-input", "n_submit")
    )
    
    # 第一个回调函数: 只处理消息发送和显示等待效果
    @app.callback(
        Output("chat-messages-container", "children", allow_duplicate=True),
        Output("chat-input", "value"),
        Output("message-processing-store", "data"),
        Input("send-message-btn", "n_clicks"),
        Input("chat-input", "n_submit"),
        State("chat-input", "value"),
        State("chat-session-store", "data"),
        State("chat-messages-container", "children"),
        prevent_initial_call=True
    )
    def send_message_stage1(n_clicks, n_submit, message, session_data, current_messages):
        """第一阶段: 显示用户消息和等待状态"""
        print(f"发送消息第一阶段: 点击={n_clicks}, 回车={n_submit}, 消息={message}")
        
        # 检查触发器和消息
        if not dash.callback_context.triggered or not message or message.strip() == "":
            print("没有有效的触发器或消息")
            return dash.no_update, dash.no_update, dash.no_update
        
        # 初始化数据结构
        if current_messages is None:
            current_messages = []
        
        if session_data is None:
            session_data = {"session_id": str(uuid.uuid4()), "messages": []}
        
        # 检查API密钥
        if not deepseek_api.api_key:
            error_msg = html.Div(
                [
                    html.Div(
                        "请先设置API密钥",
                        className="p-3 mb-2 bg-danger text-white rounded-3"
                    )
                ],
                className="d-flex justify-content-start mb-3"
            )
            return current_messages + [error_msg], "", {"message": message, "error": True}
        
        # 创建用户消息元素
        user_message_div = html.Div(
            [
                html.Div(
                    message,
                    className="p-3 mb-2 bg-light rounded-3"
                )
            ],
            className="d-flex justify-content-end mb-3",
            id={"type": "user-message", "index": n_clicks or n_submit or 0}
        )
        
        # 创建加载消息元素 - 增强视觉反馈
        waiting_div = html.Div(
            [
                html.Div(
                    [
                        html.Span("正在生成回复", className="me-2 fw-bold"),
                        html.Div(className="spinner-border text-primary", 
                                style={"width": "1.2rem", "height": "1.2rem"})
                    ],
                    className="p-3 mb-2 bg-light bg-opacity-75 rounded-3 d-flex align-items-center shadow-sm"
                )
            ],
            className="d-flex justify-content-start mb-3",
            id="waiting-message-container"
        )
        
        # 将消息存储起来供第二阶段使用
        return current_messages + [user_message_div, waiting_div], "", {"message": message, "session_data": session_data}
    
    # 第二个回调函数: 处理API响应并更新最终消息
    @app.callback(
        Output("chat-messages-container", "children", allow_duplicate=True),
        Output("chat-session-store", "data", allow_duplicate=True),
        Output("request-state-store", "data", allow_duplicate=True),
        Input("message-processing-store", "data"),
        State("model-dropdown", "value"),
        State("uploaded-files-store", "data"),
        State("chat-session-store", "data"),
        State("chat-messages-container", "children"),
        prevent_initial_call=True
    )
    def send_message_stage2(processing_data, model, uploaded_files, session_data, current_messages):
        """第二阶段: 处理API调用并返回AI响应"""
        print(f"发送消息第二阶段: 处理数据={processing_data}")
        
        # 如果没有处理数据或有错误，直接返回
        if not processing_data or processing_data.get("error", False):
            return dash.no_update, dash.no_update, False
            
        message = processing_data.get("message")
        session_data = processing_data.get("session_data") or session_data
        
        # 更新会话历史
        messages = session_data.get("messages", [])
        messages.append({"role": "user", "content": message})
        
        try:
            # 准备文件路径列表
            file_paths = [file["path"] for file in uploaded_files] if uploaded_files else []
            
            # 调用相应的API
            if file_paths:
                response = deepseek_api.chat_with_file(messages, file_paths, model=model)
            else:
                response = deepseek_api.chat(messages, model=model)
            
            # 处理响应
            if "error" in response:
                ai_message = f"错误: {response['error']}"
            else:
                ai_message = response.get("choices", [{}])[0].get("message", {}).get("content", "无响应")
            
            # 添加AI回复到会话历史
            messages.append({"role": "assistant", "content": ai_message})
            
            # 移除保存会话历史功能
            session_id = session_data.get("session_id")
            
            # 创建AI回复消息元素
            ai_message_div = html.Div(
                [
                    html.Div(
                        ai_message.replace("\n", "\n\n"),  # 增加换行间距，提高可读性
                        className="p-3 mb-2 bg-primary text-white rounded-3 message-content",
                        style={
                            "white-space": "pre-wrap",  # 保留换行和空格
                            "overflow-wrap": "break-word",  # 长文本自动换行
                            "font-family": "'Segoe UI', sans-serif",  # 使用易读字体
                            "line-height": "1.5",  # 增加行高
                        }
                    )
                ],
                className="d-flex justify-content-start mb-3"
            )
            
            # 更新会话数据
            updated_session_data = {"session_id": session_id, "messages": messages}
            
            # 引用所有消息，除了等待消息
            final_messages = [msg for msg in current_messages if not (isinstance(msg, dict) and msg.get('id') == 'waiting-message-container')]
            
            # 添加AI回复
            if len(final_messages) > 0 and len(final_messages) == len(current_messages):
                # 如果没有移除等待消息，可能是因为它不存在
                # 尝试找到最后一个用户消息，并在其后添加AI回复
                user_msg_indices = [
                    i for i, msg in enumerate(current_messages) 
                    if isinstance(msg, dict) and isinstance(msg.get('id'), dict) and msg.get('id', {}).get('type') == 'user-message'
                ]
                
                if user_msg_indices:
                    last_user_index = user_msg_indices[-1]
                    final_messages = current_messages[:last_user_index+1] + [ai_message_div] + current_messages[last_user_index+1:]
                else:
                    # 如果找不到用户消息，直接添加到最后
                    final_messages = current_messages + [ai_message_div]
            else:
                # 添加AI回复到用户消息之后
                final_messages.append(ai_message_div)
            
            return final_messages, updated_session_data, False
            
        except Exception as e:
            # 异常处理
            print(f"错误发生: {str(e)}")
            traceback.print_exc()
            
            # 创建错误消息
            error_div = html.Div(
                [
                    html.Div(
                        f"发生错误: {str(e)}",
                        className="p-3 mb-2 bg-danger text-white rounded-3"
                    )
                ],
                className="d-flex justify-content-start mb-3"
            )
            
            # 替换等待消息为错误消息
            final_messages = [msg for msg in current_messages if not (isinstance(msg, dict) and msg.get('id') == 'waiting-message-container')]
            final_messages.append(error_div)
            
            return final_messages, session_data, False

    # 更新当前模型显示
    @app.callback(
        Output("current-model-display", "children"),
        Input("model-dropdown", "value")
    )
    def update_model_display(model):
        model_names = {
            "deepseek-reasoner": "DeepSeek-R1 (推理增强)",
            "deepseek-chat": "DeepSeek Chat (通用对话)",
            "deepseek-coder": "DeepSeek Coder (代码专家)"
        }
        return model_names.get(model, model)
