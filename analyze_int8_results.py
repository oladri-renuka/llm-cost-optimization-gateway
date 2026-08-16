#!/usr/bin/env python3
"""
Analysis script for int8_per_token_head experiment results.

Compares the three configurations and generates:
1. Accuracy comparison table
2. Taxonomy distribution comparison
3. Shortcut Collapse analysis
4. Cross-configuration differences
"""

import os
import json
import pandas as pd
import numpy as np
from collections import defaultdict

WORK_DIR = os.getenv('WORK_DIR', '/workspace/int8_per_token_head_experiment')
RESULTS_DIR = os.path.join(WORK_DIR, 'results')

TAXONOMY_CATEGORIES = {
    'NO_FAILURE': 'Correct answers with sound reasoning',
    'HOLLOW_CONVERGENCE': 'Correct answer but incomplete reasoning',
    'PREMISE_HIJACKING': 'Accepts false assumption, reasons correctly from it',
    'SHORTCUT_COLLAPSE': 'Bypasses required steps, unjustified leaps',
    'OVERCOUNTING': 'Correct intermediate answer, then continues unnecessarily',
    'CONFIDENCE_SNOWBALLING': 'Single early error propagates through reasoning'
}

def load_results():
    """Load all results CSVs"""
    results = {}

    for config in ['baseline', 'fp8', 'int8_per_token_head']:
        path = os.path.join(RESULTS_DIR, f'results_{config}.csv')

        if os.path.exists(path):
            df = pd.read_csv(path)
            results[config] = df
            print(f"✓ Loaded results_{config}.csv ({len(df)} rows)")
        else:
            print(f"✗ Not found: {path}")

    return results

def accuracy_comparison(results):
    """Compare accuracy across configurations"""

    print("\n" + "="*70)
    print("ACCURACY COMPARISON")
    print("="*70 + "\n")

    comparison = []

    for config_name in ['baseline', 'fp8', 'int8_per_token_head']:
        if config_name not in results:
            continue

        df = results[config_name]
        total = len(df)
        correct = df['correct'].sum()
        acc = (correct / total * 100) if total > 0 else 0

        # Break down by benchmark
        benchmarks = {}
        for bench in df['benchmark'].unique():
            bench_df = df[df['benchmark'] == bench]
            bench_acc = (bench_df['correct'].sum() / len(bench_df) * 100) if len(bench_df) > 0 else 0
            benchmarks[bench] = {
                'n': len(bench_df),
                'correct': bench_df['correct'].sum(),
                'accuracy': bench_acc
            }

        comparison.append({
            'config': config_name,
            'total': total,
            'correct': correct,
            'accuracy': acc,
            'benchmarks': benchmarks
        })

        print(f"{config_name.upper()}")
        print(f"  Overall accuracy: {acc:.1f}% ({correct}/{total})")
        for bench, stats in benchmarks.items():
            print(f"    {bench:10s}: {stats['accuracy']:5.1f}% ({stats['correct']}/{stats['n']})")
        print()

    return comparison

def taxonomy_analysis(results):
    """Analyze taxonomy category distributions"""

    print("\n" + "="*70)
    print("TAXONOMY DISTRIBUTION")
    print("="*70 + "\n")

    taxonomy_dist = {}

    for config_name in ['baseline', 'fp8', 'int8_per_token_head']:
        if config_name not in results:
            continue

        df = results[config_name]

        # Check if taxonomy classification was done
        if 'taxonomy_category' not in df.columns:
            print(f"{config_name.upper()}: No taxonomy classification found")
            continue

        print(f"{config_name.upper()}")

        dist = defaultdict(int)
        for cat in df['taxonomy_category'].dropna().unique():
            count = (df['taxonomy_category'] == cat).sum()
            pct = (count / len(df) * 100) if len(df) > 0 else 0
            dist[cat] = {'count': count, 'pct': pct}
            print(f"  {cat:30s}: {count:3d} ({pct:5.1f}%)")

        # Specific focus: Shortcut Collapse among failures
        failures = df[~df['correct']]
        if len(failures) > 0:
            sc_count = (failures['taxonomy_category'] == 'SHORTCUT_COLLAPSE').sum()
            sc_pct = (sc_count / len(failures) * 100)
            print(f"\n  Among FAILURES (n={len(failures)}):")
            print(f"    Shortcut Collapse: {sc_count} ({sc_pct:.1f}%)")

        taxonomy_dist[config_name] = dist
        print()

    return taxonomy_dist

def shortcut_collapse_focus(results):
    """Deep dive into Shortcut Collapse patterns"""

    print("\n" + "="*70)
    print("SHORTCUT COLLAPSE FOCUS")
    print("="*70 + "\n")

    print("This is the key finding from the paper — does int8_per_token_head")
    print("cause a shift in Shortcut Collapse rates similar to NF4?\n")

    for config_name in ['baseline', 'fp8', 'int8_per_token_head']:
        if config_name not in results:
            continue

        df = results[config_name]

        if 'taxonomy_category' not in df.columns:
            print(f"{config_name.upper()}: No taxonomy data")
            continue

        # Among failures, what % are Shortcut Collapse?
        failures = df[~df['correct']]
        total_failures = len(failures)

        if total_failures == 0:
            print(f"{config_name.upper()}: No failures to analyze")
            continue

        sc_count = (failures['taxonomy_category'] == 'SHORTCUT_COLLAPSE').sum()
        sc_pct = (sc_count / total_failures * 100)

        # Other categories among failures
        other_cats = {}
        for cat in TAXONOMY_CATEGORIES:
            if cat in ['NO_FAILURE', 'HOLLOW_CONVERGENCE']:
                continue
            count = (failures['taxonomy_category'] == cat).sum()
            pct = (count / total_failures * 100) if total_failures > 0 else 0
            if count > 0:
                other_cats[cat] = {'count': count, 'pct': pct}

        print(f"{config_name.upper()} — Failure Mode Breakdown (n={total_failures}):")
        print(f"  Shortcut Collapse:       {sc_count:3d} ({sc_pct:5.1f}%)")
        for cat, stats in sorted(other_cats.items(), key=lambda x: x[1]['count'], reverse=True):
            print(f"  {cat:20s}: {stats['count']:3d} ({stats['pct']:5.1f}%)")
        print()

