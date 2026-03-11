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

## Reference File Categories

Users place reference files in a `references/` folder (or send via Telegram). Each category is routed only to the agents that need it.

### Folder Structure

```
references/
├── drafts/           # User's own previous drafts and paper versions
├── papers/           # General related work (for citation)
├── venue_papers/     # Best papers from target venue (style alignment)
│   └── NSDI/
│       ├── bestpaper_2024_xxx.pdf
│       └── bestpaper_2023_xxx.pdf
├── experiments/      # Experiment results (CSV, LOG, notes)
└── guidelines/       # Venue submission guidelines and templates
```

### Agent Access Matrix

| Category | Code Analyst | Planner | Researcher | Writer | Critic | Formatter |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| `drafts/` | | | | ✓ | ✓ | |
| `papers/` | | | ✓ | ✓ | | |
| `venue_papers/` | | ✓ | | ✓ | ✓ | |
| `experiments/` | ✓ | ✓ | | | | |
| `guidelines/` | | ✓ | | | | ✓ |

### Category Descriptions

- **drafts/** — User's own paper drafts. Writer uses for style continuity; Critic checks for logical consistency with existing content.
- **papers/** — General related literature for citation. Researcher extracts metadata; Writer uses when drafting related work sections.
- **venue_papers/** — Representative papers from the target venue (e.g., NSDI best papers). Writer aligns writing style; Planner references structure; Critic benchmarks quality.
- **experiments/** — CSV metrics, log files, experiment notes. Code Analyst extracts key results; Planner structures paper around findings.
- **guidelines/** — Venue templates, formatting rules, page limits. Planner enforces structure; Formatter applies citation and layout style.

### Input Methods

- **Telegram file upload** — Send files directly to the bot; bot categorizes by file type and user prompt
- **Local folder** — `/analyze /path/to/references/`
- **GitHub repo** — `/analyze https://github.com/user/repo`

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

## Researcher Agent Workflow

The Researcher Agent runs **automatically** before each `/write <section>` call — it searches for papers relevant to that section's topic and stores results in the session. It also runs once during `/analyze` to surface related work. Users can trigger it manually:

```
/search "attention mechanism transformers"
```

References are stored with a short citation key (`smith2021`, `vaswani2017`) and full metadata. The Writer inserts `\cite{key}` placeholders; the Formatter resolves them to the requested style.

---

## Revision Instruction Handling

When a user says "Revise paragraph 3 per suggestion 2", the Orchestrator:
1. Retrieves the latest Critic feedback from session (numbered list)
2. Identifies the referenced suggestion index (e.g., suggestion #2)
3. Retrieves the current section draft
4. Passes `{draft, target_paragraph: 3, instruction: suggestion_2_text}` to Writer

The Orchestrator uses an LLM call (DeepSeek-V3) to parse natural language references to feedback items. If it cannot resolve the reference, it asks the user to clarify.

---

## Cross-Section Context

When writing a new section, the Writer receives:
- The approved outline
- The experiment summary
- Previously written sections (as read-only context, truncated to last 2 if context is large)
- Relevant references for this section

This ensures narrative consistency across sections.

---

## Paper Session State Machine

```
INIT → ANALYZING → OUTLINED → WRITING → REVIEWING → FORMATTING → DONE
```

| State | Allowed Commands |
|-------|-----------------|
| INIT | `/newpaper`, `/analyze` |
| ANALYZING | (waiting for Code Analyst) |
| OUTLINED | `/write`, `/search`, `/status` |
| WRITING | `/review`, `/write`, `/status` |
| REVIEWING | `/write` (revision), `/status` |
| FORMATTING | `/format`, `/status` |
| DONE | `/export` (future), `/status` |

A paper can start without `/analyze` (skip Code Analyst). In that case it moves from INIT → OUTLINED after `/newpaper` + `/outline`.

---

## Context Window Management

Each agent call enforces a token budget:
- `experiment_summary`: max 2000 tokens
- `outline`: max 1000 tokens
- `previous_sections`: max 3000 tokens (truncated from oldest)
- `references`: max 2000 tokens (top N by relevance)
- `chat_history`: last 10 turns, max 2000 tokens
- `current_draft`: max 4000 tokens

If total exceeds model context limit, older sections and references are dropped first. User is notified if truncation occurs.

---

## Orchestrator Intent Classification

The Orchestrator uses a lightweight LLM call (DeepSeek-V3 or Haiku) with a structured prompt to classify each message into one of:

- `COMMAND` — maps directly to a slash command equivalent
- `REVISION` — user wants to modify a draft (routes to Writer)
- `QUESTION` — user has a question about the paper/process (Orchestrator answers)
- `CONFIRM` / `REJECT` — response to a yes/no prompt

Explicit slash commands bypass classification and are routed directly.

---

## Session Lifecycle

- Sessions persist indefinitely in SQLite
- `/status` shows current paper state at any time
- Users can switch between multiple sessions: `/sessions` lists all, `/switch <title>` activates one
- Sessions are not auto-deleted; manual `/delete <title>` required

---

## Concurrency & Rate Limiting

- Each user has at most one active agent task at a time (queued if busy)
- ArXiv and Semantic Scholar responses are cached in SQLite for 24 hours
- LLM API calls are sequential per session (no parallel agent calls in v1)
- Per-user rate limit: 20 LLM calls per hour (configurable)

---

## Error Handling

- LLM API failures: retry once with same model, then fall back to Claude Haiku; user notified of fallback
- GitHub API rate limits: notify user, suggest using local path
- Long responses: chunked Telegram messages (4096 char limit)
- Session not found: prompt user to run `/newpaper` first
- GitHub token: validated on first use; code is sent to LLM as-is (user responsible for not exposing secrets; documented in README)

---

## Cost & Observability

- Each LLM call logs: agent name, model used, input/output tokens, cost estimate
- `/cost` command shows total token spend for the current session
- All logs written to `logs/paperagent.log` with structured JSON entries

---

## Clarifications & Edge Cases

### Mode Switching
`/mode fast` overrides all agent models to Claude Haiku in-memory for the current bot session. It does NOT modify `config.yaml`. On bot restart, models revert to `config.yaml` defaults. `/mode balanced` restores defaults within the session.

### GitHub Private Repo Authentication
On `/analyze <private_github_url>`:
1. Bot checks if `GITHUB_TOKEN` is set in `.env`
2. If set: uses token silently
3. If not set: responds with "This appears to be a private repo. Please add your `GITHUB_TOKEN` to `.env` and restart the bot."

The token is validated on first use; if invalid, the user receives a clear error message.

### Citation Key Collisions
Citation keys are generated as `{first_author_lastname}{year}`. If a collision occurs (two papers: `smith2021`), a letter suffix is appended: `smith2021a`, `smith2021b`. The Formatter resolves all keys when formatting.

### Context Window Budget
All default models (DeepSeek-V3: 128K, Claude Haiku: 200K, Claude Sonnet: 200K, Claude Opus: 200K) have ample context. The total token budget (~14K) is well within all model limits. If a user configures a custom model with a small context window, the bot logs a warning but does not enforce budget changes in v1.

### Outline Generation
`/outline` behavior:
- If no outline exists: triggers Planner to generate one (requires title; prompts user if not set)
- If outline exists: displays current outline
- To regenerate: `/outline regenerate`

Target venue is set during `/newpaper` or prompted by Planner if missing.

### Confirmation Timeouts
Confirmations (outline approval, experiment summary approval) do **not** timeout. They persist until the user explicitly confirms or rejects. Sessions can be resumed after any gap.

If the user rejects a summary/outline, the agent re-runs with the user's feedback as additional instruction.

### Multi-User Collaboration
Each user has their own active session. Two users cannot edit the same session simultaneously in v1. Shared collaboration is out of scope; team members work independently on separate sessions.

### Chat History
Chat history includes both user messages and assistant responses (full conversation turns). System messages and tool call internals are excluded. Counts as one turn per user message + assistant reply pair.

### Researcher Agent Invocation
Researcher runs automatically before `/write <section>` with a brief status message: "Searching for related work...". Results are cached in session. If the section already has references, the cache is used (no re-search). Manual `/search` always runs a fresh query.

### Revision Instruction Passing to Writer
Parsed revision result is passed to Writer as a structured dict:
```python
{
  "action": "revise",
  "section": "introduction",
  "draft": "<current draft text>",
  "instruction": "<resolved natural language instruction>",
  "source_feedback": "<original Critic suggestion text if referenced>"
}
```

### Orchestrator Scope
The Orchestrator answers questions about: the current paper, the writing process, and agent capabilities. It does not answer general ML/research questions — for those it delegates to the Researcher or Writer agents depending on context.

---

## Out of Scope (v1)

- PDF export (LaTeX compilation)
- Image/figure generation
- Real-time collaboration between team members on the same session
- Web UI
- Automatic secret scanning before sending code to LLM
