# core/agent/langgraph_agent.py
# LangGraph对话代理
# 职责：使用LangGraph编排对话流程，调用LLM生成回复
# 设计：基于状态图的流程编排，整合人物设定、记忆和对话生成

from __future__ import annotations

import os
from typing import TypedDict, List, Any, Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from core.npc.npc_manager import NPCManager
from core.memory.memory_store import MemoryStore
from core.memory.conversation_log import ConversationLog


class AgentState(TypedDict):
    """
    代理状态数据结构
    
    字段说明：
    - session_id (str)：会话ID，用于区分不同的对话
    - npc_id (str)：NPC唯一标识，用于获取人物设定
    - messages (List[Any])：对话消息列表，包含系统提示、用户输入和AI回复
    - response (str)：生成的AI回复内容
    """
    session_id: str
    npc_id: str
    messages: List[Any]
    response: str


class LangGraphAgent:
    """
    LangGraph对话代理
    
    职责：
    - 使用LangGraph构建对话流程
    - 加载人物设定和记忆上下文
    - 调用LLM生成符合角色设定的回复
    - 管理对话历史和长期记忆
    
    协作关系：
    - NPCManager：提供人物设定和系统提示
    - MemoryStore：管理长期记忆的召回和存储
    - ConversationLog：记录短期对话历史用于展示
    """

    def __init__(self, npc_manager: NPCManager):
        """
        初始化LangGraph对话代理
        
        参数：
        - npc_manager (NPCManager)：NPC管理器实例
        """
        self.npc_manager = npc_manager
        self.memory = MemoryStore()
        self.log = ConversationLog()
        self.llm = self._build_llm()
        self.graph = self._build_graph()

    # -------------------------
    # 构建 LLM（兼容 DashScope OpenAI compatible-mode）
    # -------------------------
    def _build_llm(self) -> ChatOpenAI:
        """
        构建LLM实例（兼容DashScope OpenAI兼容模式）
        
        支持的环境变量：
        - API_KEY / OPENAI_API_KEY / DASHSCOPE_API_KEY：API密钥
        - API_BASE_URL / OPENAI_BASE_URL：API基础地址
        - MODEL_NAME / OPENAI_MODEL：模型名称，默认"qwen-turbo"
        
        返回：
        - ChatOpenAI：配置好的LLM实例
        
        异常：
        - RuntimeError：缺少API密钥时抛出
        """
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("API_BASE_URL")
        model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL_NAME") or "qwen-turbo"

        if not api_key:
            raise RuntimeError("Missing API key: set API_KEY (or OPENAI_API_KEY) in .env")

        # base_url 对 openai 官方可为空，但对 DashScope 兼容模式通常需要
        llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        return llm

    # -------------------------
    # LangGraph 构建
    # -------------------------
    def _build_graph(self):
        """
        构建LangGraph状态图
        
        返回：
        - 编译后的LangGraph图实例
        """
        g = StateGraph(AgentState)
        g.add_node("load_context", self._load_context)
        g.add_node("generate", self._generate)

        g.set_entry_point("load_context")
        g.add_edge("load_context", "generate")
        g.add_edge("generate", END)

        return g.compile()

    # -------------------------
    # Node: load_context
    # -------------------------
    def _load_context(self, state: AgentState) -> AgentState:
        """
        加载对话上下文节点
        
        功能：
        - 获取NPC的系统提示
        - 从长期记忆中召回相关记忆
        - 构建完整的上下文消息
        
        参数：
        - state (AgentState)：当前代理状态
        
        返回：
        - AgentState：更新后的代理状态，包含完整的上下文消息
        """
        npc_id = state["npc_id"]
        npc = self.npc_manager.get_npc(npc_id)

        # 找到最新一条用户输入
        user_text = ""
        for m in reversed(state["messages"]):
            if isinstance(m, HumanMessage):
                user_text = m.content
                break

        # 从 PowerMem 召回长期记忆
        memory_block = self.memory.recall(
            session_id=state["session_id"],
            query=user_text,
            k=5,
        )

        system_prompt = npc["prompt"]
        if memory_block:
            system_prompt += f"\n\n【长期记忆】\n{memory_block}"

        # 将 system prompt 作为首条消息（system role 用 AIMessage 承载，最少侵入）
        state["messages"] = [AIMessage(content=system_prompt)] + state["messages"]
        return state

    # -------------------------
    # Node: generate
    # -------------------------
    def _generate(self, state: AgentState) -> AgentState:
        """
        生成回复节点
        
        功能：
        - 调用LLM生成回复
        - 记录对话到短期日志
        - 将对话内容提交到长期记忆
        
        参数：
        - state (AgentState)：当前代理状态
        
        返回：
        - AgentState：更新后的代理状态，包含生成的回复
        """
        resp = self.llm.invoke(state["messages"])
        assistant_text = resp.content
        state["response"] = assistant_text

        # 提取当前轮 user_text（本基础版：单轮输入）
        user_text = ""
        for m in state["messages"]:
            if isinstance(m, HumanMessage):
                user_text = m.content
                break

        # 记录对话日志（用于展示/窗口）
        self.log.append(state["session_id"], user_text, assistant_text)

        # 写入长期记忆（PowerMem infer=True）
        self.memory.commit(state["session_id"], user_text, assistant_text)

        # 追加到 messages（可选：后续若要多轮窗口可用）
        state["messages"].append(AIMessage(content=assistant_text))
        return state

    # -------------------------
    # 对外运行接口（给 app.py 用）
    # -------------------------
    def run(self, session_id: str, npc_id: str, user_text: str) -> str:
        """
        对外运行接口
        
        参数：
        - session_id (str)：会话ID
        - npc_id (str)：NPC唯一标识
        - user_text (str)：用户输入的消息
        
        返回：
        - str：AI生成的回复内容
        """
        init_state: AgentState = {
            "session_id": session_id,
            "npc_id": npc_id,
            "messages": [HumanMessage(content=user_text)],
            "response": "",
        }
        final_state = self.graph.invoke(init_state)
        return final_state["response"]


# -----------------------------
# 工厂函数：与 app.py 兼容
# -----------------------------
_agent_singleton: Optional[LangGraphAgent] = None


def get_langgraph_agent(npc_manager: NPCManager) -> LangGraphAgent:
    """
    获取LangGraphAgent单例实例
    
    参数：
    - npc_manager (NPCManager)：NPC管理器实例
    
    返回：
    - LangGraphAgent：单例实例
    
    设计：
    - 使用单例模式，避免重复创建代理实例
    - 确保整个应用中只有一个代理实例在运行
    """
    global _agent_singleton
    if _agent_singleton is None:
        _agent_singleton = LangGraphAgent(npc_manager)
    return _agent_singleton
