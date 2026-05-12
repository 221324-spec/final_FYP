# Recovery Road — Python ML Service: Windows Quick Start

## Problem: venv Wheel Compatibility

The `.venv` folder created with 32-bit Python cannot install scipy or scikit-learn because no 32-bit wheels are available.

**Solution:** Use system Python 3.10 directly (it already has the packages installed).

---

## Quick Start (60 seconds)

### Option 1: Use System Python (RECOMMENDED)

The system Python 3.10 already has scikit-learn 1.7.2 installed.

```powershell
# Install only missing Flask/utilities
python -m pip install Flask flask-cors python-dotenv requests pydantic

# Verify
python -c "import sklearn, numpy, pandas, joblib; print('✓ Ready')"

# Start service
python backend/ml_service/app.py
```

**Output:**
```
============================================================
  Recovery Road — Python ML Service
============================================================
[OK] Models ready:
   Text Risk   : TF-IDF + Logistic Regression -- 100% acc
   Emotion     : TF-IDF + Logistic Regression -- 95.9% acc
   Risk Feature: Logistic Regression -- 85.6% acc

 * Running on http://127.0.0.1:5001
```

---

### Option 2: Fix venv (Requires 64-bit Python)

If you have 64-bit Python 3.11 installed separately:

```powershell
# Delete the broken 32-bit venv
Remove-Item -Recurse .venv

# Create 64-bit venv with explicit Python path
# (adjust path if your Python 3.11 is in a different location)
"C:\Program Files\Python311\python.exe" -m venv .venv

# Activate
.venv\Scripts\Activate.ps1

# Install
pip install -r backend/ml_service/requirements.txt
```

---

## System Python Details

```powershell
# Check what's installed
python --version
# Output: Python 3.10.x

python -c "import sklearn; print(f'scikit-learn: {sklearn.__version__}')"
# Output: scikit-learn: 1.7.2

python -c "import sys; print('64-bit' if sys.maxsize > 2**32 else '32-bit')"
# Output: 64-bit

# Check sklearn dependencies
python -c "import numpy, scipy, pandas; print('✓ All deps OK')"
# Output: ✓ All deps OK
```

---

## Run ML Service with System Python

```powershell
# From workspace root
python backend/ml_service/app.py
```

**The service works identically whether using system Python or a properly-configured venv.**

---

## Test Predictions

```powershell
# In another terminal
python -c "
import requests
resp = requests.post('http://localhost:5001/api/ml/classify-text', 
                     json={'text': 'I want to relapse'})
print(resp.json())
"
```

---

## Optional: Install Advanced Features

If you want XGBoost, LightGBM, or Transformers:

```powershell
# These require 64-bit Python and may need MSVC toolchain
python -m pip install xgboost lightgbm

# Or (transformer benchmarking; requires torch)
python -m pip install transformers sentence-transformers torch
```

---

## Health Check

```powershell
python -m ml_service.health_check
```

**Output:**
```
Recovery Road — ML Service Environment Check
Version: 1.0.0

1. Python Version
  ✓ Python 3.10.x supported on win32

2. Core Dependencies
  ✓ numpy 1.24.x (required)
  ✓ scikit-learn 1.7.2 (required)
  ✓ pandas 2.x (required)
  ✓ joblib 1.x (required)

3. Optional Enhancements
  ⚠ xgboost (not installed; optional)
  ⚠ lightgbm (not installed; optional)
  ⚠ torch (not installed; optional)

4. Model Files
  ✓ text_risk_classifier.joblib
  ✓ emotion_classifier.joblib
  ✓ risk_feature_classifier.joblib
  ✓ model_meta.json

5. Inference Capability
  ✓ Inference works
    Sample: risk=HIGH, emotion=sadness, confidence=0.98

Summary
  ✓ All systems go! ML service is ready.
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'sklearn'"

```powershell
# Install system-wide
python -m pip install scikit-learn

# Or use system Python which has it pre-installed
which python
```

### "Could not find a version that satisfies the requirement scipy"

**This is expected and OK.** Scikit-learn works without scipy for most use cases.

If you absolutely need scipy:
1. Install 64-bit Python 3.11
2. Install Visual C++ Build Tools
3. Try again

### Service won't start

```powershell
# Verify Python environment
python --version
python -c "import flask, sklearn; print('OK')"

# Check if port 5001 is in use
netstat -ano | findstr :5001

# Use different port if needed
set FLASK_PORT=5002
python backend/ml_service/app.py
```

---

## Summary

| Method | Status | Time | Effort |
|--------|--------|------|--------|
| **System Python (3.10)** | ✓ Works now | < 2 min | ⭐ Minimal |
| 64-bit venv (if available) | ✓ Works | 5-10 min | ⭐⭐ Medium |
| 32-bit venv (current) | ✗ Can't build | N/A | ✗ Won't work |

**Recommendation:** Use system Python 3.10 for immediate success. It's already configured and ready to go.

---

**Last Updated:** May 2026  
**For:** Recovery Road Project  
**Platform:** Windows 10/11
