---
title: "Quality Refinement Autoloop"
summary: "Run a self-refinement loop when a Blender result is subpar, user expectations are not met, validation fails, or repeated issues reveal missing guide depth. The loop diagnoses the gap, decides whether to repair the artifact or acquire/refine a generic guide, sanitizes lessons for reusable publication, updates docs/versioning, validates, and prepares stage/commit/push when explicitly requested."
applies_to: "Blender 4.5+"
---

# Quality Refinement Autoloop

> Internal knowledge for **blender-skill**. Read in place; this is not an installable guide.

## MCP backend

Use when: Subpar output, user rejects quality, repeated Blender failure, RALPH loop, guide gap diagnosis, autonomous guide refinement, sanitized guide contribution, release prep, docs/version bump, staged commit and push workflow.

Before the first Blender call, read [../text-to-blender/references/mcp-backends.md](../text-to-blender/references/mcp-backends.md). Prefer official MCP for shared capabilities; preserve the selected backend for the whole task. Tool names in recipes are client/legacy examples: map them through that reference and its agent-host guide.
# Quality Refinement Autoloop

Use this when the user says the result is wrong, ugly, not aligned, not textured, not animated, not exportable, or otherwise below expectation. The goal is not to keep tweaking blindly. The goal is to convert failure into a reusable, generic guide improvement before trying again.

## Autoloop phases

### 0. Freeze and preserve

- Stop making product changes immediately.
- Preserve the last accepted baseline and the failed artifact.
- Name the failed branch/version honestly; do not overwrite accepted outputs.

### 1. Evidence capture

Collect the smallest evidence set that proves the failure:

- user feedback quote or summary;
- source/reference files used;
- current output path/version;
- relevant render/contact sheet/overlay/audit report;
- scene/material/object inventory if the failure is inside Blender.

### 2. Diagnose failure dimension

Classify the primary gap:

- geometry / silhouette / landmarks;
- multiview/depth consistency;
- UV / atlas / texture fit;
- closed surface coverage (front/back/side);
- look/material/lighting calibration;
- animation/motion/export truth;
- orchestration/handoff between guides;
- missing validator or missing deterministic helper script.

### 3. Guide-gap decision

Ask: does the current guide stack already contain a generic method for this failure?

- If yes: run the existing guide and repair the artifact.
- If no: add/refine a generic guide first, then repair.
- If repeated failures come from guide interplay, update the harmonizer/handoff rule, not just a leaf guide.

### 4. Sanitize the lesson

Before writing a guide change:

- remove project/client/asset names;
- remove secrets, raw logs, private paths, personal data, and copyrighted source content;
- keep only reusable method, gates, scripts, and failure patterns;
- describe inputs/outputs generically;
- prefer deterministic scripts for fragile audits.

### 5. Patch guide stack

Apply the smallest publishable change:

- one concise guide or one concise section in an existing guide;
- optional helper script if the validation is repeatable;
- harmonizer update if ordering/handoff changed;
- manifest entry/version update.

### 6. Validate guide change

Required checks:

- scripts compile;
- manifest paths exist;
- guide graph audit passes with harmonizer present;
- sanitizer scan passes for project-specific terms;
- if applicable, run the new helper against the failed artifact and save a report.

### 7. Repair product only after guide gate

Rebuild or repair from the correct baseline using the improved guide. Do not reuse rejected outputs unless explicitly marked as source evidence.

### 8. Release prep when requested

Only when the user asks to publish/commit/push:

1. fetch latest remote and confirm local branch is up to date;
2. resolve/harmonize conflicts before staging;
3. bump version using semver appropriate to scope;
4. update README / plugin README / CHANGELOG / VERSIONING when relevant;
5. run sanitizer and compile/audit checks;
6. stage, commit, and push using the configured remote.

## Hard rules

- Do not bake task-specific examples into public guides.
- Do not call overlay curves/planes “texture coverage” unless the real mesh surface also passes coverage gates.
- Do not tune lighting/materials to hide geometry or UV failures.
- Do not claim export support if the effect exists only in Blender Python or a render sequence.
- Do not push without an explicit user request and an up-to-date remote check.

## Recommended artifacts

Save these near the project output when running the loop:

- `RALPH_OR_QUALITY_LOOP_REPORT.md`
- `failure_evidence/` or references to existing renders/reports
- `skill_gap_decision.json`
- `sanitization_report.json`
- `validation_report.json`

## Scripts

- `scripts/ralph_autoloop_plan.py` creates a generic failure-classification and loop plan from feedback/artifact hints.
- `scripts/sanitize_guide_contributions.py` scans guide files for project-specific or private terms before publication.
- `scripts/release_readiness_check.py` performs lightweight manifest/docs/version/path checks before commit/push.
