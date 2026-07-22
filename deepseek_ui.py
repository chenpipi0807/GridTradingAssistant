"""DeepSeek UI 模块 - 流式对话 + 多轮对话支持"""
import dash
from dash import dcc, html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import os
import uuid
import json
import traceback
import threading
from datetime import datetime
import pandas as pd

from deepseek_api import DeepSeekAPI
import utils

# 创建缓存目录
chattemp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chattemp")
os.makedirs(chattemp_dir, exist_ok=True)

# 初始化 DeepSeek API
deepseek_api = DeepSeekAPI()
DEFAULT_MODEL = "deepseek-v4-pro"

# 界面配置常量
CHAT_CONTAINER_HEIGHT = "calc(70vh - 150px)"

# ---- 流式输出全局状态 ----
_streaming_sessions = {}  # {session_id: {"text": "...", "done": bool, "error": str|None}}
_stream_lock = threading.Lock()


def _run_stream_api(session_id, model, messages, file_paths):
    """后台线程: 流式调用 DeepSeek API, 实时写入 _streaming_sessions"""
    try:
        if file_paths:
            generator = deepseek_api.chat_with_file(
                model=model, messages=messages,
                file_paths=file_paths, stream=True
            )
        else:
            generator = deepseek_api.chat(
                model=model, messages=messages, stream=True
            )

        full_text = ""
        for chunk in generator:
            if isinstance(chunk, dict):
                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if delta:
                    full_text += delta
                    with _stream_lock:
                        _streaming_sessions[session_id] = {"text": full_text, "done": False}

        with _stream_lock:
            _streaming_sessions[session_id] = {"text": full_text, "done": True}

    except Exception as e:
        traceback.print_exc()
        with _stream_lock:
            _streaming_sessions[session_id] = {
                "text": f"调用 API 时出错: {str(e)}",
                "done": True,
                "error": str(e)
            }


def get_stock_data_info():
    """获取当前股票数据文件信息"""
    stock_info = {
        "exists": False,
        "stock_code": "未知",
        "stock_name": "未知",
        "date_range": "",
        "file_path": ""
    }

    stock_file_path = os.path.join(chattemp_dir, "current_stock_data.csv")
    stock_info_path = os.path.join(chattemp_dir, "current_stock_info.json")

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

    if os.path.exists(stock_file_path):
        stock_info["exists"] = True
        stock_info["file_path"] = stock_file_path

        try:
            df = pd.read_csv(stock_file_path)
            if len(df) > 0:
                if stock_info["stock_code"] == "未知":
                    for code_col in ['code', 'stock_code', '代码', '股票代码']:
                        if code_col in df.columns:
                            stock_info["stock_code"] = str(df.iloc[0][code_col])
                            break

                if stock_info["stock_name"] == "未知":
                    for name_col in ['name', 'stock_name', '名称', '股票名称']:
                        if name_col in df.columns:
                            stock_info["stock_name"] = str(df.iloc[0][name_col])
                            break

                if stock_info["stock_code"].isdigit():
                    code = stock_info["stock_code"]
                    if len(code) == 6:
                        stock_info["stock_code"] = f"sh{code}" if code.startswith('6') else f"sz{code}"

                if not stock_info["date_range"] and 'date' in df.columns:
                    stock_info["date_range"] = f"{df['date'].iloc[0]} 至 {df['date'].iloc[-1]}"
        except Exception as e:
            print(f"读取股票数据文件时出错: {str(e)}")

    return stock_info


def _make_message_div(role, content, msg_id=None):
    """创建一条聊天消息的 Div"""
    if role == "user":
        return html.Div(
            html.Div(content, className="p-3 mb-2 bg-light rounded"),
            className="d-flex justify-content-end mb-3",
            id=msg_id
        )
    else:
        return html.Div(
            html.Div(
                dcc.Markdown(content, className="chat-markdown", dangerously_allow_html=True),
                className="p-3 mb-2 bg-primary bg-opacity-10 rounded"
            ),
            className="d-flex justify-content-start mb-3",
            id=msg_id
        )


