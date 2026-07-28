# SEO Agent Unit Test Plan

**Version:** 1.0  
**Date:** 2024  
**Status:** Draft  
**Author:** SEO Agent Development Team  

---

## 1. Executive Summary

This document outlines the comprehensive unit testing strategy for the SEO Agent project. The codebase consists of approximately 76 source files organized into 10 packages. All 11 test files are currently empty placeholders requiring implementation.

### 1.1 Testing Objectives

1. **Achieve 80%+ code coverage** across all packages
2. **Validate core patterns** (Result type, DI container, exception hierarchy)
3. **Test all public APIs** with unit tests
4. **Ensure workflow stages** are properly tested
5. **Validate integration boundaries** with mocked external dependencies

### 1.2 Current State Assessment

| Package | Files | Test File | Coverage | Priority |
|---------|-------|-----------|----------|----------|
| Core | 7 | test_core | 0% | HIGH |
| Models | 6 | N/A | N/A | MEDIUM |
| Workflow | 3 | test_workflow | 0% | HIGH |
| API | 6 | N/A | N/A | HIGH |
| Repository | 4 | test_repository | 0% | HIGH |
| Review | 3 | test_review | 0% | HIGH |
| SEO | 4 | test_seo | 0% | MEDIUM |
| Agents | 5 | test_agents | 0% | HIGH |
| Git | 2 | N/A | N/A | MEDIUM |
| Integrations | 3 | N/A | N/A | MEDIUM |

---

## 2. Testing Strategy

### 2.1 Test Organization

```
tests/
├── unit/
│   ├── test_core/
│   │   ├── __init__.py
│   │   ├── test_result.py          # Result[T, E] pattern tests
│   │   ├── test_container.py       # DI container tests
│   │   ├── test_exceptions.py      # Exception hierarchy tests
│   │   ├── test_logging.py         # Logging configuration tests
│   │   ├── test_types.py           # Type definitions tests
│   │   └── test_utils.py           # Utility function tests
│   ├── test_models/
│   │   ├── __init__.py
│   │   ├── test_api_models.py      # API request/response models
│   │   ├── test_repository_models.py
│   │   ├── test_seo_models.py
│   │   ├── test_task_models.py
│   │   └── test_workflow_models.py
│   ├── test_workflow/
│   │   ├── __init__.py
│   │   ├── test_context.py          # WorkflowContext tests
│   │   ├── test_stages.py           # WorkflowStage enum tests
│   │   └── test_orchestrator.py     # WorkflowOrchestrator tests
│   ├── test_api/
│   │   ├── __init__.py
│   │   ├── test_routes.py           # API endpoint tests
│   │   ├── test_schemas.py          # Pydantic model validation tests
│   │   ├── test_middleware.py       # Middleware tests
│   │   └── test_dependencies.py     # Dependency injection tests
│   ├── test_repository/
│   │   ├── __init__.py
│   │   ├── test_scanner.py          # RepositoryScanner tests
│   │   ├── test_framework_detector.py
│   │   ├── test_page_discovery.py
│   │   └── test_metadata_parser.py
│   ├── test_review/
│   │   ├── __init__.py
│   │   ├── test_validator.py        # MetadataValidator tests
│   │   ├── test_diff_analyzer.py    # FileClassifier tests
│   │   └── test_feedback.py
│   ├── test_seo/
│   │   ├── __init__.py
│   │   ├── test_metadata_optimizer.py
│   │   ├── test_robots.py
│   │   ├── test_sitemap.py
│   │   └── test_seo_page_generator.py
│   ├── test_agents/
│   │   ├── __init__.py
│   │   ├── test_planner.py          # Planner orchestration tests
│   │   ├── test_keyword_selector.py
│   │   ├── test_repository_analyzer.py
│   │   ├── test_task_planner.py
│   │   └── test_executor.py         # ExecutionAgent tests
│   ├── test_git/
│   │   ├── __init__.py
│   │   ├── test_client.py           # GitClient tests
│   │   └── test_operations.py
│   └── test_integrations/
│       ├── __init__.py
│       ├── test_opencode_client.py
│       ├── test_opencode_adapter.py
│       └── test_models.py
├── integration/
│   └── test_workflow/
│       ├── __init__.py
│       └── test_stage_integration.py
└── e2e/
    └── test_pipeline/
        ├── __init__.py
        └── test_end_to_end.py
```

