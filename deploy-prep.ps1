# Deployment Preparation Script (Windows)
# Run this BEFORE deploying to validate your setup

Write-Host "═════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Recovery Road - Deployment Prep Check" -ForegroundColor Cyan
Write-Host "═════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Function to check file exists
function Check-File($path) {
    if (Test-Path $path) {
        Write-Host "✓ Found: $path" -ForegroundColor Green
        return $true
    } else {
        Write-Host "✗ Missing: $path" -ForegroundColor Red
        return $false
    }
}

# Function to check command exists
function Check-Command($cmd) {
    try {
        $null = & $cmd --version 2>&1
        Write-Host "✓ Installed: $cmd" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "✗ Not installed: $cmd" -ForegroundColor Red
        return $false
    }
}

Write-Host "📁 Project Structure Check:" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray
Check-File "backend\server.js" | Out-Null
Check-File "backend\package.json" | Out-Null
Check-File "backend\ml_service\app.py" | Out-Null
Check-File "backend\ml_service\requirements.txt" | Out-Null
Check-File "frontend\package.json" | Out-Null
Check-File "frontend\vite.config.js" | Out-Null
Check-File "backend\.env" | Out-Null

Write-Host ""
Write-Host "📦 Installed Tools:" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray
Check-Command "node" | Out-Null
Check-Command "npm" | Out-Null
Check-Command "python" | Out-Null
Check-Command "git" | Out-Null

Write-Host ""
Write-Host "🔐 Environment Variables:" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

# Check .env file
if (Test-Path "backend\.env") {
    $envContent = Get-Content "backend\.env"
    
    if ($envContent -match "GROQ_API_KEY") {
        Write-Host "✓ GROQ_API_KEY is configured" -ForegroundColor Green
    } else {
        Write-Host "✗ GROQ_API_KEY is NOT configured" -ForegroundColor Red
    }
    
    if ($envContent -match "MONGO_URI") {
        Write-Host "✓ MONGO_URI is configured" -ForegroundColor Green
    } else {
        Write-Host "⚠ MONGO_URI not configured (needed for production)" -ForegroundColor Yellow
    }
    
    if ($envContent -match "JWT_SECRET") {
        Write-Host "✓ JWT_SECRET is configured" -ForegroundColor Green
    } else {
        Write-Host "✗ JWT_SECRET is NOT configured" -ForegroundColor Red
    }
    
    if ($envContent -match "CHAT_PROVIDER=GROQ") {
        Write-Host "✓ CHAT_PROVIDER is set to GROQ" -ForegroundColor Green
    }
    
    if ($envContent -match "GROQ_MODEL=llama-3.3-70b-versatile") {
        Write-Host "✓ GROQ_MODEL is correctly configured" -ForegroundColor Green
    }
} else {
    Write-Host "✗ backend\.env not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "✅ Backend Service Status:" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

# Check if backend is running
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ Backend is running on http://127.0.0.1:5000" -ForegroundColor Green
} catch {
    Write-Host "⚠ Backend is NOT running (normal for deployment prep)" -ForegroundColor Yellow
}

# Check if ML service is running
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5001/api/ml/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ ML Service is running on http://127.0.0.1:5001" -ForegroundColor Green
} catch {
    Write-Host "⚠ ML Service is NOT running (normal for deployment prep)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📝 Production Deployment Checklist:" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "For production deployment, ensure:" -ForegroundColor White
Write-Host "  - [ ] MongoDB Atlas cluster created at https://mongodb.com/atlas" -ForegroundColor White
Write-Host "  - [ ] MONGO_URI updated in backend\.env" -ForegroundColor White
Write-Host "  - [ ] JWT_SECRET set to random 32+ character string" -ForegroundColor White
Write-Host "  - [ ] GitHub repository is public (for Vercel/Railway)" -ForegroundColor White
Write-Host "  - [ ] Groq API key is active and valid" -ForegroundColor White
Write-Host "  - [ ] FRONTEND_URL will be set during deployment" -ForegroundColor White
Write-Host "  - [ ] ML_SERVICE_URL will be set after ML service deploys" -ForegroundColor White

Write-Host ""
Write-Host "═════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Pre-deployment check complete!" -ForegroundColor Cyan
Write-Host "═════════════════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Review DEPLOYMENT_QUICK_START.md" -ForegroundColor White
Write-Host "2. Generate new JWT_SECRET if needed" -ForegroundColor White
Write-Host "3. Commit and push to GitHub" -ForegroundColor White
Write-Host "4. Follow Vercel (frontend) → Railway (backend + ML) deployment steps" -ForegroundColor White
Write-Host ""

# Display current Git status
Write-Host "📊 Git Status:" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray
try {
    $branch = git rev-parse --abbrev-ref HEAD 2>&1
    $status = git status --porcelain 2>&1
    Write-Host "Current branch: $branch" -ForegroundColor Cyan
    if ($status) {
        Write-Host "Uncommitted changes detected:" -ForegroundColor Yellow
        $status | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    } else {
        Write-Host "Working directory clean ✓" -ForegroundColor Green
    }
} catch {
    Write-Host "Not a git repository" -ForegroundColor Yellow
}

Write-Host ""
