import os
import pyseekdb

_seekdb_instance = None


def get_seekdb():
    """获取SeekDB单例实例
    
    确保全项目只有一个SeekDB实例，避免资源冲突
    
    Returns:
        pyseekdb.Client: SeekDB客户端实例
    """
    global _seekdb_instance
    if _seekdb_instance is None:
        # 使用绝对路径确保正确定位
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        seekdb_path = os.path.join(base_dir, "storage", "seekdb", "seekdb.db")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(seekdb_path), exist_ok=True)
        
        try:
            _seekdb_instance = pyseekdb.Client(
                path=seekdb_path
            )
            print(f"SeekDB initialized successfully at: {seekdb_path}")
        except Exception as e:
            print(f"Failed to initialize SeekDB: {e}")
            raise
    return _seekdb_instance


# 确保SeekDB客户端在导入时初始化
try:
    get_seekdb()
except Exception as e:
    print(f"Error initializing SeekDB: {e}")
