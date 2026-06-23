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

#### [metadata_mapper.py](file:///home/eason/proj/open-webui/chip_agent/src/ingestion/metadata_mapper.py)
- Updated `_normalize_category` aliases mapping to support all 9 new categories.
- Mapped `foundry_doc` / `foundry` to `PDK`.
- Mapped checklist templates to `Platform_Flow` and checklist results/logs to `Project_Doc`.
- Mapped retired categories like `general` / `training` to `Literature`.

#### [metadata.py](file:///home/eason/proj/open-webui/chip_agent/src/metadata.py)
- Aligned `QueryMetadata` schema category descriptions and `normalize_metadata` mapping logic to be identical to the ingestion mapper.

#### [supervisor_prompt.py](file:///home/eason/proj/open-webui/chip_agent/src/prompts/supervisor_prompt.py)
- Aligned `SYSTEM_PROMPT` categories schema with the new 9-category taxonomy.
- Updated metadata extraction rules and few-shot routing examples to accurately extract checklist templates (`Platform_Flow`) versus project checklist results (`Project_Doc`).

#### [supervisor.py](file:///home/eason/proj/open-webui/chip_agent/src/supervisor.py)
- Changed the default fallback category from `"General"` to `"Literature"`.

### Ingestion CLI & TSMC Secure Document Detection

#### [ingest_documents.py](file:///home/eason/proj/open-webui/chip_agent/scripts/ingest_documents.py)
- Updated CLI parser to allow the 9 new category choices.
- Added support for `--vendor` metadata parameter mapping during ingestion.
- Added **TSMC Secure Document (TSD) detection**: Read the first 50 bytes of any uploaded `.pdf`. If `%TSD-Header-###%` is matched, it halts and reports a clear description explaining that standard open-source parsers cannot read DRM-protected TSD files directly, giving engineers instructions to decrypt or export to plain text before ingesting.
- Fixed a mock `FileNotFoundError` bug and a `NameError: name 'logger' is not defined` bug when checking non-existent PDF headers during testing.

### Intranet DNS Resolution Bypass

#### [.env](file:///home/eason/proj/open-webui/chip_agent/.env)
- Bypassed WSL2 hostname resolution timeouts for the corporate intranet domain `jmaicloud.jaguarmicro.com` by inspecting active backend connections (`ss -apn`) and updating the API base URL directly to `http://10.1.88.119:8100/v1`.

---

## 2. Verification and Tests

### Automated Unit Tests
We updated the test suite in the following files:
- [test_metadata_mapper.py](file:///home/eason/proj/open-webui/chip_agent/tests/test_metadata_mapper.py): Verified mapping from aliases like `general` to `Literature`, `foundry_doc` to `PDK`, `checklist_template` to `Platform_Flow`, `checklist_result` to `Project_Doc`, `liberty` to `StdCell`, and `memory` to `SRAM`.
- [test_supervisor.py](file:///home/eason/proj/open-webui/chip_agent/tests/test_supervisor.py): Aligned mock expectations and general fallback assertions with the new taxonomy.

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
