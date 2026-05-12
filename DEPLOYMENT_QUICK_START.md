# 🚀 Deployment Quick Start (5-15 mins)

## ⚡ FASTEST PATH: Vercel + Railway

### 1️⃣ Setup Database (5 mins)
- [ ] Go to https://mongodb.com/atlas
- [ ] Create FREE cluster (M0)
- [ ] Get connection string: `mongodb+srv://user:pass@cluster.mongodb.net/dbname`
- [ ] Whitelist 0.0.0.0/0 in Network Access

### 2️⃣ Deploy Frontend to Vercel (3 mins)
```
1. Go to https://vercel.com → New Project
2. Select your GitHub repo → Select "frontend" folder
3. Click Deploy ✅
4. Copy your Vercel URL (e.g., https://recovery-road.vercel.app)
```

### 3️⃣ Deploy Backend to Railway (5 mins)
```
1. Go to https://railway.app → New Project
2. Deploy from GitHub → Select your repo
3. In Settings, add:
   - Build: cd backend && npm install
   - Start: cd backend && npm start
4. Add Environment Variables:
   - MONGO_URI = your MongoDB connection string
   - JWT_SECRET = any random 32+ character string
   - GROQ_API_KEY = (your-groq-api-key-from-.env)
   - CHAT_PROVIDER = GROQ
   - FRONTEND_URL = your Vercel URL
5. Deploy ✅
6. Copy Railway backend URL
```

### 4️⃣ Deploy ML Service to Railway (5 mins)
```
1. Railway → New Project → Deploy from GitHub
2. In Settings, add:
   - Build: cd backend/ml_service && pip install -r requirements.txt
   - Start: cd backend/ml_service && python app.py
3. Add: PYTHONUNBUFFERED = 1
4. Deploy ✅
5. Copy ML Service URL
```

### 5️⃣ Connect Everything (2 mins)
```
Backend Railway:
- Add ML_SERVICE_URL = your ML service Railway URL
- Redeploy

Vercel Frontend:
- Settings → Environment Variables
- Add: REACT_APP_API_URL = your backend Railway URL
- Redeploy
```

### ✅ Test It Works
```bash
curl https://your-backend-url/api/health
curl https://your-ml-service-url/api/ml/health
```

---

## 📋 Environment Variables Reference

### Backend (Railway)
```
NODE_ENV=production
MONGO_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/recoveryroad?retryWrites=true&w=majority
JWT_SECRET=your-super-secret-key-minimum-32-characters-long
JWT_EXPIRE=7d
GROQ_API_KEY=(your-groq-api-key-from-.env)
CHAT_PROVIDER=GROQ
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT_MS=25000
FRONTEND_URL=https://recovery-road.vercel.app
ML_SERVICE_URL=https://your-ml-railway-url.railway.app
```

### Frontend (Vercel)
```
REACT_APP_API_URL=https://your-backend-railway-url.railway.app
REACT_APP_SOCKET_URL=https://your-backend-railway-url.railway.app
```

### ML Service (Railway)
```
PYTHONUNBUFFERED=1
FLASK_ENV=production
```

---

## 🎯 What Each Does

| Service | What It Is | Where It Runs | Port |
|---------|-----------|---------------|------|
| **Frontend** | React SPA (Vite) | Vercel CDN | HTTPS only |
| **Backend** | Node.js Express API | Railway Container | 5000 |
| **ML Service** | Python Flask ML | Railway Container | 5001 |
| **Database** | MongoDB Atlas | MongoDB Cloud | 27017 |

---

## 🔒 Security Notes

- Always use HTTPS URLs (Vercel/Railway provide automatically)
- JWT_SECRET: Use strong random string (Railway generates for you)
- MongoDB: Whitelist your app IPs or use 0.0.0.0/0 for dev/testing
- Groq API Key: Keep it secret in env vars, never commit to GitHub

---

## 💰 Cost Breakdown (Monthly)

- **Vercel Frontend**: FREE (Hobby tier unlimited)
- **Railway Backend**: FREE - $5 (2GB RAM free, pay-as-you-go after)
- **Railway ML Service**: FREE - $5 (same as above)
- **MongoDB Atlas**: FREE (5GB, enough for development)

**Total: $0 - $10/month** (suitable for small production)

---

## ⚠️ Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| Frontend can't connect to backend | Check FRONTEND_URL matches exactly in backend env vars (https, domain, no trailing slash) |
| Chat returns 503 | ML service cold-starting (takes 30s on free tier first request) — just retry |
| Database connection timeout | Whitelist your hosting platform IP in MongoDB Atlas Network Access |
| Socket.IO not connecting | Use HTTPS URL matching backend URL exactly |
| Deployment fails | Check build logs on Railway/Vercel dashboard |

---

## 🎉 Success Checklist

After all 5 steps:

- [ ] Frontend loads at https://recovery-road.vercel.app
- [ ] Backend responds to: `curl https://your-backend/api/health`
- [ ] ML Service responds to: `curl https://your-ml-service/api/ml/health`
- [ ] Chat endpoint works: `curl -X POST https://your-backend/api/chat/send -d '...'`
- [ ] All environment variables are set on hosting platforms
- [ ] Can log in, send messages, get Groq responses

**You're production-ready! 🚀**

---

## 📖 Full Guide Available

See `DEPLOYMENT_GUIDE_EASY.md` for detailed troubleshooting and alternative deployment options.

