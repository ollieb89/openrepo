---
name: review
description: L3 Work Reviewer for git diffs on staging branches with merge or reject decisions.
metadata:
  openclaw:
    emoji: "📝"
    category: "orchestration-core"
---

# SKILL: L3 Work Reviewer

## Overview
Reviews L3 git diffs on staging branches and makes merge or reject decisions to main. Provides systematic code review workflow for maintaining code quality and architectural consistency.

## Tools
- `review_diff`: Review changes on a staging branch and recommend action
- `merge_approved`: Merge approved changes to main branch
- `reject_changes`: Reject changes with feedback and close staging branch
- `review_queue`: List pending reviews in the queue

## Usage
```bash
# Review a staging branch
openclaw exec pumplai_pm "review_diff --task-id task-001 --staging_branch feature/new-api --action review"

# Merge approved changes
openclaw exec pumplai_pm "merge_approved --task-id task-001 --staging_branch feature/new-api"

# Reject with feedback
openclaw exec pumplai_pm "reject_changes --task-id task-001 --staging_branch feature/new-api --reason 'Architecture violation'"

# Check review queue
openclaw exec pumplai_pm "review_queue"
```

## Review Criteria
- **Code Quality**: Adherence to coding standards and best practices
- **Architecture**: Consistency with existing system architecture
- **Security**: No security vulnerabilities or anti-patterns
- **Performance**: No performance regressions or inefficiencies
- **Testing**: Adequate test coverage and test quality
- **Documentation**: Clear documentation and comments where needed

## Workflow
1. L3 specialist completes work and pushes to staging branch
2. L2 project manager initiates review via this skill
3. Skill analyzes git diff and provides recommendations
4. Based on analysis, skill merges or rejects changes
5. Status is updated in project tracking system

## Implementation
Uses the existing `review.py` module which provides:
- Git diff analysis and parsing
- Code quality assessment
- Automated merge/reject decisions
- Integration with project state tracking

## Dependencies
- Git Python library
- openclaw state engine
- Project configuration system
- Git repository with staging branch workflow
