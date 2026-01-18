---
title: "Compound Knowledge Integration - Command Improvements"
date: 2026-01-18
category: documentation
status: implemented
tags:
  - compound-engineering
  - workflow-optimization
  - knowledge-management
---

# Compound Knowledge Integration - Command Improvements

## Summary

Enhanced all workflow commands to leverage the compound knowledge base (`docs/solutions/`) inspired by [Every's compound engineering plugin](https://github.com/EveryInc/compound-engineering-plugin). Each command now proactively uses documented solutions to prevent re-solving problems.

## Philosophy

**Knowledge compounds.** The first time you solve a problem takes 30 minutes. Document it (5 min), and next time takes 2 minutes. Each solution makes future work easier.

## Commands Enhanced

### 1. `/plan-feature` ✨ NEW BEHAVIOR

**Before:** Created technical plans based only on current codebase research

**Now:** 
- Searches `docs/solutions/.index` before planning
- Includes "Known Considerations" section citing past solutions
- References prevention strategies from documented issues
- Links to relevant patterns and anti-patterns

**Impact:** Plans now incorporate team's historical knowledge, avoiding known pitfalls

---

### 2. `/code-review` ✨ NEW BEHAVIOR

**Before:** Reviewed code against plan and general best practices

**Now:**
- Cross-references against known issues in `.index`
- Checks if code introduces patterns similar to documented problems
- Validates prevention strategies from related solutions are applied
- Includes "Compound Knowledge Check" section
- Flags similar issues: `⚠️ Similar to: docs/solutions/[file].md`
- Suggests documenting new issues: `💡 Consider /compound for: [description]`

**Impact:** Catches problems team has faced before, prevents regression

---

### 3. `/mentor` ✨ NEW BEHAVIOR

**Before:** Explained concepts with generic examples

**Now:**
- References real examples from `docs/solutions/`
- Cites actual bugs/fixes that illustrate best practices
- Uses tag index to find related patterns
- Grounds explanations in team's actual experience

**Impact:** Learning is context-specific to your codebase, not generic advice

---

### 4. `/write-docs` ✨ NEW BEHAVIOR

**Before:** Documented features based on implementation

**Now:**
- Links to related `docs/solutions/` entries for context
- Adds "Known Issues" section when relevant
- References prevention strategies from past fixes
- Includes "Common Pitfalls" citing real problems

**Impact:** Documentation becomes actionable, connected to real experience

---

### 5. `/search-solutions` 🆕 NEW COMMAND

**Purpose:** Quickly search compound knowledge base

**Search modes:**
- By keyword: `/search-solutions context managers`
- By tag: `/search-solutions tag:pytest`
- By category: `/search-solutions category:test-failures`
- By component: `/search-solutions component:attestation`
- By severity: `/search-solutions severity:high`
- Browse all: `/search-solutions`

**Output:** Shows matching solutions with preview, links, tags, and severity

**Integration:** Used automatically by other commands

---

### 6. `/pre-implement` 🆕 NEW COMMAND

**Purpose:** Pre-implementation check using compound knowledge

**What it does:**
1. **Component Risk Assessment** - Searches for known issues in target components
2. **Pattern Recognition** - Finds similar past implementations
3. **Prevention Strategy Review** - Extracts prevention strategies from solutions
4. **Dependency Analysis** - Checks if related components have issues

**Output:** Comprehensive pre-flight check with recommendations

**When to use:**
- Before planning
- Before implementing
- Before refactoring
- When joining codebase

**Impact:** Prevents re-solving problems, surfaces constraints early

---

## The Compound Loop

```
Implement → Debug → Fix → /compound → Document
                                ↓
                         Knowledge Base
                                ↓
/pre-implement → /plan-feature → /code-review → /write-docs
        ↓               ↓               ↓              ↓
   Use knowledge   Plan with       Catch known    Link to
   before coding   prevention      patterns       solutions
```

## Files Changed

### Modified
- `.cursor/commands/plan-feature.md` - Added compound knowledge integration
- `.cursor/commands/code-review.md` - Added solution cross-referencing
- `.cursor/commands/mentor.md` - Added real-example grounding
- `.cursor/commands/write-docs.md` - Added solution linking

### Created
- `.cursor/commands/search-solutions.md` - New search command
- `.cursor/commands/pre-implement.md` - New pre-flight check command

## Usage Example

```bash
# 1. Before starting work
/pre-implement authentication
# → Shows known issues, patterns, prevention strategies

# 2. Plan with compound knowledge
/plan-feature "Add OAuth2 authentication"
# → Includes "Known Considerations" from past auth work

# 3. Implement (code here)

# 4. Review against compound knowledge
/code-review
# → Checks if prevention strategies applied
# → Flags if similar to past issues

# 5. Document solution
/compound
# → Adds to knowledge base for future reference

# 6. Document feature
/write-docs
# → Links to related solutions
```

## Benefits

### For Individual Developers
- **Faster implementation** - Don't re-solve problems
- **Better code** - Learn from past mistakes
- **Context preservation** - Knowledge survives context switches

### For Teams
- **Compounding returns** - Each solution makes next one easier
- **Shared learning** - Junior devs access senior insights
- **Pattern recognition** - See recurring issues across codebase

### For Codebase
- **Reduced technical debt** - Prevention strategies applied proactively
- **Better architecture** - Past refactoring lessons inform new code
- **Living documentation** - Docs connected to real problems

## Metrics

Track compound knowledge effectiveness:
- Solutions documented: **2 (current)**
- Solutions referenced in plans: **Track going forward**
- Issues prevented by pre-implementation checks: **Track going forward**
- Time saved on repeated issues: **Track going forward**

## Next Steps

1. ✅ Commands enhanced with compound knowledge integration
2. Document more solutions as they're solved
3. Build more categories (performance, security, etc.)
4. Track metrics on time saved
5. Consider automated solution suggestions during code

## References

- Original inspiration: [Every's Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin/blob/main/plugins/compound-engineering/commands/workflows/compound.md)
- Solutions index: `docs/solutions/.index`
- Solutions README: `docs/solutions/README.md`

---

**Remember:** Each documented solution compounds your team's knowledge. The first time takes research. Document it, and next time takes minutes.
