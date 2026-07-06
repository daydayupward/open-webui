# Walkthrough: Unified Document Category Expansion and Checklist Split

We have successfully expanded the document classification system to the 9-category system, consolidated `Foundry_Doc` under `PDK`, split sign-off checklists into template files (`Platform_Flow`) and project run results (`Project_Doc`), added a safety detection check for encrypted TSMC Secure Documents, and successfully ingested the platform PNR user guide.

## 1. Summary of Changes

### 9-Category Schema Alignment
We unified the category definitions between the ingestion/indexing pipeline and the LLM query supervisor:
- **PDK**: PDK & Foundry Manuals (process, DRC/LVS decks, ESD, EM reliability manuals).
- **StdCell**: Standard cell characterization and liberty (.lib) files.
- **SRAM**: SRAM compiler macro datasheets and reports.
- **IP**: Protocol and analog IPs (contains `vendor` metadata field).
- **EDA**: Tool reference manuals (contains `tool` metadata field).
- **Platform_Flow**: Company-wide automated flow guides, platform guides, and standard sign-off checklist templates.
- **Project_Doc**: Project-specific documents (SPEC, PRD) and actual project-specific checklist results/run logs.
- **Script**: Custom run scripts (Tcl, Python, Makefile, Csh, Sh).
- **Literature**: External textbooks, papers, standards, training materials, and general engineering reference documents (acts as a fallback for the retired `General` and `Training` categories).

### Core File Modifications

#### [metadata_mapper.py](file:///home/eason/proj/open-webui/jbprag/src/ingestion/metadata_mapper.py)
- Updated `_normalize_category` aliases mapping to support all 9 new categories.
- Mapped `foundry_doc` / `foundry` to `PDK`.
- Mapped checklist templates to `Platform_Flow` and checklist results/logs to `Project_Doc`.
- Mapped retired categories like `general` / `training` to `Literature`.

#### [metadata.py](file:///home/eason/proj/open-webui/jbprag/src/metadata.py)
- Aligned `QueryMetadata` schema category descriptions and `normalize_metadata` mapping logic to be identical to the ingestion mapper.

#### [supervisor_prompt.py](file:///home/eason/proj/open-webui/jbprag/src/prompts/supervisor_prompt.py)
- Aligned `SYSTEM_PROMPT` categories schema with the new 9-category taxonomy.
- Updated metadata extraction rules and few-shot routing examples to accurately extract checklist templates (`Platform_Flow`) versus project checklist results (`Project_Doc`).

#### [supervisor.py](file:///home/eason/proj/open-webui/jbprag/src/supervisor.py)
- Changed the default fallback category from `"General"` to `"Literature"`.

### Ingestion CLI & TSMC Secure Document Detection

#### [ingest_documents.py](file:///home/eason/proj/open-webui/jbprag/scripts/ingest_documents.py)
- Updated CLI parser to allow the 9 new category choices.
- Added support for `--vendor` metadata parameter mapping during ingestion.
- Added **TSMC Secure Document (TSD) detection**: Read the first 50 bytes of any uploaded `.pdf`. If `%TSD-Header-###%` is matched, it halts and reports a clear description explaining that standard open-source parsers cannot read DRM-protected TSD files directly, giving engineers instructions to decrypt or export to plain text before ingesting.
- Fixed a mock `FileNotFoundError` bug and a `NameError: name 'logger' is not defined` bug when checking non-existent PDF headers during testing.

### Intranet DNS Resolution Bypass

#### [.env](file:///home/eason/proj/open-webui/jbprag/.env)
- Bypassed WSL2 hostname resolution timeouts for the corporate intranet domain `jmaicloud.jaguarmicro.com` by inspecting active backend connections (`ss -apn`) and updating the API base URL directly to `http://10.1.88.119:8100/v1`.

---

## 2. Verification and Tests

### Automated Unit Tests
We updated the test suite in the following files:
- [test_metadata_mapper.py](file:///home/eason/proj/open-webui/jbprag/tests/test_metadata_mapper.py): Verified mapping from aliases like `general` to `Literature`, `foundry_doc` to `PDK`, `checklist_template` to `Platform_Flow`, `checklist_result` to `Project_Doc`, `liberty` to `StdCell`, and `memory` to `SRAM`.
- [test_supervisor.py](file:///home/eason/proj/open-webui/jbprag/tests/test_supervisor.py): Aligned mock expectations and general fallback assertions with the new taxonomy.

All **209 unit tests** compiled, ran, and passed successfully inside the WSL environment.

### Ingestion Verification
1. **TSD Document Blocked Safely**:
   Attempting to ingest the secure document `RN_TSN7_1PRF_20151201_130A.pdf` was intercepted by our TSD check:
   ```stderr
   Error: 'RN_TSN7_1PRF_20151201_130A.pdf' is a TSMC Secure Document (TSD) encrypted with TSMC DRM.
   Standard open-source PDF parsers cannot read DRM-protected TSD files directly.
   Please decrypt the file first (e.g., by printing to a standard PDF or exporting to plain text) and ingest the decrypted file.
   ```
2. **PNR User Guide Ingested Successfully**:
   Ingested `E:\flow\03_JBP_PNR\jbp_pnr_ug.md` under category `Platform_Flow` successfully:
   ```bash
   Converting document via MarkItDown: jbp_pnr_ug.md...
   Indexing 247 chunks into vector store collection 'project_docs'...
   File jbp_pnr_ug.md indexed successfully. Stats: {'total_input': 247, 'after_dedup': 247, 'indexed': 247, 'batches': 3}
   ```

---

## 3. JBP Platform Flow Retrieval Fix (chip-rag0.3)

### Root Cause
When the query contains the platform name "JBP" (JaguarMicro Backend Platform), the supervisor metadata extractor parses `"JBP"` as a `project_id`. Because `project_id` filtering was unconditionally applied, queries on platform guides like `jbp_pnr_ug.md` (which have category `Platform_Flow` and `project_id = null`) matched 0 chunks.

### Fix Implemented
1. **Project ID Normalization**: Added rules to `normalize_metadata` in [src/metadata.py](file:///home/eason/proj/open-webui/jbprag/src/metadata.py) to map platform names (e.g. `"jbp"` case-insensitive) to `None`.
2. **Conditional Project Filtering**: Modified `_build_filter` in [src/retrieval/project_retriever.py](file:///home/eason/proj/open-webui/jbprag/src/retrieval/project_retriever.py) to only apply the SQL metadata `project_id` filter when the query specifically targets project-specific documents (`Project_Doc`) by checking if `db_cats == ["Project_Doc"]`. General and platform documents (like `Platform_Flow` or `PDK`) remain project-independent and are correctly matched even when the query contains metadata for a project. Also added `"project_id"` to `EXCLUDED_KEYS` to prevent it from being automatically copied from metadata.

### Verification Outcome
* Created and ran a scratch test `test_jbp_query.py` confirming that `jbp中 place and route 执行的步骤和流程图` retrieves 3 relevant chunks from the database instead of 0.
* Re-ran the full test suite (`pytest`) successfully, verifying that all 209 unit tests continue to pass.
