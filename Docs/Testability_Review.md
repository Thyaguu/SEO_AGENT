# SEO Agent Testability Review

**Document Version:** 1.0  
**Date:** 2024  
**Status:** Complete  
**Scope:** All 11 packages in the SEO Agent project

---

## Executive Summary

This document provides a comprehensive testability assessment of the SEO Agent codebase. The review evaluates each package's readiness for unit testing, identifies hidden dependencies, and provides concrete recommendations for improving test isolation.

### Overall Assessment

| Metric | Value |
|--------|-------|
| **Average Testability Score** | 6.5/10 |
| **Packages Ready for Testing** | 7 of 11 |
| **Refactoring Required** | 4 packages |
| **Primary Issue** | Global state in logging module |

### Package Summary

| Package | Score | Classification | Refactoring Required |
|--------|-------|----------------|---------------------|
| `models` | 10/10 | Excellent | No |
| `core` | 5/10 | Needs Improvement | Yes |
| `repository` | 7/10 | Good | No |
| `agents/planning` | 7/10 | Good | No |
| `agents/execution` | 6/10 | Needs Improvement | Yes |
| `review` | 9/10 | Excellent | No |
| `workflow` | 5/10 | Needs Improvement | Yes |
| `seo` | 6/10 | Needs Improvement | Yes |
| `git` | 6/10 | Needs Improvement | Yes |
| `api` | 7/10 | Good | No |
| `integrations/opencode` | 7/10 | Good | No |

---

## Critical Findings

### 1. Global State in Logging Module

**Location:** `seo_agent/core/logging.py`

**Issue:** The `get_logger()` function uses a module-level `_loggers` dictionary and `configure_logging()` modifies the root logger globally. This creates hidden state that persists across tests.

**Impact:** Tests may affect each other's logging configuration. Logger state from one test can leak into another.

**Recommendation:** 
- Inject logger as a dependency where possible
- Add `reset_loggers()` function for test cleanup
- Use `unittest.mock.patch` to mock `get_logger` in tests

### 2. Mutable WorkflowContext

**Location:** `seo_agent/workflow/context.py`

**Issue:** `WorkflowContext` is a mutable dataclass that accumulates state during workflow execution. Testing components that depend on context requires careful state management.

**Impact:** Tests must reset context state between test cases. Complex setup required for meaningful assertions.

**Recommendation:**
- Consider making context immutable with builder pattern
- Provide `reset()` method for test isolation
- Use fixtures to manage context lifecycle

### 3. Singleton Service Registration

**Location:** `seo_agent/api/dependencies.py`

**Issue:** All services are registered as singletons in the DI container. This means state can persist across tests if services cache data.

**Impact:** Test ordering may affect results. Shared state between tests.

**Recommendation:**
- Add `reset_container()` function for test isolation
- Consider transient registration for stateless services
- Document which services maintain state

---

## Package-by-Package Analysis

---

### 1. `models` Package

**Testability Score:** 10/10 (Excellent)

**Classification:** Excellent - Ready for large-scale unit testing

#### Package Contents
- `api.py` - API request/response models
- `repository.py` - Repository metadata models
- `seo.py` - SEO data models
- `task.py` - Task and execution models
- `workflow.py` - Workflow state models
- `review.py` - Review result models

#### Dependency Analysis
```
models
├── dataclasses (stdlib)
├── datetime (stdlib)
├── enum (stdlib)
└── typing (stdlib)
```

**No external dependencies.** All models are pure Python dataclasses.

#### Mocking Strategy
**No mocking required.** All models are frozen dataclasses with no behavior.

#### Testability Characteristics
- ✅ All classes are frozen dataclasses
- ✅ No external dependencies
- ✅ No state management
- ✅ No I/O operations
- ✅ Deterministic behavior
- ✅ Clear equality semantics

#### Required Fixtures
None required. Models can be instantiated directly in tests.

#### Testing Priority
**Priority 1** - Start testing here. These are the foundation for all other tests.

#### Example Test Pattern
```python
def test_seo_metadata_creation():
    # Direct instantiation - no mocking needed
    metadata = Metadata(
        title="Test Page",
        description="Test description",
        keywords=("test", "example"),
    )
    assert metadata.title == "Test Page"

def test_immutability():
    metadata = Metadata(title="Original")
    with pytest.raises(dataclasses.FrozenInstanceError):
        metadata.title = "Modified"
```

