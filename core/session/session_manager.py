# core/session/session_manager.py
# 会话管理器
# 职责：生成和维护会话ID，防止不同NPC或用户的记忆串用
# 设计：单主体版本，后续可扩展为多用户/多主体支持

import uuid
from typing import Optional


class SessionManager:
    """
    会话管理器
    
    职责：
    - 生成唯一的会话ID
    - 验证和重用现有的会话ID
    - 防止不同对话之间的记忆串用
    
    设计：
    - 单主体版本，适用于当前项目需求
    - 后续可扩展为多用户/多主体支持
    """

    def get_or_create(self, session_id: Optional[str]) -> str:
        """
        获取或创建会话ID
        
        参数：
        - session_id (Optional[str])：现有的会话ID，若为None或无效则创建新ID
        
        返回：
        - str：有效的会话ID
        """
        if session_id and isinstance(session_id, str):
            return session_id
        return uuid.uuid4().hex
