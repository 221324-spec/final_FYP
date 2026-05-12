# 📋 Deployment Checklist - Step by Step

Copy-paste this checklist and check off items as you complete them.

---

## ✅ PRE-DEPLOYMENT (5 mins)

### Prepare Your Environment
- [ ] Git repository is pushed to GitHub
- [ ] Run deployment prep check: `powershell -ExecutionPolicy Bypass -File deploy-prep.ps1`
- [ ] All environment variables verified in `.env`
- [ ] Project builds locally: `cd backend && npm start`
- [ ] ML service runs locally: `python backend/ml_service/app.py`

---

## 🔐 STEP 1: MongoDB Atlas Setup (5 mins)

### Create Free Database
- [ ] Go to https://mongodb.com/atlas
- [ ] Sign up / Log in
- [ ] Create Organization
- [ ] Create Free M0 Cluster
  - Region: (select closest to users)
  - Cluster Name: recovery-road-prod
- [ ] Wait for cluster to be ready (~10 mins)

### Configure Access
- [ ] Go to: Cluster → Network Access
- [ ] Click: "Add IP Address"
- [ ] Enter: 0.0.0.0/0 (allows all IPs) OR your specific IP
- [ ] Confirm

### Get Connection String
- [ ] Go to: Database → Your Cluster
- [ ] Click: "Connect"
- [ ] Choose: "Drivers"
- [ ] Copy connection string
- [ ] Replace placeholders:
  - `<username>` with your MongoDB username
  - `<password>` with your MongoDB password
  - `dbname` with recoveryroad
- [ ] Final format: `mongodb+srv://user:pass@cluster.xxxxx.mongodb.net/recoveryroad?retryWrites=true&w=majority`
- [ ] **Save this string** ✅

---

## 🎨 STEP 2: Deploy Frontend (Vercel) - 5 mins

### Create Vercel Project
- [ ] Go to: https://vercel.com
- [ ] Sign in with GitHub
- [ ] Click: "Add New" → "Project"
- [ ] Select: Recovery Road repository
- [ ] Configure:
  - Root Directory: `frontend`
  - Framework: Vite (auto-detected)
  - Build Command: `npm run build`
  - Output Directory: `dist`
- [ ] Click: **"Deploy"**
- [ ] Wait for deployment (2-3 minutes)

### Save Your Frontend URL
- [ ] After deployment, copy your URL
- [ ] Format: `https://recovery-road-xxxxx.vercel.app`
- [ ] **Save this URL** ✅

---

## 🔧 STEP 3: Deploy Backend (Railway) - 10 mins

### Create Railway Backend Project
- [ ] Go to: https://railway.app
- [ ] Sign in with GitHub
- [ ] Click: "New Project"
- [ ] Select: "Deploy from GitHub Repo"
- [ ] Choose: Recovery Road repository
- [ ] Click: "Deploy Now"

### Configure Backend Build
- [ ] Wait for Railway to auto-detect Node.js
- [ ] Click: Service → "Settings" tab
- [ ] Set Build Command:
  ```
  cd backend && npm install
  ```
- [ ] Set Start Command:
  ```
  cd backend && npm start
  ```

### Add Backend Environment Variables
- [ ] Click: "Variables" tab
- [ ] Add each variable (copy-paste exactly):

```
NODE_ENV
production

MONGO_URI
mongodb+srv://your_username:your_password@cluster.xxxxx.mongodb.net/recoveryroad?retryWrites=true&w=majority

JWT_SECRET
(generate: 32+ random characters OR paste: superstrongsecretkey1234567890ab)

JWT_EXPIRE
7d

GROQ_API_KEY
(your-groq-api-key-from-.env)

CHAT_PROVIDER
GROQ

GROQ_MODEL
llama-3.3-70b-versatile

GROQ_TIMEOUT_MS
25000

FRONTEND_URL
https://your-vercel-url-from-step-2.vercel.app

ML_SERVICE_URL
(UPDATE AFTER STEP 4 - leave empty for now)
```

### Deploy Backend
- [ ] Railway auto-deploys when variables are set
- [ ] Wait for status to show "Running" (green)
- [ ] Copy your backend URL
- [ ] Format: `https://recovery-road-xxx.railway.app`
- [ ] **Save this URL** ✅

---

## 🤖 STEP 4: Deploy ML Service (Railway) - 10 mins

### Create Railway ML Project
- [ ] Go to: https://railway.app (dashboard)
- [ ] Click: "New Project"
- [ ] Select: "Deploy from GitHub Repo"
- [ ] Choose: Same Recovery Road repository
- [ ] Click: "Deploy Now"

### Configure ML Service Build
- [ ] Wait for Railway auto-detection
- [ ] Click: Service → "Settings"
- [ ] Set Build Command:
  ```
  cd backend/ml_service && pip install -r requirements.txt
  ```
