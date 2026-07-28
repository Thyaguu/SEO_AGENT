# PROJECT_GUIDELINES.md

# SEO AI Agent – Development Guidelines

## Purpose

This document defines the mandatory development standards for the SEO AI Agent project.

Every implementation, code modification, refactoring, or feature addition must follow these guidelines.

If there is any conflict between generated code and this document, **this document always takes precedence.**

The detailed functional behavior of the system is documented in **docs/FRD.md**. This document focuses on implementation standards and architectural consistency.

---

# Project Philosophy

This project is designed around the following principles:

- Modular architecture
- Clear separation of responsibilities
- Framework independence
- Repository safety
- Production-ready code
- Maintainability over cleverness
- Deterministic behavior
- Minimal coupling
- Maximum extensibility

Every implementation should prioritize readability and maintainability over unnecessary abstraction.

---

# Architecture

The project follows a strict two-agent architecture.

```
                 FastAPI
                    │
                    ▼
     SEO Planning Agent (Orchestrator)
                    │
                    ▼
       OpenCode Execution Agent
                    │
                    ▼
          Repository Modifications
                    │
                    ▼
     SEO Planning Agent (Review Mode)
             │               │
             ▼               ▼
          Approved        Rejected
             │               │
             ▼               ▼
        Git Commit      Retry (Max 3)
```

The Planning Agent is responsible for planning and validation.

The OpenCode Execution Agent is responsible only for repository modifications.

---

# AI Components

Only two AI agents are permitted.

## 1. SEO Planning Agent

Responsibilities

- Repository understanding
- Framework detection
- SEO planning
- Keyword selection
- Execution planning
- Review
- Retry management
- Git approval

The Planning Agent must never modify repository files directly.

---

## 2. OpenCode Execution Agent

Responsibilities

- Repository editing
- Metadata updates
- SEO page generation
- Sitemap updates
- robots.txt updates
- Route generation

The OpenCode Agent must never make planning decisions.

---

# Development Principles

Always:

- Build one module at a time.
- Keep functions small and focused.
- Prefer composition over inheritance.
- Use dependency injection.
- Write reusable services.
- Write testable code.
- Keep modules independent.
- Minimize side effects.

Never:

- Introduce unnecessary abstractions.
- Duplicate logic.
- Hardcode configuration values.
- Mix business logic with API code.
- Perform repository modifications inside the Planning Agent.

---

# Development Order

Development should always follow this order.

## Phase 1

- requirements.txt
- .env.example
- config.py

---

## Phase 2

Project foundation

- Logging
- Dependency Injection
- Folder structure
- Models
- Interfaces

---

## Phase 3

Repository services

- Framework detection
- Repository scanner
- Page discovery
- Metadata parser

---

## Phase 4

FastAPI

- API
- Request models
- Response models
- Validation

---

## Phase 5

SEO Planning Agent

- Planning
- Repository analysis
- Keyword mapping
- Task planning

---

## Phase 6

OpenCode Integration

- Prompt generation
- Repository editing
- File writing

---

## Phase 7

Review Engine

- Validation
- Retry loop
- Approval

---

## Phase 8

Git Integration

- Branch creation
- Commit creation

---

## Phase 9

Pipeline Trigger

- Configurable CI/CD

---

## Phase 10

Testing

- Unit tests
- Integration tests
- End-to-end tests

---

# Repository Rules

Repository modifications must always be safe.

Allowed

- Metadata updates
- SEO pages
- sitemap.xml
- robots.txt

Forbidden

- Business logic changes
- UI redesign
- Dependency changes
- Build configuration changes
- Package modifications

---

# Human Visibility Rule

This is the most important rule in the project.

The AI must never modify content visible to users.

Forbidden:

- Headings
- Paragraphs
- Buttons
- Labels
- Navigation
- Menus
- Pricing
- Product descriptions
- Forms
- Testimonials

Only invisible SEO metadata may be modified.

---

# SEO Page Rules

Generated pages must:

- Exist only under `/seo`
- Follow the detected framework
- Use generated routes
- Include metadata
- Include schema
- Include FAQ
- Include competitor comparison

Maximum pages allowed:

10

If necessary:

Automatically prune the oldest generated SEO pages.

---

# Review Rules

Every repository modification must be reviewed.

Workflow

Planning Agent

↓

OpenCode

↓

Review

PASS

↓

Git Commit

FAIL

↓

Generate Fix Task

↓

OpenCode

Maximum retries:

3

After the third failure:

- Return failure.
- Do not commit.
- Do not trigger the pipeline.

---

# Framework Support

The system should automatically detect and support:

- Static HTML
- React
- Next.js
- Vue
- Nuxt
- Angular
- Astro
- Svelte
- Remix
- Gatsby
- Laravel Blade
- Django
- Flask
- Express

Never hardcode framework logic.

Framework-specific behavior must be encapsulated behind reusable services.

---

# Configuration

Configuration must be loaded exclusively through `pydantic-settings`.

Never read environment variables directly.

Never hardcode:

- API keys
- Paths
- URLs
- Git settings
- Pipeline settings

---

# Logging

Every major operation should be logged.

Minimum logging includes:

- Repository analysis
- Framework detection
- Planning
- Execution
- Validation
- Git
- Pipeline
- Errors

Use structured logging wherever possible.

---

# Error Handling

Never expose internal exceptions.

Always return structured errors.

Errors should include:

- Error type
- Message
- Context
- Suggested resolution (where applicable)

---

# Code Quality

Every module should:

- Have a single responsibility.
- Be independently testable.
- Avoid circular dependencies.
- Use clear naming.
- Avoid deeply nested logic.
- Prefer typed interfaces.
- Follow SOLID principles where practical.

---

# Testing

Every major module should include tests.

Required:

- Unit tests
- Integration tests

Critical workflows should include end-to-end tests.

---

# Documentation

Every public class and function should include concise documentation.

Complex workflows should include architecture comments explaining intent rather than implementation details.

---

# Copilot Instructions

When implementing any feature:

1. Read this document first.
2. Follow the architecture exactly.
3. Do not introduce additional AI agents.
4. Keep business logic out of the API layer.
5. Prefer reusable services over large classes.
6. Build incrementally.
7. Do not modify unrelated modules.
8. Ensure repository safety.
9. Preserve user-visible content.
10. Ask for clarification if a requested change conflicts with these guidelines.

---

# Source of Truth

Project behavior:

- `docs/FRD.md`

Development standards:

- `PROJECT_GUIDELINES.md`

If conflicts arise, this document governs implementation decisions, while the FRD governs functional requirements.