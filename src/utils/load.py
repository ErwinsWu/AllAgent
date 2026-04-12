import os
from enum import Enum
from dotenv import load_dotenv
from model.client import ModelClient

class Provider(Enum):
    DOUBAO = ("https://ark.cn-beijing.volces.com/api/v3", "DOUBAO_API_KEY")
    MINIMAX = ("https://api.minimax.chat/v1", "MINIMAX_API_KEY")
    GLM = ("https://open.bigmodel.cn/api/paas/v4", "GLM_API_KEY")
    QWEN = ("https://dashscope.aliyuncs.com/api/v1", "QWEN_API_KEY")
    CLAUDE = ("https://api.anthropic.com/v1", "CLAUDE_API_KEY")
    GPT = ("https://api.openai.com/v1", "OPENAI_API_KEY")
    GEMINI = ("https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY")

def load_model_client(provider: Provider, model_name: str) -> ModelClient:
    """
    从本地 .env 文件中加载对应商户的 API_KEY，使用内置的 BASE_URL 初始化 ModelClient。

    Args:
        provider (Provider): 大模型商户枚举
        model_name (str): 模型名称

    Returns:
        ModelClient: 初始化后的客户端实例

    Raises:
        ValueError: 如果 .env 文件中缺少对应商户的 API_KEY
    """
    load_dotenv()  # 加载 .env 文件

    base_url, env_key = provider.value
    api_key = os.getenv(env_key)

    if not api_key:
        raise ValueError(f"{env_key} must be set in .env file")

    return ModelClient(api_key, base_url, model_name)
