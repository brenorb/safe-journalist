import os

import httpx
from dotenv import load_dotenv

from safe_journalist.client import encrypted_openai_call
from safe_journalist.session import create_session


def main() -> None:
    load_dotenv()

    api_url = os.getenv("MAPLE_API_URL", "https://enclave.trymaple.ai").rstrip("/")
    api_key = os.getenv("MAPLE_API_KEY")
    model = os.getenv("MAPLE_MODEL", "llama-3.3-70b")

    if not api_key:
        raise SystemExit("MAPLE_API_KEY is not set. Copy .env.example to .env and fill it.")

    with httpx.Client(timeout=60.0) as client:
        session = create_session(api_url=api_url, api_key=api_key, client=client)
        result = encrypted_openai_call(
            session=session,
            api_key=api_key,
            path="/v1/chat/completions",
            payload={
                "model": model,
                "messages": [{"role": "user", "content": "who are you?"}],
                "stream": False,
            },
            client=client,
        )

    text = (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    print(text)