def differences_between_configs(results):
    """Identify key differences between configurations"""

    print("\n" + "="*70)
    print("CONFIGURATION DIFFERENCES")
    print("="*70 + "\n")

    if 'baseline' not in results or 'int8_per_token_head' not in results:
        print("Cannot compare: missing baseline or int8_per_token_head results")
        return

    baseline_df = results['baseline']
    int8_df = results['int8_per_token_head']

    # Find samples where correctness changed
    baseline_correct = set(baseline_df[baseline_df['correct']]['id'])
    int8_correct = set(int8_df[int8_df['correct']]['id'])

    newly_wrong = baseline_correct - int8_correct
    newly_correct = int8_correct - baseline_correct

    print(f"Samples with changed correctness:")
    print(f"  Newly wrong in int8:    {len(newly_wrong)}")
    print(f"  Newly correct in int8:  {len(newly_correct)}")
    print()

    if len(newly_wrong) > 0:
        print(f"Examples of newly-wrong samples (int8_per_token_head broke them):")
        for sample_id in list(newly_wrong)[:5]:
            row = int8_df[int8_df['id'] == sample_id].iloc[0]
            print(f"  {sample_id}: {row['question'][:60]}...")

    print()

def generate_report(results, taxonomy_dist):
    """Generate final report"""

    print("\n" + "="*70)
    print("EXPERIMENT REPORT: int8_per_token_head KV Cache Quantization")
    print("="*70 + "\n")

    print("HYPOTHESIS:")
    print("  Does int8_per_token_head KV cache quantization cause a shift in")
    print("  reasoning failure modes similar to NF4 weight quantization?")
    print()

    print("METHODOLOGY:")
    print("  - Model: Qwen2.5 7B-Instruct")
    print("  - Test set: AIME 2025 (30q) + GSM8K subset (70q) = 100 questions")
    print("  - Configurations:")
    print("      1. Baseline (auto KV cache)")
    print("      2. FP8 KV cache quantization")
    print("      3. INT8 per-token-head KV cache quantization")
    print("  - Taxonomy: 6-category failure classification from paper")
    print()

    print("KEY FINDINGS:")
    print()

    # Finding 1: Accuracy
    if 'baseline' in results and 'int8_per_token_head' in results:
        baseline_acc = (results['baseline']['correct'].sum() / len(results['baseline']) * 100)
        int8_acc = (results['int8_per_token_head']['correct'].sum() / len(results['int8_per_token_head']) * 100)
        delta = int8_acc - baseline_acc

        print(f"1. ACCURACY IMPACT:")
        print(f"   Baseline: {baseline_acc:.1f}%")
        print(f"   INT8:     {int8_acc:.1f}%")
        print(f"   Δ:        {delta:+.1f}pp")
        print()

    # Finding 2: Shortcut Collapse shift
    if 'baseline' in taxonomy_dist and 'int8_per_token_head' in taxonomy_dist:
        baseline_sc = taxonomy_dist['baseline'].get('SHORTCUT_COLLAPSE', {}).get('pct', 0)
        int8_sc = taxonomy_dist['int8_per_token_head'].get('SHORTCUT_COLLAPSE', {}).get('pct', 0)
        delta_sc = int8_sc - baseline_sc

        print(f"2. SHORTCUT COLLAPSE SHIFT:")
        print(f"   Among all failures:")
        print(f"   Baseline SC rate: {baseline_sc:.1f}%")
        print(f"   INT8 SC rate:     {int8_sc:.1f}%")
        print(f"   Δ:                {delta_sc:+.1f}pp")
        print()

    print("3. QUALITATIVE COMPARISON:")
    print("   - Does int8 show similar failure mode patterns as the paper's NF4 analysis?")
    print("   - Are Shortcut Collapse cases distinguishable from other failure types?")
    print("   - Are there emergent failure modes unique to KV cache quantization?")
    print()

    print("NEXT STEPS:")
    print("   - Manual spot-check of 5-10 Shortcut Collapse examples")
    print("   - Investigate any GPU errors or numerical instabilities")
    print("   - Compare against fp8 as intermediate case")
    print()

    print("="*70)

def main():
    print("\nLoading results...\n")

    results = load_results()

    if not results:
        print("\n✗ No results found. Run the main experiment first.")
        return

    # Run all analyses
    accuracy_comparison(results)
    taxonomy_dist = taxonomy_analysis(results)
    shortcut_collapse_focus(results)
    differences_between_configs(results)
    generate_report(results, taxonomy_dist)

    print("\n✓ Analysis complete!")

if __name__ == '__main__':
    main()
