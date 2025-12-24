from typing import List
from powermem import Memory, auto_config


class MemoryStore:
    """
    官方 PowerMem 的唯一封装层
    """

    def __init__(self):
        config = auto_config()
        self._memory = Memory(config=config)

    def recall(self, session_id: str, query: str, k: int = 5) -> str:
        if not query:
            return ""

        results = self._memory.search(
            query=query,
            user_id=session_id,
            limit=k
        )

        lines: List[str] = []
        for item in results:
            if isinstance(item, dict):
                text = item.get("content") or item.get("text") or ""
            else:
                text = str(item)
            if text:
                lines.append(f"- {text}")

        return "\n".join(lines)

    def commit(self, session_id: str, user_msg: str, ai_msg: str):
        self._memory.add(
            messages=[
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": ai_msg},
            ],
            user_id=session_id,
            infer=True
        )
