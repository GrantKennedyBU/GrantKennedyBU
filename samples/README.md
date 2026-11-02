# Code samples

Short excerpts from the private repositories behind the [projects](../README.md), shared so you can see how the code is written. Each file's header says where it comes from and what was left out. They are not meant to run on their own.

| File | Project | What it shows |
| --- | --- | --- |
| [audit_chain.py](audit_chain.py) | [AI Ops Agent](../projects/ai-ops-agent.md) | A hash-chained, tamper-evident audit log, written through checked file descriptors and anchored in the systemd journal |
| [model_fallback.py](model_fallback.py) | [AI Discord bots](../projects/discord-bots.md) | Failover between Claude and OpenAI models, where a refusal counts as an answer and only real failures switch providers |
| [job_screen.py](job_screen.py) | [JobScout](../projects/jobscout.md) | A low-cost Claude Haiku screen with structured JSON output, score caps and prompt-injection framing |
