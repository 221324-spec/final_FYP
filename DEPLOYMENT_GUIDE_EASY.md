# 🚀 Recovery Road - Easy Deployment Guide

Complete step-by-step guide to deploy the frontend, backend, and ML service. Choose your preferred hosting platform.

---

## 📋 Prerequisites

Before starting, you'll need:
- [ ] GitHub account (for easy deployments)
- [ ] MongoDB Atlas account (free tier available)
- [ ] Groq API key (already configured in `.env`)
- [ ] Hosting accounts (see options below)

---

## 🌐 Database Setup (Required for All)

### Step 1: Create MongoDB Atlas Cluster

1. Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Sign up / log in → Create a new project
3. Click **"Create Deployment"** → Choose **Free (M0)** tier
4. Set username/password (remember these!)
5. Whitelist IP: Click **"Network Access"** → Add **0.0.0.0/0** (allows all IPs)
6. Go to **"Database"** → Click **"Connect"** on your cluster
7. Choose **"Drivers"** → Copy the connection string:
   ```
   mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/dbname?retryWrites=true&w=majority
   ```
8. Replace `username`, `password`, and `dbname` with your values
9. Save this string — you'll need it for backend deployment ✅

---

## 🎯 EASY DEPLOYMENT OPTIONS

Choose one option for each component:

---

# OPTION A: Vercel (Frontend) + Railway (Backend) + Railway (ML Service) ⭐ RECOMMENDED

**Pros:** Easiest, free tier, excellent integration
**Time:** ~15 minutes

---

### Frontend Deployment (Vercel)

#### Step 1: Connect Repository

