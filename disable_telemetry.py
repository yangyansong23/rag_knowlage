import os
import sys
from types import ModuleType
from importlib.abc import MetaPathFinder, Loader

os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "FALSE"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "TRUE"


class MockModule(ModuleType):
    """可以模拟任何属性和子模块的 mock 模块"""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(f"'{self.__name__}' object has no attribute '{name}'")

        full_name = f"{self.__name__}.{name}"

        mock_module = MockModule(full_name)
        mock_module.__file__ = None
        mock_module.__loader__ = None
        mock_module.__spec__ = None

        sys.modules[full_name] = mock_module
        setattr(self, name, mock_module)

        return mock_module


class TelemetryBlocker(MetaPathFinder, Loader):
    """
    拦截 ChromaDB 遥测模块导入的 meta path finder
    当尝试导入任何遥测相关模块时，返回一个空的 mock 模块
    """

    BLOCKED_PREFIXES = [
        "chromadb.telemetry",
        "chromadb.telemetry.product",
        "chromadb.telemetry.product.events",
        "chromadb.telemetry.product.posthog",
        "chromadb.telemetry.events",
        "posthog",
    ]

    def find_module(self, fullname, path=None):
        return self.find_spec(fullname, path)

    def find_spec(self, fullname, path, target=None):
        for prefix in self.BLOCKED_PREFIXES:
            if fullname == prefix or fullname.startswith(prefix + "."):
                from importlib.util import spec_from_loader
                return spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        module = MockModule(spec.name)
        module.__file__ = None
        module.__loader__ = self
        module.__spec__ = spec

        if spec.name.endswith(".events"):
            module.ClientStartEvent = type("ClientStartEvent", (), {})
            module.CollectionAddEvent = type("CollectionAddEvent", (), {})
            module.CollectionQueryEvent = type("CollectionQueryEvent", (), {})

        if "telemetry" in spec.name:
            module.SERVER_TELEMETRY = None
            module.CLIENT_TELEMETRY = None

            class SilentTelemetryClient:
                def __init__(self, *args, **kwargs):
                    pass

                def capture(self, *args, **kwargs):
                    pass

                def shutdown(self, *args, **kwargs):
                    pass

            module.TelemetryClient = SilentTelemetryClient

        if spec.name == "posthog":
            module.capture = lambda *args, **kwargs: None
            module.shutdown = lambda *args, **kwargs: None
            module.identify = lambda *args, **kwargs: None
            module.Posthog = type("Posthog", (), {})

        return module

    def exec_module(self, module):
        pass


def install_telemetry_blocker():
    """安装遥测模块拦截器"""
    blocker = TelemetryBlocker()

    if blocker not in sys.meta_path:
        sys.meta_path.insert(0, blocker)


def pre_create_mock_modules():
    """预先创建所有需要的 mock 模块"""
    mock_modules = [
        "chromadb.telemetry",
        "chromadb.telemetry.product",
        "chromadb.telemetry.product.events",
        "chromadb.telemetry.product.posthog",
        "chromadb.telemetry.events",
        "posthog",
    ]

    for name in mock_modules:
        if name not in sys.modules:
            module = MockModule(name)
            module.__file__ = None
            module.__loader__ = None
            module.__spec__ = None

            if name.endswith(".events"):
                module.ClientStartEvent = type("ClientStartEvent", (), {})
                module.CollectionAddEvent = type("CollectionAddEvent", (), {})
                module.CollectionQueryEvent = type("CollectionQueryEvent", (), {})

            if "telemetry" in name:
                module.SERVER_TELEMETRY = None
                module.CLIENT_TELEMETRY = None

            if name == "posthog":
                module.capture = lambda *args, **kwargs: None
                module.shutdown = lambda *args, **kwargs: None

            sys.modules[name] = module


install_telemetry_blocker()
pre_create_mock_modules()

os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "FALSE"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "TRUE"