def get_deepseek_layout():
    """获取 DeepSeek 对话标签页的布局"""

    session_id = str(uuid.uuid4())
    initial_messages = []
    stock_info = get_stock_data_info()

    layout = html.Div([
        dbc.Row([
            # 左侧控制面板
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
                        dbc.Label("模型选择", className="small fw-bold"),
                        dbc.Select(
                            id="model-selector",
                            options=[
                                {"label": "DeepSeek V4 Pro (高性能)", "value": "deepseek-v4-pro"},
                                {"label": "DeepSeek V4 Flash (极速响应)", "value": "deepseek-v4-flash"},
                            ],
                            value=DEFAULT_MODEL,
                            size="sm",
                            className="border-light-subtle",
                        ),
                    ]),
                ], className="mb-3 shadow-sm"),

                # 股票数据卡片
                dbc.Card([
                    dbc.CardHeader(html.H6("对话股票数据", className="mb-0 fw-bold")),
                    dbc.CardBody([
                        dbc.Label("选择要分析的股票", className="small fw-bold mb-1"),
                        dcc.Dropdown(
                            id="deepseek-stock-selector",
                            placeholder="选择已加载的股票数据...",
                            className="mb-2 small",
                            style={"fontSize": "11px"},
                            clearable=True,
                        ),
                        html.Div(
                            id="deepseek-stock-info",
                            children=[
                                html.Div([
                                    html.Strong(f"{stock_info['stock_code']} ", className="me-1"),
                                    html.Span(f"({stock_info['stock_name']})", className="text-muted")
                                ] if stock_info["exists"] else "未选择股票数据", className="mb-1"),
                                html.Div(
                                    f"日期: {stock_info['date_range']}" if stock_info["exists"] else "",
                                    className="small text-muted"
                                ),
                            ] if stock_info["exists"] else "未选择股票数据",
                            className="p-2 bg-light rounded mb-2" if stock_info["exists"] else "text-center text-muted py-2"
                        ),
                        html.Div([
                            dbc.Label("发送数据给AI", className="me-2 small", html_for="use-stock-data-switch"),
                            dbc.Switch(id="use-stock-data-switch", value=True, className="d-inline-block")
                        ], className="d-flex align-items-center mt-2"),
                        html.Div(
                            "💡 提示：先在「行情分析」中加载股票数据，再回到此处选择对话",
                            className="small text-muted mt-2"
                        ),
                    ]),
                ], className="mb-3 shadow-sm"),

                # 使用提示
                dbc.Card([
                    dbc.CardHeader(html.H6("使用提示", className="mb-0 fw-bold")),
                    dbc.CardBody([
                        html.P("本系统使用 DeepSeek V4 大模型进行对话，支持以下功能：", className="mb-2"),
                        html.Ul([
                            html.Li("解析股票数据并提供专业分析"),
                            html.Li("根据历史数据计算适合的网格交易参数"),
                            html.Li("流式输出 + 多轮对话"),
                            html.Li("自动使用选中的股票数据")
                        ], className="ps-3 mb-0"),
                    ]),
                ], className="shadow-sm"),
            ], width=3),

            # 右侧对话区域
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.H5("DeepSeek V4 对话", className="mb-0 d-inline fw-bold"),
                            html.Button(
                                "新会话",
                                id="new-chat-btn",
                                className="btn btn-sm btn-outline-primary float-end"
                            ),
                        ]),
                    ]),

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

                        # 常用问题
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
                                html.Span("发送", style={"fontSize": "14px", "fontWeight": "500"}),
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
        dcc.Store(id="deepseek-stock-file-store", data=None),
        # 流式输出用：当前正在流式输出的 session_id + 轮询定时器
        dcc.Store(id="streaming-state-store", data={"active_session": "", "done": True}),
        dcc.Interval(id="chat-stream-interval", interval=200, disabled=True),
    ])

    return layout


