import os
import json

class NPCManager:
    """Manager for NPC information and knowledge base"""
    
    def __init__(self, npc_dir='./npc', knowledge_base_dir='./knowledge_base'):
        """Initialize NPC manager"""
        self.npc_dir = npc_dir
        self.knowledge_base_dir = knowledge_base_dir
        
        # Ensure directories exist
        os.makedirs(self.npc_dir, exist_ok=True)
        os.makedirs(self.knowledge_base_dir, exist_ok=True)
    
    def get_all_npcs(self):
        """Get list of all NPCs"""
        npcs = []
        for filename in os.listdir(self.npc_dir):
            if filename.endswith('.json'):
                npc_id = filename[:-5]  # Remove .json extension
                try:
                    with open(os.path.join(self.npc_dir, filename), 'r', encoding='utf-8') as f:
                        npc_data = json.load(f)
                        npcs.append({
                            'id': npc_id,
                            'name': npc_data.get('name', npc_id),
                            'avatar': npc_data.get('avatar', '/static/avatar/default.png'),
                            'description': npc_data.get('description', '')
                        })
                except Exception as e:
                    print(f"Error loading NPC {filename}: {e}")
        return npcs
    
    def get_npc(self, npc_id):
        """Get NPC information"""
        npc_file = os.path.join(self.npc_dir, f'{npc_id}.json')
        if not os.path.exists(npc_file):
            return None
        
        try:
            with open(npc_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading NPC {npc_id}: {e}")
            return None
    
    def create_npc(self, npc_id, name, avatar='', description=''):
        """Create a new NPC"""
        npc_file = os.path.join(self.npc_dir, f'{npc_id}.json')
        
        if os.path.exists(npc_file):
            return False, 'NPC already exists'
        
        npc_data = {
            'name': name,
            'avatar': avatar,
            'description': description
        }
        
        try:
            with open(npc_file, 'w', encoding='utf-8') as f:
                json.dump(npc_data, f, ensure_ascii=False, indent=2)
            return True, 'NPC created successfully'
        except Exception as e:
            return False, f'Error creating NPC: {e}'
    
    def update_npc(self, npc_id, name=None, avatar=None, description=None):
        """Update NPC information"""
        npc = self.get_npc(npc_id)
        if not npc:
            return False, 'NPC not found'
        
        if name is not None:
            npc['name'] = name
        if avatar is not None:
            npc['avatar'] = avatar
        if description is not None:
            npc['description'] = description
        
        try:
            with open(os.path.join(self.npc_dir, f'{npc_id}.json'), 'w', encoding='utf-8') as f:
                json.dump(npc, f, ensure_ascii=False, indent=2)
            return True, 'NPC updated successfully'
        except Exception as e:
            return False, f'Error updating NPC: {e}'
    
    def delete_npc(self, npc_id):
        """Delete an NPC"""
        npc_file = os.path.join(self.npc_dir, f'{npc_id}.json')
        if not os.path.exists(npc_file):
            return False, 'NPC not found'
        
        try:
            os.remove(npc_file)
            # Also delete knowledge base if exists
            kb_dir = os.path.join(self.knowledge_base_dir, npc_id)
            if os.path.exists(kb_dir):
                import shutil
                shutil.rmtree(kb_dir)
            return True, 'NPC deleted successfully'
        except Exception as e:
            return False, f'Error deleting NPC: {e}'
    
    def get_npc_knowledge(self, npc_id):
        """Get NPC knowledge base"""
        kb_dir = os.path.join(self.knowledge_base_dir, npc_id)
        if not os.path.exists(kb_dir):
            return {}
        
        knowledge = {}
        for filename in os.listdir(kb_dir):
            if filename.endswith('.txt'):
                category = filename[:-4]  # Remove .txt extension
                try:
                    with open(os.path.join(kb_dir, filename), 'r', encoding='utf-8') as f:
                        knowledge[category] = f.read()
                except Exception as e:
                    print(f"Error loading knowledge {filename}: {e}")
        return knowledge
    
    def add_knowledge(self, npc_id, category, content):
        """Add knowledge to NPC's knowledge base"""
        kb_dir = os.path.join(self.knowledge_base_dir, npc_id)
        os.makedirs(kb_dir, exist_ok=True)
        
        try:
            with open(os.path.join(kb_dir, f'{category}.txt'), 'w', encoding='utf-8') as f:
                f.write(content)
            return True, 'Knowledge added successfully'
        except Exception as e:
            return False, f'Error adding knowledge: {e}'
    
    def delete_knowledge(self, npc_id, category):
        """Delete knowledge from NPC's knowledge base"""
        kb_file = os.path.join(self.knowledge_base_dir, npc_id, f'{category}.txt')
        if not os.path.exists(kb_file):
            return False, 'Knowledge not found'
        
        try:
            os.remove(kb_file)
            return True, 'Knowledge deleted successfully'
        except Exception as e:
            return False, f'Error deleting knowledge: {e}'