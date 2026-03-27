import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # reads .env from the project root into os.environ


def get_client() -> tuple[OpenAI, str]:
    """
    Returns (client, model_name) for whichever AI provider is configured.

    Usage:
        client, model = get_client()
        response = client.chat.completions.create(model=model, ...)
    """
    provider = os.getenv("AI_PROVIDER", "ollama").lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        client = OpenAI(api_key=api_key)

    else:
        # Default: Ollama running locally.
        # api_key is required by the SDK but not actually checked by Ollama,
        # so we use the conventional placeholder value "ollama".
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model    = os.getenv("OLLAMA_MODEL", "llama3.2")
        client   = OpenAI(base_url=base_url, api_key="ollama")

    return client, model