---

### 2. `core` Package

**Testability Score:** 5/10 (Needs Improvement)

**Classification:** Needs Improvement - Requires refactoring before comprehensive testing

#### Package Contents
- `constants.py` - Application constants
- `types.py` - Type aliases
- `utils.py` - Utility functions
- `logging.py` - **CRITICAL ISSUE** - Global state
- `result.py` - Result pattern implementation
- `exceptions.py` - Custom exceptions
- `dependency_injection.py` - DI container
- `result.py` - Result pattern

#### Dependency Analysis
```
core
├── dataclasses (stdlib)
├── enum (stdlib)
├── logging (stdlib) - GLOBAL STATE CONCERN
├── typing (stdlib)
└── pathlib (stdlib)
```

#### Hidden Dependencies
1. **Global `_loggers` dictionary** in `logging.py`
2. **Root logger modification** in `configure_logging()`
3. **Module-level container instance** in `dependency_injection.py`

#### Mocking Strategy
```python
# Mock get_logger for all core tests
@pytest.fixture(autouse=True)
def mock_logger():
    with patch('seo_agent.core.logging.get_logger') as mock:
        mock.return_value = MagicMock()
        yield mock

# Mock global container
@pytest.fixture
def mock_container():
    with patch('seo_agent.core.dependency_injection._container') as mock:
        yield mock
```

#### Testability Characteristics
- ⚠️ `logging.py` has global state issues
- ⚠️ `dependency_injection.py` has module-level singleton
- ✅ `result.py` is pure and testable
- ✅ `exceptions.py` is pure and testable
- ✅ `types.py` is pure and testable
- ✅ `constants.py` is pure and testable
- ⚠️ `utils.py` may have filesystem dependencies

#### Refactoring Required
**Yes** - For comprehensive testing:

1. Add `reset_loggers()` function to `logging.py`:
```python
def reset_loggers() -> None:
    """Reset all cached loggers. For testing only."""
    _loggers.clear()
```

2. Add `reset_container()` function to `dependency_injection.py`:
```python
def reset_container() -> None:
    """Reset the global container. For testing only."""
    global _container
    _container = Container()
```

#### Required Fixtures
```python
@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    from seo_agent.core import logging, dependency_injection
    logging.reset_loggers()
    dependency_injection.reset_container()
    yield
    logging.reset_loggers()
    dependency_injection.reset_container()
```

#### Testing Priority
**Priority 2** - After models, test the Result pattern and exceptions.

---

### 3. `repository` Package

**Testability Score:** 7/10 (Good)

**Classification:** Good - Minor issues, mostly ready for testing

#### Package Contents
- `framework_detector.py` - Detects project frameworks
- `metadata_parser.py` - Parses metadata files
- `page_discovery.py` - Discovers SEO pages
- `scanner.py` - Repository scanning

#### Dependency Analysis
```
repository
├── seo_agent.core.logging (get_logger)
├── seo_agent.core.result (Result)
├── seo_agent.models.repository (models)
├── seo_agent.models.seo (models)
├── pathlib (stdlib)
├── json (stdlib)
├── re (stdlib)
└── typing (stdlib)
```

#### Hidden Dependencies
1. **Filesystem access** - All services read/write files
2. **Global logger** - `get_logger()` call in each service

#### Mocking Strategy
```python
@pytest.fixture
def mock_logger():
    with patch('seo_agent.repository.scanner.get_logger') as mock:
        mock.return_value = MagicMock()
        yield mock

@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure."""
    (tmp_path / "index.html").write_text("<html><body>Test</body></html>")
    return tmp_path

def test_scanner_with_mocked_filesystem(mock_logger, temp_repo):
    scanner = RepositoryScanner()
    result = scanner.scan(temp_repo)
    assert result.pages_found >= 0
```

#### Testability Characteristics
- ✅ Pure frozen dataclasses for models
- ✅ Result[T, E] return types for error handling
- ⚠️ Filesystem dependencies require temp directory fixtures
- ⚠️ Global logger dependency

