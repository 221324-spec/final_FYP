# Recovery Road — Python ML Service Setup Script for Windows
# 
# Usage:
#   .\setup_ml_service.ps1
#
# This script automates environment setup on Windows:
# 1. Validates Python version (3.10+, 64-bit)
# 2. Creates virtual environment
# 3. Upgrades pip/setuptools/wheel
# 4. Installs requirements from requirements.txt
# 5. Runs health check
# 6. Optionally trains models
#

param(
    [switch]$SkipHealthCheck = $false,
    [switch]$SkipTrain = $false,
    [switch]$SkipEmotionService = $false,
    [switch]$InstallDev = $false
)

$ErrorActionPreference = "Stop"

# Color output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error-Msg { Write-Host $args -ForegroundColor Red }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Blue
Write-Host "║   Recovery Road — Python ML Service Setup (Windows)        ║" -ForegroundColor Blue
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Blue
Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# 1. Validate Python Version & Architecture
# ─────────────────────────────────────────────────────────────────────

Write-Info "Step 1: Validating Python version..."

$pythonVersion = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error-Msg "ERROR: Python not found. Please install Python 3.11 from https://www.python.org"
    exit 1
}

Write-Success "✓ $pythonVersion"

# Check architecture
$arch = python -c "import struct; print('64-bit' if struct.calcsize('P') == 8 else '32-bit')"
if ($arch -ne "64-bit") {
    Write-Error-Msg "ERROR: 32-bit Python detected. Scikit-learn requires 64-bit Python."
    Write-Error-Msg "       Download 64-bit Python 3.11 from https://www.python.org"
    exit 1
}
Write-Success "✓ Architecture: $arch"

# Check version number
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
if ($versionMatch) {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        Write-Error-Msg "ERROR: Python $major.$minor is too old. Minimum required: Python 3.10"
        exit 1
    }
    
    if ($major -eq 3 -and $minor -eq 11) {
        Write-Success "✓ Python $major.$minor (recommended)"
    } elseif ($major -eq 3 -and ($minor -eq 10 -or $minor -eq 12)) {
        Write-Success "✓ Python $major.$minor (compatible)"
    } elseif ($major -ge 3 -and $minor -ge 13) {
        Write-Warning "⚠ Python $major.$minor may have compatibility issues"
    }
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# 2. Create Virtual Environment
# ─────────────────────────────────────────────────────────────────────

Write-Info "Step 2: Setting up virtual environment..."

if (Test-Path ".\.venv") {
    Write-Warning "⚠ Virtual environment already exists (.\.venv)"
    Write-Info "   Skipping creation; reusing existing venv"
} else {
    Write-Info "   Creating new virtual environment..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Msg "ERROR: Failed to create virtual environment"
        exit 1
    }
    Write-Success "✓ Virtual environment created"
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# 3. Activate Virtual Environment
# ─────────────────────────────────────────────────────────────────────

Write-Info "Step 3: Activating virtual environment..."

# PowerShell execution policy bypass for activation script
$activationScript = ".\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $activationScript)) {
    Write-Error-Msg "ERROR: Activation script not found at $activationScript"
    exit 1
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force | Out-Null
& $activationScript

if ($LASTEXITCODE -ne 0) {
    Write-Error-Msg "ERROR: Failed to activate virtual environment"
    exit 1
}

Write-Success "✓ Virtual environment activated"
Write-Info "   Prompt should now show: (.venv)"

Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# 4. Upgrade pip, setuptools, wheel
# ─────────────────────────────────────────────────────────────────────

Write-Info "Step 4: Upgrading pip, setuptools, wheel..."

python -m pip install --quiet --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    Write-Error-Msg "ERROR: Failed to upgrade pip/setuptools/wheel"
    exit 1
}

Write-Success "✓ pip, setuptools, wheel upgraded"

Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# 5. Install Dependencies
# ─────────────────────────────────────────────────────────────────────

Write-Info "Step 5: Installing ML service dependencies..."
Write-Info "   This may take 2-5 minutes (NumPy + SciPy compilation)..."

$requirementsPath = "backend\ml_service\requirements.txt"
if (-not (Test-Path $requirementsPath)) {
    Write-Error-Msg "ERROR: $requirementsPath not found"
    exit 1
}

