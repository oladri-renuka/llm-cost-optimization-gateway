# Deploy to Hugging Face Spaces - Step-by-Step Guide

## Prerequisites

- Hugging Face account (free at https://huggingface.co)
- `metrics.db` file with load test data (already included)
- Git (optional, for easier management)

---

## Method 1: Web Upload (Easiest - 5 minutes)

### Step 1: Create a New Space

1. Go to https://huggingface.co/new-space
2. Fill in the form:
   - **Space name**: `llm-gateway-dashboard`
   - **License**: Apache 2.0
   - **Space SDK**: Gradio
   - **Visibility**: Public
3. Click "Create Space"

### Step 2: Upload Files

The Space will open with an empty editor. Upload these files:

1. **app.py** (from this repo)
2. **requirements.txt** (from this repo)
3. **metrics.db** (from this repo)

Click the "Files" button → "Upload" → select all three files

### Step 3: Wait for Build

The Space will automatically:
- Detect `app.py` as the Gradio app
- Install dependencies from `requirements.txt`
- Load the dashboard

Build time: ~2-3 minutes

### Step 4: Done! 🎉

Your dashboard is live at:
```
https://huggingface.co/spaces/[your-username]/llm-gateway-dashboard
```

---

## Method 2: Git (Recommended for Teams)

### Step 1: Create Space on HF

Same as Method 1, Step 1-2

### Step 2: Clone Space Repository

```bash
git clone https://huggingface.co/spaces/[your-username]/llm-gateway-dashboard
cd llm-gateway-dashboard
```

### Step 3: Add Files

```bash
# Copy from main repo
cp /path/to/main-repo/app.py .
cp /path/to/main-repo/requirements.txt .
cp /path/to/main-repo/metrics.db .
```

### Step 4: Push to HF

```bash
git add .
git commit -m "Initial dashboard deployment"
git push
```

HF will automatically rebuild and deploy.

---

## Verify Deployment

Once deployed, you should see:

- ✅ **Green status banner** (100% success rate)
- ✅ **Money Saved card** showing $0.27 (36.9%)
- ✅ **500 total requests** processed
- ✅ **Charts rendering** correctly
- ✅ **No errors** in the browser console

---

## Updating Metrics

### Fresh Load Test Data

To update with new load test results:

```bash
# From main repo, run new load test
python scripts/load_test.py 500

# Copy metrics.db to Space
cp metrics.db /path/to/hf-space/

# If using git, commit and push
cd /path/to/hf-space
git add metrics.db
git commit -m "Update metrics with new load test"
git push
```

The dashboard will automatically read the new data on refresh.

---

## Customization

### Change Colors

Edit `COLORS` dict in `app.py`:

```python
COLORS = {
    "primary": "#2563EB",      # Blue
    "success": "#10B981",      # Green
    "warning": "#F59E0B",      # Yellow
    "danger": "#EF4444",       # Red
    # ... etc
}
```

### Change Title/Description

```python
gr.Markdown("# 🚀 My Custom Gateway")
gr.Markdown("Your custom description here")
```

### Add More Metrics

Extend the charts by modifying `get_routing_accuracy_chart()` or `get_quality_by_tier_chart()`.

### Deploy & Test

Every git push triggers an automatic rebuild. Changes live within 2-3 minutes.

---

## Troubleshooting

### "metrics.db not found"

Make sure `metrics.db` is uploaded to the Space files section.

**Solution:**
1. Go to Space "Files" tab
2. Click "Upload"
3. Select `metrics.db` from your computer

### "Python dependency not found"

Make sure `requirements.txt` includes all dependencies.

**Solution:**
```bash
# Add missing dependency
echo "missing-package>=1.0.0" >> requirements.txt
git add requirements.txt
git commit -m "Add missing dependency"
git push
```

### "Charts not rendering"

Ensure Plotly is installed:

```bash
pip install plotly>=5.17.0
```

---

## Performance Notes

- **Load time**: <2 seconds (all local data)
- **Database queries**: <500ms for 500 requests
- **Chart rendering**: <1 second
- **No API calls**: All data self-contained

---

## Privacy & Security

✅ **Data stays in your Space** — no external API calls  
✅ **Open source code** — full transparency  
✅ **No authentication required** — public demo  
✅ **Metrics only** — no sensitive data  

---

## Next Steps

1. **Deploy now** using Method 1 or 2
2. **Share the Space URL** with your team
3. **Update metrics** from your production load tests
4. **Monitor performance** in real-time

---

## Support & Questions

For issues:
- Check the HF Spaces documentation: https://huggingface.co/docs/hub/spaces
- Review the main gateway README
- Check the DESIGN.md for architecture details

---

**Ready to deploy?**

👉 Go to https://huggingface.co/new-space and create your space!

**Questions?** Open an issue on the main repository.
