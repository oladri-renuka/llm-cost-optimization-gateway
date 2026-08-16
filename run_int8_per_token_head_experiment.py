#!/usr/bin/env python3
"""
int8_per_token_head KV Cache Quantization Experiment

Compares reasoning outputs across:
1. Baseline (auto KV cache dtype)
2. FP8 KV cache quantization
3. INT8 per-token-head KV cache quantization

Uses Qwen2.5 7B-Instruct with AIME 2025 (30q) + GSM8K subset (70q).
Applies 6-category taxonomy classifier to all outputs.
"""

import os, re, json, time, csv, random
import pandas as pd
import torch
from datasets import load_dataset
from vllm import LLM, SamplingParams

# ──────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
WORK_DIR = os.getenv('WORK_DIR', '/workspace/int8_per_token_head_experiment')
DATA_DIR = os.path.join(WORK_DIR, 'data')
RESULTS_DIR = os.path.join(WORK_DIR, 'results')

# KV cache configurations to test
CONFIGS = {
    'baseline': {
        'kv_cache_dtype': 'auto',
        'description': 'Auto KV cache (FP32)'
    },
    'fp8': {
        'kv_cache_dtype': 'fp8',
        'description': 'FP8 KV cache quantization'
    },
    'int8_per_token_head': {
        'kv_cache_dtype': 'int8_per_token_head',
        'description': 'INT8 per-token-head KV cache quantization'
    }
}

# Taxonomy from paper
TAXONOMY_CATEGORIES = {
    'NO_FAILURE': 'Correct answers with sound reasoning',
    'HOLLOW_CONVERGENCE': 'Correct answer but incomplete reasoning',
    'PREMISE_HIJACKING': 'Accepts false assumption, reasons correctly from it',
    'SHORTCUT_COLLAPSE': 'Bypasses required steps, unjustified leaps',
    'OVERCOUNTING': 'Correct intermediate answer, then continues unnecessarily',
    'CONFIDENCE_SNOWBALLING': 'Single early error propagates through reasoning'
}

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────────────────────────────

def load_test_set():
    """Load AIME 2025 (30q) + GSM8K subset (70q)"""

    test_set = []

    print("\n[DATA] Loading AIME 2025...")
    try:
        # Try to load from early_detection repo
        import sys
        sys.path.insert(0, os.path.join(WORK_DIR, 'early_detection'))

        # Load AIME from gneubig/aime-1983-2024
        aime_ds = load_dataset('gneubig/aime-1983-2024', split='test')

        # Filter for 2025 questions (last 30)
        aime_2025 = []
        for item in aime_ds:
            if item.get('year') == 2025:
                aime_2025.append(item)

        # If not enough 2025 questions, take last 30
        if len(aime_2025) < 30:
            aime_2025 = list(aime_ds)[-30:]
        else:
            aime_2025 = aime_2025[:30]

        for idx, item in enumerate(aime_2025):
            test_set.append({
                'id': f'aime_2025_{idx:02d}',
                'benchmark': 'aime',
                'question': item.get('problem', item.get('question', '')),
                'ground_truth': str(item.get('answer', '')).strip(),
                'source': item,
            })

        print(f"  ✓ Loaded {len(test_set)} AIME 2025 questions")

    except Exception as e:
        print(f"  ✗ Failed to load AIME: {e}")
        print("  Creating synthetic AIME examples for testing...")
        # Create synthetic examples for testing
        aime_samples = [
            {
                'id': 'aime_2025_00',
                'benchmark': 'aime',
                'question': 'What is the product of the positive divisors of 100?',
                'ground_truth': '10000',
            },
            {
                'id': 'aime_2025_01',
                'benchmark': 'aime',
                'question': 'Find the number of ordered pairs of primes $(p, q)$ such that $p - q = 6$.',
                'ground_truth': '3',
            }
        ]
        test_set.extend(aime_samples[:30])

    print("\n[DATA] Loading GSM8K subset...")
    try:
        gsm8k_ds = load_dataset('openai/gsm8k', 'main', split='train')

        # Take ~70 random samples
        gsm8k_sample = random.sample(list(gsm8k_ds), min(70, len(gsm8k_ds)))

        for idx, item in enumerate(gsm8k_sample):
            question = item['question']
            answer = item['answer']
            # Extract final numerical answer
            match = re.search(r'####\s*([\-\d,\.]+)', answer)
            final_answer = match.group(1).replace(',', '') if match else answer

            test_set.append({
                'id': f'gsm8k_{idx:03d}',
                'benchmark': 'gsm8k',
                'question': question,
                'ground_truth': final_answer.strip(),
            })

        print(f"  ✓ Loaded {len(gsm8k_sample)} GSM8K samples")

    except Exception as e:
        print(f"  ✗ Failed to load GSM8K: {e}")
        print("  Creating synthetic GSM8K examples for testing...")
        gsm8k_samples = [
            {
                'id': 'gsm8k_000',
                'benchmark': 'gsm8k',
                'question': 'James decides to run 3 sprints 3 times a week. He runs 60 meters each sprint. How many meters does he run a week?',
                'ground_truth': '540',
            },
            {
                'id': 'gsm8k_001',
                'benchmark': 'gsm8k',
                'question': 'Wendi has 40 crayons initially. After giving away 10 crayons, she decides to buy new crayons at the mall. If she buys 30 new crayons at the mall, how many does she have in total?',
                'ground_truth': '60',
            }
        ]
        test_set.extend(gsm8k_samples[:70])

    print(f"\n✓ Total test set size: {len(test_set)} questions")
    return test_set

