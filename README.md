# AI News Helper

一个轻量级的 AI 新闻聚合与摘要工具。自动从 RSS 源抓取新闻，用 LLM 生成中文摘要并分类，保存到本地，通过独立 HTML 查看器浏览。

## Pipeline

1. **Gather** — 从 RSS 源抓取标题，可选抓取完整文章内容以提升摘要质量。
2. **Analyze** — 使用 LLM 生成中文摘要并分类（支持 Ollama 本地、Groq、OpenAI）。
3. **Store** — 保存为本地 Markdown + JSON 文件。
4. **Notify** — 完成后发送邮件通知（可选）。

## 目录结构

```
ai-news/
├── config/           # 配置文件（settings.yaml、sources.yaml）
├── src/
│   ├── gather/       # 新闻抓取
│   ├── analyze/      # LLM 摘要
│   ├── store/        # 本地存储
│   ├── notify/       # 邮件通知
│   └── run.py        # 主入口
├── scripts/
│   └── view_digest.py  # 独立 HTML 查看器
├── data/             # 本地输出（已加入 .gitignore）
└── .env.example
```

## 快速开始

1. 创建虚拟环境并安装依赖：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. 复制 `.env.example` 为 `.env`，按需填写 API Key（仅 Groq/OpenAI 需要）。
3. 运行 pipeline：
   ```bash
   python -m src.run
   ```
4. 打开查看器：
   ```bash
   python scripts/view_digest.py
   ```

## 查看器

`scripts/view_digest.py` 是一个独立的 HTML 查看器，无需服务器。运行后自动在浏览器打开，左侧按日期浏览，右侧展示文章卡片和 AI 中文摘要。

## LLM 配置

在 `config/settings.yaml` 中配置：

```yaml
analyze:
  provider: ollama        # ollama / groq / openai / none
  model: deepseek-r1:8b
  max_tokens: 1200
```

### Ollama（本地，$0）

1. 安装 [Ollama](https://ollama.com/download)
2. 拉取模型：
   ```bash
   ollama pull deepseek-r1:8b
   ```
3. 无需 API Key，直接运行。

其他可用模型：`llama3.2`、`qwen2.5`、`mistral` 等，在 `config/settings.yaml` 中修改 `model` 即可。

### Groq（免费额度）

1. 在 [console.groq.com](https://console.groq.com) 注册，获取免费 API Key。
2. 在 `.env` 中添加：`GROQ_API_KEY=gsk_xxx`
3. 将 `provider` 改为 `groq`，`model` 改为 `llama-3.3-70b-versatile`。

### OpenAI

在 `.env` 中添加 `OPENAI_API_KEY`，将 `provider` 改为 `openai`。

## 费用估算

| 模块 | 方案 | 费用 |
|------|------|------|
| Gather | RSS 抓取 | **$0** |
| Analyze | Ollama 本地 | **$0** |
| Analyze | Groq 免费额度 | **$0** |
| Analyze | OpenAI gpt-4o-mini | ~$2–5/月 |
| Store | 本地文件 | **$0** |
| Notify | Gmail / SMTP | **$0** |

**典型总费用：$0**（RSS + Ollama 或 Groq + 本地存储）

## 数据源

新闻来源在 `config/sources.yaml` 中配置，默认包含：

| 来源 | 语言 | 地址 |
|------|------|------|
| TechCrunch | EN | https://techcrunch.com/feed/ |
| MIT Technology Review | EN | https://www.technologyreview.com/feed/ |
| VentureBeat | EN | https://venturebeat.com/feed |
| The Verge | EN | https://www.theverge.com/rss/index.xml |
| TechNode | EN | https://technode.com/feed/ |
| 36氪 | ZH | https://www.36kr.com/feed |

可在 `config/sources.yaml` 中自由添加或删除 RSS 源。设置 `gather.filter_keywords` 可过滤只保留 AI 相关内容（如 `["AI", "GPT", "LLM"]`）。
