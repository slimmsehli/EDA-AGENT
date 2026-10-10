# EDA Agent

EDA Agent is a small terminal assistant for semiconductor design and verification
work. It can answer questions about the project you are working in, inspect local
files with its tools, and use engineering guidance from the included skills.

The agent currently connects to Gemini through its OpenAI-compatible API. The
planned version is an experimental copy that asks the model to maintain a visible
plan before using tools.

## What’s included

- `src/agent_gemini.py` — the standard terminal agent.
- `src/agent_gemini_planned.py` — the planned version for comparison.
- `bin/eda-agent` — launcher for the standard agent; add `bin/` to your `PATH`.
- `config/system_prompt.md` — shared instructions loaded at startup.
- `config/mcp_servers.json` — addresses of optional MCP servers.
- `skills/` — engineering workflows and reference guidance.
- `mcp/terminal_toolbox.py` — optional local MCP server for document and data utilities.

## Install

Use Python 3.10 or newer. From the directory where you placed the agent:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

## Configure your model

Each person should configure their own copy of the agent. Copy the template:

Edit `config/.env` and set the API key, base URL, and model for your provider:

```dotenv
GEMINI_API_KEY=your-api-key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.5-flash
```

The example values are for Gemini. The agent uses an OpenAI-compatible API, so
other compatible providers can be configured with their own endpoint and model.
Keep your real key private. Do not commit or send `config/.env` to teammates.

## Run it from any project

Add the agent's `bin/` directory to your `PATH`. Replace the example path with
the location where you installed it:

```bash
export PATH="/path/to/agent/bin:$PATH"
```

To keep this setting for future terminals, put the line in `~/.bashrc` or
`~/.zshrc`. Then change to a project directory and start the agent:

```bash
cd /path/to/your/project
team-agent
```

The launcher finds the agent code and configuration relative to its own
location, so it can be run from any directory. The agent saves history, tool
logs, and usage statistics in `agent_logs/` under the directory you launched it
from. Each project therefore has its own agent history.

To try the planned version instead:

```bash
/path/to/agent/.venv/bin/python /path/to/agent/src/agent_gemini_planned.py
```

## Optional toolbox

The local toolbox provides utilities for CSV, Markdown, HTML, PDF, JSON, and
text files. It runs as a separate MCP server; the agent does not start it
automatically.

Start it in another terminal:

```bash
/path/to/agent/.venv/bin/python /path/to/agent/mcp/terminal_toolbox.py
```

The current MCP configuration uses `http://127.0.0.1:8766/mcp`. The toolbox
works with files on the local machine. Its tools do not use the shell tool's
confirmation prompt, so only connect to MCP servers you trust.

## A note about engineering data

The agent sends prompts and relevant conversation context to the configured
model provider. Check that provider is approved for the data you plan to use;
do not send proprietary RTL, netlists, layouts, PDKs, unreleased results, or
customer information unless your team's policy permits it.

Shell commands ask for confirmation before running. The agent's prompt asks it
to inspect the current project first and preserve source files and run artifacts.
Treat its analysis as assistance, not as design sign-off.
