# core/memory/conversation_log.py
# 对话日志管理器
# 职责：存储和检索短期对话历史，用于前端展示
# 设计：内存存储，重启后数据会丢失，仅用于展示最近的对话内容

import time
from typing import List, Dict


class ConversationLog:
    """
    对话日志管理器
    
    职责：
    - 存储会话的短期对话历史
    - 提供最近对话的查询接口
    - 支持按会话ID管理不同的对话记录
    
    设计：
    - 内存存储，重启后数据会丢失
    - 仅用于前端展示，与长期记忆(PowerMem)严格分离
    - 按会话ID组织对话记录，防止记忆串用
    """

    def __init__(self):
        """
        初始化对话日志管理器
        
        创建一个空的对话日志字典，键为会话ID，值为对话记录列表
        """
        self._logs: Dict[str, List[Dict]] = {}

    def append(self, session_id: str, user_msg: str, ai_msg: str):
        """
        添加对话记录到指定会话
        
        参数：
        - session_id (str)：会话ID
        - user_msg (str)：用户输入的消息
        - ai_msg (str)：AI生成的回复
        
        功能：
        - 如果会话ID不存在，自动创建新的会话记录列表
        - 为每条记录添加时间戳（秒级）
        - 将用户消息和AI回复存储为字典格式
        """
        self._logs.setdefault(session_id, []).append({
            "timestamp": int(time.time()),
            "user": user_msg,
            "assistant": ai_msg,
        })

    def recent(self, session_id: str, limit: int = 6) -> List[Dict]:
        """
        获取指定会话的最近对话记录
        
        参数：
        - session_id (str)：会话ID
        - limit (int)：返回的最大记录数，默认6条
        
        返回：
        - List[Dict]：对话记录列表，每条记录包含timestamp、user和assistant字段
        
        功能：
        - 如果会话ID不存在，返回空列表
        - 返回最近的limit条记录，按时间顺序排列
        """
        return self._logs.get(session_id, [])[-limit:]
