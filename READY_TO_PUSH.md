# Ready to Push — Complete Checklist

## ✅ All Files Ready

### **Core Experiment Scripts**
- ✅ `runpod_setup.sh` — One-time environment setup
- ✅ `verify_setup.py` — Pre-flight verification
- ✅ `run_int8_per_token_head_experiment.py` — **Main experiment**
- ✅ `analyze_int8_results.py` — Analysis & reporting

### **Documentation**
- ✅ `INT8_EXPERIMENT_README.md` — Full detailed guide
- ✅ `QUICKSTART.md` — Quick reference (start here)
- ✅ `SETUP_NOTES.md` — Token/environment clarification
- ✅ `OPENROUTER_SETUP.md` — OpenRouter 5-minute guide
- ✅ `EXPERIMENT_CHECKLIST.md` — Step-by-step checklist
- ✅ `PUSH_TO_GITHUB.sh` — Git push helper

### **Metadata**
- ✅ `READY_TO_PUSH.md` — This file

---

## ✅ Key Updates Made

### **OpenRouter Now Required**
- ✅ `verify_setup.py` — Requires OPENROUTER_KEY
- ✅ `run_int8_per_token_head_experiment.py` — Exits if key not set
- ✅ All docs updated to reflect requirement
- ✅ Clear error messages guide user to openrouter.ai

### **HuggingFace Token Now Optional**
- ✅ Qwen2.5 is public, no auth needed
- ✅ HF_TOKEN only for future gated models
- ✅ Docs clarified

---

## 📋 What User Gets

After complete run:

```
1. Setup (10 min)
   └─ bash runpod_setup.sh
   └─ source venv/bin/activate

2. Verify (2 min)
   └─ python3 verify_setup.py
   └─ export OPENROUTER_KEY='sk-...'

3. Main Experiment (8-12 hours)
   └─ python3 run_int8_per_token_head_experiment.py
   
4. Analysis (2 min)
   └─ python3 analyze_int8_results.py

OUTPUT: results/
├── results_baseline.csv              (100 rows)
├── results_fp8.csv                   (100 rows)
├── results_int8_per_token_head.csv   (100 rows)
└── summary_*.json                    (accuracy + taxonomy breakdown)
```

**Key Findings:**
- Accuracy: baseline vs fp8 vs int8
- **Shortcut Collapse rates** (does int8 shift like NF4?)
- Full taxonomy breakdown
- Raw reasoning traces for spot-checking

---

## 🚀 Quick Start Instructions (for user)

```bash
# 1. Get OpenRouter key (5 min)
# - Sign up: https://openrouter.ai
# - Copy key

# 2. Spin up RunPod (A100 SXM, $1.59/hr)

# 3. Clone and run
git clone https://github.com/oladri-renuka/vlm.git
cd vlm
git checkout int8-per-token-head-experiment

bash runpod_setup.sh
source venv/bin/activate
export OPENROUTER_KEY='sk-...'
python3 verify_setup.py

# 4. Run experiment (grab coffee, 8-12 hours)
python3 run_int8_per_token_head_experiment.py

# 5. Analyze (2 min)
python3 analyze_int8_results.py

# Done! ✅
```

---

## 📊 Experiment Design (Verified)

### **Model**
- ✅ Qwen2.5-7B-Instruct
- ✅ FP16 weights
- ✅ FlashInfer backend (avoids Triton bug)
- ✅ Greedy decoding

### **Test Set**
- ✅ AIME 2025: 30 questions (hardest)
- ✅ GSM8K: ~70 questions (easier)
- ✅ **Total: 100 questions**

### **Configurations**
- ✅ Baseline: auto KV cache (FP32 default)
- ✅ FP8: FP8 KV cache quantization
- ✅ INT8: INT8 per-token-head KV cache (TARGET)

### **Taxonomy (6 categories)**
- ✅ NO_FAILURE — Correct with sound reasoning
- ✅ HOLLOW_CONVERGENCE — Correct but incomplete reasoning
- ✅ PREMISE_HIJACKING — Flawed assumption, correct reasoning from it
- ✅ **SHORTCUT_COLLAPSE** ← KEY METRIC
- ✅ OVERCOUNTING — Correct intermediate, then continues
- ✅ CONFIDENCE_SNOWBALLING — Single error propagates

---

## 💾 Push Command

```bash
cd /Users/renukaoladri/Claude/Projects/open_source/vlm
bash PUSH_TO_GITHUB.sh
```

This will:
1. Create branch: `int8-per-token-head-experiment`
2. Stage all files
3. Commit with descriptive message
4. Push to: `https://github.com/oladri-renuka/vlm`

---

## ✅ Files to Push (10 files)

```
1. runpod_setup.sh
2. verify_setup.py
3. run_int8_per_token_head_experiment.py
4. analyze_int8_results.py
5. INT8_EXPERIMENT_README.md
6. QUICKSTART.md
7. SETUP_NOTES.md
8. OPENROUTER_SETUP.md
9. EXPERIMENT_CHECKLIST.md
10. PUSH_TO_GITHUB.sh
```

---

## 📝 Branch Info

- **Branch name:** `int8-per-token-head-experiment`
- **Base:** main
- **Commits:** 1 (all files in one commit)
- **PR needed?** User decision (can merge directly or create PR)

---

## 🎯 Research Question

**Core hypothesis:** 
"Does INT8 per-token-head KV cache quantization cause a shift in reasoning failure modes similar to NF4 weight quantization?"

**Key metric:** 
Shortcut Collapse rate across baseline → fp8 → int8_per_token_head

**Expected finding:**
- Paper found 28pp Shortcut Collapse shift with NF4 on 3B models
- This experiment will show if KV cache quantization has similar/different effects
- Data will be in `results/summary_*.json` and `analyze_int8_results.py` output

---

## ✅ Ready!

All files are:
- ✅ Properly updated
- ✅ Internally consistent
- ✅ Well-documented
- ✅ Ready to push

**User can now:**
1. Push to GitHub: `bash PUSH_TO_GITHUB.sh`
2. Spin up RunPod
3. Pull code: `git clone` + `git checkout int8-per-token-head-experiment`
4. Get OpenRouter key: 5 minutes
5. Run: `bash runpod_setup.sh` → `python3 run_int8_per_token_head_experiment.py`
6. Analyze: `python3 analyze_int8_results.py`

**Total cost:** ~$25 (RunPod A100 10h + OpenRouter $5-10)

---

## 🚀 Status

**READY FOR PRODUCTION**

All systems go. User can execute immediately upon approval.

---

Last updated: 2026-08-15  
Ready to ship: ✅ YES
