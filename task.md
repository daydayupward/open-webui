# Checklist: Document Category Expansion and Checklist Split

- [x] 1. Update `chip_agent/src/ingestion/metadata_mapper.py` for new categories and aliasing (split checklists, merge foundry_doc into PDK).
- [x] 2. Update `chip_agent/src/metadata.py` to align `normalize_metadata` and `QueryMetadata` schema with `metadata_mapper.py`.
- [x] 3. Update `chip_agent/src/prompts/supervisor_prompt.py` for the 9-category system prompt and few-shot routing.
- [x] 4. Update unit tests in `chip_agent/tests/test_metadata_mapper.py` to test the new category aliases.
- [x] 5. Update unit tests in `chip_agent/tests/test_supervisor.py` to align with new categories.
- [x] 6. Run the pytest suite and verify that all 209+ tests pass without regression.
