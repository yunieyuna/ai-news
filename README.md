# AI News Helper

A lightweight pipeline to gather AI-related news, summarize it, store results, and notify you when done. Built for a ~$10/month budget.

## Pipeline

1. **Gather** — Fetch headlines from RSS, then (optional) **fetch full article text** from each link for better summaries.
2. **Analyze** — Summarize and categorize with an LLM (Ollama local, Groq, or OpenAI).
3. **Store** — Save digests to local markdown + JSON.
4. **Notify** — Email when done (optional).

Full-article fetch is controlled by `gather.fetch_full_content` and `gather.max_articles_to_fetch` in `config/settings.yaml`.

## Structure

```
ai-news/
├── config/           # Settings and source definitions
├── src/
│   ├── gather/       # News fetching
│   ├── analyze/      # Summarization
│   ├── store/        # Persistence
│   ├── notify/       # Email / messaging
│   ├── web/          # Simple UI to view digests
│   └── run.py        # Main pipeline
├── data/             # Local output (gitignored)
├── scripts/          # Run commands
└── .env.example
```

## Setup

1. Create a venv and install deps:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add any keys (optional for RSS-only + local store).
3. Run: `python -m src.run` (or `./scripts/run.sh` from project root).

## Web UI

A simple local UI to browse saved digests:

```bash
python -m src.web.app
```

Then open **http://127.0.0.1:5000** in your browser. You’ll see a list of digests; click one to view it. No extra cost (runs locally).

## Open-source LLM (Ollama) — $0/month

To avoid any API cost, use a **local open-source model** via [Ollama](https://ollama.com):

1. **Install Ollama** (macOS / Linux / Windows): https://ollama.com/download  
2. **Pull a model** (in a terminal):
   ```bash
   ollama pull llama3.2
   ```
   Other options: `mistral`, `llama3.1`, `qwen2.5` — set `analyze.model` in `config/settings.yaml` to the model name.
3. **Config** is already set to `provider: ollama` and `model: llama3.2`. No API key needed.
4. **Run the pipeline** — make sure Ollama is running (it starts when you `ollama run llama3.2` or run the app). The pipeline will call `http://localhost:11434/v1`.

If Ollama runs on another machine, set `OLLAMA_BASE_URL` in `.env` or `ollama_base_url` in `config/settings.yaml` (e.g. `http://192.168.1.10:11434/v1`).

---

## Cost per month

| Part | Option | Est. cost |
|------|--------|-----------|
| **Gather** | RSS feeds only | **$0** |
| **Analyze** | Ollama (local) | **$0** |
| **Analyze** | Groq (free tier) | **$0** |
| **Analyze** | OpenAI (e.g. gpt-4o-mini, light use) | ~$2–5 |
| **Store** | Local files | **$0** |
| **Notify** | Gmail / SMTP | **$0** |
| **Web UI** | Local Flask | **$0** |

**Typical total: $0** (RSS + Ollama or Groq + local + SMTP).

**About Cursor (this IDE):** The $2–5 above is for **this project’s APIs** (e.g. OpenAI for summarization). Cursor itself is a separate product: billing is set up in **Cursor → Settings → Account/Billing** when you choose a paid plan. If you haven’t added a card, you’re on the free tier; Cursor will only charge you if you upgrade and add payment details.

---

## Data sources

News is fetched from the RSS feeds in `config/sources.yaml`. Defaults include English, Chinese, and Japanese sources:

| Source | Language | URL |
|--------|-----------|-----|
| TechCrunch | EN | https://techcrunch.com/feed/ |
| MIT Technology Review | EN | https://www.technologyreview.com/feed/ |
| VentureBeat | EN | https://venturebeat.com/feed |
| The Verge | EN | https://www.theverge.com/rss/index.xml |
| GitHub Trending (daily) | EN | GitHub trending repos (via RSS) |
| TechNode | EN (China tech) | https://technode.com/feed/ |
| 36氪 (36Kr) | ZH | https://www.36kr.com/feed |
| TechCrunch Japan | JA | https://jp.techcrunch.com/feed/ |
| ITmedia | JA | https://rss.itmedia.co.jp/rss/2.0/topstory.xml |

You can add or remove feeds in `config/sources.yaml`. Optional: set `gather.filter_keywords` in `config/settings.yaml` to keep only AI-related items (e.g. `["AI", "GPT", "LLM"]`).