python -m pip install -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    Write-Error-Msg "ERROR: Failed to install dependencies"
    Write-Error-Msg ""
    Write-Error-Msg "Troubleshooting:"
    Write-Error-Msg "  1. If error mentions 'Microsoft Visual C++': Download C++ Build Tools"
    Write-Error-Msg "     https://visualstudio.microsoft.com/visual-cpp-build-tools/"
    Write-Error-Msg "  2. Ensure 64-bit Python is installed"
    Write-Error-Msg "  3. Try: pip install --upgrade pip setuptools wheel"
    exit 1
}

Write-Success "✓ ML service dependencies installed"

Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# 6. (Optional) Install Emotion Service Dependencies
# ─────────────────────────────────────────────────────────────────────

if (-not $SkipEmotionService) {
    Write-Info "Step 6a: Installing emotion service dependencies..."
    Write-Info "   (DeepFace, TensorFlow — may take 5-10 minutes)"

    $emotionRequirementsPath = "backend\emotion_service\requirements.txt"
    if (Test-Path $emotionRequirementsPath) {
        python -m pip install -r $emotionRequirementsPath
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "⚠ Emotion service installation had issues (optional)"
            Write-Warning "  System will still work with core ML features"
        } else {
            Write-Success "✓ Emotion service dependencies installed"
        }
    } else {
        Write-Warning "⚠ Emotion service requirements not found (optional)"
    }
    
    Write-Host ""
} else {
    Write-Info "Step 6a: Skipping emotion service (use --SkipEmotionService:$false to install)"
    Write-Host ""
}

# ─────────────────────────────────────────────────────────────────────
# 7. (Optional) Install Development Tools
# ─────────────────────────────────────────────────────────────────────

if ($InstallDev) {
    Write-Info "Step 6b: Installing development tools..."

    $devRequirementsPath = "backend\ml_service\requirements-dev.txt"
    if (Test-Path $devRequirementsPath) {
        python -m pip install -r $devRequirementsPath
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "⚠ Dev tools installation had issues (optional)"
        } else {
            Write-Success "✓ Development tools installed"
        }
    }
    
    Write-Host ""
} else {
    Write-Info "Step 6b: Skipping dev tools (use -InstallDev to install)"
    Write-Host ""
}

# ─────────────────────────────────────────────────────────────────────
# 8. Run Health Check
# ─────────────────────────────────────────────────────────────────────

if (-not $SkipHealthCheck) {
    Write-Info "Step 7: Running environment health check..."
    Write-Host ""

    python -m ml_service.health_check
    $healthStatus = $LASTEXITCODE

    Write-Host ""
    
    if ($healthStatus -ne 0) {
        Write-Warning "⚠ Health check reported issues (see above)"
        Write-Warning "  This may be normal if models haven't been trained yet"
    } else {
        Write-Success "✓ Health check passed"
    }
} else {
    Write-Info "Step 7: Skipping health check"
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# 9. (Optional) Train Models
# ─────────────────────────────────────────────────────────────────────

if (-not $SkipTrain) {
    Write-Info "Step 8: Training ML models..."
    Write-Info "   First-time training takes 30-60 seconds..."
    Write-Host ""

    python backend/ml_service/ml_models.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Msg "ERROR: Model training failed"
        Write-Error-Msg "       Try running manually: python backend/ml_service/ml_models.py"
        exit 1
    }

    Write-Success "✓ Models trained successfully"
} else {
    Write-Info "Step 8: Skipping model training (use -SkipTrain:$false to train)"
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   Setup Complete! ✓                                        ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Info "Next steps:"
Write-Host ""
Write-Host "  1. Activate venv each time you work:"
Write-Host "     .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "  2. Start ML service:"
Write-Host "     python backend\ml_service\app.py"
Write-Host ""
Write-Host "  3. In another terminal, start Node backend:"
Write-Host "     cd backend && npm start"
Write-Host ""
Write-Host "  4. Check health:"
Write-Host "     python -m ml_service.health_check"
Write-Host ""
Write-Info "Documentation: backend/ml_service/SETUP_WINDOWS.md"
Write-Host ""
