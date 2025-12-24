# app.py - Flask接入层
# 职责：提供静态页面入口与API路由，连接前端与后端核心服务
# 交互：调用NPCManager获取人物设定，LangGraphAgent处理对话逻辑，SessionManager维护会话
# 约束：不直接处理人物设定、记忆检索或模型调用细节，仅作为请求转发与响应封装层

from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import os

from core.npc.npc_manager import NPCManager
from core.agent.langgraph_agent import get_langgraph_agent
from core.session.session_manager import SessionManager
from core.memory.conversation_log import ConversationLog

# Create conversation log instance
conversation_log = ConversationLog()

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Use absolute paths to avoid working directory issues
base_dir = os.path.dirname(os.path.abspath(__file__))

# 初始化核心服务实例
# - NPCManager：管理人物设定与背景知识
# - LangGraphAgent：处理对话流程编排
# - SessionManager：维护会话ID，防止记忆串用
npc_manager = NPCManager(
    npc_dir=os.path.join(base_dir, "npc"),
    knowledge_base_dir=os.path.join(base_dir, "knowledge_base"),
)

langgraph_agent = get_langgraph_agent(npc_manager)
session_mgr = SessionManager()


@app.route("/chat", methods=["POST"])
def chat():
    """
    聊天接口
    
    功能：处理聊天请求，调用LangGraphAgent生成回复，并记录对话日志
    请求体：
    - npc_id (str)：NPC唯一标识
    - message (str)：用户输入的消息
    - session_id (str, optional)：会话ID，若不提供则自动创建
    
    返回：
    - 200 OK：{"session_id": str, "npc_id": str, "reply": str}
    - 400 Bad Request：{"error": "npc_id and message required"}
    """
    data = request.get_json(silent=True) or {}

    npc_id = data.get("npc_id")
    message = data.get("message")
    session_id = session_mgr.get_or_create(data.get("session_id"))

    if not npc_id or not message:
        return jsonify({"error": "npc_id and message required"}), 400

    reply = langgraph_agent.run(
        session_id=session_id,
        npc_id=npc_id,
        user_text=message,
    )

    return jsonify(
        {
            "session_id": session_id,
            "npc_id": npc_id,
            "reply": reply,
        }
    )


@app.route("/")
def index():
    """
    首页入口
    
    返回：
    - 静态文件：static/index.html（NPC列表页面）
    """
    return send_from_directory("static", "index.html")

@app.route("/npc/<npc_id>")
def npc_chat(npc_id):
    """
    NPC对话页面入口
    
    参数：
    - npc_id (str)：NPC唯一标识
    
    返回：
    - 静态文件：static/npc_chat.html（对话界面）
    """
    return send_from_directory("static", "npc_chat.html")

@app.route("/api/npc_list", methods=["GET"])
def get_npc_list():
    """
    获取所有可用NPC列表
    
    返回：
    - 200 OK：[{'id': str, 'name': str, 'avatar': str, 'description': str}, ...]
    """
    npcs = npc_manager.get_all_npcs()
    return jsonify(npcs)

@app.route("/api/npc/<npc_id>", methods=["GET"])
def get_npc_info(npc_id):
    """
    获取特定NPC的详细信息
    
    参数：
    - npc_id (str)：NPC唯一标识
    
    返回：
    - 200 OK：{"id": str, "name": str, "avatar": str, "description": str, "prompt": str, "meta": dict}
    - 404 Not Found：{"error": "NPC not found"}
    """
    npc = npc_manager.get_npc(npc_id)
    if npc:
        return jsonify(npc)
    return jsonify({"error": "NPC not found"}), 404

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    API聊天接口
    
    功能：处理聊天请求，调用LangGraphAgent生成回复
    请求体：
    - npc_id (str)：NPC唯一标识
    - message (str)：用户输入的消息
    
    返回：
    - 200 OK：{"response": str}（AI回复内容）
    - 400 Bad Request：{"error": "npc_id and message required"}
    """
    data = request.get_json(silent=True) or {}
    
    npc_id = data.get("npc_id")
    message = data.get("message")
    
    if not npc_id or not message:
        return jsonify({"error": "npc_id and message required"}), 400
    
    reply = langgraph_agent.run(
        session_id="default",
        npc_id=npc_id,
        user_text=message,
    )
    
    return jsonify({
        "response": reply
    })

@app.route("/api/memories/<npc_id>", methods=["GET"])
def get_memories(npc_id):
    """
    获取特定NPC的聊天记忆
    
    参数：
    - npc_id (str)：NPC唯一标识
    
    返回：
    - 200 OK：[{"user_message": str, "assistant_message": str, "timestamp": int}, ...]
    """
    # Use session_id as npc_id since we're storing by session
    memories = conversation_log.recent(npc_id, limit=200)
    # Convert to frontend format
    formatted_memories = []
    for memory in memories:
        formatted_memories.append({
            "user_message": memory["user"],
            "assistant_message": memory["assistant"],
            "timestamp": memory["timestamp"]
        })
    return jsonify(formatted_memories)

@app.route("/api/memories/<npc_id>", methods=["DELETE"])
def clear_memories(npc_id):
    """
    清除特定NPC的聊天记忆
    
    参数：
    - npc_id (str)：NPC唯一标识
    
    返回：
    - 200 OK：{"message": "Memories cleared successfully"}
    - 500 Internal Server Error：{"error": "Failed to clear memories"}
    """
    # Since ConversationLog doesn't have a clear method, we'll add one
    if hasattr(conversation_log, "_logs"):
        if npc_id in conversation_log._logs:
            del conversation_log._logs[npc_id]
        return jsonify({"message": "Memories cleared successfully"})
    return jsonify({"error": "Failed to clear memories"}), 500

if __name__ == "__main__":
    # Keep host/port explicit for server usage
    app.run(host="0.0.0.0", port=5000, debug=True)