#### Required Fixtures
```python
@pytest.fixture
def temp_repository(tmp_path):
    """Create a temporary repository with test files."""
    (tmp_path / "index.html").write_text("<html><head><title>Test</title></head></html>")
    (tmp_path / "about.html").write_text("<html><body>About</body></html>")
    return tmp_path

@pytest.fixture
def mock_logger():
    with patch('seo_agent.repository.scanner.get_logger') as mock:
        mock.return_value = MagicMock()
        yield mock
```

#### Testing Priority
**Priority 3** - Test after core utilities.

---

### 4. `agents/planning` Package

**Testability Score:** 7/10 (Good)

**Classification:** Good - Mostly testable with proper mocking

#### Package Contents
- `planner.py` - Main planning orchestrator
- `keyword_selector.py` - Keyword selection logic
- `repository_analyzer.py` - Repository analysis
- `task_planner.py` - Task planning logic

#### Dependency Analysis
```
agents/planning
├── seo_agent.core.logging (get_logger)
├── seo_agent.core.result (Result)
├── seo_agent.models.task (models)
├── seo_agent.models.seo (models)
├── seo_agent.workflow.orchestrator (WorkflowOrchestrator)
├── seo_agent.workflow.context (WorkflowContext)
├── seo_agent.workflow.stages (WorkflowStage)
├── seo_agent.repository.scanner (RepositoryScanner)
├── seo_agent.repository.framework_detector (FrameworkDetector)
└── typing (stdlib)
```

#### Hidden Dependencies
1. **Global logger** - `get_logger()` in each module
2. **WorkflowOrchestrator** - Complex orchestrator dependency
3. **RepositoryScanner** - Filesystem access

#### Mocking Strategy
```python
@pytest.fixture
def mock_planner_dependencies():
    with patch('seo_agent.agents.planning.planner.get_logger') as log_mock, \
         patch('seo_agent.agents.planning.planner.RepositoryScanner') as scanner_mock, \
         patch('seo_agent.agents.planning.planner.FrameworkDetector') as detector_mock:
        log_mock.return_value = MagicMock()
        yield {
            'logger': log_mock,
            'scanner': scanner_mock,
            'detector': detector_mock,
        }

def test_keyword_selector():
    """KeywordSelector is highly testable - pure logic."""
    selector = KeywordSelector()
    keywords = [
        KeywordPayload(term="test", search_volume=1000, difficulty=50),
        KeywordPayload(term="example", search_volume=500, difficulty=30),
    ]
    result = selector.select_keywords(keywords, max_keywords=1)
    assert len(result.selected_keywords) == 1
```

#### Testability Characteristics
- ✅ Pure frozen dataclasses for models (KeywordScore, SEOOpportunity, TaskGroup)
- ✅ KeywordSelector has testable pure methods
- ⚠️ Planner has complex orchestrator dependencies
- ⚠️ RepositoryAnalyzer depends on RepositoryScanner

#### Required Fixtures
```python
@pytest.fixture
def sample_keyword_payload():
    return [
        KeywordPayload(term="seo", search_volume=1000, difficulty=40),
        KeywordPayload(term="optimization", search_volume=800, difficulty=35),
    ]

@pytest.fixture
def mock_repository_scanner():
    mock = MagicMock(spec=RepositoryScanner)
    mock.scan.return_value = Success(RepositoryScanResult(...))
    return mock
```

#### Testing Priority
**Priority 3** - Test KeywordSelector and TaskPlanner first (pure logic), then Planner.

---

### 5. `agents/execution` Package

**Testability Score:** 6/10 (Needs Improvement)

**Classification:** Needs Improvement - Critical dependency on OpenCodeAdapter

#### Package Contents
- `executor.py` - ExecutionAgent class

#### Dependency Analysis
```
agents/execution
├── seo_agent.core.logging (get_logger)
├── seo_agent.core.result (Result)
├── seo_agent.core.exceptions (ExecutionError)
├── seo_agent.models.task (ExecutionResult, Task)
├── seo_agent.integrations.opencode.adapter (OpenCodeAdapter)
├── seo_agent.agents.planning.task_planner (TaskPlanner)
└── typing (stdlib)
```

#### Hidden Dependencies
1. **OpenCodeAdapter** - **CRITICAL** - Raises ExecutionError if None
2. **Global logger** - `get_logger()` call

