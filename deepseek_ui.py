"""DeepSeek UI 模块 - 提供 DeepSeek 对话界面的 Dash 组件

这是一个重新设计的简化版本，专注于:
- 只支持 DeepSeek R1 模型（无模型选择）
- 默认流式输出
- 支持多轮对话（会话内存储，非持久化）
- 从 key.txt 加载 API 密钥
- 默认加载股票数据
"""
import dash
from dash import dcc, html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import os
import uuid
import json
import traceback
from datetime import datetime
import pandas as pd

from deepseek_api import DeepSeekAPI

# 创建缓存目录
chattemp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chattemp")
os.makedirs(chattemp_dir, exist_ok=True)

# 初始化 DeepSeek API - 只使用 R1 模型
deepseek_api = DeepSeekAPI()
DEFAULT_MODEL = "deepseek-reasoner"  # DeepSeek R1 模型

# 界面配置常量
CHAT_CONTAINER_HEIGHT = "calc(70vh - 150px)"  # 减小聊天容器高度

def get_stock_data_info():
    """获取当前股票数据文件信息"""
    stock_info = {
        "exists": False,
        "stock_code": "未知",
        "stock_name": "未知",
        "date_range": "",
        "file_path": ""
    }
    
    # 检查默认股票数据文件是否存在
    stock_file_path = os.path.join(chattemp_dir, "current_stock_data.csv")
    stock_info_path = os.path.join(chattemp_dir, "current_stock_info.json")
    
    # 先尝试从JSON文件读取信息（如果存在）
    if os.path.exists(stock_info_path):
        try:
            with open(stock_info_path, 'r', encoding='utf-8') as f:
                info_data = json.load(f)
                if "code" in info_data:
                    stock_info["stock_code"] = info_data["code"]
                if "name" in info_data:
                    stock_info["stock_name"] = info_data["name"]
                if "period" in info_data:
                    stock_info["date_range"] = info_data["period"]
        except Exception as e:
            print(f"读取股票信息JSON文件时出错: {str(e)}")
    
    # 检查CSV文件并补充缺失的信息
    if os.path.exists(stock_file_path):
        stock_info["exists"] = True
        stock_info["file_path"] = stock_file_path
        
        # 尝试读取CSV数据了解股票信息
        try:
            df = pd.read_csv(stock_file_path)
            if len(df) > 0:
                # 如果从JSON文件获取不到股票代码和名称，则尝试从CSV文件中获取
                if stock_info["stock_code"] == "未知":
                    # 获取股票代码 - 尝试可能的列名
                    for code_col in ['code', 'stock_code', '代码', '股票代码']:
                        if code_col in df.columns:
                            stock_info["stock_code"] = str(df.iloc[0][code_col])
                            break
                
                if stock_info["stock_name"] == "未知":
                    # 获取股票名称 - 尝试可能的列名
                    for name_col in ['name', 'stock_name', '名称', '股票名称']:
                        if name_col in df.columns:
                            stock_info["stock_name"] = str(df.iloc[0][name_col])
                            break
                
                # 如果从CSV和JSON中都无法获取股票代码，尝试从文件名中提取
                if stock_info["stock_code"] == "未知":
                    filename = os.path.basename(stock_file_path)
                    if "_" in filename and not filename.startswith("current"):
                        stock_info["stock_code"] = filename.split("_")[0]
                
                # 检查是否为数字股票代码，如果是则添加前缀
                if stock_info["stock_code"].isdigit():
                    code = stock_info["stock_code"]
                    if len(code) == 6:
                        if code.startswith('6'):
                            stock_info["stock_code"] = f"sh{code}"
                        else:
                            stock_info["stock_code"] = f"sz{code}"
                
                # 如果还没有获取日期范围，尝试从CSV数据中获取
                if not stock_info["date_range"] and 'date' in df.columns:
                    start_date = df['date'].iloc[0]
                    end_date = df['date'].iloc[-1]
                    stock_info["date_range"] = f"{start_date} 至 {end_date}"
        except Exception as e:
            print(f"读取股票数据文件时出错: {str(e)}")
    
    return stock_info

