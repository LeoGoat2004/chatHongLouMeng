# core/npc/npc_manager.py

import json
import os
from typing import Dict, Optional


class NPCManager:
    """
    NPC 静态设定管理器

    职责：
    - 读取 npc.json（角色行为/风格指令）
    - 读取 knowledge_base（人物/世界静态背景）
    - 生成稳定、可控的 system prompt

    不负责：
    - 记忆（PowerMem）
    - 对话状态
    - LangGraph 流程
    """

    def __init__(
        self,
        npc_dir: str,
        knowledge_base_dir: str,
    ):
        self.npc_dir = npc_dir
        self.knowledge_base_dir = knowledge_base_dir

    # -----------------------------
    # 对外主入口
    # -----------------------------
    def get_npc(self, npc_id: str) -> Dict:
        """
        返回：
        {
          "id": npc_id,
          "name": "...",
          "prompt": "...",   # 已拼接好的 system prompt
          "meta": {...}      # 其他配置（可选）
        }
        """
        npc_config = self._load_npc_config(npc_id)
        background = self._load_background(npc_id)

        prompt = self._build_prompt(
            npc_config=npc_config,
            background=background,
        )

        return {
            "id": npc_id,
            "name": npc_config.get("name", npc_id),
            "avatar": npc_config.get("avatar", "/static/avatar/default.jpg"),
            "description": npc_config.get("description", ""),
            "prompt": prompt,
            "meta": {
                k: v
                for k, v in npc_config.items()
                if k not in {"name", "instruction", "avatar", "description"}
            },
        }

    def get_all_npcs(self) -> list:
        """
        获取所有可用的NPC列表
        返回：
        [          {"id": "npc_id", "name": "npc_name"},          ...        ]
        """
        npcs = []
        if os.path.exists(self.npc_dir):
            for filename in os.listdir(self.npc_dir):
                if filename.endswith(".json"):
                    npc_id = filename[:-5]  # 移除.json扩展名
                    try:
                        npc_config = self._load_npc_config(npc_id)
                        npcs.append({
                            "id": npc_id,
                            "name": npc_config.get("name", npc_id),
                            "avatar": npc_config.get("avatar", "/static/avatar/default.jpg"),
                            "description": npc_config.get("description", "")
                        })
                    except FileNotFoundError:
                        continue
        return npcs

    # -----------------------------
    # 内部方法
    # -----------------------------
    def _load_npc_config(self, npc_id: str) -> Dict:
        path = os.path.join(self.npc_dir, f"{npc_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"NPC config not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_background(self, npc_id: str) -> Optional[str]:
        """
        默认读取：
        knowledge_base/{npc_id}/background.txt

        若不存在则返回 None（允许某些 NPC 无背景）
        """
        path = os.path.join(
            self.knowledge_base_dir,
            npc_id,
            "background.txt",
        )
        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
            return text if text else None

    def _build_prompt(self, npc_config: Dict, background: Optional[str]) -> str:
        sections = []

        # 1️⃣ 背景（客观事实）
        if background:
            sections.append(
                f"【人物背景与世界设定】\n{background}"
            )

        # 2️⃣ 指令（核心任务）
        instruction = npc_config.get("instruction", "")
        if instruction:
            sections.append(
                f"【核心任务指令】\n{instruction}"
            )

        # 3️⃣ 身份 + 性格
        desc = npc_config.get("description")
        persona = npc_config.get("persona", {})

        persona_lines = []
        if persona:
            if persona.get("core_traits"):
                persona_lines.append(
                    f"核心性格特质：{', '.join(persona['core_traits'])}"
                )
            if persona.get("values"):
                persona_lines.append(
                    f"价值观：{', '.join(persona['values'])}"
                )
            if persona.get("flaws"):
                persona_lines.append(
                    f"性格弱点：{', '.join(persona['flaws'])}"
                )

        identity_block = []
        if desc:
            identity_block.append(desc)
        if persona_lines:
            identity_block.append("\n".join(persona_lines))

        if identity_block:
            sections.append(
                "【人物身份与性格】\n" + "\n".join(identity_block)
            )

        # 3️⃣ 语言风格
        speech = npc_config.get("speech_style", {})
        if speech:
            style_lines = []
            for k, v in speech.items():
                if isinstance(v, list):
                    style_lines.append(f"{k}：{', '.join(v)}")
                else:
                    style_lines.append(f"{k}：{v}")
            sections.append(
                "【语言风格与表达习惯】\n" + "\n".join(style_lines)
            )

        # 4️⃣ 互动策略
        policy = npc_config.get("interaction_policy", {})
        if policy:
            policy_lines = []
            for k, v in policy.items():
                if isinstance(v, list):
                    policy_lines.append(f"{k}：{', '.join(v)}")
                else:
                    policy_lines.append(f"{k}：{v}")
            sections.append(
                "【互动与行为策略】\n" + "\n".join(policy_lines)
            )

        # 5️⃣ 系统约束（统一兜底）
        sections.append(
            "【系统约束】\n"
            "你始终以该角色的第一人称视角进行回应，"
            "不得提及你是模型、AI 或系统提示的存在。"
        )

        return "\n\n".join(sections)