### 2.2 Test Naming Conventions

- **Unit tests:** `test_<module_name>_<description>.py`
- **Test class:** `Test<ClassName>`
- **Test method:** `test_<method_name>_<scenario>`
- **Fixtures:** `fixture_<name>`

### 2.3 Testing Framework

- **Framework:** pytest
- **Mocking:** pytest-mock, unittest.mock
- **Coverage:** pytest-cov
- **Fixtures:** pytest fixtures with proper scoping

---

## 3. Package-by-Package Test Plan

### 3.1 Core Package (Priority: HIGH)

**Files to Test:**
- `seo_agent/core/result.py` - Result[T, E] pattern
- `seo_agent/core/dependency_injection.py` - Container class
- `seo_agent/core/exceptions.py` - Exception hierarchy
- `seo_agent/core/logging.py` - Logging configuration
- `seo_agent/core/types.py` - Type definitions
- `seo_agent/core/utils.py` - Utility functions
- `seo_agent/core/constants.py` - Constants

**Test Cases:**

#### test_result.py
```python
class TestSuccess:
    - test_is_success_returns_true
    - test_is_failure_returns_false
    - test_get_or_none_returns_value
    - test_get_error_or_none_returns_none
    - test_unwrap_returns_value
    - test_unwrap_or_returns_value

class TestFailure:
    - test_is_success_returns_false
    - test_is_failure_returns_true
    - test_get_or_none_returns_none
    - test_get_error_or_none_returns_error
    - test_unwrap_raises_value_error
    - test_unwrap_or_returns_default

class TestResultHelpers:
    - test_success_creates_success_instance
    - test_failure_creates_failure_instance
    - test_from_exception_converts_exception
    - test_from_bool_returns_correct_result
```

#### test_container.py
```python
class TestContainer:
    - test_register_singleton_returns_same_instance
    - test_register_transient_returns_new_instance
    - test_resolve_raises_when_not_registered
    - test_is_registered_returns_correct_value
    - test_clear_removes_all_registrations
    - test_register_raises_on_duplicate

class TestInjectDecorator:
    - test_inject_resolves_dependencies
    - test_inject_raises_on_missing_dependency
```

#### test_exceptions.py
```python
class TestExceptionHierarchy:
    - test_seo_agent_error_is_base
    - test_all_subclasses_inherit_correctly
    - test_exception_contains_details
    - test_str_returns_message

class TestSpecificExceptions:
    - test_validation_error_creation
    - test_execution_error_creation
    - test_review_error_creation
    - test_git_error_creation
    - test_integration_error_creation
```

**Dependencies to Mock:** None (pure Python)

---

### 3.2 Models Package (Priority: MEDIUM)

**Files to Test:**
- `seo_agent/models/api.py` - API models
- `seo_agent/models/repository.py` - RepositoryInfo, FrameworkInfo
- `seo_agent/models/seo.py` - SEOPage, Metadata, Keyword
- `seo_agent/models/task.py` - ExecutionPlan, Task, Phase
- `seo_agent/models/workflow.py` - WorkflowResult
- `seo_agent/models/review.py` - ReviewResult

**Test Cases:**

#### test_api_models.py
```python
class TestSEOPayload:
    - test_valid_payload_creation
    - test_field_validator_rejects_empty_seed_keywords
    - test_field_validator_accepts_valid_keywords

class TestSEOResponse:
    - test_response_serialization
    - test_stage_results_included
```

#### test_task_models.py
```python
class TestExecutionPlan:
    - test_total_tasks_calculation
    - test_phases_property
    - test_request_id_required

class TestTask:
    - test_task_status_transitions
    - test_task_type_enum_values
    - test_priority_ordering

class TestPhase:
    - test_phase_id_generation
    - test_tasks_list_operations
```

**Dependencies to Mock:** None (pure Pydantic models)

---

### 3.3 Workflow Package (Priority: HIGH)

**Files to Test:**
- `seo_agent/workflow/context.py` - WorkflowContext
- `seo_agent/workflow/stages.py` - WorkflowStage enum
- `seo_agent/workflow/orchestrator.py` - WorkflowOrchestrator

**Test Cases:**

