# Product Requirement Analysis Rules

## Purpose
Systematic framework for analyzing Feishu documents containing product requirements.

## Analysis Dimensions

### 1. Ambiguity Check
Identify vague terms that need clarification:
- "fast", "slow", "performant" → What are specific metrics?
- "easy to use" → What is the target user skill level?
- "later", "phase 2" → When exactly? What triggers it?
- "suitable format" → What formats specifically?

**Action**: Flag these and ask "What is the specific metric/timeline?"

### 2. Logic Consistency
Check for contradictions within the document:
- User Flow contradicts Feature List
- Edge cases not handled (offline, server error, empty state)
- Preconditions not defined (what must exist before this works?)
- Success/failure states unclear

**Action**: Point out contradictions and request clarification.

### 3. Data Integrity
If document defines data structures:
- Are field Types specified?
- Are Max Length constraints defined?
- Are Default Values specified?
- Are Required/Optional fields marked?

**Action**: Flag missing data definitions.

### 4. Completeness
- User stories present with acceptance criteria?
- Edge cases identified?
- Non-functional requirements (performance, security) specified?
- Success metrics defined?

## Output Template

# PRD Analysis: [Document Title]

## Executive Summary
[One-paragraph overview of PRD quality and readiness]

## Critical Findings

### Ambiguities Requiring Clarification
1. [Term] - [Why it's ambiguous] - [Suggested clarification]
2. ...

### Logical Contradictions
1. [Contradiction] - [Impact] - [Resolution needed]
2. ...

### Data Structure Issues
1. [Missing definition] - [Why it matters]
2. ...

### Completeness Gaps
1. [Missing element] - [Risk level]
2. ...

## Questions for Product Team
1. [Specific clarifying question]
2. ...

## Recommendations
1. [Actionable improvement]
2. ...

## Overall Assessment
[Ready / Needs Revision / Major Gaps]
