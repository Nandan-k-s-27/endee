"""
BreakGuard - Example Usage Script
Demonstrates the full pipeline: scan → analyze → report.

Run this after setup:
    python example_usage.py
"""

import os
import sys


def main():
    print("=" * 60)
    print("  BreakGuard - Example Usage")
    print("=" * 60)

    # ─── Step 1: Test the Code Analyzer ─────────────────────────
    print("\n[Step 1] Testing Code Analyzer...")
    from analyzer.code_analyzer import scan_project, get_api_call_locations

    test_dir = os.path.join(os.path.dirname(__file__), "test_project")
    if not os.path.exists(test_dir):
        print(f"  ERROR: Test project not found at {test_dir}")
        sys.exit(1)

    api_usage = scan_project(test_dir)
    print(f"  Found API calls in {len(api_usage)} files:")
    for filepath, calls in api_usage.items():
        rel = os.path.relpath(filepath, test_dir)
        print(f"    {rel}: {calls}")

    # ─── Step 2: Test the Embedding Engine ──────────────────────
    print("\n[Step 2] Testing Embedding Engine...")
    from embeddings.embedding_engine import EmbeddingEngine

    engine = EmbeddingEngine()

    test_texts = [
        "ReactDOM.render: Render a React element into the DOM",
        "createRoot: Create a React root for rendering",
        "useState: Declare state variable in functional component",
    ]

    vectors = engine.encode_batch(test_texts)
    for text, vec in zip(test_texts, vectors):
        print(f"  '{text[:40]}...' → [{vec[0]:.4f}, {vec[1]:.4f}, ...] (dim={len(vec)})")

    # ─── Step 3: Compute similarity examples ───────────────────
    print("\n[Step 3] Similarity Examples...")
    import numpy as np

    def cosine_sim(a, b):
        a, b = np.array(a), np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    pairs = [
        ("ReactDOM.render: Render React element into DOM",
         "createRoot: Create a React root for rendering"),
        ("useState: Declare state in functional component",
         "useState: Returns stateful value and setter function"),
        ("ReactDOM.render: Render React element",
         "console.log: Print to console"),
    ]

    for t1, t2 in pairs:
        v1 = engine.encode(t1)
        v2 = engine.encode(t2)
        sim = cosine_sim(v1, v2)
        print(f"  sim('{t1[:30]}...', '{t2[:30]}...') = {sim:.4f}")

    # ─── Step 4: Run full check (requires Endee) ───────────────
    print("\n[Step 4] Running full compatibility check...")
    print("  (Requires Endee server + knowledge base)")

    try:
        from checker.compatibility_checker import CompatibilityChecker

        checker = CompatibilityChecker()
        results = checker.check_project(api_usage, "17", "18", "react")

        summary = results["summary"]
        print(f"\n  Results:")
        print(f"    Breaking changes: {summary['breaking']}")
        print(f"    Minor changes:    {summary['minor']}")
        print(f"    Compatible:       {summary['compatible']}")
        if summary.get("errors", 0):
            print(f"    Errors:           {summary['errors']}")
        print(f"\n  Full check completed successfully!")
    except Exception as e:
        print(f"  Skipped (Endee not available): {e}")
        print("  Run 'docker compose up -d' and 'python build_knowledge_base.py' first.")

    print("\n" + "=" * 60)
    print("  Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
