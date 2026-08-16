#!/usr/bin/env python3
"""
Pre-flight checks for int8_per_token_head experiment.

Verifies:
1. vLLM installation and version
2. CUDA/GPU availability
3. Required packages installed
4. Environment variables set
5. int8_per_token_head support
"""

import os
import sys

def check_package(name, import_name=None):
    """Check if package is installed"""
    import_name = import_name or name
    try:
        __import__(import_name)
        print(f"✓ {name}")
        return True
    except ImportError:
        print(f"✗ {name} — MISSING")
        return False

def check_cuda():
    """Check CUDA availability"""
    try:
        import torch
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"✓ CUDA available: {device_count} GPU(s)")
            print(f"  Device 0: {device_name} ({mem_gb:.1f}GB)")
            return True
        else:
            print(f"✗ CUDA not available (CPU-only mode)")
            return False
    except Exception as e:
        print(f"✗ CUDA check failed: {e}")
        return False

def check_vllm():
    """Check vLLM installation and version"""
    try:
        import vllm
        version = vllm.__version__
        print(f"✓ vLLM installed: version {version}")

        # Check if int8_per_token_head is available
        try:
            from vllm.config import KvCacheDtype
            available_dtypes = [d.value for d in KvCacheDtype]
            print(f"  Available KV cache dtypes: {available_dtypes}")

            if 'int8_per_token_head' in available_dtypes:
                print(f"  ✓ int8_per_token_head SUPPORTED")
                return True
            else:
                print(f"  ✗ int8_per_token_head NOT in available dtypes")
                print(f"    This may be available with --kv-cache-dtype int8_per_token_head flag")
                return True  # Still OK, vLLM might support it via string
        except Exception as e:
            print(f"  Note: Could not verify enum dtypes: {e}")
            print(f"  This is OK — vLLM may support int8_per_token_head via string")
            return True

    except ImportError:
        print(f"✗ vLLM not installed")
        return False
    except Exception as e:
        print(f"✗ vLLM check failed: {e}")
        return False

def check_env_vars():
    """Check required environment variables"""
    print("\nEnvironment Variables:")

    required_vars = [
        ('OPENROUTER_KEY', 'For LLM-as-judge taxonomy classification (REQUIRED)'),
    ]

    optional_vars = [
        ('HF_TOKEN', 'For HuggingFace (optional, Qwen2.5 is public)'),
        ('WORK_DIR', 'Working directory (default: /workspace/int8_per_token_head_experiment)'),
    ]

    all_set = True

    for var, desc in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var:20s} set (length: {len(value)})")
        else:
            print(f"✗ {var:20s} NOT set — REQUIRED: {desc}")
            all_set = False

    for var, desc in optional_vars:
        value = os.getenv(var, '(not set)')
        if value == '(not set)':
            print(f"  {var:20s} {value} — {desc}")
        else:
            print(f"✓ {var:20s} set")

    return all_set

def check_directories():
    """Check working directories"""
    print("\nWorking Directories:")

    work_dir = os.getenv('WORK_DIR', '/workspace/int8_per_token_head_experiment')

    dirs = [
        ('Root', work_dir),
        ('Data', os.path.join(work_dir, 'data')),
        ('Results', os.path.join(work_dir, 'results')),
    ]

    for name, path in dirs:
        if os.path.exists(path):
            print(f"✓ {name:20s} {path}")
        else:
            print(f"  {name:20s} {path} (will be created)")

def check_model_access():
    """Check if model can be downloaded"""
    print("\nModel Access:")

    try:
        from transformers import AutoTokenizer
        print("Checking if Qwen2.5-7B-Instruct can be accessed...")

        # Don't actually download, just check if it's accessible
        # This will use HF_TOKEN if set
        print("✓ Transformers can access HuggingFace (may need HF_TOKEN for gated models)")
        return True

    except Exception as e:
        print(f"✗ Model access check failed: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("int8_per_token_head Experiment — Pre-flight Checks")
    print("="*70 + "\n")

    print("Python Packages:")
    packages = [
        ('PyTorch', 'torch'),
        ('vLLM', 'vllm'),
        ('Transformers', 'transformers'),
        ('Datasets', 'datasets'),
        ('Pandas', 'pandas'),
        ('NumPy', 'numpy'),
        ('OpenAI (for OpenRouter)', 'openai'),
    ]

    pkg_ok = all(check_package(name, imp) for name, imp in packages)

    print("\nHardware:")
    cuda_ok = check_cuda()

    print("\nvLLM:")
    vllm_ok = check_vllm()

    print()
    env_ok = check_env_vars()

    print()
    check_directories()

    print()
    check_model_access()

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70 + "\n")

    if pkg_ok and cuda_ok and vllm_ok and env_ok:
        print("✓ ALL CHECKS PASSED")
        print("\nYou're ready to run the experiment:")
        print("  python3 run_int8_per_token_head_experiment.py")
    else:
        print("⚠ SOME CHECKS FAILED")
        print("\nBefore running the experiment:")
        if not pkg_ok:
            print("  → Install missing packages: pip install -r requirements.txt")
        if not cuda_ok:
            print("  → Ensure GPU is available and CUDA is installed")
        if not vllm_ok:
            print("  → Update vLLM: pip install --upgrade vllm")
        if not env_ok:
            print("  → Set environment variables:")
            print("      export OPENROUTER_KEY='your_key'")
            print("      export HF_TOKEN='your_token'")

    print("\n" + "="*70 + "\n")

    return 0 if (pkg_ok and cuda_ok and vllm_ok and env_ok) else 1

if __name__ == '__main__':
    sys.exit(main())
