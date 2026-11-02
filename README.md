# Grant Kennedy

**AI Solutions Engineer.** I design and deploy practical AI tools, along with the guardrails that make them safe to run. I spent 8+ years in technical presales at Dell Technologies, and I now build LLM apps, AI agents and the infrastructure they run on.

Austin, TX · Relocating to Denver, CO · [LinkedIn](https://linkedin.com/in/g-grant-kennedy)

## Projects

| Project | What it does | What it shows |
| --- | --- | --- |
| [AI Ops Agent](projects/ai-ops-agent.md) | A self-hosted AI agent that diagnoses and fixes problems on a Fedora Linux workstation | Agentic AI with guardrails: MCP tools, approval tiers, a tamper-evident audit log, undo, and local and cloud models |
| [JobScout](projects/jobscout.md) | A private AI job-matching app that finds postings and ranks each against a person's profile and resumes | End-to-end solution design: a two-stage model pipeline, cost control, evidence checking, Docker, zero-trust access, CI/CD |
| [AI Discord bots](projects/discord-bots.md) | Two Discord bots for a community of about 1,500 members: a multiplayer dice game and an AI assistant | Production AI in front of real users: multi-provider failover, prompt-injection defense, an AI bug-fix pipeline, self-hosted deploys with rollback |

The source code for these projects is private. Each write-up covers the problem, the architecture and the key design decisions, and [`samples/`](samples/) holds short excerpts of the real code. I'm happy to walk through any of it live.

## How I build

- The Discord bots were hand-coded first, starting in 2023, then overhauled with AI coding agents (Claude Code) to current best practices. Newer projects use Claude Code from the start.
- In every project I own the architecture, the guardrails and the tests, and I review every change before it merges.
- Every repository has a protected `main` branch, and every change is a pull request. CI runs a secret scan, lint, compile checks and tests before anything merges.
- Every project has a design document, a decision log and a recovery runbook.

## Skills

- **AI and LLMs:** RAG, connecting LLMs to data and tools (MCP), agentic AI with guardrails, multi-model routing and failover, prompt-injection defense, AI cost control, hallucination mitigation
- **Models and tools:** Anthropic API (Claude Opus, Sonnet, Haiku), OpenAI API, Ollama (local Qwen models), Goose, Claude Code
- **Code and data:** Python, SQL (PostgreSQL, Teradata), FastAPI, SQLAlchemy, pytest
- **Infrastructure:** Linux (Fedora, AlmaLinux), VMware vSphere and ESXi, Docker, Podman, Ansible, systemd, Cloudflare Tunnel and Access, Tailscale, GitHub Actions
- **Certification:** VMware vSphere Foundation 9.0 Administrator (Broadcom, 2026)
