# Telegram Paper Writing Agent Team — Design Spec

**Date:** 2026-03-11
**Status:** Approved

---

## Overview

A Telegram bot that fronts a team of AI agents to help a small team (2–10 people) write academic research papers (IEEE, ACM, NeurIPS, ICML, CVPR style) in English. The agents understand the user's codebase and experimental results, then collaborate to produce a full paper draft — from outline to formatted manuscript.

---

## Architecture

```
Telegram User
     │
     ▼
Telegram Bot (python-telegram-bot)
     │
     ▼
Orchestrator Agent ←──── Session Store (SQLite)
     │                    (paper metadata, outline, drafts, summaries, chat history)
     │
     ├──► Code Analyst Agent   ← GitHub API / local folder
     │         ├── .py / .sh / config files
     │         └── experiment results (CSV, LOG)
     │
     ├──► Planner Agent
     ├──► Researcher Agent     ← arXiv / Semantic Scholar API
     ├──► Writer Agent
     ├──► Critic Agent
     └──► Formatter Agent
```

---

## Components

### Telegram Bot Layer
- Built with `python-telegram-bot`
- Handles slash commands and free-form chat
- Routes all input to the Orchestrator
- Streams long responses in chunks to avoid Telegram message limits

### Orchestrator Agent
- Classifies user intent (command vs. conversational)
- Maintains conversation context across turns
- Dispatches tasks to specialist agents
- Returns results to the user
- Default model: DeepSeek-V3 (fallback: Claude Haiku)

### Code Analyst Agent
- Accepts a GitHub repo URL (public or private) or local folder path
- Reads: `.py`, `.sh`, config files (YAML/JSON), CSV metrics, LOG files
- Produces a structured `experiment_summary`:
  - Model architecture description
  - Training setup (hyperparameters, dataset, hardware)
  - Key results and conclusions (numbers from CSVs/logs)
- Summary stored in session; user confirms before proceeding
- Default model: DeepSeek-V3 (fallback: Claude Haiku)

### Planner Agent
- Takes `experiment_summary` + target venue as input
- Generates a section-by-section outline
- User approves outline before writing begins
- Default model: DeepSeek-R1 (fallback: Claude Haiku)

### Researcher Agent
- Searches arXiv and Semantic Scholar for related work
- Summarizes key papers and extracts citation metadata
- Returns ranked list of references relevant to the paper topic
- Default model: DeepSeek-V3 (fallback: Claude Haiku)

### Writer Agent
- Drafts individual sections based on: outline + experiment_summary + references
- Handles one section at a time
- Accepts revision instructions referencing Critic feedback
- Default model: Claude Sonnet (fallback: Claude Haiku)

### Critic Agent
- Reviews drafted sections for: logical consistency, clarity, completeness, academic tone
- Returns structured feedback (issues + suggestions)
- Can be triggered manually (`/review`) or automatically after writing
- Default model: Claude Opus (fallback: Claude Haiku)

### Formatter Agent
- Handles citation formatting (APA, IEEE, ACM, etc.)
- Produces LaTeX-ready output on request
- Cleans up section formatting for target venue style
- Default model: DeepSeek-V3 (fallback: Claude Haiku)

---

## Model Configuration

Models are specified in a `config.yaml` file and can be switched at runtime via bot commands.

```yaml
agents:
  orchestrator:
    model: deepseek-v3
    provider: deepseek
  code_analyst:
    model: deepseek-v3
    provider: deepseek
  planner:
    model: deepseek-r1
    provider: deepseek
  researcher:
    model: deepseek-v3
    provider: deepseek
  writer:
    model: claude-sonnet-4-6
    provider: anthropic
  critic:
    model: claude-opus-4-6
    provider: anthropic
  formatter:
    model: deepseek-v3
    provider: deepseek
```

### Mode Switching

| Command | Effect |
|---------|--------|
| `/mode fast` | Switch all agents to Claude Haiku |
| `/mode balanced` | Restore default config |

---

## Session Data Model

Each paper has its own session stored in SQLite:

```
paper_session
├── metadata
│   ├── title
│   ├── target_venue
│   └── word_limit
├── experiment_summary (from Code Analyst)
├── outline (section list, user-approved)
├── sections
│   └── [section_name]
│       ├── draft (current version)
│       └── revision_history (list of past drafts)
├── references (collected by Researcher)
└── chat_history (last 20 turns)
```

Multiple users can have separate active paper sessions. One user can have one active session at a time.

---

## Key Commands

| Command | Description |
|---------|-------------|
| `/newpaper <title>` | Start a new paper session |
| `/analyze <github_url or path>` | Run Code Analyst on repo/folder |
| `/outline` | Generate or show current outline |
| `/write <section>` | Write a specific section |
| `/review` | Run Critic on current section or full draft |
| `/format <style>` | Format citations and output (e.g., `ieee`, `apa`) |
| `/mode fast` | Switch all agents to Claude Haiku |
| `/mode balanced` | Restore default model config |
| `/status` | Show current paper session state |

Free-form chat is handled by the Orchestrator for all other interactions.

---

## Typical Workflow

```
1. /analyze https://github.com/user/repo
   → Code Analyst reads code + results → returns experiment_summary
   → User confirms summary

2. /newpaper "Efficient Attention Mechanism for Long Documents"
   → Planner generates outline based on experiment_summary + title
   → User approves outline

3. /write introduction
   → Researcher finds related work
   → Writer drafts Introduction using outline + summary + references

4. /review
   → Critic reviews Introduction, returns feedback

5. "Revise paragraph 3 per suggestion 2"
   → Orchestrator routes to Writer with revision instructions

6. /write methods
   → Writer drafts Methods section

7. /format ieee
   → Formatter outputs IEEE-formatted manuscript
```

---

## GitHub Integration

- Public repos: accessed via GitHub REST API, no auth required
- Private repos: GitHub personal access token configured in `.env`
- Local folders: direct filesystem access via mounted path

```env
GITHUB_TOKEN=ghp_...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Telegram Bot | `python-telegram-bot` v20+ |
| Agent orchestration | Custom Python (no heavy framework) |
| Session storage | SQLite via `sqlite3` |
| LLM providers | Anthropic SDK, DeepSeek API (OpenAI-compatible) |
| Literature search | arXiv API, Semantic Scholar API |
| GitHub access | PyGithub / GitHub REST API |
| Config | YAML (`config.yaml`) + `.env` |

---

## Out of Scope (v1)

- PDF export (LaTeX compilation)
- Image/figure generation
- Real-time collaboration between team members on the same session
- Web UI
- Automatic secret scanning before sending code to LLM