#### test_context.py
```python
class TestWorkflowContext:
    - test_initialization_with_required_fields
    - test_update_stage_changes_stage
    - test_record_failure_adds_error
    - test_add_error_accumulates_errors
    - test_get_stage_duration_calculates_correctly
    - test_get_total_duration_calculates_correctly
    - test_has_errors_returns_correct_value
    - test_get_error_summary_returns_string
    - test_is_complete_returns_true_at_terminal
    - test_is_successful_returns_true_when_completed
    - test_set_repository_info_stores_info
    - test_stage_transitions_recorded
```

#### test_stages.py
```python
class TestWorkflowStage:
    - test_all_stages_have_correct_properties
    - test_terminal_stages_identified
    - test_execution_stages_identified
    - test_display_name_readable
    - test_stage_ordering

class TestStageTransitions:
    - test_valid_transitions_defined
    - test_invalid_transitions_raise_error
    - test_can_transition_returns_correct_value
    - test_get_next_stage_returns_correct_stage
```

#### test_orchestrator.py
```python
class TestWorkflowOrchestrator:
    - test_initialization_with_config
    - test_register_stage_handler_adds_handler
    - test_register_handlers_adds_multiple
    - test_run_executes_all_stages
    - test_run_stops_on_failure
    - test_run_respects_max_retries
    - test_run_creates_checkpoint_on_interval
    - test_context_updated_after_each_stage

class TestOrchestratorConfig:
    - test_default_config_values
    - test_custom_config_overrides
```

**Dependencies to Mock:** Stage handlers (use simple lambda functions)

---

### 3.4 API Package (Priority: HIGH)

**Files to Test:**
- `seo_agent/api/routes.py` - FastAPI endpoints
- `seo_agent/api/schemas.py` - Pydantic models
- `seo_agent/api/middleware.py` - Middleware
- `seo_agent/api/dependencies.py` - Dependency injection
- `seo_agent/api/health.py` - Health check

**Test Cases:**

#### test_routes.py
```python
class TestSEORunEndpoint:
    - test_valid_request_returns_200
    - test_invalid_payload_returns_422
    - test_request_to_context_conversion
    - test_context_to_response_mapping
    - test_status_message_generation
    - test_warnings_generation
    - test_workflow_failure_returns_500
    - test_workflow_timeout_handling

class TestHealthEndpoint:
    - test_health_returns_200
    - test_health_includes_version
```

#### test_schemas.py
```python
class TestExecutionStatus:
    - test_all_status_values_defined
    - test_status_transitions_valid

class TestSEOAgentRequest:
    - test_valid_request_passes_validation
    - test_invalid_keywords_rejected
    - test_missing_required_fields_rejected
    - test_field_validators_work_correctly

class TestFileChange:
    - test_to_dict_returns_correct_structure
    - test_change_type_enum_values

class TestStageResult:
    - test_duration_calculation
    - test_error_handling
```

#### test_middleware.py
```python
class TestMiddleware:
    - test_request_logging_middleware
    - test_error_handling_middleware
    - test_cors_middleware_configuration
```

**Dependencies to Mock:**
- WorkflowOrchestrator
- Container
- Logger

---

### 3.5 Repository Package (Priority: HIGH)

**Files to Test:**
- `seo_agent/repository/scanner.py` - RepositoryScanner
- `seo_agent/repository/framework_detector.py` - FrameworkDetector
- `seo_agent/repository/page_discovery.py` - PageDiscovery
- `seo_agent/repository/metadata_parser.py` - MetadataParser

**Test Cases:**

#### test_scanner.py
```python
class TestRepositoryScanner:
    - test_scan_returns_repository_info
    - test_scan_respects_ignore_patterns
    - test_detect_sitemap_finds_sitemap
    - test_detect_robots_finds_robots
    - test_detect_public_assets_finds_assets
    - test_seo_indicator_files_detection
    - test_empty_repository_handling
    - test_large_repository_handling

class TestScannerConstants:
    - test_default_ignore_dirs_defined
    - test_seo_indicator_files_listed
    - test_public_dir_patterns_defined
```

