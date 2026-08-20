#!/usr/bin/env python3
"""Generate architecture and workflow diagrams for jbprag using gpt-image-2."""

import requests
import base64
import os
from pathlib import Path

API_BASE = "https://jmapi01.jaguarmicro.com"
API_KEY = "sk-4FdTM7qOGWDEKoO86FweSAbkANjnPlshni1kiHv3gTKj1rrZ"
OUTPUT_DIR = Path(__file__).parent / "image"

def generate_image(prompt: str, filename: str, size: str = "1536x1024") -> bool:
    """Generate an image using gpt-image-2 API."""
    url = f"{API_BASE}/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": size
    }

    try:
        print(f"Generating: {filename}...")
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        if "data" in data and len(data["data"]) > 0:
            img_b64 = data["data"][0].get("b64_json")
            if img_b64:
                img_bytes = base64.b64decode(img_b64)
                output_path = OUTPUT_DIR / filename
                output_path.write_bytes(img_bytes)
                print(f"  ✓ Saved to {output_path} ({len(img_bytes)} bytes)")
                return True

        print(f"  ✗ Unexpected response: {data}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    prompts = {
        "arch_overview.png": (
            "A clean, professional technical architecture diagram for a RAG (Retrieval-Augmented Generation) system "
            "called 'Chip-RAG' for semiconductor chip physical design. "
            "The diagram should show: "
            "1) Top layer: User Query Input → Supervisor Agent (Router) "
            "2) Middle layer: Three expert nodes - PDK Expert, EDA Script Expert, Metrics Analyst "
            "3) Bottom layer: Knowledge Base with PostgreSQL+pgvector, containing PDK rules, EDA manuals, Project docs "
            "4) Supporting components: Embedding (bge-m3), Reranker (qwen3-reranker-8b), Self-RAG validation loop "
            "5) Output: Finalizer → Streaming Response with Citations "
            "Use a modern flat design style with blue and white color scheme. "
            "Include arrows showing data flow. "
            "Text should be in English. "
            "Professional, suitable for a corporate presentation slide."
        ),
        "rag_workflow.png": (
            "A detailed RAG workflow diagram showing the complete retrieval-augmented generation pipeline. "
            "The workflow should show these steps in a vertical flow: "
            "1) Query Preprocessing: Abbreviation expansion (STA→Static Timing Analysis), metadata extraction "
            "2) Retrieval: Vector search (50 candidates) → Parent text injection → Reranking (top 10-15) "
            "3) Self-RAG Loop: Document grading → Answer generation → Hallucination check → Completeness check → Retry if failed "
            "4) Post-processing: Citation injection, image extraction, reference formatting "
            "5) Output: Stream response with numbered citations [1][2] and source drawer "
            "Use a clean flowchart style with decision diamonds for the Self-RAG loop. "
            "Color code: green for retrieval, blue for generation, yellow for validation. "
            "Professional technical diagram style."
        ),
        "sota_comparison.png": (
            "A professional comparison table/infographic comparing Chip-RAG with state-of-the-art RAG approaches. "
            "Show these approaches side by side: "
            "1) Naive RAG: Basic vector search + LLM generation, no validation "
            "2) Advanced RAG: Query rewriting + reranking, but no hallucination detection "
            "3) Self-RAG: Reflection tokens for grounding, but single-pass "
            "4) Chip-RAG (Our System): Multi-expert routing + Self-RAG loop + Parent-child chunking + Domain-specific query expansion + SQL guardrails "
            "Use a table format with checkmarks (✓) and crosses (✗) for features. "
            "Features to compare: Query expansion, Reranking, Hallucination detection, Multi-expert routing, Parent-child chunks, SQL integration, Image retrieval "
            "Color scheme: blue for our system advantages. "
            "Professional, suitable for presentation."
        ),
        "chunking_strategy.png": (
            "A visual diagram explaining the parent-child chunking strategy for document processing. "
            "Show: "
            "1) Original document (large rectangle) "
            "2) Parent chunks (medium rectangles, ~2000 tokens each, with 500 token overlap shown as overlapping areas) "
            "3) Child chunks (small rectangles within parents, ~300 tokens each, with 50 token overlap) "
            "4) Storage: Child text in vector DB 'document' column, parent text in 'cmetadata.parent_text' "
            "5) Retrieval flow: Child match → Parent text injection → Richer context for LLM "
            "Use nested rectangles to show the hierarchy. "
            "Color code: light blue for parents, darker blue for children. "
            "Show overlap areas with gradient or pattern. "
            "Clean, technical illustration style."
        ),
    }

    results = {}
    for filename, prompt in prompts.items():
        success = generate_image(prompt, filename)
        results[filename] = success

    print("\n" + "="*50)
    print("Generation Summary:")
    print("="*50)
    for filename, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {filename}: {status}")

    success_count = sum(1 for s in results.values() if s)
    print(f"\nTotal: {success_count}/{len(results)} images generated successfully.")


if __name__ == "__main__":
    main()
