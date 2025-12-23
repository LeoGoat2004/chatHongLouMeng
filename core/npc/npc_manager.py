# core/npc/npc_manager.py

import os
import json
from typing import Dict, Any

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
NPC_DIR = os.path.join(BASE_DIR, "npc")
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")


class NPCManager:
    """
    NPC 配置管理器
    - 加载 / 校验 / 规范化 npc.json
    """

    def __init__(self, npc_dir: str = NPC_DIR, knowledge_base_dir: str = KNOWLEDGE_BASE_DIR):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.npc_dir = npc_dir
        self.knowledge_base_dir = knowledge_base_dir

    def get_npc(self, npc_id: str) -> Dict[str, Any]:
        if npc_id in self._cache:
            return self._cache[npc_id]

        path = os.path.join(self.npc_dir, f"{npc_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"NPC 不存在: {npc_id}")

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        npc = self._normalize(raw)
        self._cache[npc_id] = npc
        return npc

    def get_all_npcs(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有NPC的信息
        """
        all_npcs = {}
        if not os.path.exists(self.npc_dir):
            return all_npcs
        
        for fname in os.listdir(self.npc_dir):
            if fname.endswith(".json"):
                npc_id = fname[:-5]  # 去掉.json后缀
                try:
                    npc_info = self.get_npc(npc_id)
                    all_npcs[npc_id] = npc_info
                except Exception as e:
                    print(f"Error loading NPC {npc_id}: {e}")
        return all_npcs

    def get_npc_knowledge(self, npc_id: str) -> Dict[str, str]:
        """
        获取NPC的知识库
        """
        npc_knowledge_dir = os.path.join(self.knowledge_base_dir, npc_id)
        if not os.path.exists(npc_knowledge_dir):
            return {}
        knowledge = {}
        for fname in os.listdir(npc_knowledge_dir):
            if not fname.endswith(".txt"):
                continue
            file_path = os.path.join(npc_knowledge_dir, fname)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    knowledge[fname.replace(".txt", "")] = content
        return knowledge

    def _normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        npc_id = raw.get("id")
        if not npc_id:
            raise ValueError("npc.json 缺少 id 字段")

        return {
            "id": npc_id,
            "name": raw.get("name", npc_id),
            "avatar": raw.get("avatar", ""),
            "description": raw.get("description", ""),

            "persona": raw.get("persona", {}),

            "speech_style": raw.get("speech_style", {
                "base_style": "稳妥克制",
                "tone": "",
                "diction": "",
                "tempo": "",
                "addressing": "",
                "forbidden": []
            }),

            "interaction_policy": raw.get("interaction_policy", {
                "towards_user": "",
                "sensitive_topics": []
            })
        }


_npc_manager_instance = None


def get_npc_manager() -> NPCManager:
    global _npc_manager_instance
    if _npc_manager_instance is None:
        _npc_manager_instance = NPCManager()
    return _npc_manager_instance