#### test_framework_detector.py
```python
class TestFrameworkDetector:
    - test_detect_nextjs_returns_nextjs
    - test_detect_react_returns_react
    - test_detect_vue_returns_vue
    - test_detect_angular_returns_angular
    - test_detect_astro_returns_astro
    - test_detect_svelte_returns_svelte
    - test_detect_remix_returns_remix
    - test_detect_gatsby_returns_gatsby
    - test_detect_laravel_returns_laravel
    - test_detect_django_returns_django
    - test_detect_flask_returns_flask
    - test_detect_express_returns_express
    - test_detect_unknown_returns_none
    - test_routing_strategy_detection
    - test_framework_metadata_extraction

class TestRoutingPatterns:
    - test_nextjs_pages_router_detected
    - test_nextjs_app_router_detected
    - test_react_router_detected
    - test_vue_router_detected
```

#### test_page_discovery.py
```python
class TestPageDiscovery:
    - test_discover_finds_html_files
    - test_discover_finds_jsx_tsx_files
    - test_discover_finds_vue_files
    - test_discover_respects_framework
    - test_discover_filters_by_route_patterns
    - test_discover_handles_nested_directories
```

#### test_metadata_parser.py
```python
class TestMetadataParser:
    - test_parse_extracts_title
    - test_parse_extracts_description
    - test_parse_extracts_canonical
    - test_parse_extracts_og_tags
    - test_parse_extracts_structured_data
    - test_parse_handles_missing_tags
    - test_parse_handles_invalid_html
```

**Dependencies to Mock:** None (use temporary directories with test files)

---

### 3.6 Review Package (Priority: HIGH)

**Files to Test:**
- `seo_agent/review/validator.py` - MetadataValidator
- `seo_agent/review/diff_analyzer.py` - FileClassifier
- `seo_agent/review/feedback.py` - FeedbackGenerator

**Test Cases:**

#### test_validator.py
```python
class TestValidationSeverity:
    - test_all_severity_levels_defined
    - test_severity_ordering

class TestValidationCategory:
    - test_all_categories_defined
    - test_category_values

class TestValidationIssue:
    - test_issue_creation
    - test_to_dict_returns_correct_structure
    - test_issue_id_generation

class TestValidationResult:
    - test_is_valid_false_when_issues
    - test_critical_issues_filter
    - test_error_issues_filter
    - test_warning_issues_filter
    - test_info_issues_filter
    - test_has_blocking_issues_detection
    - test_to_dict_includes_counts

class TestMetadataValidator:
    - test_validate_title_length
    - test_validate_title_detects_keyword_stuffing
    - test_validate_description_length
    - test_validate_canonical_url
    - test_validate_og_tags
    - test_validate_structured_data
    - test_validate_internal_links
```

#### test_diff_analyzer.py
```python
class TestChangeType:
    - test_all_change_types_defined

class TestChangeCategory:
    - test_all_categories_defined

class TestChangeSeverity:
    - test_all_severities_defined

class TestFileChange:
    - test_change_creation
    - test_to_dict_structure
    - test_is_within_seo_directory_detection

class TestDiffAnalysis:
    - test_all_changes_combines_correctly
    - test_has_seo_pages_detection
    - test_has_blocking_changes_detection
    - test_to_dict_includes_all_fields

class TestFileClassifier:
    - test_classify_seo_page
    - test_classify_sitemap
    - test_classify_robots
    - test_classify_dependency_file
    - test_classify_build_config
    - test_classify_source_code
    - test_classify_documentation
    - test_classify_unknown
```

**Dependencies to Mock:** None (use sample HTML/diff content)

---

### 3.7 SEO Package (Priority: MEDIUM)

**Files to Test:**
- `seo_agent/seo/metadata_optimizer.py` - MetadataOptimizer
- `seo_agent/seo/robots.py` - RobotsTxtGenerator
- `seo_agent/seo/sitemap.py` - SitemapGenerator
- `seo_agent/seo/seo_page_generator.py` - SEOPageGenerator

**Test Cases:**