- [ ] Set Start Command:
  ```
  cd backend/ml_service && python app.py
  ```

### Add ML Service Environment Variables
- [ ] Click: "Variables" tab
- [ ] Add:

```
PYTHONUNBUFFERED
1

FLASK_ENV
production
```

### Deploy ML Service
- [ ] Wait for status to show "Running" (green)
- [ ] Copy your ML service URL
- [ ] Format: `https://recovery-road-ml-xxx.railway.app`
- [ ] **Save this URL** ✅

---

## 🔗 STEP 5: Connect Everything (2 mins)

### Update Backend with ML Service URL
- [ ] Go back to Railway Backend project
- [ ] Click: "Variables" tab
- [ ] Update: `ML_SERVICE_URL` = your ML service URL
- [ ] Railway auto-redeploys
- [ ] Wait for "Running" status

### Update Frontend with Backend URL
- [ ] Go to Vercel → Your project
- [ ] Click: "Settings" → "Environment Variables"
- [ ] Add/Update:

```
REACT_APP_API_URL
https://your-backend-railway-url.railway.app

REACT_APP_SOCKET_URL
https://your-backend-railway-url.railway.app
```

- [ ] Click: "Save"
- [ ] Click: "Redeploy" button
- [ ] Wait for deployment to complete

---

## ✅ STEP 6: Verification (5 mins)

### Test Frontend
- [ ] Open: `https://your-vercel-url.vercel.app`
- [ ] Page loads without errors
- [ ] Can see login form ✅

### Test Backend Health
- [ ] Command:
```powershell
Invoke-WebRequest -Uri "https://your-backend-url/api/health" -Method Get | ConvertTo-Json
```
- [ ] Should return: `{ "ok": true, ... }` ✅

### Test ML Service Health
- [ ] Command:
```powershell
Invoke-WebRequest -Uri "https://your-ml-url/api/ml/health" -Method Get | ConvertTo-Json
```
- [ ] Should return: `{ "status": "ready", ... }` ✅

### Test Chat Endpoint
- [ ] Command:
```powershell
$body = @{
    userId = "test-user"
    messageText = "I am feeling stressed"
    conversationHistory = @()
} | ConvertTo-Json

Invoke-WebRequest -Uri "https://your-backend-url/api/chat/send" `
  -Method Post `
  -Headers @{"Content-Type" = "application/json"} `
  -Body $body | ConvertTo-Json
```
- [ ] Should return chat reply ✅

### Manual App Test
- [ ] Go to frontend URL in browser
- [ ] Sign up with test account
- [ ] Send message: "I am feeling stressed"
- [ ] Get Groq-powered response ✅
- [ ] Send message: "I want to use drugs right now"
- [ ] Get crisis template response ✅

---

## 🎉 SUCCESS CHECKLIST

All systems are deployed when:

- [ ] ✅ Frontend loads at HTTPS
- [ ] ✅ Can create account and log in
- [ ] ✅ LOW-risk message gets Groq response
- [ ] ✅ HIGH-risk message gets crisis template
- [ ] ✅ Backend health endpoint responds
- [ ] ✅ ML service health endpoint responds
- [ ] ✅ Chat endpoint returns valid JSON
- [ ] ✅ Real-time chat works (instant responses)
- [ ] ✅ No errors in browser console
- [ ] ✅ No errors in Railway/Vercel logs

**🚀 YOU'RE LIVE! 🚀**

---

## 🆘 If Something Goes Wrong

### Check in This Order:
1. [ ] Railway backend logs: Dashboard → Service → Logs
2. [ ] Railway ML logs: Dashboard → Service → Logs
3. [ ] Vercel logs: Project → Deployments → Latest
4. [ ] Browser console (F12): Look for CORS/network errors
5. [ ] MongoDB Atlas connection: Database → Clusters → Connect → Test
6. [ ] API health checks (see verification section above)

### Quick Fixes:
- [ ] Restart backend service: Railway → Service → More → Restart
- [ ] Restart ML service: Railway → Service → More → Restart
- [ ] Redeploy frontend: Vercel → Deployments → Redeploy
- [ ] Update env variables: Re-enter values and save/redeploy

---

## 📞 Need Help?

**Document:** DEPLOYMENT_COMPLETE_GUIDE.md (detailed troubleshooting)
**Logs Location:**
- Backend: Railway dashboard → Service → Logs
- Frontend: Vercel dashboard → Analytics / Deployments
- Database: MongoDB Atlas → Database → Cluster logs

**External Resources:**
- Railway: https://docs.railway.app
- Vercel: https://vercel.com/docs
- MongoDB: https://docs.atlas.mongodb.com

---

**Checklist Last Updated:** May 12, 2026
**Status:** ✅ Production Ready

