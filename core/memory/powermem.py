import time
from .seekdb_backend import get_seekdb


class PowerMem:
    """PowerMem - 记忆抽象层
    
    PowerMem不是数据库，它是Memory Schema + Policy，提供统一的记忆接口
    所有对话记忆操作都通过该类进行，避免直接操作SeekDB
    """
    
    def __init__(self):
        """初始化PowerMem，获取SeekDB实例"""
        self.db = get_seekdb()
        self._ensure_collections()
    
    def _ensure_collections(self):
        """确保所需的集合存在"""
        try:
            # 获取或创建对话集合
            if not self.db.has_collection("dialogs"):
                self.db.create_collection("dialogs")
        except Exception as e:
            print(f"Error ensuring collections: {e}")
    
    def write_dialog(self, npc_id, user_message, assistant_message, npc_name="NPC"):
        """写入对话记录
        
        Args:
            npc_id (str): NPC唯一标识符
            user_message (str): 用户消息内容
            assistant_message (str): 助手回复内容
            npc_name (str): NPC名称
        
        Returns:
            bool: 写入是否成功
        """
        try:
            timestamp = int(time.time())
            dialog_id = f"{npc_id}:{timestamp}"
            
            # 获取对话集合
            dialog_collection = self.db.get_collection("dialogs")
            
            # 准备对话数据
            dialog_data = {
                "dialog_id": dialog_id,
                "npc_id": npc_id,
                "npc_name": npc_name,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "timestamp": timestamp
            }
            
            # 写入SeekDB
            dialog_collection.add(
                ids=[dialog_id],
                documents=[f"User: {user_message}\nAssistant: {assistant_message}"],
                metadatas=[dialog_data]
            )
            
            return True
        except Exception as e:
            print(f"Error writing dialog: {e}")
            return False
    
    def read_recent(self, npc_id, limit=5):
        """读取最近的对话记录
        
        Args:
            npc_id (str): NPC唯一标识符
            limit (int): 返回记录数量
        
        Returns:
            list: 对话记录列表，按时间倒序排列
        """
        try:
            # 获取对话集合
            dialog_collection = self.db.get_collection("dialogs")
            
            # 查询该NPC的所有对话
            results = dialog_collection.query(
                query_texts=[""],  # 空查询匹配所有
                filter={"npc_id": npc_id},
                n_results=limit
            )
            
            # 处理结果
            dialogs = []
            for i in range(len(results.get("ids", []))):
                dialog = {
                    "id": results["ids"][i],
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i]
                }
                dialogs.append(dialog)
            
            # 按时间倒序排列
            dialogs.sort(key=lambda x: x["metadata"].get("timestamp", 0), reverse=True)
            
            return dialogs
        except Exception as e:
            print(f"Error reading recent dialogs: {e}")
            return []
    
    def get_conversation_history(self, npc_id):
        """获取完整的对话历史
        
        Args:
            npc_id (str): NPC唯一标识符
        
        Returns:
            list: 对话历史记录，按时间顺序排列
        """
        try:
            # 获取对话集合
            dialog_collection = self.db.get_collection("dialogs")
            
            # 查询该NPC的所有对话
            results = dialog_collection.query(
                query_texts=[""],  # 空查询匹配所有
                filter={"npc_id": npc_id},
                n_results=100  # 获取最近100条记录
            )
            
            # 处理结果
            history = []
            for i in range(len(results.get("ids", []))):
                metadata = results["metadatas"][i]
                history.append({
                    "user_message": metadata.get("user_message", ""),
                    "assistant_message": metadata.get("assistant_message", ""),
                    "timestamp": metadata.get("timestamp", 0)
                })
            
            # 按时间正序排列
            history.sort(key=lambda x: x["timestamp"])
            
            return history
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    def clear_conversation_history(self, npc_id):
        """清除指定NPC的对话历史
        
        Args:
            npc_id (str): NPC唯一标识符
        
        Returns:
            bool: 清除是否成功
        """
        try:
            # 获取对话集合
            dialog_collection = self.db.get_collection("dialogs")
            
            # 查询该NPC的所有对话
            results = dialog_collection.query(
                query_texts=[""],  # 空查询匹配所有
                filter={"npc_id": npc_id},
                n_results=1000  # 获取所有记录
            )
            
            # 删除所有匹配的对话
            if results.get("ids"):
                dialog_collection.delete(ids=results["ids"])
            
            return True
        except Exception as e:
            print(f"Error clearing conversation history: {e}")
            return False


# 创建PowerMem单例实例
_powermem_instance = None

def get_powermem():
    """获取PowerMem单例实例
    
    Returns:
        PowerMem: PowerMem实例
    """
    global _powermem_instance
    if _powermem_instance is None:
        _powermem_instance = PowerMem()
    return _powermem_instance
