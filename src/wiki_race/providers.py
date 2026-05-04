from __future__ import annotations


def call_ai(model_id: str, prompt: str, config: dict[str, str]) -> str:
    provider, name = model_id.split("/", 1)

    if provider == "openai":
        from openai import OpenAI

        reasoning_models = {"gpt-5", "gpt-5-mini", "o1", "o1-mini", "o3", "o3-mini", "o4-mini"}
        max_tokens = 4000 if name in reasoning_models else 300
        kwargs = {"max_completion_tokens": max_tokens, "timeout": 60}
        if name not in reasoning_models:
            kwargs["temperature"] = 0

        response = OpenAI(api_key=config["openai_key"]).chat.completions.create(
            model=name,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.choices[0].message.content.strip()

    if provider == "gemini":
        from google import genai as google_genai

        client = google_genai.Client(api_key=config["gemini_key"])
        return client.models.generate_content(model=name, contents=prompt).text.strip()

    if provider == "anthropic":
        import anthropic

        response = anthropic.Anthropic(api_key=config["anthropic_key"]).messages.create(
            model=name,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    if provider == "xai":
        from openai import OpenAI

        response = OpenAI(api_key=config["xai_key"], base_url="https://api.x.ai/v1").chat.completions.create(
            model=name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0,
            timeout=30,
        )
        return response.choices[0].message.content.strip()

    raise ValueError(f"Unknown provider: {provider}")
