# SEO Agent

AI-powered SEO optimization agent for HTML repositories. Automatically analyzes your HTML pages, selects keywords, applies invisible SEO improvements, generates sitemaps and robots.txt, and validates every change through a built-in review loop.

## Architecture

The system uses a strict **two-agent model**:

```
  ┌─────────────────────────────────┐
  │    CLI / Shell Entry Point      │
  │  run_seo_adjustment_on_pages.sh │
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │    SEO Planning Agent           │
  │  (Orchestrator + Planner)       │
  │                                 │
  │  • Repository analysis          │
  │  • Framework detection          │
  │  • Keyword selection            │
  │  • Task planning                │
  │  • Review & validation          │
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │  OpenCode Execution Agent       │
  │  (Isolated per-task sessions)   │
  │                                 │
  │  • HTML metadata updates        │
  │  • Internal linking             │
  │  • SEO page generation          │
  │  • Sitemap & robots.txt         │
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │  Reporting & Output             │
  │  Markdown │ JSON                 │
  └─────────────────────────────────┘
```

**Planning Agent** decides *what* to do. **Execution Agent** does *only* the file modifications. Neither crosses its boundary.

## Prerequisites

- **Python 3.11+**
- **OpenCode server** running locally (default: `http://127.0.0.1:4096`)
- **pip** for dependency installation

## Quick Start

### 1. Clone & Install

```bash
git clone <repo-url> SEO_AGENT
cd SEO_AGENT
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
OPENCODE_api_key=<your-opencode-api-key>
OPENCODE_base_url=http://127.0.0.1:4096
```

### 3. Run the Workflow

```bash
./run_seo_adjustment_on_pages.sh --Path_html=/absolute/path/to/html/repository
```

**Example:**

```bash
./run_seo_adjustment_on_pages.sh \
  --Path_html=/Users/thyagarajan/Desktop/Hireko/Sample_project/Hireko_demo
```

### What the CLI Does

1. Validates the target directory exists and contains HTML files
2. Starts/connects to the OpenCode server
3. Analyzes the repository structure and detects the framework
4. Reads keyword intelligence from `seo_intelligence_report.csv`
5. Plans SEO tasks (metadata, internal linking, page generation)
6. Executes each task in an isolated OpenCode session
7. Reviews all changes and calculates a quality score
8. Generates sitemap.xml and robots.txt
9. Produces reports in Markdown and JSON
10. Prints a summary dashboard

### CLI Options

| Option | Required | Description |
|--------|----------|-------------|
| `--Path_html=<path>` | Yes | Absolute path to the target HTML repository |

### Expected Output

```
============================================================
SEO AGENT
============================================================

Repository:
/path/to/your/html/repo

============================================================
         WORKFLOW EXECUTION SUMMARY
============================================================

Pages                  : 6
Keywords               : 11
Tasks Planned          : 11
Tasks Executed         : 11
Tasks Failed           : 0
Files Modified         : 6
Files Skipped          : 0
Review Score           : 100/100
Sitemap                : Generated
Robots                 : Generated
Reports                : Markdown | JSON
Overall Status         : SUCCESS
Total Duration         : 143.63 seconds
============================================================
```

## Project Structure

