# Deploy to HuggingFace Spaces

## Step 1: Create Docker Space

1. Go to https://huggingface.co/new-space
2. Fill in:
   - Space name: `llm-gateway`
   - License: Apache 2.0
   - **SDK: Docker** (important!)
   - Visibility: Public
3. Click "Create Space"

## Step 2: Upload Files

After space is created:
1. Click "Files" tab
2. Click "Upload" button
3. Upload these files from the repo:
   - `Dockerfile`
   - `app.py`
   - `requirements.txt`
   - `metrics.db`
   - Entire `src/` folder
   - Entire `config/` folder

Or clone the repo:
```bash
git clone https://huggingface.co/spaces/[your-username]/llm-gateway
cd llm-gateway
cp -r /path/to/llm-cost-optimization-gateway/* .
git add .
git commit -m "Deploy gateway"
git push
```

## Step 3: Set Environment Variable

1. Go to Space "Settings"
2. Click "Repository secrets"
3. Add:
   - Key: `OPENROUTER_API_KEY`
   - Value: Your OpenRouter API key (from https://openrouter.ai)

## Step 4: Wait for Build

HF Spaces will automatically build the Docker image. This takes 3-5 minutes.

Check build progress in the "Logs" tab.

## Step 5: Access

Once deployed:
- **Dashboard**: https://huggingface.co/spaces/[your-username]/llm-gateway
- **API**: Same URL with `:8000` port
- **Health**: https://huggingface.co/spaces/[your-username]/llm-gateway:8000/health

## Test It

```bash
# Test API health
curl https://huggingface.co/spaces/[your-username]/llm-gateway:8000/health

# Test dashboard
# Visit: https://huggingface.co/spaces/[your-username]/llm-gateway
```

## Environment Variables

Only required:
- `OPENROUTER_API_KEY` - Your API key from OpenRouter

Optional (have defaults):
- `REDIS_URL` - Auto-configured
- `LOG_LEVEL` - Default: INFO
- `CACHE_TTL` - Default: 3600

---

That's it! Your production gateway is live.
