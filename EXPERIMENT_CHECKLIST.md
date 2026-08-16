# Experiment Checklist: int8_per_token_head KV Cache Quantization

## Pre-Experiment

### Infrastructure
- [ ] RunPod instance provisioned and running
  - [ ] GPU: A100 or H100 (40GB+ VRAM)
  - [ ] SSH access working
  - [ ] Instance URL/IP noted: ________________

### Code & Setup
- [ ] All scripts downloaded/available:
  - [ ] `runpod_setup.sh`
  - [ ] `verify_setup.py`
  - [ ] `run_int8_per_token_head_experiment.py`
  - [ ] `analyze_int8_results.py`
  - [ ] `INT8_EXPERIMENT_README.md`
  - [ ] `QUICKSTART.md`

- [ ] Run setup script: `bash runpod_setup.sh`
  - [ ] Cloned repos (silent-failures, early_detection)
  - [ ] Virtual environment created
  - [ ] vLLM installed
  - [ ] All dependencies installed

### API Keys & Environment
- [ ] OpenRouter API key obtained
  - [ ] URL: https://openrouter.ai
  - [ ] Key: `sk-...` (first 10 chars: __________)

- [ ] HuggingFace token obtained
  - [ ] URL: https://huggingface.co/settings/tokens
  - [ ] Token: `hf_...` (first 10 chars: __________)

- [ ] Environment variables set:
  ```bash
  export OPENROUTER_KEY='sk-...'
  export HF_TOKEN='hf_...'
  export WORK_DIR='/workspace/int8_per_token_head_experiment'
  ```

### Verification
- [ ] Run `python3 verify_setup.py`
  - [ ] All packages installed ✓
  - [ ] CUDA/GPU detected ✓
  - [ ] vLLM version OK ✓
  - [ ] int8_per_token_head support verified ✓
  - [ ] Environment variables set ✓

---

## During Experiment

### Main Run
- [ ] Start time: ____________ (YYYY-MM-DD HH:MM UTC)
- [ ] GPU instance confirmed: `nvidia-smi` shows A100/H100
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Run main experiment:
  ```bash
  python3 run_int8_per_token_head_experiment.py
  ```

### Monitoring
- [ ] Check GPU memory usage every hour:
  ```bash
  # In another terminal:
  watch -n 10 nvidia-smi
  ```

- [ ] Monitor progress (expected order):
  1. Load AIME 2025 (30 questions)
  2. Load GSM8K (~70 questions)
  3. **Baseline run** (~2h total):
     - Load model in FP32
     - Inference
     - Taxonomy classification (1-2h)
  4. **FP8 run** (~1.5h)
  5. **INT8 run** (~1.5h)
  6. Total: 8-12 hours

- [ ] Check `results/` directory periodically:
  ```bash
  ls -lh results/
  tail -20 results/results_baseline.csv  # Check if running
  ```

### Logs to Save
- [ ] Copy console output:
  ```bash
  python3 run_int8_per_token_head_experiment.py 2>&1 | tee experiment_run.log
  ```

- [ ] Capture final screen output with timestamps

---

## Post-Experiment

### Results Verification
- [ ] Check output files exist:
  ```bash
  ls -lh results/
  ```
  Should have:
  - [ ] `results_baseline.csv` (~100KB, 100 rows)
  - [ ] `results_fp8.csv`
  - [ ] `results_int8_per_token_head.csv`
  - [ ] `summary_baseline.json`
  - [ ] `summary_fp8.json`
  - [ ] `summary_int8_per_token_head.json`

- [ ] Spot-check CSV format:
  ```bash
  head results/results_baseline.csv
  ```
  Should have columns: id, benchmark, question, ground_truth, cot_chain, model_answer, correct, config, taxonomy_category

- [ ] Check for errors in files:
  ```bash
  grep -i error results/*.csv || echo "No errors found"
  ```

### Analysis
- [ ] Run analysis: `python3 analyze_int8_results.py`
- [ ] Capture output:
  ```bash
  python3 analyze_int8_results.py 2>&1 | tee analysis_report.txt
  ```

- [ ] Review key metrics from output:
  - [ ] Baseline accuracy: ______%
  - [ ] FP8 accuracy: ______%
  - [ ] INT8 accuracy: ______%
  - [ ] Accuracy delta (int8 vs baseline): ______pp

- [ ] Review Shortcut Collapse rates:
  - [ ] Baseline SC rate: ______%
  - [ ] FP8 SC rate: ______%
  - [ ] INT8 SC rate: ______%
  - [ ] SC shift (int8 vs baseline): ______pp

### Spot Checking
- [ ] Manually review 5-10 samples classified as Shortcut Collapse:
  ```python
  import pandas as pd
  df = pd.read_csv('results/results_int8_per_token_head.csv')
  shortcut_samples = df[df['taxonomy_category'] == 'SHORTCUT_COLLAPSE'].head(5)
  for idx, row in shortcut_samples.iterrows():
      print(f"ID: {row['id']}")
      print(f"Q: {row['question']}")
      print(f"A: {row['model_answer']}")
      print(f"Reasoning:\n{row['cot_chain'][:500]}...\n")
  ```