```
SEO_AGENT/
├── run_seo_adjustment_on_pages.sh    # Shell entry point (CLI)
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variable template
├── .env                               # Local env config (git-ignored)
├── Project_guidelines.md              # Development standards
├── seo_intelligence_report.csv        # Keyword intelligence input
│
├── config/                            # Configuration (pydantic-settings)
│   ├── base.py                        #   Base settings
│   ├── api.py                         #   API server config
│   ├── git.py                         #   Git integration config
│   ├── logging.py                     #   Logging config
│   ├── opencode.py                    #   OpenCode server config
│   ├── pipeline.py                    #   Pipeline config
│   ├── repository.py                  #   Repository analysis config
│   ├── seo.py                         #   SEO-specific config
│   └── settings.py                    #   Aggregated settings
│
├── seo_agent/                         # Main application package
│   ├── cli.py                         #   CLI argparse entry point
│   ├── __main__.py                    #   python -m seo_agent support
│   ├── version.py                     #   Version string
│   │
│   ├── core/                          #   Core utilities
│   │   ├── constants.py               #     Enums & constants
│   │   ├── dependency_injection.py    #     DI container
│   │   ├── exceptions.py              #     Custom exceptions
│   │   ├── logging.py                 #     Logging setup
│   │   ├── result.py                  #     Result type
│   │   ├── types.py                   #     Type aliases
│   │   └── utils.py                   #     Utility functions
│   │
│   ├── models/                        #   Data models
│   │   ├── api.py                     #     API request/response
│   │   ├── execution_session.py       #     Execution session state
│   │   ├── page_keyword_mapping.py    #     Page ↔ keyword mapping
│   │   ├── repository.py              #     Repository metadata
│   │   ├── review.py                  #     Review results
│   │   ├── seo.py                     #     SEO data models
│   │   ├── seo_input.py               #     Input data models
│   │   ├── task.py                    #     Task definitions
│   │   └── workflow.py                #     Workflow state
│   │
│   ├── agents/                        #   Agent implementations
│   │   ├── planning/                  #     SEO Planning Agent
│   │   │   ├── keyword_selector.py    #       Keyword selection
│   │   │   ├── page_keyword_matcher.py#       Page ↔ keyword matching
│   │   │   ├── planner.py             #       Main planner
│   │   │   ├── repository_analyzer.py #       Repo analysis
│   │   │   └── task_planner.py        #       Task planning
│   │   └── execution/                 #     Execution engine
│   │       └── executor.py            #       Task executor
│   │
│   ├── integrations/                  #   External integrations
│   │   └── opencode/                  #     OpenCode server
│   │       ├── adapter.py             #       High-level adapter
│   │       ├── client.py              #       HTTP/CLI client
│   │       ├── models.py              #       OpenCode models
│   │       └── server.py              #       Server lifecycle
│   │
│   ├── workflow/                      #   Workflow orchestration
│   │   ├── context.py                 #     Workflow context/state
│   │   ├── orchestrator.py            #     Main orchestrator
│   │   └── stages.py                  #     Stage definitions
│   │
│   ├── prompts/                       #   LLM prompt templates
│   │   ├── execution/                 #     Execution prompts
│   │   ├── planning/                  #     Planning prompts
│   │   └── review/                    #     Review prompts
│   │
│   ├── repository/                    #   Repository services
│   │   ├── framework_detector.py      #     Framework detection
│   │   ├── metadata_parser.py         #     HTML metadata parsing
│   │   ├── page_discovery.py          #     HTML page discovery
│   │   └── scanner.py                 #     Repository scanner
│   │
│   ├── review/                        #   Review engine
│   │   ├── diff_analyzer.py           #     Diff analysis
│   │   ├── feedback.py                #     Feedback generation
│   │   └── validator.py               #     Change validation
│   │
│   ├── seo/                           #   SEO operations
│   │   ├── applier.py                 #     Apply approved changes
│   │   ├── metadata_optimizer.py      #     Metadata optimization
│   │   ├── robots.py                  #     robots.txt generation
│   │   ├── seo_page_generator.py      #     SEO page generation
│   │   └── sitemap.py                 #     sitemap.xml generation
│   │
│   ├── reporting/                     #   Report generation
│   │   ├── html_renderer.py           #     HTML report
│   │   ├── json_renderer.py           #     JSON report
│   │   ├── manager.py                 #     Report manager
│   │   ├── markdown_renderer.py       #     Markdown report
│   │   ├── models.py                  #     Report models
│   │   └── report_generator.py        #     Report generator
│   │
│   ├── inputs/                        #   Input data readers
│   │   ├── base.py                    #     Base reader
│   │   ├── csv_reader.py              #     CSV reader
│   │   └── json_reader.py             #     JSON reader
│   │
│   ├── git/                           #   Git integration
│   │   ├── client.py                  #     Git client
│   │   ├── models.py                  #     Git models
│   │   └── operations.py              #     Git operations
│   │
│   ├── interfaces/                    #   Abstract interfaces
│   │   ├── git.py, llm.py, repository.py, review.py, seo.py
│   │
│   └── api/                           #   FastAPI server (optional)
│       ├── app.py                     #     Application factory
│       ├── dependencies.py            #     DI setup
│       ├── exception_handlers.py      #     Error handlers
│       ├── health.py                  #     Health checks
│       ├── middleware.py              #     API middleware
│       ├── routes.py                  #     API routes
│       └── schemas.py                 #     API schemas
│
├── tests/                             # Test suite (406 tests)
│   ├── test_csv_reader.py             #   Input reader tests
│   ├── test_keyword_matcher.py        #   Keyword matcher tests
│   ├── test_retry_policy.py           #   Retry policy tests
│   ├── unit/                          #   Unit tests
│   │   ├── test_agents/               #     Agent tests
│   │   ├── test_core/                 #     Core module tests
│   │   ├── test_integrations/         #     Integration tests
│   │   ├── test_models/               #     Model tests
│   │   ├── test_repository/           #     Repository tests
│   │   ├── test_review/               #     Review tests
│   │   └── test_seo/                  #     SEO tests
│   ├── integration/                   #   Integration tests
│   └── e2e/                           #   End-to-end tests
│
└── Docs/                              # Design documentation
    ├── Functional_requirements.md     #   Detailed FRD
    ├── Architecture_Reevaluation_v2.md#   Architecture analysis
    ├── Testability_Review.md          #   Testability assessment
    └── Unit_Test_Plan.md              #   Test planning
```