1. Go to [Vercel](https://vercel.com)
2. Sign in → Click **"Add New"** → **"Project"**
3. Import your GitHub repository
4. Select the **`frontend`** folder as root
5. Click **"Deploy"** ✅

Your frontend is now live! You'll get a URL like `https://recovery-road.vercel.app`

#### Step 2: Configure Environment Variables

After deployment, go to **Settings** → **Environment Variables** and add:

```
REACT_APP_API_URL=https://your-backend-railway-url.railway.app
REACT_APP_SOCKET_URL=https://your-backend-railway-url.railway.app
```

(You'll update these after deploying the backend)

---

### Backend Deployment (Railway)

#### Step 1: Create Railway Project

1. Go to [Railway.app](https://railway.app)
2. Sign in with GitHub → **"New Project"**
3. Select **"Deploy from GitHub Repo"**
4. Choose your Recovery Road repository
5. Railway auto-detects Node.js ✅

#### Step 2: Configure Build & Start Commands

In Railway dashboard, go to **Settings**:

- **Build Command:** `cd backend && npm install`
- **Start Command:** `cd backend && npm start`
- **Root Directory:** (leave blank or set to `backend`)

#### Step 3: Add Environment Variables

Click **"Variables"** tab and add:

```
NODE_ENV=production
MONGO_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/recoveryroad?retryWrites=true&w=majority
JWT_SECRET=your-long-random-secret-key-min-32-characters
JWT_EXPIRE=7d
GROQ_API_KEY=(your-groq-api-key-from-.env)
CHAT_PROVIDER=GROQ
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT_MS=25000
FRONTEND_URL=https://recovery-road.vercel.app
ML_SERVICE_URL=https://your-ml-service-url.railway.app
```

#### Step 4: Deploy

Click the **"Deploy"** button. Railway builds and deploys automatically.

Once deployed, you'll get a URL like `https://recovery-road-backend-prod.railway.app`

#### Step 5: Update Frontend Variables

Go back to Vercel:
1. **Settings** → **Environment Variables**
2. Update `REACT_APP_API_URL` and `REACT_APP_SOCKET_URL` with your Railway backend URL
3. **Redeploy** the frontend

---

### ML Service Deployment (Railway)

#### Step 1: Create Second Railway Project

1. In Railway, click **"New Project"** → **"Deploy from GitHub Repo"**
2. Choose the same Recovery Road repository
3. Railway should detect **Python** automatically

#### Step 2: Configure for Python

In **Settings**:

- **Build Command:** `cd backend/ml_service && pip install -r requirements.txt`
- **Start Command:** `cd backend/ml_service && python app.py`
- **Root Directory:** (leave blank)
- **Python Version:** `3.11` (optional, Railway defaults to 3.12+)

#### Step 3: Add Environment Variables

```
PYTHONUNBUFFERED=1
FLASK_ENV=production
```

#### Step 4: Deploy & Get URL

Railway deploys automatically. You'll get a URL like `https://recovery-road-ml-prod.railway.app`

#### Step 5: Update Backend

Go back to Railway backend dashboard:
1. **Variables** → Update `ML_SERVICE_URL` to your ML service Railway URL
2. **Redeploy** backend

---

## ✅ Verification After Deployment

### Test Frontend
```bash
curl https://recovery-road.vercel.app
# Should return HTML with React app
```

### Test Backend Health
```bash
curl https://your-backend-railway-url/api/health
# Should return: { "ok": true, ... }
```

### Test ML Service Health
```bash
curl https://your-ml-service-railway-url/api/ml/health
# Should return: { "status": "ready", ... }
```

### Test Chat Endpoint
```bash
curl -X POST https://your-backend-railway-url/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test-user",
    "messageText": "I am feeling stressed",
    "conversationHistory": []
  }'
# Should return: { "reply": "...", "analysisResult": { ... } }
```

---

# OPTION B: Heroku (Backend + ML Service) + Netlify (Frontend)

**Pros:** Traditional, reliable, good documentation
**Time:** ~20 minutes
**Note:** Heroku free tier is now paid; use Railway or Render instead

---

# OPTION C: Render (Backend) + Vercel (Frontend)

### Backend on Render

1. Go to [Render.com](https://render.com)
2. **New** → **Web Service** → Connect GitHub repo
3. **Root directory:** `backend`
4. **Build command:** `npm install`
5. **Start command:** `npm start`
6. Add same environment variables as above
7. Deploy ✅ You get a URL like `https://recovery-road-api.onrender.com`

### ML Service on Render

1. **New** → **Web Service** → Connect same repo
2. **Root directory:** `backend/ml_service`
3. **Runtime:** Python 3.11+
4. **Build command:** `pip install -r requirements.txt`
5. **Start command:** `python app.py`
6. Deploy ✅

### Frontend on Vercel
(Same as Option A)

---

# OPTION D: Docker + AWS / DigitalOcean / Azure

For production with more control:

### Step 1: Create Dockerfile for Backend

Create `backend/Dockerfile`:
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 5000
CMD ["npm", "start"]
```

### Step 2: Create Dockerfile for ML Service

Create `backend/ml_service/Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["python", "app.py"]
```

### Step 3: Deploy to AWS ECS / DigitalOcean App Platform

(Requires Docker CLI knowledge — suitable for advanced users)

---

## 🔧 Environment Variables Checklist

Create a file to track all required variables:

```
PRODUCTION VARIABLES NEEDED:

Backend (.env):
- [ ] NODE_ENV=production
- [ ] MONGO_URI=mongodb+srv://...
- [ ] JWT_SECRET=<32+ random chars>
- [ ] JWT_EXPIRE=7d
- [ ] GROQ_API_KEY=gsk_...
- [ ] CHAT_PROVIDER=GROQ
- [ ] GROQ_MODEL=llama-3.3-70b-versatile
- [ ] GROQ_TIMEOUT_MS=25000
- [ ] FRONTEND_URL=https://your-vercel-url
- [ ] ML_SERVICE_URL=https://your-ml-service-url
- [ ] PORT=5000 (auto-set by hosting)

Frontend (.env or Vercel):
- [ ] REACT_APP_API_URL=https://your-backend-url
- [ ] REACT_APP_SOCKET_URL=https://your-backend-url

ML Service (.env):
- [ ] PYTHONUNBUFFERED=1
- [ ] FLASK_ENV=production
```

---

## 🐛 Troubleshooting

### Frontend can't reach backend
- Check CORS: Backend `FRONTEND_URL` must match exactly (http vs https, domain, subdomain)
- Check API URL: Frontend `REACT_APP_API_URL` must be correct
- Check firewall: Some hosts block outgoing requests

### Chat returns "Service Unavailable"
- Check ML service is running: Test `ML_SERVICE_URL/api/ml/health`
- Check ML_SERVICE_URL env var on backend
- ML service may be cold-starting (first request after idle takes ~30s on free tier)

### Socket.IO connection fails
- Socket.IO URL must match backend URL
- Use same protocol (HTTPS must match HTTPS)
- Check `ALLOWED_ORIGINS` on backend

### Database connection timeout
- MongoDB Atlas: Add frontend/backend IP to Network Access whitelist
- Or use 0.0.0.0/0 (less secure but works anywhere)

---

## 📊 Estimated Costs (Monthly)

| Component | Option A (Railway) | Option B (Heroku) | Option C (Render) |
|-----------|-----------------|----------|---------|
| Frontend (Vercel) | Free | Free | Free |
| Backend | Free - $5 | $7 | $7 - $12 |
| ML Service | Free - $5 | $7 | $7 - $12 |
| Database (Atlas) | Free (5GB) | Free (5GB) | Free (5GB) |
| **TOTAL** | **Free - $10** | **$14** | **$14 - $24** |

Free tier suitable for testing/small usage. Scale as needed.

---

## 🎉 You're Deployed!

After verification, your system is live:
- Frontend: `https://recovery-road.vercel.app`
- Backend API: `https://your-backend-url/api/chat/send`
- ML Service: `https://your-ml-service-url/api/ml/health`

### Next Steps:
1. Test all endpoints
2. Monitor logs for errors
3. Set up error tracking (Sentry)
4. Configure backups for database
5. Enable SSL/TLS (should be automatic)

---

## 📞 Support

If you encounter issues:
1. Check logs on the hosting platform
2. Test endpoints with `curl` command from above
3. Verify all environment variables are set
4. Check MongoDB Atlas connection string format