#### test_metadata_optimizer.py
```python
class TestMetadataOptimizer:
    - test_optimize_page_updates_title
    - test_optimize_page_updates_description
    - test_optimize_page_updates_canonical
    - test_optimize_page_updates_og_tags
    - test_optimize_page_updates_twitter_tags
    - test_optimize_page_updates_structured_data
    - test_optimize_page_preserves_existing_content
    - test_optimize_page_handles_missing_file
    - test_optimize_page_rejects_unsupported_type
    - test_optimize_pages_batch_processing
    - test_optimize_pages_accumulates_errors

class TestMetadataOptimizerHelpers:
    - test_update_title_tag_inserts_new
    - test_update_title_tag_replaces_existing
    - test_update_meta_tag_inserts_new
    - test_update_meta_tag_replaces_existing
    - test_update_canonical_handles_missing
    - test_update_og_tags_complete
    - test_update_twitter_tags_complete
    - test_update_structured_data_json_ld
```

#### test_robots.py
```python
class TestRobotsTxtGenerator:
    - test_generate_basic_robots_txt
    - test_generate_with_sitemap_url
    - test_generate_with_disallow_rules
    - test_generate_with_allow_rules
    - test_generate_with_user_agent_specific
    - test_generate_with_crawl_delay
```

#### test_sitemap.py
```python
class TestSitemapGenerator:
    - test_generate_sitemap_xml
    - test_generate_with_all_pages
    - test_generate_with_priority
    - test_generate_with_change_frequency
    - test_generate_with_lastmod
    - test_generate_handles_nested_urls
```

#### test_seo_page_generator.py
```python
class TestSEOPageGenerator:
    - test_generate_basic_page
    - test_generate_with_metadata
    - test_generate_with_structured_data
    - test_generate_with_og_tags
    - test_generate_with_twitter_cards
    - test_generate_preserves_template
```

**Dependencies to Mock:** None (use temporary HTML files)

---

### 3.8 Agents Package (Priority: HIGH)

**Files to Test:**
- `seo_agent/agents/planning/planner.py` - Planner
- `seo_agent/agents/planning/keyword_selector.py` - KeywordSelector
- `seo_agent/agents/planning/repository_analyzer.py` - RepositoryAnalyzer
- `seo_agent/agents/planning/task_planner.py` - TaskPlanner
- `seo_agent/agents/execution/executor.py` - ExecutionAgent

**Test Cases:**

#### test_planner.py
```python
class TestPlanningInput:
    - test_input_creation
    - test_input_immutable

class TestPlanningResult:
    - test_result_contains_all_fields
    - test_planned_at_timestamp

class TestPlanner:
    - test_plan_executes_three_steps
    - test_plan_returns_execution_plan
    - test_plan_simple_returns_only_plan
    - test_from_container_creates_instance
    - test_planner_does_not_modify_files
    - test_planner_does_not_call_llm
```

#### test_keyword_selector.py
```python
class TestKeywordSelectionResult:
    - test_result_structure
    - test_total_selected_count

class TestKeywordSelector:
    - test_select_returns_result
    - test_select_prioritizes_by_relevance
    - test_select_respects_max_keywords
    - test_select_considers_existing_pages
    - test_select_calculates_opportunity_score
```

#### test_repository_analyzer.py
```python
class TestRepositoryAnalysis:
    - test_analysis_structure
    - test_opportunities_list

class TestRepositoryAnalyzer:
    - test_analyze_returns_analysis
    - test_analyze_identifies_opportunities
    - test_analyze_considers_framework
```

#### test_task_planner.py
```python
class TestTaskPlanner:
    - test_plan_generates_execution_plan
    - test_plan_creates_phases
    - test_plan_orders_tasks_by_dependency
    - test_plan_assigns_priorities
    - test_plan_sets_task_types
```

#### test_executor.py
```python
class TestExecutionConfig:
    - test_default_config_values
    - test_custom_config_values

class TestExecutionSummary:
    - test_summary_accumulates_results
    - test_summary_calculates_durations

class TestExecutionAgent:
    - test_execute_requires_adapter
    - test_execute_requires_plan
    - test_execute_empty_plan_returns_failure
    - test_execute_runs_all_phases
    - test_execute_stops_on_critical_failure
    - test_execute_continues_on_warning
    - test_execute_aggregates_results
    - test_execute_returns_execution_result
```

**Dependencies to Mock:**
- OpenCodeAdapter
- RepositoryAnalyzer
- KeywordSelector
- TaskPlanner

---

### 3.9 Git Package (Priority: MEDIUM)

**Files to Test:**
- `seo_agent/git/client.py` - GitClient
- `seo_agent/git/operations.py` - GitOperations

**Test Cases:**

