# Recovery Road — Python ML Service Setup Guide

## Overview

This guide covers setting up the Python ML microservice on **Windows** with Python 3.11.

**Target Environment:**
- **OS**: Windows 10/11
- **Python**: 3.11.x (preferred), 3.10.x or 3.12.x (compatible)
- **Architecture**: 64-bit (required; 32-bit will fail with scikit-learn)
- **Inference**: CPU-first; optional GPU support via CUDA

## Quick Start (5 minutes)

### 1. Verify Python Installation

```powershell
# Check Python version (must be 3.10+)
python --version

# Check architecture (must show 64-bit)
python -c "import struct; print('64-bit' if struct.calcsize('P') == 8 else '32-bit')"
```

**Expected Output:**
```
Python 3.11.x
64-bit
```

### 2. Create Virtual Environment

```powershell
# Navigate to workspace
cd C:\Users\DELL\Desktop\Recovery_Road-irfanswork

# Create venv
python -m venv .venv

# Activate venv (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Or for Command Prompt (cmd):
.venv\Scripts\activate.bat
```

**Note for PowerShell users:** If you get an execution policy error, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### 3. Upgrade pip, setuptools, wheel

```powershell
python -m pip install --upgrade pip setuptools wheel
```

**Expected:** pip 24+, setuptools 75+, wheel 0.45+

### 4. Install Dependencies

#### Core ML Service (scikit-learn, pandas, numpy)
```powershell
pip install -r backend/ml_service/requirements.txt
```

**Installation time:** ~2-5 minutes (numpy + scikit-learn build from source on first install)

**Note on Windows:**
- NumPy and SciPy may take time to compile on first install
- If build fails, ensure you have Visual C++ Build Tools installed
- Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

#### (Optional) Emotion Service (DeepFace, TensorFlow)
```powershell
pip install -r backend/emotion_service/requirements.txt
```

**Installation time:** ~5-10 minutes (TensorFlow is large)

#### (Optional) Development Tools
```powershell
pip install -r backend/ml_service/requirements-dev.txt
```

### 5. Verify Installation

```powershell
# Check environment health
python -m ml_service.health_check

# Expected output:
# ✓ Python 3.11.x supported
# ✓ numpy 1.26.4 (required)
# ✓ scipy 1.14.1 (required)
# ✓ scikit-learn 1.5.1 (required)
# ✓ ... etc
# ✓ All systems go! ML service is ready.
```

### 6. Train Models (First Time Only)

```powershell
# From workspace root
python backend/ml_service/ml_models.py
```

**Expected output:**
- Models trained on shared datasets
- Accuracy metrics displayed
- Model files written to `backend/ml_service/models/`

### 7. Start ML Service

```powershell
# From workspace root
python backend/ml_service/app.py
```

**Expected output:**
```
============================================================
  Recovery Road — Python ML Service
============================================================
INFO: Python 3.11.x is supported.
    Recommended: Python 3.11
[OK] Models ready:
   Text Risk   : TF-IDF + Logistic Regression -- 100% acc
   Emotion     : TF-IDF + Logistic Regression -- 95.9% acc
   Risk Feature: LightGBM -- 85.6% acc

 * Running on http://127.0.0.1:5001
```

## Dependency Breakdown

### Core ML Dependencies

| Package | Version | Purpose | Required | Windows Notes |
|---------|---------|---------|----------|---------------|
| **numpy** | 1.26.4 | Numerical computing | ✓ Yes | May require MSVC build tools |
| **scipy** | 1.14.1 | Scientific computing | ✓ Yes | Dependency of scikit-learn |
| **scikit-learn** | 1.5.1 | ML algorithms | ✓ Yes | Requires 64-bit Python |
| **pandas** | 2.2.2 | Data manipulation | ✓ Yes | — |
| **joblib** | 1.4.2 | Model serialization | ✓ Yes | — |

### Optional ML Enhancements

| Package | Version | Purpose | Optional | Notes |
|---------|---------|---------|----------|-------|
| **xgboost** | 2.1.1 | Gradient boosting | ✓ Yes | Falls back to sklearn GradientBoosting if missing |
| **lightgbm** | 4.4.0 | Lightweight boosting | ✓ Yes | Falls back to XGBoost if missing |
| **transformers** | 4.40.2 | Sentence embeddings | ✓ Yes | Optional benchmark only |
| **sentence-transformers** | 2.7.0 | Sentence embeddings | ✓ Yes | Requires transformers |
| **torch** | 2.3.1 | PyTorch (CPU) | ✓ Yes | Only needed for transformers |

### Emotion Service Dependencies

| Package | Version | Purpose | Platform |
|---------|---------|---------|----------|
| **fastapi** | 0.115.0 | Async web framework | Cross-platform |
| **uvicorn** | 0.30.0 | ASGI server | Cross-platform |
| **opencv-python-headless** | 4.10.0.84 | Computer vision (headless) | Windows-compatible |
| **tensorflow** | 2.16.1 | Neural networks | CPU or GPU |
| **deepface** | 0.0.93 | Face emotion detection | Windows-compatible |

