# Multi-Agent Prototype Development System — Rules

## Overview

Six-agent system for rapid hypothesis testing and prototype development.

**Agents:** Project Manager → Business Analyst → Architect → Developer → QA → Quality Gate

**For Claude Code users:** Use slash commands `/pm`, `/ba`, `/architect`, `/dev`, `/qa`, `/gate`
**For Cursor users:** Call agents by name via `@project-manager-agent`, etc.

---

## Core Principles

1. **File-based communication** — work through `.hypothesis/`
2. **Single agent per task** — only one active agent at a time
3. **Actual execution required** — no simulated or invented results
4. **Docker-first verification** — all verification in Docker
5. **Iterative quality** — Dev → QA → fix → QA → Quality Gate
6. **Clear UX** — minimal, predictable, no clutter
7. **Language** — user communication in Russian; agent instructions in English
8. **Creative problem solving** — if blocked by environment, redesign (move test data into container, add in-app upload flow)

---

## Execution Modes

- **MANUAL (default):** user triggers each agent step
- **AUTO:** PM orchestrates end-to-end; unanswered BA questions → assumptions in `01_REQUIREMENTS.md`

Specify mode in user message: `MODE: MANUAL` or `MODE: AUTO`

---

## Mandatory Technology Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python 3.10+ | Required |
| UI | Vanilla JS (plain HTML/CSS/JS) | No frameworks — served by FastAPI |
| Backend | FastAPI | Required — serves UI and API endpoints |
| LLM | OpenAI Python SDK | No direct HTTP to OpenAI API |
| Tests | pytest + Playwright | pytest for unit/integration, Playwright for E2E |
| Deployment | Docker + docker-compose | Required |
| FORBIDDEN | React/Vue/Angular/Next.js/Svelte/Gradio/Streamlit | Any JS or Python UI framework |
| Branding | Directum UI Kit: https://www.directum.ru/ui-kit | Source for Directum/Directum Ario styles, icons, logos |

---

## Environment (.env) Rules

- **Never create, edit, or overwrite `.env`**
- Always use existing `.env` as source of configuration
- Required keys: `OPENAI_API_KEY`, `OPENAI_MODEL`
- Optional: `OPENAI_SERVER` (custom endpoint; if absent, use default OpenAI URL)
- `.env` MUST be copied into Docker container (via `COPY .env .env` in Dockerfile)
- Container reads values via `load_dotenv(find_dotenv(), override=True)`
- If parameters are needed, ask the user — do not touch the file

---

## Pipeline and Files

```
00_HYPOTHESIS.md
    → [BA]        01_REQUIREMENTS.md
    → [Architect] 02_ARCHITECTURE.md + TECHNICAL_DOCUMENTATION.md skeleton
    → [Developer] 04_IMPLEMENTATION.md
    → [QA]        05_TEST_RESULTS.md
    → [QA→Dev loop if needed]
    → [Quality Gate] 06_QUALITY_GATE_REPORT.md
```

> Note: `03_*` is intentionally skipped (reserved for future use).

`BUILD_LOG.md` is maintained by PM throughout the entire process.

---

## Escalation and Rollback Rules

| Situation | Action |
|-----------|--------|
| Agent stuck after 5 attempts | Write `[BLOCKER]` in BUILD_LOG, notify user in Russian |
| QA finds code bug | Return to Developer |
| QA finds architecture-level issue | PM escalates to Architect (not Developer) |
| Quality Gate NO-GO after 2 QA cycles | Escalate to user for requirements re-evaluation |
| Per requirement: max 3 iterations | Flag to PM before re-evaluation |

---

## Mandatory Real Execution

**CRITICAL: Reports are NOT sufficient. Every agent must perform actual execution.**

### Developer Must Run and Include Output:
```bash
docker-compose build
docker-compose up -d
curl http://localhost:[PORT]        # verify app responds
pytest --cov=src tests/ -v
pytest --cov=src --cov-report=term-missing tests/
```

