# core/memory/seekdb_backend.py

import os
import pyseekdb

_seekdb_instance = None


def get_seekdb():
    """
    获取 SeekDB 单例实例（embedded 模式）

    SeekDB 在本项目中的职责：
    - 仅用于对话片段的向量化存储与召回
    - 不存储结构化事实
    - 不作为权威记忆源
    """
    global _seekdb_instance

    if _seekdb_instance is None:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        seekdb_path = os.path.join(base_dir, "storage", "seekdb", "data")

        os.makedirs(os.path.dirname(seekdb_path), exist_ok=True)

        _seekdb_instance = pyseekdb.Client(path=seekdb_path)
        print(f"[SeekDB] embedded instance started at {seekdb_path}")

    return _seekdb_instance