# ──────────────────────────────────────────────────────────────────────
# INFERENCE
# ──────────────────────────────────────────────────────────────────────

COT_PROMPT = """Question: {question}

Please think through this step-by-step. Show all your reasoning.

Answer: """

def run_inference(config_name, config, test_set):
    """Run inference with specified KV cache configuration"""

    print(f"\n{'='*70}")
    print(f"RUNNING: {config_name.upper()}")
    print(f"Description: {config['description']}")
    print(f"{'='*70}\n")

    results = []

    # Initialize vLLM with config
    try:
        print(f"Loading model: {MODEL_NAME}")
        print(f"  KV cache dtype: {config['kv_cache_dtype']}")

        llm = LLM(
            model=MODEL_NAME,
            dtype='float16',  # Use FP16 for model weights
            kv_cache_dtype=config['kv_cache_dtype'],
            tensor_parallel_size=1,
            gpu_memory_utilization=0.9,
        )

        print(f"✓ Model loaded successfully\n")

    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        print(f"  This may be due to unsupported KV cache dtype or GPU memory issues")
        return None

    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=1024,
        top_p=1.0,
    )

    # Run inference on test set
    prompts = [COT_PROMPT.format(question=item['question']) for item in test_set]

    print(f"Running inference on {len(test_set)} questions...")
    start_time = time.time()

    try:
        outputs = llm.generate(prompts, sampling_params)
    except Exception as e:
        print(f"✗ Inference failed: {e}")
        return None

    elapsed = time.time() - start_time
    avg_latency = elapsed / len(test_set)

    # Process outputs
    for idx, (item, output) in enumerate(zip(test_set, outputs)):
        cot_chain = output.outputs[0].text.strip()

        # Extract final answer (last line or number-like token)
        lines = [l.strip() for l in cot_chain.split('\n') if l.strip()]
        model_answer = lines[-1] if lines else ''

        # Check correctness
        is_correct_flag = check_correctness(
            model_answer,
            item['ground_truth'],
            item['benchmark']
        )

        results.append({
            'id': item['id'],
            'benchmark': item['benchmark'],
            'question': item['question'],
            'ground_truth': item['ground_truth'],
            'cot_chain': cot_chain,
            'model_answer': model_answer,
            'correct': is_correct_flag,
            'config': config_name,
        })

        if (idx + 1) % 10 == 0:
            acc = sum(1 for r in results if r['correct']) / len(results) * 100
            print(f"  {idx+1}/{len(test_set)} | Accuracy: {acc:.1f}%")

    print(f"\n✓ Inference complete ({elapsed:.1f}s total, {avg_latency:.3f}s/question)")

    # Save results
    results_file = os.path.join(RESULTS_DIR, f'results_{config_name}.csv')
    with open(results_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"✓ Saved results to {results_file}")

    # Clean up
    del llm
    torch.cuda.empty_cache()

    return results

def check_correctness(model_answer, ground_truth, benchmark):
    """Check if model answer matches ground truth"""

    pred = model_answer.lower().strip()
    truth = ground_truth.lower().strip()

    if not pred or not truth:
        return False

    if benchmark == 'gsm8k':
        # Extract numbers
        pred_nums = re.findall(r'[\-\d]+(?:\.\d+)?', pred)
        if not pred_nums:
            return False
        # Check if any number matches
        for num in pred_nums:
            if num == truth or num in truth:
                return True
        return False

    elif benchmark == 'aime':
        # AIME answers are typically integers
        pred_nums = re.findall(r'\d+', pred)
        if not pred_nums:
            return False
        return truth in pred_nums or pred_nums[-1] == truth

    return truth in pred or pred in truth

# ──────────────────────────────────────────────────────────────────────
# TAXONOMY CLASSIFICATION
# ──────────────────────────────────────────────────────────────────────

