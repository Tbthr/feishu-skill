---
description: "Analyze Feishu PRD documents using the feishu-analyst skill with auto-loaded PRD checklist framework"
---

You are analyzing a Product Requirements Document (PRD) from Feishu. Follow these steps:

1. Use the feishu-analyst skill to fetch and process the document
2. Load the PRD checklist from `skills/feishu-analyst/references/prd_checklist.md`
3. Apply the systematic analysis framework across 4 dimensions:
   - Ambiguity Check (vague terms, metrics, timelines)
   - Logic Consistency (contradictions, edge cases, preconditions)
   - Data Integrity (type definitions, constraints, required fields)
   - Completeness (user stories, acceptance criteria, success metrics)
4. Generate a structured review following the output template in the checklist

The user will provide a Feishu document URL (either `/docx/` or `/wiki/` format).
