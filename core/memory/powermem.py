# core/memory/powermem.py

import time
import json
from typing import Dict, Any, List

from .seekdb_backend import get_seekdb


class PowerMem:
    """
    PowerMem - 记忆抽象层

    设计原则：
    - SeekDB metadata 只存「稳定、短、结构化字段」
    - 长文本（对话原文、角色态 JSON）一律进 documents
    - 对话历史用于“长期存储+可检索”，不直接当“上下文窗口”
    """

    def __init__(self):
        self.db = get_seekdb()
        self._ensure_collections()

    def _ensure_collections(self):
        if not self.db.has_collection("dialogs"):
            self.db.create_collection("dialogs")
        if not self.db.has_collection("character_state"):
            self.db.create_collection("character_state")

    # -------------------------
    # 对话记忆（长期）
    # -------------------------

    def write_dialog(self, npc_id: str, user_message: str, assistant_message: str, npc_name: str = "角色") -> bool:
        """
        写入一条对话记录
        - documents: 存可读文本（用于检索/回放）
        - metadatas: 只存短字段（必须是严格 JSON 可表达的结构）
        """
        try:
            timestamp = int(time.time())
            dialog_id = f"{npc_id}:{timestamp}"

            dialog_collection = self.db.get_collection("dialogs")

            # 文本只进 documents
            document_text = f"用户：{user_message}\n{npc_name}：{assistant_message}"

            # metadata 只保留安全字段（严禁放长文本）
            metadata = {
                "dialog_id": dialog_id,
                "npc_id": npc_id,
                "timestamp": timestamp,
            }

            dialog_collection.add(
                ids=[dialog_id],
                documents=[document_text],
                metadatas=[metadata],
            )
            return True
        except Exception as e:
            print(f"[PowerMem] write_dialog failed: {e}")
            return False

    def get_conversation_history(self, npc_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        读取对话记录（结构化返回），按时间正序排列
        注意：这不是“上下文窗口”，上层应自行裁剪
        """
        try:
            dialog_collection = self.db.get_collection("dialogs")
            results = dialog_collection.query(
                query_texts=[""],
                filter={"npc_id": npc_id},
                n_results=limit,
            )

            documents = results.get("documents", []) or []
            metadatas = results.get("metadatas", []) or []

            n = min(len(documents), len(metadatas))
            history: List[Dict[str, Any]] = []

            for i in range(n):
                doc = documents[i]
                meta = metadatas[i] if isinstance(metadatas[i], dict) else {}

                user_msg = ""
                assistant_msg = ""

                if isinstance(doc, str):
                    lines = [x.strip() for x in doc.split("\n") if x.strip()]
                    for line in lines:
                        if line.startswith("用户："):
                            user_msg = line.replace("用户：", "", 1).strip()
                        else:
                            # 角色行：形如 “宝玉：xxx”
                            if "：" in line and not assistant_msg:
                                assistant_msg = line.split("：", 1)[1].strip()

                ts = 0
                if isinstance(meta, dict):
                    ts = int(meta.get("timestamp", 0) or 0)

                history.append(
                    {
                        "user_message": user_msg,
                        "assistant_message": assistant_msg,
                        "timestamp": ts,
                    }
                )

            history.sort(key=lambda x: x.get("timestamp", 0))
            return history
        except Exception as e:
            print(f"[PowerMem] get_conversation_history failed: {e}")
            return []

    def clear_conversation_history(self, npc_id: str) -> bool:
        """
        清空指定 NPC 的对话记录
        """
        try:
            dialog_collection = self.db.get_collection("dialogs")
            results = dialog_collection.query(
                query_texts=[""],
                filter={"npc_id": npc_id},
                n_results=2000,
            )

            ids_to_delete = results.get("ids", []) or []

            # 兼容可能的嵌套结构
            flat: List[str] = []
            for x in ids_to_delete:
                if isinstance(x, list):
                    flat.extend([i for i in x if isinstance(i, str)])
                elif isinstance(x, str):
                    flat.append(x)

            if flat:
                dialog_collection.delete(ids=flat)

            return True
        except Exception as e:
            print(f"[PowerMem] clear_conversation_history failed: {e}")
            return False

    # -------------------------
    # 角色态记忆（长期）
    # -------------------------

    def get_character_state(self, npc_id: str) -> Dict[str, Any]:
        """
        获取角色态记忆（结构化 dict）
        约定：用 documents 存 JSON 字符串；metadata 只存 npc_id/timestamp
        """
        default_state = {
            "current_mood": "平静",
            "notes": [],
            "last_updated": 0,
        }

        try:
            col = self.db.get_collection("character_state")

            # 取最近 1 条即可
            results = col.query(
                query_texts=[""],
                filter={"npc_id": npc_id},
                n_results=1,
            )

            docs = results.get("documents", []) or []
            metas = results.get("metadatas", []) or []

            if not docs:
                return default_state

            doc = docs[0]
            meta = metas[0] if metas and isinstance(metas[0], dict) else {}

            state = default_state
            if isinstance(doc, str) and doc.strip():
                try:
                    state = json.loads(doc)
                except Exception:
                    state = default_state

            # 补充 last_updated
            if isinstance(meta, dict):
                state["last_updated"] = int(meta.get("timestamp", state.get("last_updated", 0)) or 0)

            # 兜底字段
            state.setdefault("current_mood", "平静")
            state.setdefault("notes", [])
            state.setdefault("last_updated", 0)
            return state

        except Exception as e:
            print(f"[PowerMem] get_character_state failed: {e}")
            return default_state

    def set_character_state(self, npc_id: str, state: Dict[str, Any]) -> bool:
        """
        写入一条角色态快照（append-only）
        """
        try:
            col = self.db.get_collection("character_state")
            timestamp = int(time.time())
            rid = f"{npc_id}:{timestamp}"

            # documents 存 JSON
            doc = json.dumps(state, ensure_ascii=False)

            meta = {
                "npc_id": npc_id,
                "timestamp": timestamp,
            }

            col.add(
                ids=[rid],
                documents=[doc],
                metadatas=[meta],
            )
            return True
        except Exception as e:
            print(f"[PowerMem] set_character_state failed: {e}")
            return False


_powermem_instance = None


def get_powermem() -> PowerMem:
    global _powermem_instance
    if _powermem_instance is None:
        _powermem_instance = PowerMem()
    return _powermem_instance
