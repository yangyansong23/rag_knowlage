import os
import json
import httpx
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from config import settings


class BaseLLMProvider(ABC):
    """
    LLM 提供者基类，定义统一的接口
    """
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户输入的提示
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的文本
        """
        pass
    
    @abstractmethod
    def generate_with_context(self, question: str, context: str) -> str:
        """
        基于上下文生成回答
        
        Args:
            question: 用户问题
            context: 相关上下文
            
        Returns:
            生成的回答
        """
        pass


class OllamaProvider(BaseLLMProvider):
    """
    Ollama 本地 LLM 提供者
    支持通过 Ollama 运行本地模型（如 Llama2, Mistral, Qwen 等）
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        """
        初始化 Ollama 提供者
        
        Args:
            base_url: Ollama 服务地址
            model: 使用的模型名称
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.Client(timeout=120.0)  # 增加超时时间，支持长文本生成
        
        # 验证连接
        self._check_connection()
    
    def _check_connection(self):
        """检查 Ollama 服务是否可用"""
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                print(f"✓ Ollama 服务连接成功，使用模型: {self.model}")
            else:
                print(f"⚠ Ollama 服务响应异常: {response.status_code}")
        except Exception as e:
            print(f"⚠ Ollama 服务连接失败: {e}")
            print("  请确保 Ollama 已安装并运行: ollama serve")
            print(f"  或安装模型: ollama pull {self.model}")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户输入的提示
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的文本
        """
        url = f"{self.base_url}/api/generate"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            print(f"Ollama 生成失败: {e}")
            return f"抱歉，生成回答时出错: {str(e)}"
    
    def generate_with_context(self, question: str, context: str) -> str:
        """
        基于上下文生成回答
        
        Args:
            question: 用户问题
            context: 相关上下文
            
        Returns:
            生成的回答
        """
        system_prompt = """你是一个专业的知识库助手。请基于用户提供的上下文信息，准确、专业地回答用户的问题。

回答规则：
1. 只使用上下文提供的信息来回答问题
2. 如果上下文没有足够的信息，请明确说明
3. 回答要简洁、准确、专业
4. 引用关键信息时，可以适当标注来源"""
        
        prompt = f"""请基于以下上下文信息回答问题。

【上下文信息】
{context}

【用户问题】
{question}

【回答要求】
请基于上述上下文信息，给出准确的回答。如果上下文信息不足以回答问题，请说明。"""
        
        return self.generate(prompt, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API 提供者
    支持 OpenAI 官方 API 以及兼容 OpenAI 接口的第三方服务
    """
    
    def __init__(
        self, 
        api_key: str, 
        base_url: str = "https://api.openai.com/v1", 
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        初始化 OpenAI 提供者
        
        Args:
            api_key: API 密钥
            base_url: API 基础地址
            model: 使用的模型名称
            temperature: 生成温度（0.0-2.0）
            max_tokens: 最大生成 token 数
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = httpx.Client(timeout=120.0)
        
        # 验证 API Key 是否存在
        if not self.api_key or self.api_key.strip() == "":
            print("⚠ OpenAI API Key 未配置")
        else:
            print(f"✓ OpenAI API 提供者初始化完成，使用模型: {self.model}")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户输入的提示
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的文本
        """
        url = f"{self.base_url}/chat/completions"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            response = self.client.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            result = response.json()
            
            # 提取回答内容
            choices = result.get("choices", [])
            if choices and len(choices) > 0:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except httpx.HTTPStatusError as e:
            print(f"OpenAI API 请求失败: {e.response.status_code} - {e.response.text}")
            return f"抱歉，API 请求失败: {e.response.status_code}"
        except Exception as e:
            print(f"OpenAI 生成失败: {e}")
            return f"抱歉，生成回答时出错: {str(e)}"
    
    def generate_with_context(self, question: str, context: str) -> str:
        """
        基于上下文生成回答
        
        Args:
            question: 用户问题
            context: 相关上下文
            
        Returns:
            生成的回答
        """
        system_prompt = """你是一个专业的知识库助手。请基于用户提供的上下文信息，准确、专业地回答用户的问题。

回答规则：
1. 只使用上下文提供的信息来回答问题
2. 如果上下文没有足够的信息，请明确说明
3. 回答要简洁、准确、专业
4. 引用关键信息时，可以适当标注来源"""
        
        prompt = f"""请基于以下上下文信息回答问题。

【上下文信息】
{context}

【用户问题】
{question}

【回答要求】
请基于上述上下文信息，给出准确的回答。如果上下文信息不足以回答问题，请说明。"""
        
        return self.generate(prompt, system_prompt)


class GenericAPIProvider(BaseLLMProvider):
    """
    通用 API 提供者
    支持通过自定义 API 接口接入各种 LLM 服务
    """
    
    def __init__(
        self, 
        api_url: str,
        api_key: str = "",
        model: str = "",
        request_template: Optional[Dict] = None,
        response_path: str = "response"
    ):
        """
        初始化通用 API 提供者
        
        Args:
            api_url: API 端点 URL
            api_key: API 密钥（可选）
            model: 模型名称（可选）
            request_template: 请求模板，用于指定如何构造请求
            response_path: 响应路径，用于指定如何从响应中提取文本
        """
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.request_template = request_template or {
            "prompt": "{prompt}",
            "model": "{model}",
            "stream": False
        }
        self.response_path = response_path
        self.client = httpx.Client(timeout=120.0)
        
        print(f"✓ 通用 API 提供者初始化完成，地址: {api_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _build_payload(self, prompt: str, system_prompt: Optional[str] = None) -> Dict:
        """构建请求载荷"""
        payload = {}
        for key, value in self.request_template.items():
            if isinstance(value, str):
                # 替换模板变量
                value = value.replace("{prompt}", prompt)
                value = value.replace("{model}", self.model or "")
                if system_prompt:
                    value = value.replace("{system_prompt}", system_prompt)
            payload[key] = value
        return payload
    
    def _extract_response(self, response_data: Dict) -> str:
        """从响应中提取文本"""
        # 支持点号分隔的路径，如 "choices.0.message.content"
        path_parts = self.response_path.split(".")
        current = response_data
        
        for part in path_parts:
            if isinstance(current, dict):
                current = current.get(part, {})
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return ""
            else:
                return ""
        
        if isinstance(current, str):
            return current
        return str(current) if current else ""
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户输入的提示
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的文本
        """
        try:
            payload = self._build_payload(prompt, system_prompt)
            response = self.client.post(
                self.api_url, 
                headers=self._get_headers(), 
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            return self._extract_response(result)
        except Exception as e:
            print(f"通用 API 生成失败: {e}")
            return f"抱歉，生成回答时出错: {str(e)}"
    
    def generate_with_context(self, question: str, context: str) -> str:
        """
        基于上下文生成回答
        
        Args:
            question: 用户问题
            context: 相关上下文
            
        Returns:
            生成的回答
        """
        prompt = f"""请基于以下上下文信息回答问题。

【上下文信息】
{context}

【用户问题】
{question}

请基于上述上下文信息，给出准确的回答。如果上下文信息不足以回答问题，请说明。"""
        
        return self.generate(prompt)


class RuleBasedProvider(BaseLLMProvider):
    """
    基于规则的简单提供者（备用方案）
    当没有配置 LLM 时使用，提供基于规则的简单回答
    """
    
    def __init__(self):
        print("✓ 基于规则的简单提供者初始化完成")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成文本（基于规则的简单实现）
        
        Args:
            prompt: 用户输入的提示
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的文本
        """
        return f"这是一个基于规则的简单回答。\n\n输入提示: {prompt[:200]}..."
    
    def generate_with_context(self, question: str, context: str) -> str:
        """
        基于上下文生成回答（基于规则的简单实现）
        
        Args:
            question: 用户问题
            context: 相关上下文
            
        Returns:
            生成的回答
        """
        answer_parts = []
        
        answer_parts.append("根据知识库中的相关信息，为您整理如下回答：\n")
        
        # 简单的上下文展示
        if context.strip():
            # 将上下文分段展示
            context_lines = context.split("\n")
            preview_lines = []
            for line in context_lines[:10]:
                if line.strip():
                    preview_lines.append(line[:150] + ("..." if len(line) > 150 else ""))
            
            answer_parts.append("\n【相关信息摘要】")
            answer_parts.extend(preview_lines)
        else:
            answer_parts.append("\n抱歉，没有找到足够的相关信息。")
        
        answer_parts.append("\n\n💡 提示：")
        answer_parts.append("- 以上信息来自知识库中检索到的相关文档片段")
        answer_parts.append("- 当前使用的是基于规则的简单回答生成")
        answer_parts.append("- 如需更智能的回答，请配置 LLM 服务")
        
        answer_parts.append(f"\n\n📝 关于回答质量：")
        answer_parts.append(f"当前系统使用的是基于规则的简单回答生成。")
        answer_parts.append(f"如需获取更智能、更自然的回答，您可以：")
        answer_parts.append(f"  1. 配置 OpenAI API（需要 API 密钥）")
        answer_parts.append(f"  2. 或配置本地 LLM（如 Ollama + Llama2）")
        answer_parts.append(f"  3. 或配置自定义 API 接口")
        
        return "\n".join(answer_parts)


class LLMService:
    """
    LLM 服务管理器
    统一管理不同类型的 LLM 提供者
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.active_provider: Optional[str] = None
        self._initialized = False
    
    def initialize(self, provider_type: str = None, **kwargs) -> bool:
        """
        初始化 LLM 服务
        
        Args:
            provider_type: 提供者类型（ollama, openai, generic, rule_based）
            **kwargs: 提供者特定的参数
            
        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True
        
        # 从配置获取默认值
        if provider_type is None:
            provider_type = settings.LLM_PROVIDER
        
        try:
            if provider_type == "ollama":
                base_url = kwargs.get("base_url", settings.OLLAMA_BASE_URL)
                model = kwargs.get("model", settings.OLLAMA_MODEL)
                self.providers["ollama"] = OllamaProvider(base_url=base_url, model=model)
                self.active_provider = "ollama"
                
            elif provider_type == "openai":
                api_key = kwargs.get("api_key", settings.OPENAI_API_KEY)
                base_url = kwargs.get("base_url", settings.OPENAI_BASE_URL)
                model = kwargs.get("model", settings.OPENAI_MODEL)
                temperature = kwargs.get("temperature", settings.OPENAI_TEMPERATURE)
                max_tokens = kwargs.get("max_tokens", settings.OPENAI_MAX_TOKENS)
                
                if not api_key or api_key.strip() == "":
                    print("⚠ OpenAI API Key 未配置，使用规则模式")
                    self.providers["rule_based"] = RuleBasedProvider()
                    self.active_provider = "rule_based"
                else:
                    self.providers["openai"] = OpenAIProvider(
                        api_key=api_key,
                        base_url=base_url,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    self.active_provider = "openai"
                
            elif provider_type == "generic":
                api_url = kwargs.get("api_url", settings.GENERIC_API_URL)
                api_key = kwargs.get("api_key", settings.GENERIC_API_KEY)
                model = kwargs.get("model", settings.GENERIC_API_MODEL)
                
                if not api_url:
                    print("⚠ 通用 API URL 未配置，使用规则模式")
                    self.providers["rule_based"] = RuleBasedProvider()
                    self.active_provider = "rule_based"
                else:
                    self.providers["generic"] = GenericAPIProvider(
                        api_url=api_url,
                        api_key=api_key,
                        model=model
                    )
                    self.active_provider = "generic"
                
            else:  # rule_based
                self.providers["rule_based"] = RuleBasedProvider()
                self.active_provider = "rule_based"
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"LLM 服务初始化失败: {e}，使用规则模式")
            self.providers["rule_based"] = RuleBasedProvider()
            self.active_provider = "rule_based"
            self._initialized = True
            return False
    
    def get_provider(self) -> BaseLLMProvider:
        """
        获取当前活动的提供者
        
        Returns:
            LLM 提供者实例
        """
        if not self._initialized:
            self.initialize()
        
        if self.active_provider and self.active_provider in self.providers:
            return self.providers[self.active_provider]
        
        # 默认返回规则模式
        return RuleBasedProvider()
    
    def switch_provider(self, provider_type: str, **kwargs) -> bool:
        """
        切换提供者
        
        Args:
            provider_type: 提供者类型
            **kwargs: 提供者特定的参数
            
        Returns:
            是否切换成功
        """
        return self.initialize(provider_type, **kwargs)
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户输入的提示
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的文本
        """
        provider = self.get_provider()
        return provider.generate(prompt, system_prompt)
    
    def generate_with_context(self, question: str, context: str) -> str:
        """
        基于上下文生成回答
        
        Args:
            question: 用户问题
            context: 相关上下文
            
        Returns:
            生成的回答
        """
        provider = self.get_provider()
        return provider.generate_with_context(question, context)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取 LLM 服务状态
        
        Returns:
            状态信息
        """
        return {
            "initialized": self._initialized,
            "active_provider": self.active_provider,
            "available_providers": list(self.providers.keys())
        }


# 创建全局实例
llm_service = LLMService()