#### Critical Issue
```python
# From executor.py
if self._adapter is None:
    raise ExecutionError("OpenCodeAdapter is required for execution")
```

The `ExecutionAgent` has a hard dependency on `OpenCodeAdapter`. If not injected, it raises an error at runtime rather than failing gracefully.

#### Mocking Strategy
```python
@pytest.fixture
def mock_opencode_adapter():
    mock = MagicMock(spec=OpenCodeAdapter)
    mock.execute.return_value = Success(OpenCodeExecutionResult(...))
    return mock

@pytest.fixture
def execution_agent(mock_opencode_adapter):
    return ExecutionAgent(adapter=mock_opencode_adapter)

def test_execution_agent_requires_adapter():
    """Verify that ExecutionAgent requires an adapter."""
    with pytest.raises(ExecutionError):
        ExecutionAgent(adapter=None)

def test_execution_success(execution_agent, mock_opencode_adapter):
    result = execution_agent.execute(tasks=[...])
    assert result.is_success()
    mock_opencode_adapter.execute.assert_called_once()
```

#### Testability Characteristics
- ✅ Pure frozen dataclasses for models
- ✅ Result[T, E] return types
- ⚠️ Critical dependency on OpenCodeAdapter
- ⚠️ Global logger dependency

#### Refactoring Recommended
Consider adding a factory method for easier testing:
```python
@classmethod
def create_with_mock_adapter(cls) -> ExecutionAgent:
    """Create an agent with a mock adapter for testing."""
    mock_adapter = MagicMock(spec=OpenCodeAdapter)
    return cls(adapter=mock_adapter)
```

#### Required Fixtures
```python
@pytest.fixture
def mock_opencode_adapter():
    mock = MagicMock(spec=OpenCodeAdapter)
    mock.execute.return_value = Success(OpenCodeExecutionResult(...))
    return mock

@pytest.fixture
def execution_agent(mock_opencode_adapter):
    return ExecutionAgent(adapter=mock_opencode_adapter)
```

#### Testing Priority
**Priority 4** - Test with mocked OpenCodeAdapter.

---

### 6. `review` Package

**Testability Score:** 9/10 (Excellent)

**Classification:** Excellent - Highly testable, minimal dependencies

#### Package Contents
- `validator.py` - ReviewValidator class
- `diff_analyzer.py` - DiffAnalyzer and FileClassifier
- `feedback.py` - ReviewResult and FeedbackAggregator

#### Dependency Analysis
```
review
├── seo_agent.core.logging (get_logger)
├── seo_agent.core.result (Result)
├── seo_agent.models.review (ValidationIssue, ValidationResult)
├── seo_agent.models.task (Task)
└── typing (stdlib)
```

#### Hidden Dependencies
1. **Global logger** - `get_logger()` call

#### Mocking Strategy
```python
@pytest.fixture
def mock_logger():
    with patch('seo_agent.review.validator.get_logger') as mock:
        mock.return_value = MagicMock()
        yield mock

def test_validation_issue():
    """ValidationIssue is a frozen dataclass - directly testable."""
    issue = ValidationIssue(
        severity="error",
        message="Missing title tag",
        file_path="/test.html",
        line_number=5,
    )
    assert issue.severity == "error"

def test_validator_with_mocked_logger(mock_logger):
    validator = ReviewValidator()
    result = validator.validate(tasks=[...])
    assert isinstance(result, ValidationResult)
```

#### Testability Characteristics
- ✅ Pure frozen dataclasses for models
- ✅ Read-only validation logic
- ✅ No filesystem dependencies
- ✅ Deterministic behavior
- ⚠️ Global logger dependency (minor)

#### Required Fixtures
```python
@pytest.fixture
def sample_tasks():
    return [
        Task(type=TaskType.GENERATE_PAGE, ...),
        Task(type=TaskType.EDIT_FILE, ...),
    ]

@pytest.fixture
def mock_logger():
    with patch('seo_agent.review.validator.get_logger') as mock:
        mock.return_value = MagicMock()
        yield mock
```

#### Testing Priority
**Priority 2** - High priority, excellent testability.

---

### 7. `workflow` Package

