"""统一 LLM 调用模块。

实际实现位于 app.llm_client；这里保留 src.llm_client 路径，方便后续迁移。
"""

from app.llm_client import LLMClient, generate_answer

__all__ = ["LLMClient", "generate_answer"]