## Configuration

All configuration is managed through **pydantic-settings** and loaded from the `.env` file. See [.env.example](.env.example) for all available settings.

Key configuration areas:

| Config | File | Controls |
|--------|------|----------|
| OpenCode | `config/opencode.py` | API key, base URL, timeout |
| SEO | `config/seo.py` | Page limits, output directory |
| Git | `config/git.py` | Branch, commit author |
| Logging | `config/logging.py` | Log level, format |
| Repository | `config/repository.py` | Analysis depth, ignore patterns |

## Testing

Run the full test suite:

```bash
python3 -m pytest tests/ -q
```

Run with coverage:

```bash
python3 -m pytest tests/ --cov=seo_agent --cov-report=term-missing
```

Run specific test modules:

```bash
python3 -m pytest tests/unit/test_core/ -v      # Core module tests
python3 -m pytest tests/unit/test_agents/ -v     # Agent tests
python3 -m pytest tests/unit/test_integrations/  # Integration tests
```

## Key Design Principles

- **Repository safety**: Only invisible SEO metadata is modified. User-visible content (headings, paragraphs, buttons, navigation) is never touched.
- **Session isolation**: Each OpenCode execution task runs in its own isolated session, preventing state accumulation and timeouts.
- **Framework agnostic**: Automatically detects React, Next.js, Vue, Angular, Django, Flask, static HTML, and more.
- **Review loop**: Every modification is reviewed and scored before being accepted. Failed reviews trigger up to 3 retries.

## Documentation

Detailed specifications are in the `Docs/` directory:

- [Functional Requirements](Docs/Functional_requirements.md) — Complete feature specification
- [Architecture Reevaluation](Docs/Architecture_Reevaluation_v2.md) — Architecture decisions
- [Testability Review](Docs/Testability_Review.md) — Testing strategy
- [Unit Test Plan](Docs/Unit_Test_Plan.md) — Test coverage plan
- [Project Guidelines](Project_guidelines.md) — Development standards

## License

Proprietary — Hireko.
