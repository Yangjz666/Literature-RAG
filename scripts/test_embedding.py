from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from openai import OpenAI, OpenAIError
except ImportError:  # pragma: no cover
    OpenAI = None
    OpenAIError = Exception

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_TEXT = "酸性 CO2RR 中，氯化胆碱可以调控电极界面微环境并抑制析氢反应。"


def _load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if load_dotenv is not None:
        load_dotenv(env_path)
        return

    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    raise RuntimeError(f"{name} 未填写。请先在 .env 中配置后再运行测试。")


def main() -> int:
    if OpenAI is None:
        print("依赖缺失：请先安装 openai，例如运行 pip install -r requirements.txt。", file=sys.stderr)
        return 2

    _load_env()

    try:
        api_key = _require_env("EMBEDDING_API_KEY")
        base_url = _require_env("EMBEDDING_BASE_URL")
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-v4").strip() or "text-embedding-v4"
        dim = int(os.getenv("EMBEDDING_DIM", "1024"))
    except RuntimeError as e:
        print(f"配置错误：{e}", file=sys.stderr)
        return 2
    except ValueError:
        print("配置错误：EMBEDDING_DIM 必须是整数，例如 1024。", file=sys.stderr)
        return 2

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.embeddings.create(
            model=model,
            input=[TEST_TEXT],
            dimensions=dim,
            encoding_format="float",
        )
    except OpenAIError as e:
        print(f"Embedding API 调用失败：{e}", file=sys.stderr)
        return 1

    vector = response.data[0].embedding
    print(f"使用的模型：{model}")
    print(f"向量维度：{len(vector)}")
    print(f"向量前 5 个数值：{vector[:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
