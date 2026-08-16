# OpenRouter Setup Guide (5 minutes)

## Why OpenRouter is Required

Your research question is: **"Does int8_per_token_head cause failure mode shifts like NF4 does?"**

To answer this, you need to know:
- ✅ Accuracy numbers (baseline, fp8, int8)
- ✅ **Shortcut Collapse rates** (baseline vs int8)
- ✅ Other failure mode distributions

The LLM-as-judge (via OpenRouter) classifies each output into one of 6 categories:
- NO_FAILURE
- HOLLOW_CONVERGENCE
- **SHORTCUT_COLLAPSE** ← Key metric
- PREMISE_HIJACKING
- OVERCOUNTING
- CONFIDENCE_SNOWBALLING

Without this, you just have raw accuracy numbers and can't answer your core question.

---

## Step 1: Sign Up (2 minutes)

1. Go to: https://openrouter.ai
2. Click "Sign Up"
3. Use email or GitHub login
4. Verify email

**That's it!** Free account ready.

---

## Step 2: Get API Key (1 minute)

1. After login, go to: https://openrouter.ai/settings/keys
2. Click "Create Key" or view default key
3. Copy the key (starts with `sk-`)
4. Save it somewhere safe

**Example key format:** `sk-or-v1-abcdef123456789...`

---

## Step 3: Set Environment Variable (1 minute)

In your RunPod terminal:

```bash
export OPENROUTER_KEY='sk-or-v1-your-actual-key-here'
```

**Verify it's set:**
```bash
echo $OPENROUTER_KEY
```

Should output your key (or empty if not set).

---

## Step 4: Run Experiment

```bash
python3 run_int8_per_token_head_experiment.py
```

The script will:
1. Run inference 3 times (baseline, fp8, int8)
2. For each output, call OpenRouter API
3. LLM judge returns category (e.g., "SHORTCUT_COLLAPSE")
4. Save everything to CSV with taxonomy labels

---

## Cost Breakdown

### What you're charged for:
- OpenRouter free tier has generous limits (~$5-10/month)
- This experiment: ~100 API calls (one per sample)
- Cost: **~$5-10 total**

### Why it's cheap:
- Using free-tier models (Llama 3.3 70B, Gemma, etc.)
- Not training, just classification (small prompts)
- One classification per sample (~100 samples)

### Example pricing:
- Llama 3.3 70B: ~$0.05-0.10 per classification
- 100 samples × $0.05 = **$5 total**

---

## Verification

After setting `OPENROUTER_KEY`, verify it works:

```bash
python3 verify_setup.py
```

Output should show:
```
✓ OPENROUTER_KEY       set (length: 42)
```

If it shows:
```
✗ OPENROUTER_KEY       NOT set — REQUIRED
```

Then your key isn't in the environment. Try:
```bash
echo $OPENROUTER_KEY
```

If empty, set it again:
```bash
export OPENROUTER_KEY='sk-...'
```

---

## What Happens During Inference

For each of the 100 samples, the script:

1. **Runs inference** (Qwen generates reasoning + answer)
2. **Calls OpenRouter** with:
   - Question
   - Ground truth answer
   - Model's reasoning (first 2000 chars)
   - Model's answer

3. **LLM judge returns:**
   - Category: e.g., "SHORTCUT_COLLAPSE"
   - Justification: e.g., "Model skipped necessary steps in line 3"

4. **Saves to CSV:**
   ```
   id,question,cot_chain,model_answer,correct,taxonomy_category,justification
   ```

---

## Example Output

After 10-12 hour run, you'll have:

```
results/
├── results_baseline.csv
│   └── Columns: id, question, cot_chain, model_answer, correct, 
│               taxonomy_category, justification
├── results_fp8.csv
├── results_int8_per_token_head.csv
└── summary_*.json
```

**Sample row:**
```json
{
  "id": "gsm8k_042",
  "question": "James runs 3 sprints 3x/week. Each sprint is 60m. How many meters/week?",
  "cot_chain": "Let me think...\n3 sprints × 3 times = 9 sprints total...",
  "model_answer": "540",
  "correct": true,
  "taxonomy_category": "NO_FAILURE",
  "justification": "Reasoning is sound and complete"
}
```

---

## Troubleshooting

### "OPENROUTER_KEY not set"

**Problem:** Script exits with error about missing key

**Fix:**
```bash
# Check if it's set
echo $OPENROUTER_KEY

# If empty, set it
export OPENROUTER_KEY='sk-...'

# Run again
python3 run_int8_per_token_head_experiment.py
```

### "API call failed" / "rate limit"

**Problem:** OpenRouter API is slow or hitting limits

**Why:** Free tier has rate limits. Just retry.

**Fix:**
The script has built-in retries (3 attempts per sample). If it still fails, wait a minute and run again. It checkpoints after each sample, so you won't lose progress.

### "Invalid API key"

**Problem:** Script says key is invalid

**Fix:**
1. Verify key is correct: `echo $OPENROUTER_KEY`
2. Check OpenRouter website: key still active?
3. Try creating a new key at: https://openrouter.ai/settings/keys

### "Want to skip classification?"

**Problem:** You only want raw outputs, no LLM judge

**Solution:** Remove or comment out the key before running
```bash
unset OPENROUTER_KEY
python3 run_int8_per_token_head_experiment.py
```
Script will error and tell you to set key (by design, since you need it for your research question).

---

## That's It!

You now have:
- ✅ OpenRouter account
- ✅ API key
- ✅ Know how to set it
- ✅ Ready to run experiment

**Next:** Follow the main quickstart:
```bash
bash runpod_setup.sh
export OPENROUTER_KEY='sk-...'
python3 run_int8_per_token_head_experiment.py
```

---

## Questions?

- **OpenRouter API docs:** https://openrouter.ai/docs
- **Free tier limits:** https://openrouter.ai/docs/limits
- **Models available:** https://openrouter.ai/docs/models

Good luck! 🚀
