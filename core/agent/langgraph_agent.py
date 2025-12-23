import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph
from typing import Dict, List, Any, TypedDict
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Define workflow state
class ChatWorkflowState(TypedDict):
    """State definition for the chat workflow"""
    user_message: str
    npc_info: Dict[str, Any]
    knowledge: Dict[str, str]
    conversation_history: List[Dict[str, str]]
    formatted_inputs: Dict[str, str]
    response: str

class LangGraphAgent:
    """LangGraph Agent - 推理与流程控制
    
    LangGraph只处理推理与流程，不直接接触数据库，通过PowerMem访问记忆
    """
    
    def __init__(self):
        """初始化LangGraph Agent"""
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=os.getenv('API_KEY'),
            base_url=os.getenv('API_BASE_URL'),
            model=os.getenv('MODEL_NAME', 'qwen-turbo'),
            temperature=0.7,
            max_tokens=1000
        )

        # Create prompt template
        self.prompt_template = PromptTemplate(
            template=(
                "You are {npc_name}, a {npc_description}.\n\n"  # No space after {npc_description}.
                "## NPC Background Knowledge:\n"
                "{knowledge}\n\n"  # No extra blank line after {knowledge}
                "## Conversation History:\n"
                "{conversation_history}\n\n"  # No extra blank line after {conversation_history}
                "## Current User Message:\n"
                "{user_message}\n\n"  # No extra blank line after {user_message}
                "Please respond as {npc_name} would. Keep your response natural and in character.\n"
                "Do not break character. Respond in Chinese."
            ),
            input_variables=[
                'npc_name',
                'npc_description',
                'knowledge',
                'conversation_history',
                'user_message'
            ]
        )

        # Create response generation chain
        self.response_chain = self.prompt_template | self.llm | StrOutputParser()

        # Create LangGraph workflow
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """Create LangGraph workflow for NPC response generation with modular nodes"""
        # Define nodes
        def format_knowledge(state: ChatWorkflowState) -> ChatWorkflowState:
            """Format knowledge base"""
            knowledge = state['knowledge']
            formatted_knowledge = self._format_knowledge(knowledge)
            return {
                **state,
                'formatted_inputs': {
                    **state.get('formatted_inputs', {}),
                    'knowledge': formatted_knowledge
                }
            }

        def format_conversation_history(state: ChatWorkflowState) -> ChatWorkflowState:
            """Format conversation history"""
            conversation_history = state['conversation_history'] or []
            formatted_history = self._format_conversation_history(conversation_history)
            return {
                **state,
                'formatted_inputs': {
                    **state.get('formatted_inputs', {}),
                    'conversation_history': formatted_history
                }
            }

        def generate_response(state: ChatWorkflowState) -> ChatWorkflowState:
            """Generate NPC response"""
            user_message = state['user_message']
            npc_info = state['npc_info']
            formatted_inputs = state['formatted_inputs'] or {}
            
            # Prepare prompt inputs
            prompt_inputs = {
                'npc_name': npc_info.get('name', 'NPC'),
                'npc_description': npc_info.get('description', ''),
                'knowledge': formatted_inputs.get('knowledge', ''),
                'conversation_history': formatted_inputs.get('conversation_history', ''),
                'user_message': user_message
            }
            
            # Generate response
            try:
                response = self.response_chain.invoke(prompt_inputs)
                logger.info(f"Generated response for NPC {npc_info.get('name')}: {response[:50]}...")
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                response = "抱歉，我现在无法回答你的问题。"
            
            return {
                **state,
                'response': response
            }

        # Create workflow graph
        workflow = StateGraph(ChatWorkflowState)
        
        # Add nodes
        workflow.add_node("format_knowledge", format_knowledge)
        workflow.add_node("format_conversation_history", format_conversation_history)
        workflow.add_node("generate_response", generate_response)
        
        # Define edges
        workflow.set_entry_point("format_knowledge")
        workflow.add_edge("format_knowledge", "format_conversation_history")
        workflow.add_edge("format_conversation_history", "generate_response")
        workflow.set_finish_point("generate_response")
        
        # Compile workflow
        return workflow.compile()

    def _format_knowledge(self, knowledge: Dict[str, str]) -> str:
        """Format knowledge base for prompt"""
        if not knowledge:
            return "无"
        
        formatted = []
        for category, content in knowledge.items():
            formatted.append(f"{category}: {content}")
        
        return "\n".join(formatted)

    def _format_conversation_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history for prompt"""
        if not history:
            return "无"
        
        formatted = []
        for entry in history:
            user_msg = entry.get('user_message', '')
            assistant_msg = entry.get('assistant_message', '')
            if user_msg:
                formatted.append(f"用户: {user_msg}")
            if assistant_msg:
                formatted.append(f"NPC: {assistant_msg}")
        
        return "\n".join(formatted)

    def generate_response(self, user_message: str, npc_info: Dict[str, Any], 
                         knowledge: Dict[str, str], conversation_history: List[Dict[str, str]]) -> str:
        """生成NPC响应
        
        Args:
            user_message (str): 用户消息
            npc_info (Dict[str, Any]): NPC信息
            knowledge (Dict[str, str]): NPC知识库
            conversation_history (List[Dict[str, str]]): 对话历史
            
        Returns:
            str: NPC响应内容
        """
        # Prepare initial state
        initial_state = {
            'user_message': user_message,
            'npc_info': npc_info,
            'knowledge': knowledge,
            'conversation_history': conversation_history,
            'formatted_inputs': {},
            'response': ''
        }
        
        # Run workflow
        result = self.workflow.invoke(initial_state)
        
        return result.get('response', "抱歉，我现在无法回答你的问题。")


# 创建单例实例
_langgraph_agent_instance = None

def get_langgraph_agent():
    """获取LangGraph Agent单例
    
    Returns:
        LangGraphAgent: LangGraph Agent实例
    """
    global _langgraph_agent_instance
    if _langgraph_agent_instance is None:
        _langgraph_agent_instance = LangGraphAgent()
    return _langgraph_agent_instance
