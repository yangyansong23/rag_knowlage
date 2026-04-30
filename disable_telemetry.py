import os
import sys

# 必须在任何其他导入之前设置环境变量
os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "FALSE"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "TRUE"

# 尝试禁用 chromadb 的遥测模块
def disable_chroma_telemetry():
    """
    尝试多种方式禁用 ChromaDB 遥测
    """
    try:
        # 方法 1: 尝试直接 mock 遥测模块
        from unittest.mock import MagicMock
        
        # 创建一个假的遥测模块
        class MockTelemetry:
            def __init__(self, *args, **kwargs):
                pass
            
            def capture(self, *args, **kwargs):
                # 静默忽略所有遥测调用
                pass
            
            def shutdown(self, *args, **kwargs):
                pass
        
        # 尝试在导入前替换 sys.modules
        mock_telemetry = MockTelemetry()
        
        # 尝试 mock chromadb.telemetry
        sys.modules['chromadb.telemetry'] = MagicMock()
        sys.modules['chromadb.telemetry.product'] = MagicMock()
        sys.modules['chromadb.telemetry.events'] = MagicMock()
        
        # 尝试 mock posthog (如果使用)
        sys.modules['posthog'] = MagicMock()
        
    except Exception:
        # 如果失败，静默忽略
        pass

# 执行禁用
disable_chroma_telemetry()

# 再次确认环境变量
os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "FALSE"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "TRUE"
