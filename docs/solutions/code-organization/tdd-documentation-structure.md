---
title: "TDD Documentation Structure"
category: code-organization
tags: [tdd, documentation, methodology, developer-experience]
date: 2026-01-17
symptom: "Feature-specific TDD walkthrough (TDD_WORKFLOW.md) in project root felt misplaced"
status: resolved
---

# TDD Documentation Structure

## Problem

After implementing Feature 0003 using TDD, created `TDD_WORKFLOW.md` in project root documenting the entire red-green-refactor cycle with feature-specific examples. Questions arose:

1. Should feature-specific TDD walkthroughs exist?
2. If yes, should they be in root or elsewhere?
3. How to make TDD knowledge reusable for future features?

**Symptom:**
- 400-line feature-specific TDD walkthrough in root
- Redundant with implementation summary
- Not reusable for future features
- Unclear where methodology docs belong

## Investigation

**Considered Options:**

1. **Keep in root** - Easy to find, but clutters root with feature-specific docs
2. **Move to `/docs/features/0003_TDD_WORKFLOW.md`** - Organized with feature docs, but reinforces feature-specific approach
3. **Generalize into `/docs/TDD_GUIDE.md`** - Reusable methodology, loses feature-specific examples
4. **Merge into implementation summary** - Consolidates, but loses standalone reference

**Key Questions:**
- Will this help code future features better?
- Is feature-specific TDD documentation reusable?
- What's the right balance between examples and methodology?

## Root Cause

**Documentation served two purposes:**
1. **Historical record** - "How we built Feature 0003"
2. **Methodology guide** - "How to use TDD for any feature"

These are different concerns and should be separated.

**The 400-line walkthrough was:**
- ✅ Good: Shows TDD in practice with real examples
- ❌ Bad: Too specific to Feature 0003 to be reusable
- ❌ Bad: Redundant with `0003_IMPLEMENTATION_SUMMARY.md`

## Solution

**Created generalized TDD methodology guide:**

```
docs/
├── TDD_GUIDE.md           # ← Reusable methodology (NEW)
└── features/
    └── 0003_IMPLEMENTATION_SUMMARY.md  # ← Has TDD metrics
```

**TDD_GUIDE.md contains:**
- Red-Green-Refactor cycle
- Quick recipe (code example)
- Implementation pattern
- Best practices (test naming, mocking, etc.)
- Common pitfalls
- Success criteria
- References Feature 0003 as real-world example

**Deleted:**
- Root-level `TDD_WORKFLOW.md` (feature-specific walkthrough)

## Implementation

```bash
# 1. Create generalized guide
cat > docs/TDD_GUIDE.md << 'EOF'
# TDD Methodology Guide
# [Reusable methodology content]
EOF

# 2. Remove feature-specific walkthrough
rm TDD_WORKFLOW.md
```

**Key Principle:**
> Feature implementations should reference methodology docs, not duplicate them.

## Benefits

✅ **Reusability** - Can follow TDD_GUIDE.md for any future feature  
✅ **Discoverability** - Single source of truth in `/docs`  
✅ **Maintainability** - Update methodology once, applies everywhere  
✅ **Clarity** - Feature docs focus on "what was built", methodology docs on "how to build"  

## Prevention

**Guidelines for future documentation:**

1. **Methodology → `/docs/`** (e.g., TDD_GUIDE.md, TESTING_STRATEGY.md)
2. **Feature-specific → `/docs/features/`** (e.g., 0003_PLAN.md, 0003_IMPLEMENTATION_SUMMARY.md)
3. **Cross-reference** - Implementation summaries should reference methodology docs
4. **DRY principle** - Don't duplicate methodology in feature docs

**Test:**
- Does this help build the NEXT feature? → Methodology doc
- Does this explain THIS feature? → Feature doc

## Related

- Implementation: `/docs/features/0003_IMPLEMENTATION_SUMMARY.md`
- Methodology: `/docs/TDD_GUIDE.md`
- Pattern: `/docs/solutions/README.md` (this follows same principle)

## Takeaway

**Documentation organization mirrors code organization:**
- Shared utilities → `/lib` or `/docs`
- Feature-specific → `/features` or `/docs/features`

Keep methodology documentation DRY and reusable.
