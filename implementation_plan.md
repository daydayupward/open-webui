# Implementation Plan: Unified Document Category Expansion and Checklist Split

This plan details the implementation of a refined 9-category document taxonomy for the chip backend physical design RAG pipeline, consolidating `Foundry_Doc` under `PDK` and splitting checklists between templates (`Platform_Flow`) and project results (`Project_Doc`).

## User Review Required

> [!IMPORTANT]
> 1. **Foundry Consolidation**: `Foundry_Doc` is mapped and merged directly under `PDK` (representing PDK & Foundry Manuals) to avoid category clutter.
> 2. **Checklist Division**:
>    - Standard templates and sign-off checklists are routed to `Platform_Flow`.
>    - Project-specific checklist run results/logs are routed to `Project_Doc` and require a `project_id`.
> 3. **Legacy Categories**: Legacy categories `"General"` and `"Training"` are retired and mapped to `"Literature"` (representing textbooks, papers, training guides, and general reference).

## Proposed Changes

### Metadata Model & Mappings

#### [MODIFY] [metadata_mapper.py](file:///home/eason/proj/open-webui/chip_agent/src/ingestion/metadata_mapper.py)
- Ensure `VALID_CATEGORIES` contains: `{"PDK", "StdCell", "SRAM", "IP", "EDA", "Platform_Flow", "Project_Doc", "Script", "Literature"}`.
- Update `_normalize_category` to support synonyms and aliases for all 9 categories:
  - `pdk` / `process` / `foundry` / `foundry_doc` / `foundry_manual` -> `PDK`
  - `stdcell` / `standard_cell` / `liberty` / `lib` -> `StdCell`
  - `sram` / `memory` / `macro` -> `SRAM`
  - `platform` / `flow` / `methodology` / `platform_flow` / `checklist_template` / `signoff_template` -> `Platform_Flow`
  - `script` / `tcl` / `python` / `makefile` / `csh` / `sh` -> `Script`
  - `literature` / `paper` / `book` / `textbook` / `general` / `training` / `team` -> `Literature`
  - `project_doc` / `project` / `doc` / `checklist_result` / `project_checklist` -> `Project_Doc`
  - `ip` / `ip_doc` / `datasheet` / `manual` -> `IP`
  - `eda` / `tool` / `command` -> `EDA`

#### [MODIFY] [metadata.py](file:///home/eason/proj/open-webui/chip_agent/src/metadata.py)
- Update `QueryMetadata` schema category description.
- Align `normalize_metadata` mapping logic to be identical to `_normalize_category` in `metadata_mapper.py`.

---

### Prompt Engineering (Routing & Extraction)

#### [MODIFY] [supervisor_prompt.py](file:///home/eason/proj/open-webui/chip_agent/src/prompts/supervisor_prompt.py)
- Update `SYSTEM_PROMPT`'s category schema list to include the 9 new categories.
- Update metadata extraction rules and examples to clarify the routing/categories:
  - `PDK`: Process design kit rules, DRC/LVS decks, and Foundry Manuals.
  - `Platform_Flow`: Automated flow scripts/guides, standard sign-off checklist templates.
  - `Project_Doc`: Project specs, PRDs, and filled/completed project sign-off checklist results.
- Add few-shot examples for queries targeting checklist templates vs checklist results.

---

### Test Suite Alignment

#### [MODIFY] [test_metadata_mapper.py](file:///home/eason/proj/open-webui/chip_agent/tests/test_metadata_mapper.py)
- Update `TestNormalizeCategory` to verify:
  - `general` -> `Literature`
  - `foundry_doc` -> `PDK`
  - `checklist_template` -> `Platform_Flow`
  - `checklist_result` -> `Project_Doc`
  - `stdcell` -> `StdCell`
  - `sram` -> `SRAM`

#### [MODIFY] [test_supervisor.py](file:///home/eason/proj/open-webui/chip_agent/tests/test_supervisor.py)
- Update `test_metadata_normalization` to use `Project_Doc` instead of `Project` and map `general` to `Literature`.
- Update mock assertions to check for canonicalized `Literature` and `Project_Doc` instead of `General` or `Project`.

## Verification Plan

### Automated Tests
- Run `wsl sh -c "cd /home/eason/proj/open-webui/chip_agent && PYTHONPATH=. python3 -m pytest"` to ensure all 209 unit tests compile, run, and pass.