def get_deepseek_layout():
    """获取重新设计的 DeepSeek 对话标签页的布局"""
    
    # 初始化会话数据
    session_id = str(uuid.uuid4())
    initial_messages = []
    
    # 获取股票数据信息
    stock_info = get_stock_data_info()
    
    # 构建布局
    layout = html.Div([
        dbc.Row([
            # 左侧控制面板 (25%)
            dbc.Col([
                # API 密钥设置
                dbc.Card([
                    dbc.CardHeader(html.H6("DeepSeek API 设置", className="mb-0 fw-bold")),
                    dbc.CardBody([
                        dbc.InputGroup([
                            dbc.Input(
                                id="api-key-input",
                                placeholder="输入 DeepSeek API 密钥",
                                type="password",
                                value=deepseek_api.api_key or "",
                                className="border-light-subtle",
                            ),
                            dbc.Button("保存", id="save-api-key-btn", color="primary", size="sm"),
                        ], className="mb-3"),
                    ]),
                ], className="mb-3 shadow-sm"),
                
                # 股票数据卡片
                dbc.Card([
                    dbc.CardHeader(html.H6("当前股票数据", className="mb-0 fw-bold")),
                    dbc.CardBody([
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Strong(f"{stock_info['stock_code']} ", className="me-1"),
                                        html.Span(f"({stock_info['stock_name']})", className="text-muted")
                                    ] if stock_info["exists"] else "未加载股票数据",
                                    className="mb-1"
                                ),
                                html.Div(
                                    f"时间范围: {stock_info['date_range']}" if stock_info["exists"] else "",
                                    className="small text-muted"
                                ),
                            ],
                            className="p-2 bg-light rounded mb-3" if stock_info["exists"] else "text-center text-muted py-3"
                        ),
                        # 添加使用股票数据的开关
                        html.Div([
                            dbc.Label("使用当前股票数据", className="me-2", html_for="use-stock-data-switch"),
                            dbc.Switch(
                                id="use-stock-data-switch",
                                value=True,  # 默认开启
                                className="d-inline-block"
                            )
                        ], className="d-flex align-items-center mt-2") if stock_info["exists"] else None,
                    ]),
                ], className="mb-3 shadow-sm"),
                
                # 使用提示卡片
                dbc.Card([
                    dbc.CardHeader(html.H6("使用提示", className="mb-0 fw-bold")),
                    dbc.CardBody([
                        html.P("本系统使用 DeepSeek R1 大模型进行对话，支持以下功能：", className="mb-2"),
                        html.Ul([
                            html.Li("解析股票数据并提供专业分析"),
                            html.Li("根据历史数据计算适合的网格交易参数"),
                            html.Li("多轮对话，持续深入探讨股票问题"),
                            html.Li("自动使用当前已加载的股票数据")
                        ], className="ps-3 mb-0"),
                    ]),
                ], className="shadow-sm"),
            ], width=3),
            
            # 右侧对话区域 (75%)
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.H5("DeepSeek R1 对话", className="mb-0 d-inline fw-bold"),
                            html.Button(
                                "新会话",
                                id="new-chat-btn",
                                className="btn btn-sm btn-outline-primary float-end"
                            ),
                        ]),
                    ]),
                    
                    # 对话内容区域
                    dbc.CardBody([
                        # 消息容器
                        html.Div(
                            id="chat-messages-container",
                            className="chat-container mb-4",
                            style={
                                "height": CHAT_CONTAINER_HEIGHT,
                                "overflowY": "auto",
                                "padding": "10px",
                                "scrollBehavior": "smooth"
                            }
                        ),
                        
                        # 常用问题快捷选择
                        html.Div([
                            html.Strong("常用问题：", className="me-2"),
                            html.Div([
                                dbc.Button("分析股票走势", id="quick-q1", color="light", size="sm", className="me-1 mb-1"),
                                dbc.Button("计算网格交易参数", id="quick-q2", color="light", size="sm", className="me-1 mb-1"),
                                dbc.Button("适合做网格交易吗", id="quick-q3", color="light", size="sm", className="me-1 mb-1"),
                                dbc.Button("解读中间价和振幅", id="quick-q4", color="light", size="sm", className="me-1 mb-1"),
                                dbc.Button("分析ATR指标与波动性", id="quick-q5", color="light", size="sm", className="me-1 mb-1"),
                            ]),
                        ], className="mb-3"),
                        
                        # 输入区域
                        dbc.InputGroup([
                            dbc.Textarea(
                                id="chat-input",
                                placeholder="在此输入问题...",
                                style={"resize": "none", "height": "80px"},
                                className="border rounded-start"
                            ),
                            dbc.Button(
                                html.I(className="fas fa-paper-plane"),
                                id="send-message-btn",
                                color="primary",
                                className="rounded-end d-flex align-items-center"
                            ),
                        ]),
                        
                        # 状态提示
                        dbc.Alert(
                            id="chat-status-alert",
                            color="warning",
                            dismissable=True,
                            is_open=False,
                            className="mt-3 mb-0 py-2"
                        ),
                    ], className="p-3"),
                ], className="shadow-sm h-100"),
            ], width=9),
        ]),
        
        # 存储组件
        dcc.Store(id="chat-session-store", data={"session_id": session_id, "messages": initial_messages}),
        dcc.Store(id="message-processing-store", data=None),
        dcc.Store(id="request-state-store", data={"processing": False}),
    ])
    
    return layout