#### test_client.py
```python
class TestRepositoryStatus:
    - test_status_properties

class TestGitClient:
    - test_open_repository_valid_path
    - test_open_repository_invalid_path
    - test_open_repository_bare_repo
    - test_validate_repository_returns_result
    - test_get_current_branch
    - test_get_current_branch_detached_head
    - test_branch_exists_true
    - test_branch_exists_false
    - test_get_repository_status_clean
    - test_get_repository_status_dirty
    - test_get_repository_status_staged_files
    - test_get_repository_status_modified_files
    - test_get_repository_status_untracked_files
```

#### test_operations.py
```python
class TestGitOperations:
    - test_create_branch
    - test_commit_changes
    - test_push_changes
    - test_pull_changes
    - test_create_tag
    - test_get_diff
```

**Dependencies to Mock:** git (use unittest.mock or pytest-mock)

---

### 3.10 Integrations Package (Priority: MEDIUM)

**Files to Test:**
- `seo_agent/integrations/opencode/client.py` - OpenCodeClient
- `seo_agent/integrations/opencode/adapter.py` - OpenCodeAdapter
- `seo_agent/integrations/opencode/models.py` - OpenCode models

**Test Cases:**

#### test_opencode_client.py
```python
class TestOpenCodeClient:
    - test_initialization_requires_base_url
    - test_initialization_requires_api_key
    - test_build_headers_includes_auth
    - test_serialize_request_json_format
    - test_deserialize_response_parses_correctly
    - test_execute_sends_correct_payload
    - test_execute_handles_http_error
    - test_execute_handles_timeout
    - test_execute_handles_invalid_json

class TestOpenCodeClientError:
    - test_error_creation
    - test_error_inheritance
```

#### test_opencode_adapter.py
```python
class TestFileEditResult:
    - test_result_structure

class TestPageGenerationResult:
    - test_result_structure

class TestOpenCodeExecutionResult:
    - test_result_structure
    - test_file_edits_tuple
    - test_page_generations_tuple

class TestOpenCodeAdapter:
    - test_create_file_edit_request
    - test_create_file_write_request
    - test_create_batch_request
    - test_execute_file_edits
    - test_execute_page_generations
    - test_convert_response_to_result
```

#### test_models.py
```python
class TestOpenCodeModels:
    - test_open_code_request_creation
    - test_open_code_response_parsing
    - test_open_code_action_request_creation
    - test_open_code_status_values
    - test_open_code_model_values
    - test_open_code_action_values
```

**Dependencies to Mock:** HTTP client (use unittest.mock)

---

## 4. Integration Test Plan

### 4.1 Workflow Integration Tests

**File:** `tests/integration/test_workflow/test_stage_integration.py`

```python
class TestWorkflowStageIntegration:
    - test_scanning_to_framework_detection_flow
    - test_framework_detection_to_page_discovery_flow
    - test_page_discovery_to_metadata_extraction_flow
    - test_planning_receives_correct_context
    - test_execution_receives_correct_plan
    - test_review_validates_execution_result
    - test_seo_update_applies_changes
    - test_git_commits_changes
    - test_full_workflow_completes_successfully
    - test_workflow_handles_stage_failure
```

---

## 5. E2E Test Plan

### 5.1 Pipeline E2E Tests

**File:** `tests/e2e/test_pipeline/test_end_to_end.py`

```python
class TestEndToEndPipeline:
    - test_full_pipeline_with_valid_repository
    - test_pipeline_with_nextjs_project
    - test_pipeline_with_react_project
    - test_pipeline_with_static_site
    - test_pipeline_handles_empty_repository
    - test_pipeline_handles_invalid_input
    - test_pipeline_timeout_handling
    - test_pipeline_retry_on_transient_failure
```

---

## 6. Test Implementation Priorities

### Phase 1: Core Infrastructure (Week 1)
1. **test_result.py** - Foundation for all async operations
2. **test_container.py** - Dependency injection testing
3. **test_exceptions.py** - Exception handling validation

### Phase 2: Workflow Components (Week 2)
4. **test_stages.py** - Stage enum and transitions
5. **test_context.py** - Workflow context management
6. **test_orchestrator.py** - Orchestration logic

