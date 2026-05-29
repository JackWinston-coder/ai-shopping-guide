from functools import lru_cache
from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


@lru_cache
def load_prompt(name: str) -> str:
    prompt_path = PROMPT_DIR / name
    return prompt_path.read_text(encoding="utf-8").strip()