**Testability Score:** 5/10 (Needs Improvement)

**Classification:** Needs Improvement - Mutable state and complex orchestration

#### Package Contents
- `orchestrator.py` - WorkflowOrchestrator class
- `context.py` - WorkflowContext (mutable dataclass)
- `stages.py` - WorkflowStage enum and stage utilities

#### Dependency Analysis
```
workflow
├── seo_agent.core.logging (get_logger)
├── seo_agent.core.result (Result)
├── seo_agent.workflow.context (WorkflowContext)
├── seo_agent.workflow.stages (WorkflowStage)
├── seo_agent.models.repository (models)
├── seo_agent.models.review (models)
├── seo_agent.models.task (models)
└── typing (stdlib)
```

#### Hidden Dependencies
1. **Mutable WorkflowContext** - Accumulates state during execution
2. **Global logger** - `get_logger()` call
3. **StageHandler callable** - Dynamic handler registration

#### Critical Issues
```python
# From context.py - MUTABLE DATACLASS
@dataclass
class WorkflowContext:  # NOT frozen!
    repository_path: Path
    stage: WorkflowStage
    transitions: list[StageTransition]
    errors: list[str]
    # ... many more fields that can be mutated
```

#### Mocking Strategy
```python
@pytest.fixture
def fresh_workflow_context(tmp_path):
    """Create a fresh context for each test."""
    return WorkflowContext(repository_path=tmp_path)

@pytest.fixture
def mock_stage_handler():
    """Create a mock stage handler."""
    async def handler(ctx: WorkflowContext) -> Result[None, str]:
        return Success(None)
    return handler

def test_context_stage_transitions(fresh_workflow_context):
    """Test context state management."""
    assert fresh_workflow_context.stage == WorkflowStage.INITIAL
    fresh_workflow_context.update_stage(WorkflowStage.PLANNING)
    assert fresh_workflow_context.stage == WorkflowStage.PLANNING

def test_orchestrator_with_handlers(mock_stage_handler):
    orchestrator = WorkflowOrchestrator()
    orchestrator.register_stage_handler(WorkflowStage.PLANNING, mock_stage_handler)
    # ... test execution
```

#### Testability Characteristics
- ✅ WorkflowStage enum is pure
- ✅ StageInfo is a frozen dataclass
- ⚠️ WorkflowContext is mutable
- ⚠️ WorkflowOrchestrator has complex dependencies
- ⚠️ StageHandler callable type adds complexity

#### Refactoring Recommended
Consider making WorkflowContext partially immutable:
```python
@dataclass(frozen=True)
class WorkflowContextSnapshot:
    """Immutable snapshot of workflow context at a point in time."""
    repository_path: Path
    stage: WorkflowStage
    errors: tuple[str, ...]
    # ... other fields as tuples
```

#### Required Fixtures
```python
@pytest.fixture
def workflow_context(tmp_path):
    """Create a test workflow context."""
    return WorkflowContext(repository_path=tmp_path)

@pytest.fixture
def mock_stage_handlers():
    """Create mock handlers for all stages."""
    async def noop_handler(ctx: WorkflowContext) -> Result[None, str]:
        return Success(None)
    return {stage: noop_handler for stage in WorkflowStage}
```

#### Testing Priority
**Priority 5** - Test after simpler packages.

---

### 8. `seo` Package

**Testability Score:** 6/10 (Needs Improvement)

**Classification:** Needs Improvement - Container dependency and filesystem I/O

#### Package Contents
- `metadata_optimizer.py` - MetadataOptimizer class
- `seo_page_generator.py` - SEOPageGenerator class
- `sitemap.py` - SitemapService class
- `robots.py` - RobotsService class

#### Dependency Analysis
```
seo
├── seo_agent.core.logging (get_logger)
├── seo_agent.core.result (Result)
├── seo_agent.core.dependency_injection (Container)
├── seo_agent.models.seo (Metadata, SEOPage, SitemapEntry)
├── seo_agent.models.task (ExecutionResult)
├── pathlib (stdlib)
└── re (stdlib)
```

#### Hidden Dependencies
1. **Container dependency** - All services require Container
2. **Filesystem I/O** - Read/write HTML, XML, TXT files
3. **Global logger** - `get_logger()` call

