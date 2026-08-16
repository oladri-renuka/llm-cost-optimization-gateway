#!/bin/bash
# RunPod GPU instance setup for int8_per_token_head KV cache quantization experiment

set -e

echo "=========================================="
echo "RunPod Setup: int8_per_token_head Experiment"
echo "=========================================="

# Update system packages
apt-get update && apt-get install -y \
    git \
    curl \
    python3-pip \
    python3-venv

# Create working directory
WORK_DIR="/workspace/int8_per_token_head_experiment"
mkdir -p $WORK_DIR
cd $WORK_DIR

# Clone repos if not already present
if [ ! -d "silent-failures" ]; then
    echo "Cloning silent-failures repo..."
    git clone https://github.com/oladri-renuka/silent-failures.git
fi

if [ ! -d "early_detection" ]; then
    echo "Cloning early_detection repo..."
    git clone https://github.com/oladri-renuka/early_detection.git
fi

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install core dependencies
echo "Installing core dependencies..."
pip install \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 \
    vllm>=0.6.0 \
    transformers>=4.40.0 \
    datasets>=2.18.0 \
    pynvml \
    pandas \
    numpy \
    openai \
    requests \
    tqdm

# Install additional dependencies from silent-failures
if [ -f "silent-failures/requirements.txt" ]; then
    echo "Installing silent-failures requirements..."
    pip install -r silent-failures/requirements.txt 2>/dev/null || echo "Some requirements may have already been installed"
fi

# Create data directories
mkdir -p $WORK_DIR/data
mkdir -p $WORK_DIR/results
mkdir -p $WORK_DIR/figures

# Test vLLM installation and check for int8_per_token_head support
echo ""
echo "=========================================="
echo "Verifying vLLM Installation"
echo "=========================================="
python3 << 'EOF'
import vllm
print(f"vLLM version: {vllm.__version__}")

# Try to import and check KV cache dtype options
from vllm.platforms import get_platform_name
print(f"Platform: {get_platform_name()}")

# List available KV cache dtypes
from vllm.model_executor.layers.quantization.utils import get_kv_cache_dtypes
try:
    dtypes = get_kv_cache_dtypes() if callable(get_kv_cache_dtypes) else None
    print(f"Available KV cache dtypes: {dtypes if dtypes else 'Check vLLM docs for dtype options'}")
except Exception as e:
    print(f"Note: {e}")
    print("Checking vLLM help for KV cache options...")

print("\n✓ vLLM ready!")
EOF

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. ⭐ GET OPENROUTER KEY (REQUIRED - 1 minute):"
echo "   - Sign up: https://openrouter.ai"
echo "   - Copy API key from settings"
echo "   - Set in terminal:"
echo "     export OPENROUTER_KEY='sk-...'"
echo ""
echo "2. Run verification:"
echo "   cd $WORK_DIR"
echo "   source venv/bin/activate"
echo "   python3 verify_setup.py"
echo ""
echo "3. Run the experiment (8-12 hours):"
echo "   python3 run_int8_per_token_head_experiment.py"
echo ""
echo "4. Analyze results (2 minutes):"
echo "   python3 analyze_int8_results.py"
echo ""
echo "To connect from another terminal:"
echo "   cd $WORK_DIR"
echo "   source venv/bin/activate"
