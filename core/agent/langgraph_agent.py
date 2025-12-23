# core/agent/langgraph_agent.py

import os
import logging
from typing import Dict, Any, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph

from core.memory.powermem import get_powermem

logger = logging.getLogger(__name__)
load_dotenv()


class ChatWorkflowState(TypedDict, total=False):
    user_message: str
    npc_info: Dict[str, Any]
    knowledge: Dict[str, str]
    conversation_history: str  # ✅ 这里改为字符串（由 app 层裁剪/格式化）

    character_state: Dict[str, Any]
    emotion: Dict[str, Any]
    speech_style: Dict[str, Any]
    interaction_mode: Dict[str, Any]

    formatted_inputs: Dict[str, str]
    response: str


class LangGraphAgent:
    """
    数据驱动、无角色特例、无固定话术的 LangGraph Agent
    - 角色差异完全来自 npc.json 与 knowledge_base
    - 不在 core 代码里写死角色语体
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("API_BASE_URL"),
            model=os.getenv("MODEL_NAME", "qwen-turbo"),
            temperature=0.7,
            max_tokens=1000,
        )

        self.powermem = get_powermem()

        self.prompt_template = PromptTemplate(
            template=(
                "你正在扮演一位文学作品中的人物。\n\n"
                "【人物信息】\n"
                "姓名：{npc_name}\n"
                "人物简述：{npc_description}\n\n"
                "【约束】\n"
                "1）始终保持人物身份，不跳出角色。\n"
                "2）使用中文作答，风格符合人物气质与时代。\n"
                "3）不得编造未给出的具体事实；若信息不足，应以人物口吻婉转说明。\n\n"
                "【背景知识】\n"
                "{knowledge}\n\n"
                "【角色态记忆】\n"
                "{character_state}\n\n"
                "【当前情绪】\n"
                "{emotion}\n\n"
                "【话语风格】\n"
                "{speech_style}\n\n"
                "【交互边界】\n"
                "{interaction_mode}\n\n"
                "【对话历史】\n"
                "{conversation_history}\n\n"
                "【用户的话】\n"
                "{user_message}\n\n"
                "请在遵守以上约束的前提下，自然、连贯地作答。"
            ),
            input_variables=[
                "npc_name",
                "npc_description",
                "knowledge",
                "character_state",
                "emotion",
                "speech_style",
                "interaction_mode",
                "conversation_history",
                "user_message",
            ],
        )

        self.chain = self.prompt_template | self.llm | StrOutputParser()
        self.workflow = self._build_workflow()

    # =========================================================

    def _build_workflow(self):
        def load_character_state(state: ChatWorkflowState) -> ChatWorkflowState:
            npc = state["npc_info"]
            return {**state, "character_state": self.powermem.get_character_state(npc["id"])}

        def infer_emotion(state: ChatWorkflowState) -> ChatWorkflowState:
            """
            轻量启发式情绪推断：
            - 不写死具体台词
            - 仅给出“情绪标签+强度”，用于 style policy
            """
            text = state.get("user_message", "") or ""
            prev = (state.get("character_state", {}) or {}).get("current_mood", "平静")

            label = "平静"
            arousal = 0.2

            # 尽量保持轻量、通用，避免角色特例
            if any(k in text for k in ["烦", "讨厌", "不满", "生气", "恼"]):
                label, arousal = "不悦", 0.7
            elif any(k in text for k in ["难过", "伤心", "委屈", "唉"]):
                label, arousal = "低落", 0.6

            # 让情绪有轻微惯性（仍不写死回复）
            if prev in ["不悦", "低落"] and label == "平静":
                label = prev

            return {**state, "emotion": {"label": label, "arousal": arousal}}

        def infer_speech_style(state: ChatWorkflowState) -> ChatWorkflowState:
            style = (state.get("npc_info", {}) or {}).get("speech_style", {}) or {}
            return {**state, "speech_style": style}

        def apply_interaction_policy(state: ChatWorkflowState) -> ChatWorkflowState:
            policy = (state.get("npc_info", {}) or {}).get("interaction_policy", {}) or {}
            text = state.get("user_message", "") or ""

            mode = "NORMAL"
            sensitive = policy.get("sensitive_topics", []) or []
            if sensitive and any(t in text for t in sensitive):
                mode = "SOFT_DEFLECT"

            if (state.get("emotion", {}) or {}).get("label") == "不悦":
                mode = "COOL_DOWN"

            return {**state, "interaction_mode": {"mode": mode}}

        def format_inputs(state: ChatWorkflowState) -> ChatWorkflowState:
            # ✅ conversation_history 已由 app 层格式化为 str，这里不再 dict stringify
            return {
                **state,
                "formatted_inputs": {
                    "knowledge": self._fmt(state.get("knowledge")),
                    "character_state": self._fmt(state.get("character_state")),
                    "emotion": self._fmt(state.get("emotion")),
                    "speech_style": self._fmt(state.get("speech_style")),
                    "interaction_mode": self._fmt(state.get("interaction_mode")),
                    "conversation_history": state.get("conversation_history") or "无",
                },
            }

        def generate_response(state: ChatWorkflowState) -> ChatWorkflowState:
            npc = state["npc_info"]
            fmt = state["formatted_inputs"]

            try:
                resp = self.chain.invoke(
                    {
                        "npc_name": npc.get("name", npc.get("id", "角色")),
                        "npc_description": npc.get("description", ""),
                        **fmt,
                        "user_message": state.get("user_message", ""),
                    }
                )
            except Exception as e:
                logger.exception(f"LLM generate failed: {e}")
                resp = "我一时语塞，容我想想再答。"

            # 轻量更新角色态（只记录 mood，不干预具体回答）
            try:
                emotion = state.get("emotion", {}) or {}
                prev_state = state.get("character_state", {}) or {}
                new_state = {
                    **prev_state,
                    "current_mood": emotion.get("label", prev_state.get("current_mood", "平静")),
                }
                self.powermem.set_character_state(npc["id"], new_state)
            except Exception as e:
                logger.warning(f"update character_state failed: {e}")

            return {**state, "response": resp}

        g = StateGraph(ChatWorkflowState)
        g.add_node("load_character_state", load_character_state)
        g.add_node("infer_emotion", infer_emotion)
        g.add_node("infer_speech_style", infer_speech_style)
        g.add_node("apply_interaction_policy", apply_interaction_policy)
        g.add_node("format_inputs", format_inputs)
        g.add_node("generate_response", generate_response)

        g.set_entry_point("load_character_state")
        g.add_edge("load_character_state", "infer_emotion")
        g.add_edge("infer_emotion", "infer_speech_style")
        g.add_edge("infer_speech_style", "apply_interaction_policy")
        g.add_edge("apply_interaction_policy", "format_inputs")
        g.add_edge("format_inputs", "generate_response")
        g.set_finish_point("generate_response")

        return g.compile()

    # =========================================================

    def _fmt(self, obj) -> str:
        if obj is None or obj == {} or obj == [] or obj == "":
            return "无"
        if isinstance(obj, dict):
            return "\n".join(f"{k}：{v}" for k, v in obj.items())
        return str(obj)

    def generate_response(
        self,
        user_message: str,
        npc_info: Dict[str, Any],
        knowledge: Dict[str, str],
        conversation_history: str,  # ✅ 改为字符串
    ) -> str:
        result = self.workflow.invoke(
            {
                "user_message": user_message,
                "npc_info": npc_info,
                "knowledge": knowledge,
                "conversation_history": conversation_history,
            }
        )
        return result.get("response", "")


_langgraph_agent = None


def get_langgraph_agent() -> LangGraphAgent:
    global _langgraph_agent
    if _langgraph_agent is None:
        _langgraph_agent = LangGraphAgent()
    return _langgraph_agent
