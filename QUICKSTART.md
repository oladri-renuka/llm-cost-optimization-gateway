# Quick Start: int8_per_token_head KV Cache Experiment

## TL;DR — 5 Minutes to Running

### 1. **Set up RunPod instance**
   - Open https://www.runpod.io
   - Launch a GPU pod (A100 recommended)
   - SSH into the instance once ready

### 2. **Run setup script (one time)**
   ```bash
   bash runpod_setup.sh
   ```
   This clones repos, installs vLLM, creates virtual env, and verifies setup.

### 3. **Set REQUIRED environment variable**
   ```bash
   export OPENROUTER_KEY='sk-...'    # REQUIRED: Get from https://openrouter.ai (free signup)
   ```
   
   Optional:
   ```bash
   export HF_TOKEN='hf_...'           # Optional: For gated HF models (Qwen2.5 is public)
   ```

### 4. **Run verification (takes ~1 minute)**
   ```bash
   source venv/bin/activate
   python3 verify_setup.py
   ```
   Checks GPU, vLLM, int8_per_token_head support, and environment.

### 5. **Run main experiment (takes 8-12 hours)**
   ```bash
   python3 run_int8_per_token_head_experiment.py
   ```
   - Loads 100 test questions (AIME + GSM8K)
   - Runs inference 3 times (baseline, fp8, int8_per_token_head)
   - Classifies failures using 6-category taxonomy
   - Saves results to `results/` directory

### 6. **Analyze results (takes ~2 minutes)**
   ```bash
   python3 analyze_int8_results.py
   ```
   - Compares accuracy across configurations
   - Shows Shortcut Collapse rates (key finding!)
   - Generates final report

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `runpod_setup.sh` | One-time environment setup |
| `verify_setup.py` | Pre-flight checks before running |
| `run_int8_per_token_head_experiment.py` | **Main experiment** — runs inference + taxonomy classification |
| `analyze_int8_results.py` | Analysis and reporting |
| `INT8_EXPERIMENT_README.md` | Full documentation |
| `QUICKSTART.md` | This file |

---

## Expected Output

After `run_int8_per_token_head_experiment.py`:

```
results/
├── results_baseline.csv                    # 100 rows, raw outputs
├── results_fp8.csv
├── results_int8_per_token_head.csv
│
└── summary_baseline.json                   # Accuracy: 85.0%, breakdown by taxonomy
    summary_fp8.json
    summary_int8_per_token_head.json
```

After `analyze_int8_results.py`:

```
ACCURACY COMPARISON
├── Baseline:         85.0% (85/100)
├── FP8:              83.0% (83/100)
└── INT8:             80.0% (80/100)

SHORTCUT COLLAPSE FOCUS
├── Baseline:         35% of failures are Shortcut Collapse
├── FP8:              38% of failures
└── INT8:             52% of failures  ← KEY: Did int8 cause shift?

CONFIGURATION DIFFERENCES
└── Samples where int8 broke correctness: X samples
```

---

## Key Research Question

**Does INT8 per-token-head KV cache quantization cause a shift in reasoning failure modes?**

Your paper found that NF4 weight quantization causes ~28pp shift in Shortcut Collapse for 3B models.

This experiment asks: **Does fine-grained KV cache quantization have similar effects?**

If Shortcut Collapse increases significantly (>10pp):
→ KV cache quantization affects *how* models fail, not just *whether* they fail

If Shortcut Collapse stays similar:
→ KV cache quantization is fundamentally different from weight quantization

---

## Stopping/Resuming

The main experiment **automatically checkpoints after each sample**. If interrupted:
- Resume from where it left off (already-run samples are skipped)
- No lost work

```bash
# If interrupted, just run again:
python3 run_int8_per_token_head_experiment.py
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `int8_per_token_head not supported` | Update vLLM: `pip install --upgrade vllm` |
| GPU out of memory | Reduce test set or use smaller model |
| OpenRouter timeouts | Taxonomy classification can be skipped; results still saved |
| vLLM doesn't recognize flag | Check vLLM version; may need main branch build |
| Triton errors (corrupted output) | Already using FlashInfer, but verify with `--attention-backend flashattention` |

---

## Expected Runtimes

| Step | Duration | Notes |
|------|----------|-------|
| Setup | 10 min | One-time |
| Verification | 2 min | Quick checks |
| **Main experiment** | **8-12 hours** | Depends on GPU (A100 ~8h, RTX4090 ~12h) |
| Analysis | 2 min | Fast post-processing |

---

## What Each Script Does

### `verify_setup.py`
Checks:
- ✓ vLLM installed and version
- ✓ CUDA/GPU availability and memory
- ✓ int8_per_token_head support in vLLM
- ✓ Environment variables set (OPENROUTER_KEY, HF_TOKEN)
- ✓ Required Python packages

**Run before main experiment:**
```bash
python3 verify_setup.py
```

### `run_int8_per_token_head_experiment.py`
Does:
1. Loads test set:
   - AIME 2025 (30 questions, hardest)
   - GSM8K (70 questions, easier)
2. Runs inference 3 times:
   - Baseline (FP32 KV cache)
   - FP8 KV cache
   - INT8 per-token-head KV cache
3. For each run:
   - Saves raw outputs (question, reasoning, answer, correctness)
   - Uses LLM judge to classify into 6 categories
   - Computes accuracy and failure mode distribution
4. Saves CSV and JSON results

**Runtime:** 8-12 hours (mostly taxonomy classification via OpenRouter API)

### `analyze_int8_results.py`
Analyzes results:
1. Accuracy comparison across configs
2. Taxonomy distribution (all 6 categories)
3. **Key focus:** Shortcut Collapse rate changes
4. Samples where correctness changed between configs
5. Final report with findings

**Runtime:** 2 minutes

---

## Next Steps After Results

1. **Spot-check taxonomy labels:**
   - Pick 5-10 samples classified as "Shortcut Collapse"
   - Manually verify the LLM judge got it right
   - Flag any systematic errors

2. **Compare to paper baseline:**
   - Paper found 28pp Shortcut Collapse shift with NF4
   - How does int8_per_token_head compare?
   - Is KV quantization "softer" or cause different effects?

3. **Statistical testing:**
   - Chi-squared for Shortcut Collapse rate differences
   - Confidence intervals for accuracy

4. **Extend scope:**
   - Test other models (Llama 3, Mistral)
   - Larger test sets
   - Other KV quantization modes (fp8_per_token_head)

---

## Questions?

Check `INT8_EXPERIMENT_README.md` for full documentation.

Email/contact if:
- vLLM doesn't support int8_per_token_head (check version)
- GPU memory issues (try smaller model or test set)
- OpenRouter API problems (gracefully falls back)

---

**Ready? Run:**
```bash
source venv/bin/activate
python3 verify_setup.py
python3 run_int8_per_token_head_experiment.py
python3 analyze_int8_results.py
```

**Good luck!** 🚀