## Troubleshooting

### Issue: "ERROR: Could not find a version..."

**Cause:** Package version not available for your Python version

**Solution:**
```powershell
# Check available versions
pip index versions scikit-learn

# Or upgrade pip first
python -m pip install --upgrade pip
```

### Issue: "Microsoft Visual C++ is required"

**Cause:** NumPy/SciPy compilation needs MSVC

**Solution:**
1. Download Visual C++ Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install: "Desktop development with C++"
3. Retry: `pip install scikit-learn`

### Issue: "No module named 'sklearn'"

**Cause:** Dependencies not installed or installed in wrong environment

**Solution:**
```powershell
# Verify venv is activated (should show (.venv) in prompt)
.venv\Scripts\Activate.ps1

# Reinstall
pip install -r backend/ml_service/requirements.txt

# Verify
python -c "import sklearn; print(sklearn.__version__)"
```

### Issue: Models take too long to train

**Cause:** CPU-bound operations on slow hardware

**Solution:**
- Models train once and persist to disk
- Subsequent startups use cached models (< 1 second)
- For GPU acceleration, install CUDA toolkit and torch[cuda]

### Issue: "RuntimeError: mkl-service + Intel(R) MKL..."

**Cause:** NumPy MKL library conflict on Windows

**Solution:**
```powershell
pip install nomkl
conda remove mkl (if using conda)
```

## Environment Variables

Create `.env` file in `backend/ml_service/`:

```env
# Enable optional features
ENABLE_TRANSFORMER=false          # Set to 'true' to use SentenceTransformer
TRANSFORMER_MODEL=all-MiniLM-L6-v2

# Inference settings
MAX_TEXT_LENGTH=1000
RISK_HIGH_THRESHOLD=0.7
RISK_UNCERTAIN_THRESHOLD=0.5
EMOTION_UNCERTAIN_THRESHOLD=0.45

# Logging
LOG_LEVEL=INFO
```

## Memory & Performance

### Memory Footprint

| Component | Memory Usage | Notes |
|-----------|--------------|-------|
| NumPy arrays (typical) | 50-100 MB | Runtime data |
| Scikit-learn models | 20-50 MB | Loaded into memory |
| TensorFlow (optional) | 200-500 MB | Only if transformers enabled |
| PyTorch (optional) | 150-400 MB | Only if transformers enabled |
| **Total (core ML)** | **~150 MB** | Typical setup |
| **Total (with transformers)** | **~700 MB** | Optional features |

### Inference Latency

| Task | Latency | Notes |
|------|---------|-------|
| Text risk classification | 5-15 ms | TF-IDF + LogRegression |
| Emotion classification | 5-15 ms | TF-IDF + LogRegression |
| Risk feature prediction | 2-5 ms | LightGBM inference |
| SentenceTransformer (optional) | 100-200 ms | Requires GPU for speed |

## CPU-First Inference vs. GPU

### CPU (Default, No Setup Required)
```python
# Already configured; no action needed
import torch
# CPU is default
torch.device('cpu')
```

### GPU (Optional, Requires CUDA)
```powershell
# 1. Install CUDA Toolkit 12.x from NVIDIA
# 2. Reinstall PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 3. Verify
python -c "import torch; print(f'GPU available: {torch.cuda.is_available()}')"
```

## Health Check

Run anytime to verify environment:

```powershell
python -m ml_service.health_check
```

**Output includes:**
- Python version ✓
- Core dependency versions ✓
- Optional dependency status ✓
- Model file locations ✓
- Inference capability test ✓
- Sample predictions ✓

## Python Version Support Matrix

| Python Version | Status | Notes |
|---|---|---|
| 3.9 | ❌ Unsupported | Too old |
| 3.10 | ✓ Supported | Compatible |
| 3.11 | ✅ **Recommended** | Best tested |
| 3.12 | ✓ Supported | Compatible |
| 3.13 | ⚠️ Experimental | May have issues |
| 3.14+ | ❌ Not tested | Avoid |

## Uninstall / Clean Environment

```powershell
# Deactivate venv
deactivate

# Remove venv
Remove-Item -Recurse .venv

# Verify removal
.venv\Scripts\python --version  # Should fail
```

## Next Steps

1. ✓ Install dependencies (above)
2. ✓ Run health check
3. ✓ Train models
4. ✓ Start ML service
5. → Backend Node.js will call ML service at `http://localhost:5001`

## Support

- **Setup Issues:** Check `python -m ml_service.health_check` output
- **Import Errors:** Verify venv activation and pip install output
- **Model Training:** See `backend/ml_service/ml_models.py` for algorithm details
- **Inference Problems:** Check `backend/ml_service/training_data.py` for dataset shape

---

**Last Updated:** May 2026  
**For:** Recovery Road Project  
**Platform:** Windows 10/11, Python 3.11.x
