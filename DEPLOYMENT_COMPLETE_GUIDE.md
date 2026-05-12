# 📚 Recovery Road - Complete Deployment Documentation

**Last Updated:** May 12, 2026  
**Status:** ✅ Ready for Production

---

## 📑 Table of Contents

1. [Quick Start (5-15 minutes)](#quick-start)
2. [Detailed Deployment Steps](#detailed-steps)
3. [Post-Deployment Verification](#verification)
4. [Troubleshooting](#troubleshooting)
5. [Monitoring & Maintenance](#monitoring)

---

## 🚀 Quick Start

**Choose ONE option below:**

### Option A: Vercel (Frontend) + Railway (Backend + ML) ⭐ RECOMMENDED
- **Time:** 15 minutes
- **Cost:** Free-$10/month
- **Difficulty:** Easy
- **Best for:** Quick production deployment

### Option B: Vercel + Render
- **Time:** 20 minutes
- **Cost:** $7-24/month (paid immediately)
- **Difficulty:** Easy
- **Best for:** Premium experience

### Option C: Self-hosted Docker
- **Time:** 30-60 minutes
- **Cost:** Depends on VPS provider
- **Difficulty:** Advanced
- **Best for:** Full control

---

## 📚 Detailed Steps

### STEP 1: Database Setup (Required for All Options)

#### 1.1 Create MongoDB Atlas Account
```
1. Go to: https://www.mongodb.com/atlas
2. Sign up (free)
3. Create Organization → Create Project
4. Click "Build a Database"
5. Select "FREE M0" tier (5GB, good for testing/small production)
```

#### 1.2 Create Cluster
```
1. Region: Choose closest to your users
2. Cluster Name: recovery-road-prod
3. Create Cluster (takes ~5-10 minutes)
```

#### 1.3 Configure Network Access
```
1. Go to "Network Access" tab
2. Click "Add IP Address"
3. Click "Allow Access from Anywhere" (0.0.0.0/0)
   OR manually add: 1.2.3.4 (your IP)
4. Confirm
```

⚠️ **Note:** 0.0.0.0/0 is convenient but less secure. Use for dev/testing only.

#### 1.4 Get Connection String
```
1. Go to "Database" → Your Cluster
2. Click "Connect"
3. Choose "Drivers"
4. Copy the connection string:
   mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/mydb?retryWrites=true&w=majority

5. Replace:
   - username: Your Atlas username
   - password: Your Atlas password
   - mydb: Your database name (e.g., recoveryroad)
```

✅ Save this string — you'll need it for backend deployment

---

### STEP 2A: Frontend Deployment (Vercel)

#### 2A.1 Connect Repository
```
1. Go to: https://vercel.com
2. Sign in with GitHub
3. Click "Add New" → "Project"
4. Find your Recovery Road repository
5. Click "Import"
```

#### 2A.2 Configure Project
```
1. Set "Root Directory" to: frontend
2. Framework: Vite (auto-detected)
3. Build Command: npm run build (default)
4. Output Directory: dist (default)
5. Click "Deploy"
```

⏱️ Deployment takes ~2-3 minutes

#### 2A.3 Get Your Frontend URL
```
After deployment completes:
- Your URL: https://recovery-road-xxxxx.vercel.app
- Save this URL ✅
```

#### 2A.4 Add Environment Variables (Optional for now)
```
1. Go to your Vercel project → Settings → Environment Variables
2. Add:
   REACT_APP_API_URL=https://backend-url.railway.app
   REACT_APP_SOCKET_URL=https://backend-url.railway.app
3. Redeploy after backend is live
```

---

### STEP 2B: Backend Deployment (Railway)

#### 2B.1 Create Railway Account & Project
```
1. Go to: https://railway.app
2. Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub Repo"
5. Find Recovery Road repo
6. Click "Deploy Now"
```

#### 2B.2 Configure Build & Start Commands
```
1. Go to your Railway project
2. Click on the service
3. Go to "Settings" tab
4. Set:
   Build Command: cd backend && npm install
   Start Command: cd backend && npm start
   Watch Paths: backend/**
```

#### 2B.3 Add Environment Variables

In Railway, go to **Variables** and add:

```
NODE_ENV=production
MONGO_URI=mongodb+srv://user:pass@cluster.xxxxx.mongodb.net/recoveryroad?retryWrites=true&w=majority
JWT_SECRET=your-super-secret-key-min-32-chars-long
JWT_EXPIRE=7d
GROQ_API_KEY=(your-groq-api-key-from-.env)
CHAT_PROVIDER=GROQ
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT_MS=25000
FRONTEND_URL=https://recovery-road-xxxxx.vercel.app
ML_SERVICE_URL=https://recovery-road-ml.railway.app
```

**Where to get each:**
- `MONGO_URI`: From MongoDB Atlas (Step 1.4)
- `JWT_SECRET`: Generate: `openssl rand -hex 32` or use random string
- `GROQ_API_KEY`: From .env file (already configured)
- `FRONTEND_URL`: Your Vercel URL from Step 2A.3
- `ML_SERVICE_URL`: Will update after deploying ML service

#### 2B.4 Deploy
```
Railway auto-deploys when you add variables
Wait for status: "Running" (green indicator)
Get your backend URL: https://recovery-road-xxx.railway.app
```

✅ Save backend URL — you'll need it for ML service and frontend update

---

### STEP 2C: ML Service Deployment (Railway)

#### 2C.1 Create Second Railway Project
```
1. In Railway Dashboard → "New Project"
2. "Deploy from GitHub Repo"
3. Same Recovery Road repository
4. Click "Deploy Now"
```

#### 2C.2 Configure for Python
```
1. Click on the service
2. Go to "Settings"
3. Set:
   Build Command: cd backend/ml_service && pip install -r requirements.txt
   Start Command: cd backend/ml_service && python app.py
   Python Version: 3.11 (optional)
```

#### 2C.3 Add Environment Variables
```
PYTHONUNBUFFERED=1
FLASK_ENV=production
```

#### 2C.4 Deploy
```
Wait for status: "Running"
Get ML Service URL: https://recovery-road-ml-xxx.railway.app
```

✅ Save ML service URL

---

### STEP 3: Connect Everything

#### 3.1 Update Backend with ML Service URL
```
1. Go back to Backend Railway project
2. Variables → Update ML_SERVICE_URL with your ML service URL
3. Click "Redeploy" (Railway auto-redeploys on variable change)
```

#### 3.2 Update Frontend with Backend URL
```
1. Go to Vercel project → Settings → Environment Variables
2. Update:
   REACT_APP_API_URL=your-backend-railway-url
   REACT_APP_SOCKET_URL=your-backend-railway-url
3. Click "Redeploy"
```

✅ All three services are now connected!

---

## ✅ Verification (Post-Deployment)

### 1. Test Frontend
```bash
# Frontend should load without errors
curl -I https://recovery-road-xxxxx.vercel.app
# Should return: HTTP/1.1 200 OK
```

### 2. Test Backend Health
```bash
curl https://your-backend-railway-url/api/health
# Should return: 
# {
#   "ok": true,
#   "service": "recovery-road-api",
#   "timestamp": "2026-05-12T10:00:00Z"
# }
```

### 3. Test ML Service Health
```bash
curl https://your-ml-service-railway-url/api/ml/health
# Should return:
# {
#   "status": "ready",
#   "models": {...}
# }
```

### 4. Test Chat Endpoint
```bash
curl -X POST https://your-backend-url/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test-user",
    "messageText": "I am feeling stressed",
    "conversationHistory": []
  }'
# Should return: { "reply": "...", "analysisResult": {...} }
```

### 5. Manual Testing
```
1. Go to https://recovery-road-xxxxx.vercel.app
2. Sign up / Log in
3. Send a test message
4. Should get Groq-powered response
5. Test crisis message (HIGH risk) → Should get crisis template
```

---

## 🐛 Troubleshooting

### Issue: Frontend Can't Connect to Backend
**Symptoms:** Login fails, messages don't send, blank page

**Solution:**
```
1. Check FRONTEND_URL on backend matches EXACTLY:
   - Same domain
   - HTTPS (if frontend is HTTPS)
   - No trailing slash
   Example: https://recovery-road-xxxxx.vercel.app (NOT ...vercel.app/)

2. Check frontend has correct API URL:
   REACT_APP_API_URL=https://your-backend-url

3. Check CORS on backend:
   backend/config/corsOrigins.js includes FRONTEND_URL
```

### Issue: ML Service Returns 503
**Symptoms:** "Service Unavailable" on chat

**Solution:**
```
1. ML service may be cold-starting (first request after idle takes 30s)
2. Test ML health: curl your-ml-service-url/api/ml/health
3. Wait 30-60 seconds, retry
4. Check Railway logs for errors
```

### Issue: Chat Always Returns Same Template
**Symptoms:** Gets crisis template even for LOW-risk messages

**Solution:**
```
1. Check ML service is connected: GET /api/ml/health
2. Check backend logs: Railway dashboard → Logs tab
3. Restart ML service: Railway → Service → Restart
4. Verify ML_SERVICE_URL is correct on backend
```

### Issue: MongoDB Connection Timeout
**Symptoms:** "Connection refused" or database errors

**Solution:**
```
1. Check MONGO_URI format in backend variables
2. Verify MongoDB Atlas Network Access:
   - Go to Atlas → Network Access
   - Add IP 0.0.0.0/0 (or your server IP)
3. Check cluster is running: Atlas → Database
4. Verify database name in connection string exists
```

### Issue: Groq Returns 401/403
**Symptoms:** "Unauthorized" or "Access Denied"

**Solution:**
```
1. Verify GROQ_API_KEY is set correctly
2. Check key hasn't expired or been revoked
3. Test key works locally:
   node -e "const Groq = require('groq-sdk'); const client = new Groq(); console.log('OK')"
```

### Issue: Build Fails on Railway
**Symptoms:** Red error badge, deployment stuck

**Solution:**
```
1. Check build logs: Railway → Service → Logs
2. Common issues:
   - Missing npm dependencies: npm install locally to verify
   - Wrong working directory: Check "Root Directory" setting
   - Node version: Update Node version in Railway settings
3. Try rebuilding: Railway → Service → More Options → Rebuild
```

---

## 📊 Monitoring & Maintenance

### Weekly Checks
```
1. Test app: Can you log in and chat?
2. Check database size: MongoDB Atlas → Database → Storage
3. Review errors: Railway → Logs / Vercel → Analytics
4. Monitor costs: Railway dashboard shows usage
```

### Monthly Tasks
```
1. Update dependencies: npm audit fix (backend + frontend)
2. Backup database: MongoDB Atlas → Backup & Recovery
3. Review logs for security issues
4. Test crisis workflow: HIGH-risk message → Crisis template
```

### Environment Variables Reference
```
BACKEND (Railway):
- NODE_ENV: production
- MONGO_URI: MongoDB connection
- JWT_SECRET: API auth key
- GROQ_API_KEY: LLM provider key
- CHAT_PROVIDER: GROQ (routing)
- FRONTEND_URL: CORS origin
- ML_SERVICE_URL: ML microservice

FRONTEND (Vercel):
- REACT_APP_API_URL: Backend URL
- REACT_APP_SOCKET_URL: Backend WebSocket

ML SERVICE (Railway):
- PYTHONUNBUFFERED: 1 (logging)
- FLASK_ENV: production
```

---

## 🎯 Success Indicators

Your deployment is successful when:

- ✅ Frontend loads at HTTPS URL
- ✅ Can create account and log in
- ✅ Can send LOW-risk message → Gets Groq response
- ✅ Can send HIGH-risk message → Gets crisis template + supervisor alert
- ✅ Real-time chat works (responses appear immediately)
- ✅ ML service health endpoint returns 200 OK
- ✅ Database connects without errors
- ✅ No CORS errors in browser console

---

## 📞 Getting Help

**If something goes wrong:**

1. Check Railway/Vercel logs first
2. Test each endpoint with curl
3. Verify all environment variables are set
4. Check MongoDB Atlas connection
5. Restart services (Railway → Service → Restart)
6. Review troubleshooting section above

**Additional Resources:**
- [Railway Docs](https://docs.railway.app)
- [Vercel Docs](https://vercel.com/docs)
- [MongoDB Atlas Docs](https://docs.atlas.mongodb.com)
- [Groq API Docs](https://console.groq.com/docs)

---

## 💰 Cost Breakdown (Estimated Monthly)

| Service | Free Tier | Paid (Min) |
|---------|-----------|-----------|
| Frontend (Vercel) | Unlimited | Unlimited |
| Backend (Railway) | $5/mo credit | $5+ |
| ML Service (Railway) | $5/mo credit | $5+ |
| Database (MongoDB Atlas) | 5GB | $0 - varies |
| **TOTAL** | **~$0** (first month) | **$10-20** |

Railway provides $5/month free credit for all deployments. Suitable for small-to-medium production use.

---

## ✨ You're Ready!

All deployment documentation is complete. Your Recovery Road platform is now:
- ✅ Deployed to production
- ✅ Integrated with Groq AI
- ✅ ML-powered risk detection
- ✅ Real-time chat enabled
- ✅ Crisis support automation active

**Start helping people on their recovery journey! 🎉**

