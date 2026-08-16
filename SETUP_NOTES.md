# Setup Notes: OpenRouter Required for Taxonomy Classification

## Token Situation

### **OpenRouter Key (REQUIRED) ⭐**
- **Purpose:** LLM-as-judge for taxonomy classification
- **Why required:** Your research question needs taxonomy data to see if int8_per_token_head causes failure mode shifts (like NF4 did)
- **Cost:** ~$5-10 for 100 samples (free tier available)
- **How to get:** 
  1. Sign up at https://openrouter.ai (free)
  2. Get API key from settings
  3. Set: `export OPENROUTER_KEY='sk-...'`

### **HuggingFace Token (OPTIONAL)**
- **Qwen2.5-7B-Instruct:** Open source, public model
- **No authentication required** to download
- Only needed for future gated models

---

## Execution Path: With OpenRouter (Required)

```bash
# 1. Get OpenRouter key (REQUIRED)
# - Sign up at https://openrouter.io (free)
# - Copy API key from settings
# - Run: export OPENROUTER_KEY='sk-...'

# 2. Spin up RunPod (A100 SXM recommended)
# 3. SSH in
# 4. Clone repo
git clone https://github.com/oladri-renuka/vlm.git
cd vlm

# 5. Run setup
bash runpod_setup.sh

# 6. Verify
source venv/bin/activate
python3 verify_setup.py

# 7. Set OpenRouter key
export OPENROUTER_KEY='sk-...'

# 8. Run experiment (8-12 hours)
python3 run_int8_per_token_head_experiment.py

# 9. Analyze (2 minutes)
python3 analyze_int8_results.py
```

**You'll get:**
- ✅ Raw outputs (question, reasoning, answer, correctness)
- ✅ Accuracy comparison across 3 configs
- ✅ **Taxonomy classification** (auto-judged by LLM)
- ✅ **Shortcut Collapse shift** (your key metric)

---

## OpenRouter Setup (2 minutes)

1. **Sign up:** https://openrouter.ai (free account)
2. **Get key:** Settings → Copy API key
3. **Set in terminal:**
   ```bash
   export OPENROUTER_KEY='sk-...'
   ```
4. **Done!** Script will auto-classify all 100 outputs

**What you get:**
- Taxonomy classification for all samples
- Shortcut Collapse rates (your key finding!)
- Full failure mode breakdown

**Cost:** ~$5-10 for 100 samples (free tier covers it)

---

## Pushing to GitHub

```bash
cd /Users/renukaoladri/Claude/Projects/open_source/vlm

# Run the push script
bash PUSH_TO_GITHUB.sh
```

This will:
1. Create a branch: `int8-per-token-head-experiment`
2. Stage all experiment files
3. Commit with descriptive message
4. Push to https://github.com/oladri-renuka/vlm

---

## File Structure in Repo

```
vlm/
├── runpod_setup.sh                      # One-time setup
├── verify_setup.py                      # Pre-flight checks
├── run_int8_per_token_head_experiment.py   # Main experiment (NO KEYS NEEDED)
├── analyze_int8_results.py              # Analysis
├── INT8_EXPERIMENT_README.md            # Full docs
├── QUICKSTART.md                        # Quick reference
├── EXPERIMENT_CHECKLIST.md              # Step-by-step guide
├── SETUP_NOTES.md                       # This file
└── PUSH_TO_GITHUB.sh                    # Git push helper
```

---

## TL;DR: Just Do This

```bash
# 1. Get OpenRouter key (1 min)
# Sign up at https://openrouter.ai → copy key

# 2. SSH to RunPod instance
ssh root@your-runpod-ip

# 3. Clone repo and setup (10 min)
git clone https://github.com/oladri-renuka/vlm.git
cd vlm
bash runpod_setup.sh
source venv/bin/activate

# 4. Set OpenRouter key
export OPENROUTER_KEY='sk-...'

# 5. Run experiment (8-12 hours)
python3 run_int8_per_token_head_experiment.py

# 6. Analyze results (2 min)
python3 analyze_int8_results.py

# 7. Check key findings
cat results/summary_*.json
```

**That's it!** ✅

You get:
- Accuracy: baseline vs fp8 vs int8
- **Shortcut Collapse shift** (key finding!)
- Full taxonomy breakdown
- Raw reasoning traces for spot-checking

---

## If You Hit Issues

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: vllm` | Run `bash runpod_setup.sh` first |
| `CUDA out of memory` | RunPod specs OK? Check with `nvidia-smi` |
| `Model download fails` | Might be internet issue, retry. Or set `HF_TOKEN` if gated. |
| `Taxonomy skip message` | Normal! Just skip classification or add OpenRouter key |

---

## What Gets Saved

After 10-12 hour run, you'll have in `results/`:

```
results/
├── results_baseline.csv              # 100 samples, FP32 KV cache
├── results_fp8.csv                   # 100 samples, FP8 KV cache
├── results_int8_per_token_head.csv   # 100 samples, INT8 per-token-head KV
├── summary_baseline.json             # Accuracy: X%, taxonomy breakdown
├── summary_fp8.json
└── summary_int8_per_token_head.json
```

Each CSV has:
- Question
- Ground truth
- Model's reasoning (chain-of-thought)
- Model's answer
- Whether it's correct
- Taxonomy classification (if OpenRouter enabled, else "SKIPPED")

---

## Next: Push to GitHub

```bash
bash PUSH_TO_GITHUB.sh
```

Creates branch `int8-per-token-head-experiment` on your vlm repo.

Then on GitHub:
- Create PR or merge to main
- Share results in the PR

---

**Ready?**

1. Spin up RunPod (A100 SXM: $1.59/hr)
2. Run: `bash runpod_setup.sh`
3. Run: `python3 run_int8_per_token_head_experiment.py`
4. Push: `bash PUSH_TO_GITHUB.sh`

🚀
