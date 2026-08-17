# Deploy to HuggingFace Spaces - Gradio (Free)

## Step 1: Create Gradio Space

1. Go to https://huggingface.co/new-space
2. Fill in:
   - Space name: `llm-gateway`
   - License: Apache 2.0
   - **SDK: Gradio** (not Docker!)
   - Visibility: Public
3. Click "Create Space"

## Step 2: Upload Files

Click "Files" → "Upload":
1. `app.py`
2. `requirements.txt`
3. `metrics.db`

That's it! HF will auto-detect `app.py` as the Gradio app.

## Step 3: Wait for Build

Build takes 1-2 minutes (much faster than Docker).

Check progress in "Logs" tab.

## Step 4: Access

Your dashboard is live at:
```
https://huggingface.co/spaces/[your-username]/llm-gateway
```

That's all you need!

---

## Features

- Real-time metrics display
- Routing accuracy charts
- Model confidence by tier
- Cost tracking
- Last updated timestamp
- Fully responsive

## Update Metrics

Replace `metrics.db` with new load test results:
```bash
python scripts/load_test.py 500
```

Upload updated `metrics.db` to Space → Files.

---

Done! Production dashboard deployed for free.
