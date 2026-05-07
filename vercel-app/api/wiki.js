export default async function handler(req, res) {
  const url = req.query.url;
  if (!url || !url.includes("wikipedia.org/wiki/")) {
    return res.status(400).json({ error: "Missing or invalid ?url= parameter" });
  }

  try {
    const resp = await fetch(url, {
      headers: { "User-Agent": "WikiRaceAI/1.0" },
      signal: AbortSignal.timeout(10000),
    });
    if (!resp.ok) return res.json({ text: "", links: [] });

    const html = await resp.text();

    // Extract text from mw-content-text
    const startIdx = html.indexOf('<div id="mw-content-text"');
    const endIdx = startIdx >= 0 ? html.indexOf('<div id="catlinks"', startIdx) : -1;
    const textRaw = startIdx >= 0 && endIdx >= 0 ? html.slice(startIdx, endIdx) : html;
    const text = textRaw.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 3000);

    // Extract /wiki/ links
    const BLACKLIST = new Set([
      "/wiki/Main_Page", "/wiki/Wikipedia", "/wiki/English_Wikipedia",
      "/wiki/Simple_English_Wikipedia", "/wiki/Free_content",
      "/wiki/Encyclopedia", "/wiki/Online_encyclopedia",
      "/wiki/Internet_encyclopedia_project",
    ]);
    const linkRe = /href="(\/wiki\/[^"#]+)"/g;
    const seen = new Set();
    const links = [];
    let m;
    while ((m = linkRe.exec(html)) !== null) {
      const href = m[1];
      if (!href.includes(":") && !seen.has(href) && !BLACKLIST.has(href)) {
        seen.add(href);
        links.push("https://en.wikipedia.org" + href);
        if (links.length >= 120) break;
      }
    }

    return res.json({ text, links });
  } catch (err) {
    return res.status(500).json({ error: "Failed to fetch Wikipedia page" });
  }
}