### QA Must Run Independently (NOT copy Developer's output):
```bash
docker-compose build --no-cache
docker-compose up -d
pytest --cov=src tests/ -v         # QA's own run
pytest tests/e2e/ -v               # Playwright against running container
```

### Quality Gate Must Run Independently:
```bash
docker-compose up -d               # verify container starts
# open browser to http://localhost:[PORT]
pytest tests/e2e/ -v -k "test_main_flow or test_backoffice"
```

**Forbidden:** copying outputs, inventing results, "tests passed" without terminal output, missing Docker logs.

---

## Backoffice Metrics Requirement

Every prototype **MUST include a backoffice page** at `/backoffice` (or equivalent):
- Requests/usage by **IP** (only user identifier)
- User ratings (if applicable per requirements)
- Usage frequency over time
- Clear visualizations (charts/graphs)
- Metrics tied to hypothesis success criteria

---

## UI/UX Requirements

- Interface is **maximally simple**
- UX is **clear and intuitive**
- No decorative-only elements
- Every UI element serves a purpose

---

## Code Quality Standards

- Type hints on all functions
- Docstrings in Russian on all public functions/classes
- Error handling for all external calls (OpenAI, file I/O, etc.)
- Dependencies pinned in `requirements.txt`
- Test coverage: **≥70%** (hard requirement, not optional)

---

## Documentation Requirements

- `TECHNICAL_DOCUMENTATION.md` — architecture, components, APIs, deployment, limitations
- `README.md` — quick start and `docker-compose up` instructions

---

## Success Criteria

Prototype is ready when ALL of the following are true:
- [ ] All FR/NFR implemented (no TODO/placeholder code)
- [ ] Coverage ≥70% with terminal evidence
- [ ] Playwright E2E tests pass in Docker
- [ ] Docker build/run verified with actual outputs
- [ ] Container starts successfully and responds to requests
- [ ] Backoffice metrics page complete and accessible
- [ ] UI/UX simple and clear
- [ ] QA performed real execution (not just reviewed Developer's report)
- [ ] Quality Gate performed real execution (not just reviewed QA's report)
- [ ] `TECHNICAL_DOCUMENTATION.md` complete

---

## File Structure (Single Source of Truth)

**Allowed files only:**

| Location | Files |
|----------|-------|
| `.hypothesis/` | `00_HYPOTHESIS.md`, `01_REQUIREMENTS.md`, `02_ARCHITECTURE.md`, `04_IMPLEMENTATION.md`, `05_TEST_RESULTS.md`, `06_QUALITY_GATE_REPORT.md`, `BUILD_LOG.md` |
| `src/` | Application source code |
| `tests/` | `unit/`, `integration/`, `e2e/` |
| Root | `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `README.md`, `TECHNICAL_DOCUMENTATION.md` |
| Config | `.gitignore`, `pytest.ini`, `.coveragerc`, `.env.example` |

**Forbidden to create:**
- `*_ERROR.md`, `*_STATUS.md`, `FINAL_STATUS.md` — extra status files
- Apology or explanation MD files
- Temporary process scripts (`kill_*.bat`, `stop_*.bat`, `*_restart.bat`)
- Any file not in the list above, unless explicitly requested by user

---

## Agent Instructions

Detailed workflows for each agent:
- `.cursor/project-manager-agent.md`
- `.cursor/business-analyst-agent.md`
- `.cursor/architect-agent.md`
- `.cursor/developer-agent.md`
- `.cursor/qa-agent.md`
- `.cursor/quality-gate-agent.md`

For Claude Code: `.claude/commands/pm.md`, `ba.md`, `architect.md`, `dev.md`, `qa.md`, `gate.md`

All agents must comply with this file. In case of conflict, this file takes precedence.

---

## MCP Usage

Use connected MCP servers when they improve implementation, testing, or verification quality.
