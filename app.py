from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import json
from core.npc.npc_manager import NPCManager
from core.memory.powermem import get_powermem
from core.agent.langgraph_agent import get_langgraph_agent

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Initialize managers
# Use absolute paths to avoid working directory issues
base_dir = os.path.dirname(os.path.abspath(__file__))
npc_manager = NPCManager(
    npc_dir=os.path.join(base_dir, 'npc'),
    knowledge_base_dir=os.path.join(base_dir, 'knowledge_base')
)
powermem = get_powermem()
langgraph_agent = get_langgraph_agent()

@app.route('/')
def index():
    """Homepage - display NPC selection"""
    return app.send_static_file('index.html')

@app.route('/npc/<npc_id>')
def npc_page(npc_id):
    """NPC chat page"""
    return app.send_static_file('npc_chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat API endpoint"""
    data = request.get_json()
    npc_id = data.get('npc_id')
    user_message = data.get('message')
    
    if not npc_id or not user_message:
        return jsonify({'error': 'Missing npc_id or message'}), 400
    
    # Get NPC information
    npc_info = npc_manager.get_npc(npc_id)
    if not npc_info:
        return jsonify({'error': 'NPC not found'}), 404
    
    # Get NPC knowledge base
    knowledge = npc_manager.get_npc_knowledge(npc_id)
    
    # Get conversation history from PowerMem
    history = powermem.get_conversation_history(npc_id)
    
    # Generate response using LangGraph
    response = langgraph_agent.generate_response(
        user_message=user_message,
        npc_info=npc_info,
        knowledge=knowledge,
        conversation_history=history
    )
    
    # Save conversation to PowerMem
    powermem.write_dialog(
        npc_id=npc_id,
        user_message=user_message,
        assistant_message=response,
        npc_name=npc_info.get('name', 'NPC')
    )
    
    return jsonify({'response': response})

@app.route('/api/npc_list')
def get_npc_list():
    """Get list of all NPCs"""
    return jsonify(npc_manager.get_all_npcs())

@app.route('/api/npc/<npc_id>')
def get_npc(npc_id):
    """Get NPC information"""
    npc_info = npc_manager.get_npc(npc_id)
    if not npc_info:
        return jsonify({'error': 'NPC not found'}), 404
    return jsonify(npc_info)

@app.route('/api/memories/<npc_id>', methods=['GET'])
def get_memories(npc_id):
    """Get all conversation memories for an NPC"""
    memories = powermem.get_conversation_history(npc_id)
    return jsonify(memories)

@app.route('/api/memories/<npc_id>', methods=['DELETE'])
def clear_memories(npc_id):
    """Clear all conversation memories for an NPC"""
    success = powermem.clear_conversation_history(npc_id)
    if success:
        return jsonify({'message': 'Memories cleared successfully'})
    else:
        return jsonify({'error': 'Failed to clear memories'}), 500

if __name__ == '__main__':
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5000)