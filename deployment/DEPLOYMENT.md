# Deployment Guide

## Quick Deploy Options

### Option 1: Render (Backend) + Vercel (Frontend)

#### Backend → Render
1. Push your code to GitHub
2. Go to [render.com](https://render.com) and sign up
3. Create a new "Web Service"
4. Connect your GitHub repo
5. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port 8000`
   - Environment: Python 3.11
6. Click "Deploy"

#### Frontend → Vercel
1. Go to [vercel.com](https://vercel.com) and sign up
2. Import your GitHub repo
3. Settings:
   - Framework Preset: Next.js
   - Build Command: `npm run build`
   - Output Directory: `.next`
4. Add environment variable:
   - `NEXT_PUBLIC_API_BASE_URL` = your Render backend URL (e.g., `https://your-backend.onrender.com`)
5. Click "Deploy"

---

### Option 2: Docker (Local Production)

```bash
cd deployment
docker-compose up --build
```

---

### Option 3: Railway

Railway supports both backend and frontend in one project.

1. Go to [railway.app](https://railway.app)
2. Create new project
3. Add "Python" service for backend
4. Add "Next.js" service for frontend
5. Configure environment variables
6. Deploy

---

## Manual Deployment (from your Mac)

### Backend to Render
```bash
# Ensure Git is set up
cd /Users/shyclaw/.openclaw/workspace/projects/sg-property-intel
git init
git add .
git commit -m "Property tool v1"

# Push to GitHub (create repo first on GitHub)
git remote add origin https://github.com/YOUR_USERNAME/sg-property-intel.git
git push -u main

# Then deploy via Render dashboard as shown above
```

### Frontend to Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel --prod
```

---

## Environment Variables

### Backend (if using PostgreSQL)
```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### Frontend
```
NEXT_PUBLIC_API_BASE_URL=https://your-backend-url.onrender.com
```

---

## Current Status

- **Backend**: Ready for deployment
- **Frontend**: Ready for deployment  
- **Database**: SQLite (needs to be deployed with backend or migrated to cloud DB)

For production with multiple users, consider migrating from SQLite to PostgreSQL.
