# AI News Helper

A lightweight pipeline to gather AI-related news, summarize it, store results, and notify you when done. Built for a ~$10/month budget.

## Pipeline

1. **Gather** — Fetch from free sources (RSS, etc.)
2. **Analyze** — Summarize with a cost-efficient LLM
3. **Store** — Save to local files (and optional DB)
4. **Notify** — Email or message when finished

## Structure

```
ai-news/
├── config/           # Settings and source definitions
├── src/
│   ├── gather/       # News fetching
│   ├── analyze/      # Summarization
│   ├── store/        # Persistence
│   ├── notify/       # Email / messaging
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

## Cost notes

- **Gather**: RSS = free. Optional paid APIs only if you add them.
- **Analyze**: Use free/low-cost LLM (e.g. Groq free tier, or minimal OpenAI usage).
- **Store**: Local files = free.
- **Notify**: SMTP (Gmail etc.) = free.

No gathering runs until you enable and configure the pipeline; basics are set up first.