#### Mocking Strategy
```python
@pytest.fixture
def mock_container():
    mock = MagicMock(spec=Container)
    return mock

@pytest.fixture
def metadata_optimizer(mock_container):
    return MetadataOptimizer(container=mock_container)

@pytest.fixture
def temp_html_file(tmp_path):
    """Create a temporary HTML file for testing."""
    html_content = """
    <html>
    <head><title>Test</title></head>
    <body>Content</body>
    </html>
    """
    file_path = tmp_path / "test.html"
    file_path.write_text(html_content)
    return file_path

def test_metadata_optimizer_reads_file(metadata_optimizer, temp_html_file):
    result = metadata_optimizer.optimize_page(temp_html_file, Metadata(...))
    assert result.is_success()
```

#### Testability Characteristics
- ✅ Pure frozen dataclasses for models
- ✅ Result[T, E] return types
- ⚠️ Container dependency
- ⚠️ Filesystem I/O operations
- ⚠️ Global logger dependency

#### Required Fixtures
```python
@pytest.fixture
def mock_container():
    mock = MagicMock(spec=Container)
    return mock

@pytest.fixture
def sample_metadata():
    return Metadata(
        title="Test Title",
        description="Test description",
        keywords=("test", "example"),
    )

@pytest.fixture
def temp_html_file(tmp_path):
    content = "<html><head><title>Original</title></head><body>Test</body></html>"
    file_path = tmp_path / "test.html"
    file_path.write_text(content)
    return file_path
```

#### Testing Priority
**Priority 4** - Test with mocked Container and temp files.

---

### 9. `git` Package

**Testability Score:** 6/10 (Needs Improvement)

**Classification:** Needs Improvement - External library dependency

#### Package Contents
- `client.py` - GitClient class
- `operations.py` - GitOperations class

#### Dependency Analysis
```
git
├── seo_agent.core.logging (get_logger)
├── seo_agent.core.result (Result)
├── seo_agent.core.exceptions (GitError)
├── seo_agent.models.repository (RepositoryStatus)
├── git (GitPython - external library)
└── pathlib (stdlib)
```

#### Hidden Dependencies
1. **GitPython library** - External dependency wrapping git commands
2. **Global logger** - `get_logger()` call
3. **Actual git repository** - Requires real .git directory

#### Mocking Strategy
```python
@pytest.fixture
def mock_git_repo():
    """Create a mock git.Repo object."""
    mock = MagicMock(spec=git.Repo)
    mock.active_branch.name = "main"
    mock.is_dirty.return_value = False
    mock.untracked_files = []
    mock.index.diff.return_value = []
    return mock

@pytest.fixture
def git_client(mock_git_repo):
    with patch('seo_agent.git.client.git.Repo') as mock_repo_class:
        mock_repo_class.return_value = mock_git_repo
        client = GitClient()
        yield client

def test_repository_status_frozen():
    """RepositoryStatus is a frozen dataclass - directly testable."""
    status = RepositoryStatus(
        branch="main",
        is_dirty=False,
        staged_files=(),
        modified_files=(),
        untracked_files=(),
    )
    assert status.branch == "main"

def test_git_client_with_mocked_repo(git_client, tmp_path):
    result = git_client.get_repository_status(tmp_path)
    assert result.is_success()
```

#### Testability Characteristics
- ✅ RepositoryStatus is a frozen dataclass
- ✅ Result[T, E] return types
- ⚠️ GitPython external dependency
- ⚠️ Requires actual or mocked git repository
- ⚠️ Global logger dependency

#### Required Fixtures
```python
@pytest.fixture
def mock_git_repo():
    mock = MagicMock(spec=git.Repo)
    mock.active_branch.name = "main"
    mock.is_dirty.return_value = False
    mock.untracked_files = []
    mock.index.diff.return_value = []
    return mock

@pytest.fixture
def git_client_with_mock():
    with patch('seo_agent.git.client.git.Repo') as mock_class:
        mock_class.return_value = MagicMock(spec=git.Repo)
        yield GitClient()
```

#### Testing Priority
**Priority 5** - Test with fully mocked GitPython.

---

### 10. `api` Package

**Testability Score:** 7/10 (Good)

**Classification:** Good - FastAPI testing with proper fixtures

