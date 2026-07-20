# Jbpragic RAG Development Seed Data

This directory contains seed datasets and seed files for local offline development. These samples mimic real-world PDK parameters, EDA tool manuals, project metrics, and documents.

## Directory Contents

- `pdk_rules.jsonl`: Sample rules covering node-specific metal pitch and constraints (N5, N7).
- `eda_manuals.jsonl`: Sample command reference manuals for EDA layout and floorplanning tools (Innovus, ICC2).
- `project_docs.jsonl`: Sample engineering project notes and specifications (Proj_A, Proj_B).
- `metrics_seed.sql`: Database schema and PPA metrics seed data.

## Initializing Local DB

Use `python3 scripts/seed_dev_data.py` to seed both PGVector and the read-only Metrics database.
