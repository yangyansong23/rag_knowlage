#!/usr/bin/env python3
"""
测试 ChromaDB 遥测拦截器是否正常工作
"""

import sys
import os

print("=" * 60)
print("Testing ChromaDB telemetry interceptor...")
print("=" * 60)

# 先检查 disable_telemetry 是否存在
disable_telemetry_path = os.path.join(os.path.dirname(__file__), 'disable_telemetry.py')
if not os.path.exists(disable_telemetry_path):
    print(f"ERROR: disable_telemetry.py not found at {disable_telemetry_path}")
    sys.exit(1)

print(f"✓ Found disable_telemetry.py at: {disable_telemetry_path}")

# 检查 sys.modules 状态
print(f"\nBefore importing disable_telemetry:")
print(f"  sys.meta_path length: {len(sys.meta_path)}")

# 现在导入 disable_telemetry
print("\nImporting disable_telemetry...")
try:
    import disable_telemetry
    print("✓ disable_telemetry imported successfully")
except Exception as e:
    print(f"✗ Failed to import disable_telemetry: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 检查拦截器是否已安装
print(f"\nAfter importing disable_telemetry:")
print(f"  sys.meta_path length: {len(sys.meta_path)}")

# 检查是否有我们的拦截器
for i, finder in enumerate(sys.meta_path):
    print(f"  [{i}] {type(finder).__name__}: {finder}")

# 检查预先创建的模块
telemetry_modules = [
    "chromadb.telemetry",
    "chromadb.telemetry.product",
    "chromadb.telemetry.product.events",
    "chromadb.telemetry.opentelemetry",
    "posthog",
    "opentelemetry",
]

print(f"\nChecking pre-created modules in sys.modules:")
for mod_name in telemetry_modules:
    if mod_name in sys.modules:
        mod = sys.modules[mod_name]
        print(f"  ✓ {mod_name}: {type(mod).__name__}")
    else:
        print(f"  ✗ {mod_name}: NOT FOUND")

# 现在测试是否可以导入 chromadb.telemetry
print(f"\nTesting import of chromadb.telemetry modules:")

test_imports = [
    "chromadb.telemetry",
    "chromadb.telemetry.product",
    "chromadb.telemetry.product.events",
    "chromadb.telemetry.opentelemetry",
]

for import_name in test_imports:
    try:
        if import_name in sys.modules:
            print(f"  ✓ {import_name}: already in sys.modules")
        else:
            __import__(import_name)
            print(f"  ✓ {import_name}: imported successfully")
    except Exception as e:
        print(f"  ✗ {import_name}: FAILED - {e}")

# 现在检查这些模块是否有必要的属性
print(f"\nChecking module attributes:")

if "chromadb.telemetry" in sys.modules:
    telemetry = sys.modules["chromadb.telemetry"]
    print(f"\n  chromadb.telemetry:")
    print(f"    type: {type(telemetry)}")
    print(f"    has product: {hasattr(telemetry, 'product')}")
    print(f"    has opentelemetry: {hasattr(telemetry, 'opentelemetry')}")
    
    if hasattr(telemetry, 'product'):
        product = telemetry.product
        print(f"\n  chromadb.telemetry.product:")
        print(f"    type: {type(product)}")
        print(f"    has events: {hasattr(product, 'events')}")
        print(f"    has SERVER_TELEMETRY: {hasattr(product, 'SERVER_TELEMETRY')}")
        
        if hasattr(product, 'events'):
            events = product.events
            print(f"\n  chromadb.telemetry.product.events:")
            print(f"    has ClientStartEvent: {hasattr(events, 'ClientStartEvent')}")
            print(f"    has CollectionAddEvent: {hasattr(events, 'CollectionAddEvent')}")

if "chromadb.telemetry.opentelemetry" in sys.modules:
    otel = sys.modules["chromadb.telemetry.opentelemetry"]
    print(f"\n  chromadb.telemetry.opentelemetry:")
    print(f"    type: {type(otel)}")

# 现在尝试导入实际的 ChromaDB 来测试
print(f"\n{'=' * 60}")
print("Now trying to import chromadb...")
print("=" * 60)

try:
    import chromadb
    print("✓ chromadb imported successfully!")
    
    print(f"\nchromadb.__file__: {chromadb.__file__}")
    
    # 尝试创建一个客户端来测试
    print("\nTrying to create ChromaDB client...")
    
    from chromadb.config import Settings as ChromaSettings
    
    print("✓ ChromaSettings imported successfully")
    
    print("\n" + "=" * 60)
    print("SUCCESS: All telemetry imports are working correctly!")
    print("=" * 60)
    
except ModuleNotFoundError as e:
    print(f"\n✗ ModuleNotFoundError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"\n✗ Other error: {e}")
    import traceback
    traceback.print_exc()
