#!/bin/bash
# Push int8_per_token_head experiment to GitHub

set -e

REPO_URL="https://github.com/oladri-renuka/vlm"
BRANCH="int8-per-token-head-experiment"

echo "========================================"
echo "Pushing int8_per_token_head experiment"
echo "========================================"
echo ""

# Make sure we're in the right directory
if [ ! -f "run_int8_per_token_head_experiment.py" ]; then
    echo "✗ Error: Not in vlm directory"
    echo "  Run from: /Users/renukaoladri/Claude/Projects/open_source/vlm"
    exit 1
fi

echo "1. Checking git status..."
git status

echo ""
echo "2. Creating/switching to branch: $BRANCH"
git checkout -b $BRANCH 2>/dev/null || git checkout $BRANCH

echo ""
echo "3. Adding files..."
git add \
    runpod_setup.sh \
    verify_setup.py \
    run_int8_per_token_head_experiment.py \
    analyze_int8_results.py \
    INT8_EXPERIMENT_README.md \
    QUICKSTART.md \
    EXPERIMENT_CHECKLIST.md

echo ""
echo "4. Committing..."
git commit -m "Add int8_per_token_head KV cache quantization experiment

- Main experiment script with vLLM + Qwen2.5 7B
- Tests 3 configs: baseline, fp8, int8_per_token_head
- Uses 100 questions (AIME 2025 + GSM8K)
- Optional taxonomy classification (OpenRouter)
- Complete setup, verification, and analysis scripts
- Comprehensive documentation and checklists"

echo ""
echo "5. Pushing to $REPO_URL..."
git push -u origin $BRANCH

echo ""
echo "========================================"
echo "✓ Push complete!"
echo "========================================"
echo ""
echo "Next steps on GitHub:"
echo "1. Create Pull Request from $BRANCH → main"
echo "2. Or merge directly: git merge $BRANCH"
echo ""
echo "Files pushed:"
echo "  ✓ runpod_setup.sh"
echo "  ✓ verify_setup.py"
echo "  ✓ run_int8_per_token_head_experiment.py"
echo "  ✓ analyze_int8_results.py"
echo "  ✓ INT8_EXPERIMENT_README.md"
echo "  ✓ QUICKSTART.md"
echo "  ✓ EXPERIMENT_CHECKLIST.md"