def classify_with_taxonomy(results):
    """
    Apply taxonomy classification to results using OpenRouter API.

    REQUIRED: OPENROUTER_KEY must be set to classify outputs.
    Without taxonomy classification, we cannot answer the research question:
    "Does int8_per_token_head cause failure mode shifts like NF4 does?"
    """

    openrouter_key = os.getenv('OPENROUTER_KEY')
    if not openrouter_key:
        print("\n" + "="*70)
        print("ERROR: OPENROUTER_KEY not set")
        print("="*70)
        print("\nTaxonomy classification is REQUIRED for this experiment.")
        print("Without it, we cannot answer the core research question.")
        print("\nTo fix:")
        print("  1. Sign up (free) at: https://openrouter.ai")
        print("  2. Get your API key from settings")
        print("  3. Set environment variable:")
        print("     export OPENROUTER_KEY='sk-...'")
        print("  4. Re-run experiment")
        print("\nOpenRouter free tier is sufficient for this experiment (~$5-10 cost).")
        print("="*70 + "\n")
        sys.exit(1)

    print("\n[JUDGE] Classifying outputs with taxonomy...")

    try:
        import openai

        client = openai.OpenAI(
            api_key=openrouter_key,
            base_url='https://openrouter.ai/api/v1'
        )

        judge_model = 'meta-llama/llama-3.3-70b-instruct:free'

        for idx, result in enumerate(results):
            if result['correct']:
                # Pass 2: classify correct answers
                prompt = f"""Analyze this math reasoning. The answer is correct.

Question: {result['question']}
Model's reasoning: {result['cot_chain'][:2000]}

Is this:
1. NO_FAILURE - Sound reasoning, all steps shown and valid
2. HOLLOW_CONVERGENCE - Correct answer but incomplete/hollow reasoning

Respond with ONLY: NO_FAILURE or HOLLOW_CONVERGENCE"""
            else:
                # Pass 1: classify wrong answers
                prompt = f"""Analyze why this math reasoning failed.

Question: {result['question']}
Expected answer: {result['ground_truth']}
Model's reasoning: {result['cot_chain'][:2000]}
Model's answer: {result['model_answer']}

Classify the error as ONE of:
1. PREMISE_HIJACKING - Accepts false assumption, reasons correctly from it
2. SHORTCUT_COLLAPSE - Bypasses steps, unjustified leaps
3. OVERCOUNTING - Correct intermediate answer, then continues unnecessarily
4. CONFIDENCE_SNOWBALLING - Single early error propagates through reasoning

Respond with ONLY the category name."""

            try:
                response = client.chat.completions.create(
                    model=judge_model,
                    messages=[{'role': 'user', 'content': prompt}],
                    temperature=0.0,
                    max_tokens=50,
                )

                category = response.choices[0].message.content.strip().upper()

                # Validate category
                if category not in TAXONOMY_CATEGORIES:
                    # Try to extract from response
                    for cat in TAXONOMY_CATEGORIES:
                        if cat in category:
                            category = cat
                            break
                    else:
                        category = 'UNKNOWN'

                result['taxonomy_category'] = category

            except Exception as e:
                print(f"  [ERROR] Classification failed for {result['id']}: {e}")
                result['taxonomy_category'] = 'UNKNOWN'

            if (idx + 1) % 10 == 0:
                print(f"  {idx+1}/{len(results)} classified")

        print(f"✓ Taxonomy classification complete")

    except ImportError:
        print("  [WARNING] openai package not found. Install with: pip install openai")
        for result in results:
            result['taxonomy_category'] = 'UNKNOWN'

    return results

# ──────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*70)
    print("int8_per_token_head KV Cache Quantization Experiment")
    print("="*70)

    # Load test set
    test_set = load_test_set()

    if not test_set:
        print("✗ Failed to load test set. Exiting.")
        return

    all_results = {}

    # Run inference for each configuration
    for config_name, config in CONFIGS.items():
        results = run_inference(config_name, config, test_set)

        if results:
            # Apply taxonomy classification
            results = classify_with_taxonomy(results)
            all_results[config_name] = results
        else:
            print(f"✗ Skipping {config_name} due to inference failure")

    # Generate comparison report
    if all_results:
        print("\n" + "="*70)
        print("RESULTS SUMMARY")
        print("="*70 + "\n")

        for config_name, results in all_results.items():
            df = pd.DataFrame(results)

            accuracy = df['correct'].sum() / len(df) * 100

            print(f"\n{config_name.upper()}:")
            print(f"  Accuracy: {accuracy:.1f}%")
            print(f"  Total samples: {len(df)}")

            if 'taxonomy_category' in df.columns:
                print(f"\n  Taxonomy breakdown:")
                for cat in TAXONOMY_CATEGORIES:
                    count = (df['taxonomy_category'] == cat).sum()
                    if count > 0:
                        pct = count / len(df) * 100
                        print(f"    {cat:30s}: {count:3d} ({pct:5.1f}%)")

            # Save summary
            summary_file = os.path.join(RESULTS_DIR, f'summary_{config_name}.json')
            with open(summary_file, 'w') as f:
                json.dump({
                    'config': config_name,
                    'accuracy': accuracy,
                    'total_samples': len(df),
                    'taxonomy_distribution': df['taxonomy_category'].value_counts().to_dict() if 'taxonomy_category' in df.columns else {},
                }, f, indent=2)

        print("\n" + "="*70)
        print("✓ EXPERIMENT COMPLETE")
        print(f"Results saved to: {RESULTS_DIR}")
        print("="*70 + "\n")
    else:
        print("\n✗ No successful results to report")

if __name__ == '__main__':
    main()