#### Package Contents
- `routes.py` - FastAPI endpoints
- `dependencies.py` - DI container setup
- `schemas.py` - Pydantic models
- `middleware.py` - Request/response middleware
- `health.py` - Health check endpoints

#### Dependency Analysis
```
api
├── fastapi (external framework)
├── pydantic (external library)
├── seo_agent.core.logging (get_logger)
├── seo_agent.core.dependency_injection (Container)
├── seo_agent.workflow.orchestrator (WorkflowOrchestrator)
├── seo_agent.workflow.context (WorkflowContext)
├── seo_agent.workflow.stages (WorkflowStage)
└── typing (stdlib)
```

#### Hidden Dependencies
1. **FastAPI TestClient** - Requires test client for endpoint testing
2. **DI Container** - Services registered as singletons
3. **Global logger** - `get_logger()` call

#### Mocking Strategy
```python
from fastapi.testclient import TestClient

@pytest.fixture
def test_client():
    from seo_agent.api.main import app
    return TestClient(app)

@pytest.fixture
def mock_orchestrator():
    mock = MagicMock(spec=WorkflowOrchestrator)
    mock.run.return_value = Success(WorkflowContext(...))
    return mock

def test_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_seo_run_endpoint_with_mock(test_client, mock_orchestrator):
    with patch('seo_agent.api.routes.get_workflow_orchestrator') as mock_get:
        mock_get.return_value = mock_orchestrator
        response = test_client.post("/seo/run", json={...})
        assert response.status_code == 200
```

#### Testability Characteristics
- ✅ Pydantic schemas are pure data models
- ✅ Routes follow thin controller pattern
- ✅ Health endpoints are simple
- ⚠️ Requires FastAPI TestClient
- ⚠️ DI container singleton state
- ⚠️ Global logger dependency

#### Required Fixtures
```python
@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient
    from seo_agent.api.main import app
    return TestClient(app)

@pytest.fixture
def mock_orchestrator():
    mock = MagicMock(spec=WorkflowOrchestrator)
    mock.run.return_value = Success(WorkflowContext(...))
    return mock

@pytest.fixture
def sample_request_payload():
    return {
        "request_id": "test-123",
        "repository_path": "/tmp/test-repo",
        "seo_payload": {
            "target_urls": ["https://example.com"],
            "seed_keywords": [{"term": "test", "type": "primary"}],
        },
    }
```

#### Testing Priority
**Priority 4** - Test after core services are tested.

---

### 11. `integrations/opencode` Package

**Testability Score:** 7/10 (Good)

**Classification:** Good - Adapter pattern with HTTP client

#### Package Contents
- `adapter.py` - OpenCodeAdapter class
- `client.py` - OpenCodeClient HTTP client
- `models.py` - OpenCode request/response models

#### Dependency Analysis
```
integrations/opencode
├── seo_agent.core.logging (get_logger)
├── seo_agent.core.result (Result)
├── seo_agent.core.exceptions (IntegrationError)
├── seo_agent.integrations.opencode.models (models)
├── seo_agent.models.task (models)
├── urllib.request (stdlib - HTTP client)
└── json (stdlib)
```

#### Hidden Dependencies
1. **urllib** - HTTP client for OpenCode API
2. **Global logger** - `get_logger()` call
3. **External API** - OpenCode API endpoint

#### Mocking Strategy
```python
@pytest.fixture
def mock_opencode_client():
    mock = MagicMock(spec=OpenCodeClient)
    mock.execute.return_value = Success(OpenCodeResponse(...))
    return mock

@pytest.fixture
def opencode_adapter(mock_opencode_client):
    return OpenCodeAdapter(client=mock_opencode_client)

def test_opencode_models_frozen():
    """All OpenCode models are frozen dataclasses."""
    request = OpenCodeRequest(
        request_id="test-123",
        instructions="Test instructions",
    )
    assert request.request_id == "test-123"

def test_adapter_with_mocked_client(opencode_adapter, mock_opencode_client):
    result = opencode_adapter.execute_simple(
        request_id="test-123",
        instructions="Test",
    )
    assert result.is_success()
    mock_opencode_client.execute.assert_called_once()
```