def register_callbacks(app):
    """注册 DeepSeek UI 相关的回调函数"""
    
    # 保存 API 密钥回调
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
            return True, "API 密钥不能为空", "warning"
        
        success = deepseek_api.save_api_key(api_key)
        if success:
            return True, "API 密钥保存成功", "success"
        else:
            return True, "API 密钥保存失败", "danger"
    
    # 新会话按钮回调
    @app.callback(
        [Output("chat-session-store", "data"),
         Output("chat-messages-container", "children")],
        Input("new-chat-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def create_new_session(n_clicks):
        session_id = str(uuid.uuid4())
        new_session = {"session_id": session_id, "messages": []}
        return new_session, []
    
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
            "quick-q4": "请分析解读数据中的中间价、相对振幅、ATR等指标并给出具体的交易建议",
            "quick-q5": "请分析ATR指标情况并制定网格交易策略"
        }
        
        return questions.get(trigger_id, "")
    
    # 第一阶段：显示用户消息和等待状态
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
        # 检查触发器和消息
        if not ctx.triggered or not message or message.strip() == "":
            return dash.no_update, dash.no_update, dash.no_update
        
        # 初始化数据结构
        if current_messages is None:
            current_messages = []
        
        if session_data is None:
            session_data = {"session_id": str(uuid.uuid4()), "messages": []}
        
        # 检查 API 密钥
        if not deepseek_api.api_key:
            error_msg = html.Div(
                [
                    html.Div(
                        "请先设置 API 密钥",
                        className="p-3 mb-2 bg-danger text-white rounded"
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
                    className="p-3 mb-2 bg-light rounded"
                )
            ],
            className="d-flex justify-content-end mb-3",
            id={"type": "user-message", "index": n_clicks or n_submit or 0}
        )
        
        # 创建加载消息元素
        waiting_div = html.Div(
            [
                html.Div(
                    [
                        html.Span("正在生成回复", className="me-2"),
                        html.Div(className="spinner-border spinner-border-sm text-primary")
                    ],
                    className="p-3 mb-2 bg-light bg-opacity-75 rounded d-flex align-items-center"
                )
            ],
            className="d-flex justify-content-start mb-3",
            id="waiting-message-container"
        )
        
        # 将消息存储起来供第二阶段使用
        return current_messages + [user_message_div, waiting_div], "", {"message": message, "session_data": session_data}
    
    # 第二阶段：调用 API 并渲染回复
    @app.callback(
        Output("chat-messages-container", "children", allow_duplicate=True),
        Output("chat-session-store", "data", allow_duplicate=True),
        Output("request-state-store", "data"),
        Input("message-processing-store", "data"),
        State("use-stock-data-switch", "value"),
        prevent_initial_call=True
    )
    def send_message_stage2(processing_data, use_stock_data_switch):
        # 检查数据有效性
        if not processing_data or "error" in processing_data:
            return dash.no_update, dash.no_update, {"processing": False}
        
        # 提取消息和会话数据
        message = processing_data.get("message", "")
        session_data = processing_data.get("session_data", {"session_id": str(uuid.uuid4()), "messages": []})
        
        # 准备消息上下文
        messages = session_data.get("messages", [])
        updated_messages = messages + [{"role": "user", "content": message}]
        
        # 检查是否有股票数据可用
        stock_info = get_stock_data_info()
        # 不仅数据需要存在，还需要开关处于开启状态
        use_stock_data = stock_info["exists"] and use_stock_data_switch
        stock_file_path = stock_info["file_path"] if use_stock_data else None
        
        # 如果开关关闭但有股票数据，将这一情况加入用户消息的上下文
        if stock_info["exists"] and not use_stock_data_switch:
            # 向消息列表添加一条系统消息，提醒用户当前不使用股票数据
            if len(updated_messages) > 0 and updated_messages[-1]["role"] == "user":
                system_note = f"注意：您已经手动关闭了股票数据的使用，当前对话不会包含 {stock_info['stock_code']} ({stock_info['stock_name']}) 的数据。"
        
        # 为防止消息列表过长，只保留最近的最多 10 条消息
        if len(updated_messages) > 10:
            # 始终保留系统消息
            system_messages = [msg for msg in updated_messages if msg.get("role") == "system"]
            # 取最近的对话消息
            recent_messages = [msg for msg in updated_messages if msg.get("role") != "system"][-9:]
            # 合并
            context_messages = system_messages + recent_messages
        else:
            context_messages = updated_messages
        
        # 构建回复 div
        try:
            # 调用 DeepSeek API 获取响应
            if use_stock_data:
                # 使用文件数据
                response_generator = deepseek_api.chat_with_file(
                    model=DEFAULT_MODEL,
                    messages=context_messages,
                    file_paths=[stock_file_path],  # 作为列表传递
                    stream=True  # 启用流式输出
                )
            else:
                # 普通对话
                response_generator = deepseek_api.chat(
                    model=DEFAULT_MODEL,
                    messages=context_messages,
                    stream=True  # 启用流式输出
                )
            
            # 处理 API 返回的生成器（流式输出）
            full_response = ""
            try:
                if hasattr(response_generator, "__iter__"):
                    for response_chunk in response_generator:
                        if response_chunk:
                            # 正确处理流式响应的字典结构
                            if isinstance(response_chunk, dict):
                                # 提取delta中的内容
                                delta_content = response_chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta_content:
                                    full_response += delta_content
                            elif isinstance(response_chunk, str):
                                # 直接是字符串的情况
                                full_response += response_chunk
                else:
                    # 如果不是生成器，直接获取完整响应
                    # 检查是否是字典类型
                    if isinstance(response_generator, dict):
                        full_response = response_generator.get("choices", [{}])[0].get("message", {}).get("content", "")
                    else:
                        full_response = str(response_generator)
            except Exception as e:
                print(f"处理流式响应时出错: {str(e)}")
                traceback.print_exc()
                full_response = f"处理响应时出错: {str(e)}"
            
            # 创建 AI 回复元素
            ai_message_div = html.Div(
                [
                    html.Div(
                        dcc.Markdown(
                            full_response,
                            className="chat-markdown",
                            dangerously_allow_html=True
                        ),
                        className="p-3 mb-2 bg-primary bg-opacity-10 rounded"
                    )
                ],
                className="d-flex justify-content-start mb-3"
            )
            
            # 更新会话数据
            updated_messages.append({"role": "assistant", "content": full_response})
            updated_session_data = {
                "session_id": session_data.get("session_id", str(uuid.uuid4())),
                "messages": updated_messages
            }
            
            # 查找并替换等待消息
            current_messages = dash.callback_context.outputs_list[0]
            if current_messages:
                # 移除等待提示
                new_messages = [msg for msg in current_messages if getattr(msg, 'id', None) != "waiting-message-container"]
                # 添加 AI 回复
                new_messages.append(ai_message_div)
                return new_messages, updated_session_data, {"processing": False}
            
            # 如果出现异常情况，至少返回一个消息
            return [ai_message_div], updated_session_data, {"processing": False}
            
        except Exception as e:
            # 处理异常
            error_message = f"调用 DeepSeek API 时出错: {str(e)}"
            print(error_message)
            traceback.print_exc()
            
            # 创建错误消息元素
            error_div = html.Div(
                [
                    html.Div(
                        error_message,
                        className="p-3 mb-2 bg-danger text-white rounded"
                    )
                ],
                className="d-flex justify-content-start mb-3"
            )
            
            # 查找并替换等待消息
            current_messages = dash.callback_context.outputs_list[0]
            if current_messages:
                new_messages = [msg for msg in current_messages if getattr(msg, 'id', None) != "waiting-message-container"]
                new_messages.append(error_div)
                return new_messages, session_data, {"processing": False}
            
            return [error_div], session_data, {"processing": False}