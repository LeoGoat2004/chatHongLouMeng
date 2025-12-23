# app.py

from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os

from core.npc.npc_manager import NPCManager
from core.memory.powermem import get_powermem
from core.agent.langgraph_agent import get_langgraph_agent

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="/static")

base_dir = os.path.dirname(os.path.abspath(__file__))

npc_manager = NPCManager(
    npc_dir=os.path.join(base_dir, "npc"),
    knowledge_base_dir=os.path.join(base_dir, "knowledge_base"),
)
powermem = get_powermem()
langgraph_agent = get_langgraph_agent()


def format_recent_history(raw_history, max_turns=6, max_chars=1800) -> str:
    """
    将 PowerMem 的结构化历史裁剪并格式化为 LLM 可用字符串
    - 限制轮数 + 限制字符数，防止 prompt 失控
    """
    if not raw_history:
        return "无"

    recent = raw_history[-max_turns:]

    lines = []
    for h in recent:
        u = (h.get("user_message", "") or "").strip()
        a = (h.get("assistant_message", "") or "").strip()
        if u:
            lines.append(f"用户：{u}")
        if a:
            lines.append(f"角色：{a}")

    text = "\n".join(lines).strip()
    if not text:
        return "无"

    if len(text) > max_chars:
        text = text[-max_chars:]

    return text


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/npc/<npc_id>")
def npc_page(npc_id):
    return app.send_static_file("npc_chat.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    npc_id = data.get("npc_id")
    user_message = data.get("message")

    if not npc_id or not user_message:
        return jsonify({"error": "Missing npc_id or message"}), 400

    # 获取 NPC 信息
    try:
        npc_info = npc_manager.get_npc(npc_id)
    except Exception:
        return jsonify({"error": "NPC not found"}), 404

    # 获取知识库
    knowledge = npc_manager.get_npc_knowledge(npc_id)

    # 获取历史（结构化）→ 裁剪/格式化为字符串
    raw_history = powermem.get_conversation_history(npc_id, limit=80)
    conversation_history = format_recent_history(raw_history, max_turns=6, max_chars=1800)

    # 生成回复
    response = langgraph_agent.generate_response(
        user_message=user_message,
        npc_info=npc_info,
        knowledge=knowledge,
        conversation_history=conversation_history,  # ✅ 传字符串
    )

    # 写入记忆（失败不影响对话返回）
    ok = powermem.write_dialog(
        npc_id=npc_id,
        user_message=user_message,
        assistant_message=response,
        npc_name=npc_info.get("name", "角色"),
    )
    if not ok:
        # 不要中止对话，只记录日志
        print("[app] warning: write_dialog failed")

    return jsonify({"response": response})


@app.route("/api/npc_list")
def get_npc_list():
    all_npcs = npc_manager.get_all_npcs()
    npc_list = [
        {
            "id": npc_id,
            "name": npc_info.get("name"),
            "avatar": npc_info.get("avatar"),
            "description": npc_info.get("description"),
        }
        for npc_id, npc_info in all_npcs.items()
    ]
    return jsonify(npc_list)


@app.route("/api/npc/<npc_id>")
def get_npc(npc_id):
    try:
        npc_info = npc_manager.get_npc(npc_id)
    except Exception:
        return jsonify({"error": "NPC not found"}), 404
    return jsonify(npc_info)


@app.route("/api/memories/<npc_id>", methods=["GET"])
def get_memories(npc_id):
    memories = powermem.get_conversation_history(npc_id, limit=200)
    return jsonify(memories)


@app.route("/api/memories/<npc_id>", methods=["DELETE"])
def clear_memories(npc_id):
    success = powermem.clear_conversation_history(npc_id)
    if success:
        return jsonify({"message": "Memories cleared successfully"})
    return jsonify({"error": "Failed to clear memories"}), 500


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, host="0.0.0.0", port=5000)
