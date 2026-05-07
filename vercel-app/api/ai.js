export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });

  const { model_id, prompt, api_key } = req.body;
  if (!model_id || !prompt || !api_key) {
    return res.status(400).json({ error: "Missing model_id, prompt, or api_key" });
  }

  const [provider, model] = model_id.split("/", 2);

  try {
    let text;

    if (provider === "openai" || provider === "xai") {
      const baseUrl = provider === "xai" ? "https://api.x.ai/v1" : "https://api.openai.com/v1";
      const reasoning = ["gpt-5", "gpt-5-mini", "o1", "o1-mini", "o3", "o3-mini", "o4-mini"];
      const isReasoning = reasoning.includes(model);
      const body = {
        model,
        messages: [{ role: "user", content: prompt }],
      };
      if (isReasoning) {
        body.max_completion_tokens = 4000;
      } else {
        body.max_tokens = 300;
        body.temperature = 0;
      }
      const r = await fetch(`${baseUrl}/chat/completions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${api_key}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(60000),
      });
      const d = await r.json();
      if (d.error) throw new Error(d.error.message || JSON.stringify(d.error));
      text = d.choices?.[0]?.message?.content?.trim() || "";

    } else if (provider === "gemini") {
      const r = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${api_key}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
          signal: AbortSignal.timeout(60000),
        }
      );
      const d = await r.json();
      if (d.error) throw new Error(d.error.message || JSON.stringify(d.error));
      text = d.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || "";

    } else if (provider === "anthropic") {
      const r = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": api_key,
          "content-type": "application/json",
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model,
          max_tokens: 300,
          messages: [{ role: "user", content: prompt }],
        }),
        signal: AbortSignal.timeout(60000),
      });
      const d = await r.json();
      if (d.error) throw new Error(d.error.message || JSON.stringify(d.error));
      text = d.content?.[0]?.text?.trim() || "";

    } else {
      return res.status(400).json({ error: `Unknown provider: ${provider}` });
    }

    return res.json({ text });
  } catch (err) {
    return res.status(500).json({ error: err.message || "AI call failed" });
  }
}
