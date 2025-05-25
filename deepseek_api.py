"""DeepSeek API 集成模块 - 提供与DeepSeek大模型的交互功能"""
import os
import json
import requests
from typing import List, Dict, Any, Optional, Union
import time

class DeepSeekAPI:
    """DeepSeek API 客户端类，用于与DeepSeek大模型进行交互"""
    
    def __init__(self, api_key: str = None):
        """
        初始化DeepSeek API客户端
        
        参数:
            api_key: DeepSeek API密钥，如果为None则尝试从本地文件或环境变量获取
        """
        # 首先尝试从参数获取
        self.api_key = api_key
        
        # 如果参数未提供，尝试从本地文件获取
        if not self.api_key:
            key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "key.txt")
            if os.path.exists(key_path):
                try:
                    with open(key_path, 'r', encoding='utf-8') as f:
                        self.api_key = f.read().strip()
                except Exception as e:
                    print(f"从本地文件读取API密钥失败: {e}")
        
        # 如果本地文件也没有，尝试从环境变量获取
        if not self.api_key:
            self.api_key = os.environ.get("DEEPSEEK_API_KEY")
            
        # 如果都没有，设置为None但不抛出异常，让前端处理
        if not self.api_key:
            print("警告: DeepSeek API密钥未提供，需要在前端设置")
            self.api_key = None
            
        # 初始化API基础配置
        self.__post_init__()
    
    def save_api_key(self, api_key: str) -> bool:
        """
        保存API密钥到本地文件
        
        参数:
            api_key: API密钥
            
        返回:
            保存是否成功
        """
        try:
            key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "key.txt")
            with open(key_path, 'w', encoding='utf-8') as f:
                f.write(api_key)
            self.api_key = api_key
            return True
        except Exception as e:
            print(f"保存API密钥失败: {e}")
            return False
        
    def __post_init__(self):
        """初始化API基础配置"""
        self.api_base = "https://api.deepseek.com"
        self.chat_endpoint = "/chat/completions"  # 根据最新文档更新端点
        self.models = {
            "deepseek-reasoner": "deepseek-reasoner",  # 直接使用模型标识符
            "deepseek-chat": "deepseek-chat",
            "deepseek-coder": "deepseek-coder"
        }
        self.default_model = "deepseek-chat"  # 默认使用chat模型
        
        # 创建会话历史缓存目录
        self.chat_history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chattemp")
        os.makedirs(self.chat_history_dir, exist_ok=True)
    
    def chat(self, 
             messages: List[Dict[str, str]], 
             model: str = None, 
             temperature: float = 0.7, 
             max_tokens: int = 2048,
             stream: bool = False) -> Dict[str, Any]:
        """
        与DeepSeek模型进行对话
        
        参数:
            messages: 对话消息列表，格式为[{"role": "user", "content": "你好"}]
            model: 模型名称，默认为deepseek-reasoner
            temperature: 温度参数，控制输出随机性，默认0.7
            max_tokens: 最大生成token数，默认2048
            stream: 是否使用流式输出，默认False
            
        返回:
            API响应结果
        """
        model_id = self.models.get(model or self.default_model, self.models[self.default_model])
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        try:
            response = requests.post(
                f"{self.api_base}{self.chat_endpoint}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def chat_with_file(self, 
                       messages: List[Dict[str, str]], 
                       file_paths: List[str],
                       model: str = None, 
                       temperature: float = 0.7, 
                       max_tokens: int = 2048) -> Dict[str, Any]:
        """
        发送文件并与DeepSeek模型进行对话
        
        参数:
            messages: 对话消息列表
            file_paths: 要发送的文件路径列表
            model: 模型名称，默认为deepseek-reasoner
            temperature: 温度参数，控制输出随机性，默认0.7
            max_tokens: 最大生成token数，默认2048
            
        返回:
            API响应结果
        """
        model_id = self.models.get(model or self.default_model, self.models[self.default_model])
        
        # 如果没有文件，使用标准聊天API
        if not file_paths:
            return self.chat(messages, model, temperature, max_tokens)
            
        # 读取文件内容
        file_contents = []
        try:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    # 直接读取文件内容而不是上传文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_name = os.path.basename(file_path)
                        file_contents.append({"name": file_name, "content": content})
        except Exception as e:
            return {"error": f"读取文件时出错: {str(e)}"}
            
        # 构建新的消息列表，将文件内容添加到消息中
        enriched_messages = messages.copy()
        
        # 将文件内容添加到最后一条用户消息中
        for i in reversed(range(len(enriched_messages))):
            if enriched_messages[i]["role"] == "user":
                # 在用户消息中添加文件内容
                file_text = "\n\n下面是上传的数据文件内容:\n"
                for file in file_contents:
                    file_text += f"\n--- {file['name']} ---\n{file['content']}\n"
                
                enriched_messages[i]["content"] += file_text
                break
        
        # 使用标准chat API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model_id,
            "messages": enriched_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.api_base}{self.chat_endpoint}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def save_chat_history(self, session_id: str, messages: List[Dict[str, str]]) -> bool:
        """
        保存对话历史到本地文件
        
        参数:
            session_id: 会话ID
            messages: 对话消息列表
            
        返回:
            保存是否成功
        """
        try:
            file_path = os.path.join(self.chat_history_dir, f"{session_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存对话历史失败: {e}")
            return False
    
    def load_chat_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        从本地文件加载对话历史
        
        参数:
            session_id: 会话ID
            
        返回:
            对话消息列表，如果加载失败则返回空列表
        """
        try:
            file_path = os.path.join(self.chat_history_dir, f"{session_id}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"加载对话历史失败: {e}")
            return []
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """
        获取可用模型列表
        
        返回:
            模型列表，每个模型包含id和name
        """
        return [
            {"id": "deepseek-reasoner", "name": "DeepSeek-R1 (推理增强)"},
            {"id": "deepseek-chat", "name": "DeepSeek Chat (通用对话)"},
            {"id": "deepseek-coder", "name": "DeepSeek Coder (代码专家)"}
        ]
    
    def get_all_chat_sessions(self) -> List[Dict[str, Any]]:
        """
        获取所有聊天会话
        
        返回:
            会话列表，每个会话包含id、创建时间和第一条消息
        """
        sessions = []
        try:
            for filename in os.listdir(self.chat_history_dir):
                if filename.endswith('.json'):
                    session_id = filename[:-5]  # 移除.json后缀
                    file_path = os.path.join(self.chat_history_dir, filename)
                    
                    # 获取文件修改时间
                    mod_time = os.path.getmtime(file_path)
                    
                    # 读取第一条用户消息作为会话标题
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            messages = json.load(f)
                            # 查找第一条用户消息
                            title = "新对话"
                            for msg in messages:
                                if msg.get("role") == "user":
                                    # 截取前20个字符作为标题
                                    title = msg.get("content", "")[:20]
                                    if len(msg.get("content", "")) > 20:
                                        title += "..."
                                    break
                    except:
                        title = "无法加载对话"
                    
                    sessions.append({
                        "id": session_id,
                        "time": mod_time,
                        "title": title
                    })
            
            # 按时间排序，最新的在前
            sessions.sort(key=lambda x: x["time"], reverse=True)
            
            # 转换时间戳为可读格式
            for session in sessions:
                session["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session["time"]))
            
            return sessions
        except Exception as e:
            print(f"获取会话列表失败: {e}")
            return []
    
    def delete_chat_session(self, session_id: str) -> bool:
        """
        删除聊天会话
        
        参数:
            session_id: 会话ID
            
        返回:
            删除是否成功
        """
        try:
            file_path = os.path.join(self.chat_history_dir, f"{session_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False
