---
name: english-grammar-fix
description: Auto-correct minor English grammar errors in AI responses for non-native speakers
license: MIT
compatibility: claude-code,opencode,gemini
metadata:
  triggers:
    - english-grammar-fix
    - fix grammar
    - correct english
  when_to_use: When the user wants to auto-correct minor English grammar errors in AI-generated text.
  audience: walter-worker
---

# English Grammar Fix

Automatically corrects minor English grammar and phrasing errors in AI-written content
(comments, commit messages, PR descriptions, docs).

## When to Use

- When reviewing AI-generated text before publishing
- When the user requests grammar correction on a specific piece of text
- For commit messages, PR descriptions, and documentation

## When NOT to Use

- For technical terminology or variable/function names
- For code comments that are intentionally terse
- For language that is correct but informal
- When the user prefers to review manually

## Process

### 1. Scan
Read the target text and identify grammar, style, and phrasing issues.

### 2. Classify
Categorize each issue: grammar (auto-fix silently), style (show in *italics* for review).

### 3. Apply
Apply corrections inline — the corrected version replaces the original without comment for minor fixes.

### 4. Review
Style changes shown with original for comparison. User confirms or rejects.

## What It Fixes

### Grammar
- Subject-verb agreement: "The functions are..." not "The functions is..."
- Article usage: "a function" vs "an error"
- Tense consistency within a sentence
- Plural/singular consistency

### Common Technical Writing Errors
- "it's" vs "its"
- "affect" vs "effect"
- "which" vs "that" in relative clauses
- Missing Oxford comma (standardize to include)

### Commit Message Style
- Ensure imperative mood: "Add feature" not "Added feature"
- Conventional commits format: `type(scope): description`
- Max 72 chars for subject line

## What It Does NOT Change
- Technical terminology
- Variable/function names
- Code comments that are intentionally terse
- Language that is correct but informal
