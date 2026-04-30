import socket
from typing import Optional, List
from config import settings


class PortManager:
    """
    端口管理器
    负责检测端口占用、自动查找可用端口
    """

    def __init__(self):
        self._current_port: Optional[int] = None

    def is_port_available(self, port: int, host: str = "0.0.0.0") -> bool:
        """
        检查端口是否可用

        Args:
            port: 要检查的端口
            host: 绑定地址

        Returns:
            True 如果端口可用，False 如果已被占用
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result != 0:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind((host, port))
                    sock.close()
                    return True
                except Exception:
                    return False
            return False
        except Exception:
            return False

    def find_available_port(
        self,
        start_port: int,
        max_retry: int = 10,
        host: str = "0.0.0.0"
    ) -> Optional[int]:
        """
        从起始端口开始查找可用端口

        Args:
            start_port: 起始端口
            max_retry: 最大重试次数
            host: 绑定地址

        Returns:
            可用端口号，如果没有找到则返回 None
        """
        for i in range(max_retry):
            port = start_port + i
            if self.is_port_available(port, host):
                print(f"✓ 找到可用端口: {port}")
                self._current_port = port
                return port
            else:
                print(f"⚠ 端口 {port} 已被占用，尝试下一个...")

        print(f"✗ 在 {max_retry} 次尝试后未找到可用端口")
        return None

    def find_available_port_in_range(
        self,
        start_port: int,
        end_port: int,
        host: str = "0.0.0.0"
    ) -> Optional[int]:
        """
        在指定范围内查找可用端口

        Args:
            start_port: 起始端口
            end_port: 结束端口
            host: 绑定地址

        Returns:
            可用端口号，如果没有找到则返回 None
        """
        for port in range(start_port, end_port + 1):
            if self.is_port_available(port, host):
                print(f"✓ 在范围 {start_port}-{end_port} 中找到可用端口: {port}")
                self._current_port = port
                return port

        print(f"✗ 在范围 {start_port}-{end_port} 中未找到可用端口")
        return None

    def get_available_ports(
        self,
        start_port: int,
        count: int,
        host: str = "0.0.0.0"
    ) -> List[int]:
        """
        获取指定数量的可用端口

        Args:
            start_port: 起始端口
            count: 需要的端口数量
            host: 绑定地址

        Returns:
            可用端口列表
        """
        available_ports = []
        port = start_port

        while len(available_ports) < count:
            if self.is_port_available(port, host):
                available_ports.append(port)
            port += 1

        return available_ports

    def get_server_port(self) -> int:
        """
        获取服务器端口（根据配置自动处理）

        Returns:
            最终使用的端口号
        """
        config_port = settings.SERVER_PORT
        config_host = settings.SERVER_HOST
        max_retry = settings.PORT_RETRY_MAX
        auto_find = settings.PORT_AUTO_FIND

        if self.is_port_available(config_port, config_host):
            self._current_port = config_port
            return config_port

        if auto_find:
            print(f"\n端口 {config_port} 已被占用，开始自动查找可用端口...")
            available_port = self.find_available_port(
                start_port=config_port,
                max_retry=max_retry,
                host=config_host
            )

            if available_port:
                print(f"✓ 将使用端口: {available_port}")
                return available_port
            else:
                print(f"✗ 未找到可用端口，将使用原始端口: {config_port}")
                return config_port
        else:
            print(f"✗ 端口 {config_port} 已被占用，且禁用了自动查找功能")
            return config_port

    @property
    def current_port(self) -> Optional[int]:
        """获取当前使用的端口"""
        return self._current_port


port_manager = PortManager()
