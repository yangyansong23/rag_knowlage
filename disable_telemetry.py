import os
import sys
from types import ModuleType
from importlib.abc import MetaPathFinder, Loader
from importlib.util import spec_from_loader

os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "FALSE"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "TRUE"
os.environ["CHROMA_OTEL_ENABLED"] = "FALSE"
os.environ["OTEL_SDK_DISABLED"] = "TRUE"
os.environ["OTEL_PYTHON_DISABLED"] = "TRUE"


class MockPackage(ModuleType):
    """
    一个看起来像真正包的 mock 包
    包含必要的属性，使 Python 认为这是一个合法的包
    """

    def __init__(self, name: str):
        super().__init__(name)
        self._name = name
        self._attrs = {}
        self.__path__ = []
        self.__file__ = None
        self.__loader__ = None
        self.__spec__ = None

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(f"'{self._name}' object has no attribute '{name}'")

        if name in self._attrs:
            return self._attrs[name]

        full_name = f"{self._name}.{name}"
        mock = MockPackage(full_name)

        self._attrs[name] = mock
        sys.modules[full_name] = mock
        setattr(self, name, mock)

        return mock

    def __call__(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter([])

    def __len__(self):
        return 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __bool__(self):
        return False

    def __repr__(self):
        return f"<MockPackage '{self._name}'>"


class FullTelemetryBlocker(MetaPathFinder, Loader):
    """
    完全拦截所有遥测相关模块
    """

    BLOCKED_MODULES = [
        "chromadb.telemetry",
        "chromadb.telemetry.product",
        "chromadb.telemetry.product.events",
        "chromadb.telemetry.product.posthog",
        "chromadb.telemetry.events",
        "chromadb.telemetry.opentelemetry",
        "chromadb.telemetry.opentelemetry.client",
        "chromadb.telemetry.opentelemetry.tracer",
        "posthog",
        "posthog.client",
        "posthog.version",
        "posthog.request",
        "opentelemetry",
        "opentelemetry.trace",
        "opentelemetry.sdk",
        "opentelemetry.sdk.trace",
        "opentelemetry.sdk.trace.export",
        "opentelemetry.exporter",
        "opentelemetry.exporter.otlp",
        "opentelemetry.exporter.otlp.proto",
        "opentelemetry.exporter.otlp.proto.http",
        "opentelemetry.exporter.otlp.proto.http.trace_exporter",
        "otel",
        "otel.sdk",
    ]

    def find_spec(self, fullname, path, target=None):
        for blocked in self.BLOCKED_MODULES:
            if fullname == blocked or fullname.startswith(blocked + "."):
                return spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        module = MockPackage(spec.name)

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

        if "opentelemetry" in spec.name:
            class MockTracerProvider:
                def __init__(self, *args, **kwargs):
                    pass

            class MockTracer:
                def __init__(self, *args, **kwargs):
                    pass
                def start_span(self, *args, **kwargs):
                    return self
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass

            class MockExporter:
                def __init__(self, *args, **kwargs):
                    pass
                def export(self, *args, **kwargs):
                    pass
                def shutdown(self, *args, **kwargs):
                    pass

            class MockProcessor:
                def __init__(self, *args, **kwargs):
                    pass
                def add_span_processor(self, *args, **kwargs):
                    pass
                def force_flush(self, *args, **kwargs):
                    pass
                def shutdown(self, *args, **kwargs):
                    pass

            module.TracerProvider = MockTracerProvider
            module.get_tracer = lambda *args, **kwargs: MockTracer()
            module.set_tracer_provider = lambda *args, **kwargs: None
            module.OTLPSpanExporter = MockExporter
            module.BatchSpanProcessor = MockProcessor
            module.SimpleSpanProcessor = MockProcessor
            module.ConsoleSpanExporter = MockExporter
            module.trace = module

        return module

    def exec_module(self, module):
        pass


def pre_install_mock_packages():
    """
    在任何导入发生之前，预先创建所有需要的 mock 包
    这是最关键的步骤，确保 chromadb.telemetry 被正确地识别为包
    """
    blocked_modules = [
        "chromadb.telemetry",
        "chromadb.telemetry.product",
        "chromadb.telemetry.product.events",
        "chromadb.telemetry.product.posthog",
        "chromadb.telemetry.events",
        "chromadb.telemetry.opentelemetry",
        "posthog",
        "opentelemetry",
        "otel",
    ]

    for name in blocked_modules:
        if name not in sys.modules:
            mock = MockPackage(name)

            if name.endswith(".events"):
                mock.ClientStartEvent = type("ClientStartEvent", (), {})
                mock.CollectionAddEvent = type("CollectionAddEvent", (), {})
                mock.CollectionQueryEvent = type("CollectionQueryEvent", (), {})

            if "telemetry" in name:
                mock.SERVER_TELEMETRY = None
                mock.CLIENT_TELEMETRY = None

                class SilentTelemetryClient:
                    def __init__(self, *args, **kwargs):
                        pass
                    def capture(self, *args, **kwargs):
                        pass
                    def shutdown(self, *args, **kwargs):
                        pass

                mock.TelemetryClient = SilentTelemetryClient

            if name == "posthog":
                mock.capture = lambda *args, **kwargs: None
                mock.shutdown = lambda *args, **kwargs: None
                mock.identify = lambda *args, **kwargs: None

            sys.modules[name] = mock


def install_meta_path_blocker():
    """在 sys.meta_path 中安装拦截器"""
    blocker = FullTelemetryBlocker()

    if not any(isinstance(x, FullTelemetryBlocker) for x in sys.meta_path):
        sys.meta_path.insert(0, blocker)


pre_install_mock_packages()
install_meta_path_blocker()

os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "FALSE"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "TRUE"
os.environ["CHROMA_OTEL_ENABLED"] = "FALSE"
os.environ["OTEL_SDK_DISABLED"] = "TRUE"