### Phase 3: Data Models (Week 2-3)
7. **test_api_models.py** - API request/response validation
8. **test_task_models.py** - Task and phase models
9. **test_schemas.py** - Pydantic validation

### Phase 4: Repository Analysis (Week 3)
10. **test_scanner.py** - Repository scanning
11. **test_framework_detector.py** - Framework detection
12. **test_page_discovery.py** - Page discovery

### Phase 5: Review & SEO (Week 3-4)
13. **test_validator.py** - Metadata validation
14. **test_diff_analyzer.py** - Diff analysis
15. **test_metadata_optimizer.py** - Metadata optimization

### Phase 6: Agents (Week 4-5)
16. **test_planner.py** - Planning orchestration
17. **test_executor.py** - Task execution
18. **test_keyword_selector.py** - Keyword selection

### Phase 7: API & Integration (Week 5)
19. **test_routes.py** - API endpoints
20. **test_opencode_adapter.py** - OpenCode integration

---

## 7. Test Coverage Targets

| Package | Current | Target | Priority Files |
|---------|---------|--------|----------------|
| Core | 0% | 95% | result.py, container.py |
| Models | 0% | 90% | api.py, task.py |
| Workflow | 0% | 95% | context.py, orchestrator.py |
| API | 0% | 85% | routes.py, schemas.py |
| Repository | 0% | 90% | scanner.py, framework_detector.py |
| Review | 0% | 90% | validator.py, diff_analyzer.py |
| SEO | 0% | 85% | metadata_optimizer.py |
| Agents | 0% | 85% | planner.py, executor.py |
| Git | 0% | 80% | client.py |
| Integrations | 0% | 80% | adapter.py, client.py |

---

## 8. Testing Best Practices

### 8.1 Test Structure
```python
# Each test file should follow this structure:
"""
Module docstring describing what is tested.

Tests use pytest fixtures for setup/teardown.
Mocks are used for external dependencies.
"""

import pytest
from seo_agent.core.result import Success, Failure

class TestClassName:
    """Tests for a specific class or function group."""
    
    def test_method_name_scenario_expected_result(self):
        """One-line docstring for test."""
        # Arrange
        ...
        # Act
        ...
        # Assert
        ...
```

### 8.2 Fixtures
```python
@pytest.fixture
def sample_repository(tmp_path):
    """Create a sample repository for testing."""
    # Create test files
    ...
    return tmp_path

@pytest.fixture
def mock_container():
    """Create a mock container."""
    container = Container()
    container.register_singleton(Config, mock_config)
    return container
```

### 8.3 Mocking Strategy
- Mock external HTTP calls (OpenCode API)
- Mock file system operations where appropriate
- Use `tmp_path` fixture for file operations
- Mock Git operations with `unittest.mock`

---

## 9. CI/CD Integration

### 9.1 GitHub Actions Workflow
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov pytest-mock
      - run: pytest --cov=seo_agent --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### 9.2 Coverage Requirements
- Minimum 70% line coverage for all packages
- Minimum 80% line coverage for Core and Workflow packages
- Coverage reports generated on every PR

---

## 10. Maintenance

### 10.1 Test Review Checklist
- [ ] All public methods have tests
- [ ] Edge cases covered
- [ ] Error paths tested
- [ ] Fixtures properly scoped
- [ ] No hardcoded values
- [ ] Clear test names
- [ ] Docstrings for complex tests

### 10.2 Test Update Triggers
- New feature implementation
- Bug fix (add regression test)
- Refactoring (update affected tests)
- API contract change

---

## 11. Appendix

### A. Test Data Fixtures Location
```
tests/fixtures/
├── html/
│   ├── sample_page.html
│   ├── page_with_metadata.html
│   └── page_without_metadata.html
├── json/
│   ├── sample_seo_payload.json
│   └── sample_response.json
└── repositories/
    ├── nextjs_app/
    ├── react_app/
    └── static_site/
```

### B. Mock Data Constants
```python
# tests/constants.py
SAMPLE_KEYWORDS = ["seo", "optimization", "ranking"]
SAMPLE_METADATA = Metadata(
    title="Test Page",
    description="Test description",
    canonical_url="https://example.com/page",
    keywords=SAMPLE_KEYWORDS,
)
SAMPLE_REPOSITORY_INFO = RepositoryInfo(...)
```

### C. pytest Configuration
```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
```