# Solutions Documentation

This directory contains structured documentation of problems solved during development. Each solution captures:

- **Problem symptom**: Observable behavior and error messages
- **Investigation steps**: What was tried and why
- **Root cause**: Technical explanation
- **Working solution**: Step-by-step fix with code examples
- **Prevention strategies**: How to avoid in the future
- **Cross-references**: Links to related issues and docs

## Philosophy: Compounding Knowledge

The first time you solve a problem takes research (30+ min). Document it here (5 min), and next time it takes just 2 minutes to look up.

**Knowledge compounds. Each solution makes future work easier.**

## Categories

### code-organization/
Refactoring, module architecture, separation of concerns

### build-errors/
Compilation issues, dependency conflicts, tooling problems

### test-failures/
Failing tests, assertion errors, test infrastructure

### runtime-errors/
Exceptions, crashes, unexpected behavior at runtime

### performance-issues/
Slow queries, memory leaks, optimization problems

### database-issues/
Migrations, schema problems, query issues

### security-issues/
Vulnerabilities, authentication, authorization

### ui-bugs/
Frontend issues, rendering problems, user interaction

### integration-issues/
API integration, third-party service problems

### logic-errors/
Business logic bugs, incorrect calculations, edge cases

## Document Format

Each solution uses YAML frontmatter for searchability:

```yaml
---
title: "Descriptive Problem Title"
date: YYYY-MM-DD
category: code-organization
severity: low|medium|high
tags:
  - relevant
  - tags
components:
  - affected_component
status: resolved|known-issue|workaround
related_issues: []
---
```

## Quick Search

```bash
# Find all refactoring solutions
grep -r "category: code-organization" docs/solutions/

# Find high-severity issues
grep -r "severity: high" docs/solutions/

# Search by tag
grep -r "python-architecture" docs/solutions/
```

## Contributing

When you solve a non-trivial problem:
1. Use `/compound` command to auto-generate documentation
2. Or manually create a file in the appropriate category
3. Include code examples and exact error messages
4. Add prevention strategies for future reference
