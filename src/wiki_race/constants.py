WIKI_BASE = "https://en.wikipedia.org"
MAX_STEPS = 20

LINK_BLACKLIST = {
    "/wiki/Main_Page",
    "/wiki/Wikipedia",
    "/wiki/English_Wikipedia",
    "/wiki/Simple_English_Wikipedia",
    "/wiki/Free_content",
    "/wiki/Encyclopedia",
    "/wiki/Online_encyclopedia",
    "/wiki/Internet_encyclopedia_project",
}

DEFAULT_CONFIG = {
    "openai_key": "",
    "gemini_key": "",
    "anthropic_key": "",
    "xai_key": "",
}

PROVIDER_KEY_MAP = {
    "openai": "openai_key",
    "gemini": "gemini_key",
    "anthropic": "anthropic_key",
    "xai": "xai_key",
}

MODELS = [
    {"id": "openai/gpt-5.4", "name": "GPT-5.4", "provider": "openai", "color": "#10c87f"},
    {"id": "openai/gpt-5.4-mini", "name": "GPT-5.4 Mini", "provider": "openai", "color": "#34d99a"},
    {"id": "openai/gpt-5.4-nano", "name": "GPT-5.4 Nano", "provider": "openai", "color": "#2ea88c"},
    {"id": "openai/gpt-5", "name": "GPT-5", "provider": "openai", "color": "#1a9e6c"},
    {"id": "openai/gpt-5-mini", "name": "GPT-5 Mini", "provider": "openai", "color": "#148a5a"},
    {"id": "openai/gpt-4.1", "name": "GPT-4.1", "provider": "openai", "color": "#0e7a4a"},
    {"id": "openai/gpt-4.1-mini", "name": "GPT-4.1 Mini", "provider": "openai", "color": "#0e6651"},
    {"id": "openai/gpt-4.1-nano", "name": "GPT-4.1 Nano", "provider": "openai", "color": "#0a5040"},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "openai", "color": "#1a8c6c"},
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "color": "#148a6b"},
    {"id": "gemini/gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro", "provider": "gemini", "color": "#0d652b"},
    {"id": "gemini/gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite", "provider": "gemini", "color": "#0f9d58"},
    {"id": "gemini/gemini-3-pro-preview", "name": "Gemini 3 Pro", "provider": "gemini", "color": "#1b7a35"},
    {"id": "gemini/gemini-3-flash-preview", "name": "Gemini 3 Flash", "provider": "gemini", "color": "#34a853"},
    {"id": "gemini/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini", "color": "#4285f4"},
    {"id": "gemini/gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "provider": "gemini", "color": "#1565c0"},
    {"id": "anthropic/claude-opus-4-7", "name": "Claude Opus 4.7", "provider": "anthropic", "color": "#b05e38"},
    {"id": "anthropic/claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "provider": "anthropic", "color": "#e8937a"},
    {"id": "anthropic/claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "provider": "anthropic", "color": "#f0b8a0"},
    {"id": "xai/grok-3", "name": "Grok 3", "provider": "xai", "color": "#8b5cf6"},
    {"id": "xai/grok-3-mini", "name": "Grok 3 Mini", "provider": "xai", "color": "#a78bfa"},
]

MODEL_MAP = {model["id"]: model for model in MODELS}