#### Testability Characteristics
- ✅ All models are frozen dataclasses
- ✅ Result[T, E] return types
- ✅ Adapter pattern isolates external calls
- ⚠️ HTTP client requires mocking
- ⚠️ Global logger dependency

#### Required Fixtures
```python
@pytest.fixture
def mock_opencode_client():
    mock = MagicMock(spec=OpenCodeClient)
    mock.execute.return_value = Success(OpenCodeResponse(
        request_id="test",
        status=OpenCodeStatus.COMPLETED,
        results=(),
    ))
    return mock

@pytest.fixture
def opencode_adapter(mock_opencode_client):
    return OpenCodeAdapter(client=mock_opencode_client)
```

#### Testing Priority
**Priority 3** - Test models first, then adapter with mocked client.

---

## Cross-Cutting Concerns

### Global State Summary

| Module | Global State | Impact | Mitigation |
|--------|-------------|--------|------------|
| `core/logging.py` | `_loggers` dict, root logger | High | Add `reset_loggers()`, mock in tests |
| `core/dependency_injection.py` | `_container` singleton | Medium | Add `reset_container()`, mock in tests |
| `api/dependencies.py` | Service singletons | Medium | Reset container between tests |

### Recommended Test Fixtures

Create a `tests/conftest.py` with shared fixtures:

```python
"""Shared pytest fixtures for SEO Agent tests."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Reset global state before each test
@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    from seo_agent.core import logging, dependency_injection
    
    # Store original state
    original_loggers = logging._loggers.copy()
    original_container = dependency_injection._container
    
    yield
    
    # Restore state
    logging._loggers.clear()
    logging._loggers.update(original_loggers)
    dependency_injection._container = original_container


@pytest.fixture
def mock_logger():
    """Mock get_logger for isolated testing."""
    with patch('seo_agent.core.logging.get_logger') as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture
def mock_container():
    """Mock the global container."""
    mock = MagicMock()
    with patch('seo_agent.core.dependency_injection.get_container', return_value=mock):
        yield mock


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure."""
    (tmp_path / "index.html").write_text("<html><body>Test</body></html>")
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture
def sample_metadata():
    """Create sample SEO metadata."""
    from seo_agent.models.seo import Metadata
    return Metadata(
        title="Test Page",
        description="Test description",
        keywords=("test", "example"),
    )
```

---

## Recommendations

### Immediate Actions (Before Writing Tests)

1. **Add test cleanup functions to core modules:**
   - `seo_agent/core/logging.py`: Add `reset_loggers()` function
   - `seo_agent/core/dependency_injection.py`: Add `reset_container()` function

2. **Create shared test fixtures:**
   - Create `tests/conftest.py` with `reset_global_state` fixture
   - Add `mock_logger` fixture for all packages

3. **Document testing patterns:**
   - Add docstrings with test examples to complex classes
   - Create `tests/README.md` with testing guide

### Refactoring Suggestions (Optional)

1. **WorkflowContext immutability:**
   - Consider adding `to_immutable()` method
   - Or create `WorkflowContextSnapshot` frozen dataclass

2. **Service factory methods:**
   - Add `create_with_mock_*()` methods to ExecutionAgent
   - Simplifies test setup

3. **Logger injection:**
   - Consider passing logger as constructor parameter
   - Reduces global state dependency

---

## Conclusion

The SEO Agent codebase has a **good foundation for testing** with 7 of 11 packages rated as "Good" or "Excellent" testability. The primary obstacles are:

1. **Global state in logging** - Addressable with reset functions
2. **Mutable WorkflowContext** - Addressable with careful fixture usage
3. **Container dependencies** - Addressable with mocking

With the recommended fixtures and cleanup functions in place, the codebase is **ready for large-scale unit testing**. The frozen dataclass patterns throughout the models layer provide an excellent foundation for test-driven development.

### Final Assessment

**Is the current architecture ready for large-scale unit testing?**

**Yes, with minor preparation.** The codebase follows good practices (frozen dataclasses, Result pattern, dependency injection) that facilitate testing. The main work is:
1. Adding test cleanup utilities (1-2 hours)
2. Creating shared fixtures (2-3 hours)
3. Writing tests following the patterns in this document

The investment in test infrastructure will pay dividends in code quality and regression prevention.