def register_callbacks(app):
    """注册 DeepSeek UI 相关的回调函数"""

    # ---- 保存 API 密钥 ----
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

    # ---- 加载股票选择器选项 ----
    @app.callback(
        [Output("deepseek-stock-selector", "options"),
         Output("deepseek-stock-selector", "value")],
        Input("tabs", "active_tab"),
        State("deepseek-stock-selector", "value"),
    )
    def load_stock_selector_options(active_tab, current_value):
        if active_tab != "deepseek-tab":
            return dash.no_update, dash.no_update

        files = utils.get_temp_stock_files()
        if not files:
            return [], None

        options = [{"label": f["label"], "value": f["file_path"]} for f in files]
        default_value = current_value if current_value else files[0]["file_path"]
        return options, default_value

    # ---- 股票选择变化 ----
    @app.callback(
        [Output("deepseek-stock-info", "children"),
         Output("deepseek-stock-file-store", "data")],
        Input("deepseek-stock-selector", "value"),
    )
    def on_stock_selected(file_path):
        if not file_path:
            return html.Div("未选择股票数据", className="text-center text-muted py-2"), None

        files = utils.get_temp_stock_files()
        selected = next((f for f in files if f["file_path"] == file_path), None)

        if not selected:
            return html.Div("未选择股票数据", className="text-center text-muted py-2"), None

        info_div = html.Div([
            html.Div([
                html.Strong(f"{selected['code']} ", className="me-1"),
                html.Span(f"({selected['name']})", className="text-muted")
            ], className="mb-1"),
            html.Div(
                f"日期: {selected['date_range']}" if selected.get('date_range') else "",
                className="small text-muted"
            ),
        ], className="p-2 bg-light rounded mb-2")

        return info_div, file_path

    # ---- 新会话 ----
    @app.callback(
        [Output("chat-session-store", "data", allow_duplicate=True),
         Output("chat-messages-container", "children", allow_duplicate=True),
         Output("streaming-state-store", "data", allow_duplicate=True),
         Output("chat-stream-interval", "disabled", allow_duplicate=True)],
        Input("new-chat-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def create_new_session(n_clicks):
        session_id = str(uuid.uuid4())
        new_session = {"session_id": session_id, "messages": []}
        return new_session, [], {"active_session": "", "done": True}, True

    # ---- 快捷问题 ----
    @app.callback(
        Output("chat-input", "value", allow_duplicate=True),
        [Input("quick-q1", "n_clicks"), Input("quick-q2", "n_clicks"),
         Input("quick-q3", "n_clicks"), Input("quick-q4", "n_clicks"),
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

    # ---- 发送消息（合并为单阶段 + 启动后台流式线程）----
    @app.callback(
        [Output("chat-messages-container", "children", allow_duplicate=True),
         Output("chat-input", "value", allow_duplicate=True),
         Output("chat-session-store", "data", allow_duplicate=True),
         Output("streaming-state-store", "data", allow_duplicate=True),
         Output("chat-stream-interval", "disabled", allow_duplicate=True)],
        [Input("send-message-btn", "n_clicks"),
         Input("chat-input", "n_submit")],
        [State("chat-input", "value"),
         State("chat-session-store", "data"),
         State("chat-messages-container", "children"),
         State("use-stock-data-switch", "value"),
         State("model-selector", "value"),
         State("deepseek-stock-file-store", "data")],
        prevent_initial_call=True
    )
    def send_message(n_clicks, n_submit, message, session_data, current_messages,
                     use_stock_data_switch, selected_model, selected_stock_file):
        if not ctx.triggered or not message or message.strip() == "":
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        if current_messages is None:
            current_messages = []
        if session_data is None:
            session_data = {"session_id": str(uuid.uuid4()), "messages": []}

        # 检查 API 密钥
        if not deepseek_api.api_key:
            error_div = _make_message_div("assistant", "⚠️ 请先在左侧设置 DeepSeek API 密钥")
            return current_messages + [error_div], "", dash.no_update, dash.no_update, dash.no_update

        # 1) 显示用户消息 + 空的 AI 占位
        user_div = _make_message_div("user", message.strip())
        ai_placeholder = html.Div(
            html.Div(
                html.Span("▊", style={"animation": "blink 1s infinite", "color": "#7D5BA6"}),
                className="p-3 mb-2 bg-primary bg-opacity-10 rounded"
            ),
            className="d-flex justify-content-start mb-3",
            id="streaming-ai-message"
        )
        new_children = list(current_messages) + [user_div, ai_placeholder]

        # 2) 构建 API 消息上下文
        messages = list(session_data.get("messages", []))
        messages.append({"role": "user", "content": message.strip()})

        # 限制消息历史长度
        if len(messages) > 20:
            messages = messages[-20:]

        # 3) 准备文件路径
        stock_file_path = selected_stock_file if (selected_stock_file and os.path.exists(selected_stock_file)) else None
        file_paths = [stock_file_path] if (stock_file_path and use_stock_data_switch) else None

        model = selected_model or DEFAULT_MODEL
        session_id = session_data.get("session_id", str(uuid.uuid4()))

        # 4) 启动后台流式线程
        thread = threading.Thread(
            target=_run_stream_api,
            args=(session_id, model, list(messages), file_paths),
            daemon=True
        )
        thread.start()

        # 5) 更新 session store（暂存用户消息，AI 回复在流式完成后追加）
        updated_session = {
            "session_id": session_id,
            "messages": messages
        }

        # 6) 启用心跳定时器
        streaming_state = {"active_session": session_id, "done": False}

        return new_children, "", updated_session, streaming_state, False

    # ---- 流式轮询：每 200ms 更新 AI 回复内容 ----
    @app.callback(
        [Output("chat-messages-container", "children", allow_duplicate=True),
         Output("chat-session-store", "data", allow_duplicate=True),
         Output("streaming-state-store", "data", allow_duplicate=True),
         Output("chat-stream-interval", "disabled", allow_duplicate=True)],
        Input("chat-stream-interval", "n_intervals"),
        [State("streaming-state-store", "data"),
         State("chat-messages-container", "children"),
         State("chat-session-store", "data")],
        prevent_initial_call=True
    )
    def stream_update(n_intervals, streaming_state, current_messages, session_data):
        if not streaming_state:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

        session_id = streaming_state.get("active_session", "")
        if not session_id:
            return dash.no_update, dash.no_update, dash.no_update, True

        with _stream_lock:
            state = _streaming_sessions.get(session_id)

        if state is None:
            # 还没开始
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

        if not current_messages:
            current_messages = []

        # 更新最后一条 AI 消息的内容
        text = state.get("text", "")
        done = state.get("done", False)
        has_error = state.get("error")

        if text:
            updated_ai = html.Div(
                html.Div(
                    dcc.Markdown(text, className="chat-markdown", dangerously_allow_html=True),
                    className="p-3 mb-2 bg-primary bg-opacity-10 rounded"
                ),
                className="d-flex justify-content-start mb-3",
                id="streaming-ai-message"
            )
            # 替换占位符
            new_messages = []
            for msg in current_messages:
                if hasattr(msg, 'id') and getattr(msg, 'id', None) == "streaming-ai-message":
                    new_messages.append(updated_ai)
                else:
                    new_messages.append(msg)
        else:
            new_messages = list(current_messages)

        if done:
            # 流式完成：将 AI 回复写入会话历史
            if text and not has_error:
                messages = list(session_data.get("messages", []))
                messages.append({"role": "assistant", "content": text})
                updated_session = {
                    "session_id": session_id,
                    "messages": messages
                }
            else:
                updated_session = dash.no_update

            # 清理
            with _stream_lock:
                _streaming_sessions.pop(session_id, None)

            return new_messages, updated_session, {"active_session": "", "done": True}, True

        # 继续轮询
        return new_messages, dash.no_update, dash.no_update, dash.no_update