- [ ] Verify classifications make sense:
  - [ ] Sample 1: Classification appropriate? Y/N
  - [ ] Sample 2: Classification appropriate? Y/N
  - [ ] Sample 3: Classification appropriate? Y/N
  - [ ] Sample 4: Classification appropriate? Y/N
  - [ ] Sample 5: Classification appropriate? Y/N

### Data Cleanup
- [ ] Archive results:
  ```bash
  tar -czf int8_results_YYYY-MM-DD.tar.gz results/
  ```

- [ ] Back up to external storage/GitHub

---

## Analysis & Findings

### Key Results
- [ ] Complete table: Accuracy by configuration
  | Config | Accuracy | Baseline Delta |
  |--------|----------|----------------|
  | Baseline | ___% | — |
  | FP8 | ___% | ___pp |
  | INT8 | ___% | ___pp |

- [ ] Shortcut Collapse shift:
  | Config | SC Rate | Baseline Delta |
  |--------|---------|----------------|
  | Baseline | ___% | — |
  | FP8 | ___% | ___pp |
  | INT8 | ___% | ___pp |

### Hypothesis Assessment
- [ ] Did int8_per_token_head cause Shortcut Collapse shift?
  - [ ] Yes (>10pp increase) → Similar to weight quantization effects
  - [ ] Moderate (~5-10pp) → Subtle effect
  - [ ] No (<5pp) → KV cache quantization different from weight quantization
  - [ ] Negative → Improved reasoning?

- [ ] Is the shift similar to paper baseline (28pp for 3B models)?
  - [ ] Yes, comparable effect
  - [ ] No, much smaller
  - [ ] No, in different direction

### Failure Mode Patterns
- [ ] Did failure modes shift uniformly across categories?
  - [ ] Only Shortcut Collapse increased
  - [ ] Multiple categories shifted
  - [ ] Hollow Convergence changed?

- [ ] Did AIME vs GSM8K respond differently?
  - [ ] AIME: accuracy delta ___pp, SC shift ___pp
  - [ ] GSM8K: accuracy delta ___pp, SC shift ___pp
  - [ ] Difference significant? Y/N

### Observations
- [ ] Notable findings:
  1. ________________________
  2. ________________________
  3. ________________________

---

## Publication/Sharing Checklist

### Before Sharing Results
- [ ] Verify no sensitive data in CSV files
- [ ] Remove API keys from logs
- [ ] Check for GPU serial numbers or IP addresses

### Deliverables
- [ ] Generate final report:
  - [ ] Copy `analysis_report.txt`
  - [ ] Add findings section
  - [ ] Include raw CSV summaries

- [ ] Create supplementary materials:
  - [ ] Table of accuracy metrics
  - [ ] Figure: Shortcut Collapse shift across configs
  - [ ] Sample transcripts (5-10 representative Shortcut Collapse examples)

- [ ] Prepare for publication/sharing:
  - [ ] GitHub issue or paper section
  - [ ] Blog post
  - [ ] Dataset on HuggingFace (optional)

### Final Files
- [ ] `experiment_run.log` (full console output)
- [ ] `analysis_report.txt` (full analysis)
- [ ] `results_*.csv` (raw outputs, 3 files)
- [ ] `summary_*.json` (accuracy + taxonomy breakdown, 3 files)
- [ ] `FINDINGS.md` (executive summary)

---

## Troubleshooting Log

### Issue #1
- **Problem:** ________________________
- **Time:** ____________
- **Solution:** ________________________
- **Status:** ☐ Resolved ☐ Workaround ☐ Blocking

### Issue #2
- **Problem:** ________________________
- **Time:** ____________
- **Solution:** ________________________
- **Status:** ☐ Resolved ☐ Workaround ☐ Blocking

---

## Final Status

- [ ] Experiment completed successfully
- [ ] All results saved and verified
- [ ] Analysis complete
- [ ] Key findings documented
- [ ] Ready for paper/publication
- [ ] Shared with collaborators

**Experiment end time:** ____________ (YYYY-MM-DD HH:MM UTC)  
**Total duration:** ________ hours

---

## Next Steps

After this experiment completes:

1. **Compare to paper:**
   - [ ] How do KV cache quantization effects compare to weight quantization?
   - [ ] Write up comparison

2. **Extend scope:**
   - [ ] Test more models (Llama, Mistral)
   - [ ] Test more quantization modes (fp8_per_token_head, int4)
   - [ ] Larger test sets

3. **Statistical rigor:**
   - [ ] Chi-squared test for Shortcut Collapse rates
   - [ ] Confidence intervals
   - [ ] Power analysis for significance

4. **Publication:**
   - [ ] Write paper/blog post
   - [ ] Submit to venue
   - [ ] Share code on GitHub

---

**Good luck with the experiment!** 🚀

Last updated: 2026-08-15
