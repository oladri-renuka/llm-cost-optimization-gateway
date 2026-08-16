# int8_per_token_head KV Cache Quantization Experiment

## Overview

This experiment investigates whether `int8_per_token_head` KV cache quantization in vLLM causes reasoning failure mode shifts similar to those found in post-training weight quantization (the core finding from your "Silent Failures" paper).

**Research Question:** Does fine-grained KV cache quantization with per-token-head scales change *how* models fail, even when accuracy is preserved?

## Experiment Design

### Configuration
- **Model:** Qwen2.5 7B-Instruct (safe architecture without hybrid attention)
- **Backend:** FlashInfer (avoids Triton bug #49716)
- **Test Set:** 
  - AIME 2025: 30 competition math problems
  - GSM8K: ~70 grade school math problems
  - **Total:** 100 problems
- **Inference Configurations:**
  1. **Baseline:** Auto KV cache (FP32 default)
  2. **FP8:** FP8 KV cache quantization
  3. **INT8:** INT8 per-token-head KV cache quantization

### Taxonomy
All outputs classified into 6 categories from your paper:
- **NO_FAILURE:** Correct with sound reasoning
- **HOLLOW_CONVERGENCE:** Correct but incomplete reasoning
- **PREMISE_HIJACKING:** Flawed assumption, then correct reasoning
- **SHORTCUT_COLLAPSE:** Missing required steps, unjustified leaps
- **OVERCOUNTING:** Correct intermediate, then continues unnecessarily
- **CONFIDENCE_SNOWBALLING:** Single early error propagates

## Setup

### 1. Spin up RunPod GPU instance

**Recommended specs:**
- GPU: A100 (40GB) or H100 (recommended for more headroom)
- CPU: 8+ cores
- RAM: 64GB
- Storage: 100GB

**Connection:**
```bash
ssh root@your-runpod-ip
```

### 2. Run setup script

```bash
cd /tmp
curl -O https://raw.githubusercontent.com/oladri-renuka/[your-repo]/main/runpod_setup.sh
bash runpod_setup.sh
```

This will:
- Clone the experiment code and dependencies
- Create Python virtual environment
- Install vLLM, transformers, datasets, etc.
- Verify vLLM installation

### 3. Set environment variables

```bash
export OPENROUTER_KEY='your_openrouter_key'
export HF_TOKEN='your_huggingface_token'
export WORK_DIR='/workspace/int8_per_token_head_experiment'
```

Get keys:
- **OpenRouter:** Free sign-up at https://openrouter.ai (used for LLM-as-judge taxonomy classification)
- **HuggingFace:** https://huggingface.co/settings/tokens

## Running the Experiment

### Step 1: Main inference + taxonomy classification

```bash
cd $WORK_DIR
source venv/bin/activate

python3 run_int8_per_token_head_experiment.py
```

**What it does:**
1. Loads AIME 2025 (30q) + GSM8K (~70q)
2. Runs inference on all three KV cache configurations
3. For each configuration:
   - Saves raw outputs to `results/results_{config}.csv`
   - Uses LLM-as-judge to classify into 6 taxonomy categories
   - Computes accuracy and failure mode distribution

**Expected runtime:**
- ~8-12 hours depending on GPU (A100 much faster than consumer GPUs)
- Most time spent on LLM judge classification (can be parallelized if needed)

**Output files:**
```
results/
├── results_baseline.csv              # Raw outputs + metadata
├── results_fp8.csv
├── results_int8_per_token_head.csv
├── summary_baseline.json             # Accuracy + taxonomy breakdown
├── summary_fp8.json
└── summary_int8_per_token_head.json
```

### Step 2: Analyze results

```bash
python3 analyze_int8_results.py
```

**What it does:**
1. Loads all three result CSVs
2. Generates accuracy comparison table
3. Analyzes taxonomy distributions
4. **KEY FOCUS:** Compares Shortcut Collapse rates across configurations
5. Identifies samples where correctness changed between configs
6. Generates final report

**Output:**
Printed to stdout (pipe to file if needed):
```bash
python3 analyze_int8_results.py | tee analysis_report.txt
```

## Expected Findings

### From the paper baseline:
- Smaller models (3B) show **28.1pp shift** in Shortcut Collapse under NF4 quantization
- Hollow Convergence becomes harder to detect under quantization
- Different quantization methods cause **different failure mode patterns**

### For this experiment, look for:

1. **Accuracy impact:**
   - Does int8 degrade accuracy more than fp8?
   - Is degradation uniform across benchmarks (AIME vs GSM8K)?

2. **Shortcut Collapse shift:**
   - Does Shortcut Collapse rate change from baseline → int8?
   - Is the shift similar to weight quantization effects (~20pp)?
   - Or is KV cache quantization fundamentally different?

3. **Failure mode divergence:**
   - Between baseline and int8, do failures happen for different reasons?
   - E.g., does int8 cause more Premise Hijacking vs more Confidence Snowballing?

4. **Benchmark differences:**
   - Do AIME (harder) and GSM8K (easier) show different quantization effects?

## Troubleshooting

### vLLM doesn't recognize `int8_per_token_head`

Check vLLM version and available KV cache dtypes:
```python
import vllm
print(vllm.__version__)

# Try loading a model to see what's supported
from vllm import LLM
llm = LLM("meta-llama/Llama-2-7b-hf", kv_cache_dtype='int8_per_token_head')
```

If you get an error, it may mean:
- vLLM version is too old (need main branch or latest release with this feature)
- Update with: `pip install --upgrade vllm`

### GPU memory errors

Reduce memory pressure:
1. Use smaller model: `TinyLlama-1.1B-Chat-v1.0` instead of Qwen2.5 7B
2. Reduce batch size (already set to 1 in this script)
3. Reduce test set size (modify test set loading)

### Taxonomy classification hangs or fails

If `openai` calls are slow:
1. Check OpenRouter API status
2. Verify key is set: `echo $OPENROUTER_KEY`
3. Can comment out classification and do it later (outputs are already saved)

### Triton bug #49716

If you see output corruption or crashes with int8_per_token_head:
- The script uses FlashInfer by default to avoid this
- If it still happens, try: `--attention-backend flashattention`

## File Structure

```
.
├── runpod_setup.sh                           # One-time setup script
├── run_int8_per_token_head_experiment.py    # Main experiment
├── analyze_int8_results.py                   # Analysis script
├── INT8_EXPERIMENT_README.md                 # This file
│
├── data/                                     # Downloaded datasets
│   ├── aime_2025.json
│   └── gsm8k_subset.json
│
├── results/                                  # Output CSVs and summaries
│   ├── results_baseline.csv
│   ├── results_fp8.csv
│   ├── results_int8_per_token_head.csv
│   └── summary_*.json
│
└── silent-failures/                          # Cloned dependency (judge code)
    └── 03_judge.py                          # (reference only)
```

## Key Papers / References

1. **Your paper:** "Silent Failures in Quantized LLM Reasoning" — arXiv:2607.09999
   - Established the 6-category taxonomy
   - Showed NF4 weight quantization causes failure mode shifts

2. **vLLM KV cache quantization:**
   - Issue #37319 — Extensible Per-Token Quantized KV Cache Scale Infrastructure
   - Issue #40388 — Gemma 4 per-token-head bug (use Qwen2.5 to avoid)
   - Issue #49716 — Triton corruption bug (use FlashInfer to avoid)

## Next Steps After Results

1. **Spot-check examples:**
   - Manually review 5-10 outputs classified as Shortcut Collapse
   - Verify LLM judge classification is reasonable
   - Flag any systematic mistakes in the taxonomy labels

2. **Compare to paper baseline:**
   - How do int8_per_token_head effects compare to NF4 weight quantization?
   - Is KV cache quantization "softer" (less dramatic shifts)?
   - Or does it cause entirely different failure modes?

3. **Statistical testing:**
   - Chi-squared test for Shortcut Collapse rate differences
   - Fisher's exact test for small category counts
   - Confidence intervals for accuracy deltas

4. **Extend scope:**
   - Test additional models (Llama, Mistral, etc.)
   - Larger test sets for statistical power
   - Other KV cache quantization modes (fp8_per_token_head, int8_per_head_static)

## Contact / Issues

If you hit bugs or have questions:
1. Check vLLM GitHub issues (they're very responsive)
2. OpenRouter free tier limits (falls back gracefully in the code)
3. GPU memory constraints (try a smaller model first)

---

**Start time:** YYYY-MM-DD HH:MM  
**RunPod instance:** [your-runpod-url]  
**Expected finish:** +8-12 hours  
