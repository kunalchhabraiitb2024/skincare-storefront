# Deployment Guide - Conversational Skincare Storefront

## Overview
- **Backend**: Render (FastAPI + Python)
- **Frontend**: Vercel (Next.js + React)
- **Features**: Session management, AI-powered conversations, product recommendations

## 🚀 Backend Deployment (Render)

### 1. Environment Variables to Set in Render:
```bash
GOOGLE_API_KEY=your_google_api_key_here
```

### 2. Build & Start Commands:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Root Directory**: `backend`

### 3. Your backend URL will be:
`https://your-backend-app-name.onrender.com`

## 🚀 Frontend Deployment (Vercel)

### 1. Environment Variables to Set in Vercel:
```bash
NEXT_PUBLIC_BACKEND_URL=https://your-backend-app-name.onrender.com
```

### 2. Build Settings:
- **Framework Preset**: Next.js
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `.next`

## 📁 Files Updated for Deployment:

### Backend Changes:
- ✅ Environment variable configuration (`.env`)
- ✅ Session management with UUID
- ✅ Enhanced LLM integration
- ✅ CORS configured for production

### Frontend Changes:
- ✅ Dynamic backend URL using environment variables
- ✅ Session-aware UI with conversation tracking
- ✅ Enhanced product display and follow-up questions

## 🔧 Deployment Steps:

### Backend (Render):
1. Push your code to GitHub
2. Connect Render to your repository
3. Set environment variable: `GOOGLE_API_KEY`
4. Deploy with the commands above
5. Note your backend URL

### Frontend (Vercel):
1. Connect Vercel to your repository
2. Set environment variable: `NEXT_PUBLIC_BACKEND_URL` (with your Render URL)
3. Deploy from the `frontend` directory

## ✅ Features Now Live:
- 🤖 AI-powered skincare consultation
- 💬 Session-based conversation tracking  
- 🎯 Smart product recommendations
- 📱 Responsive, modern UI
- 🔄 Real-time follow-up questions
- 🛡️ Error handling and fallbacks

## 🚦 Testing After Deployment:
1. Visit your Vercel URL
2. Test conversation flow with queries like:
   - "I have dry skin, what moisturizer do you recommend?"
   - "What's the difference between retinol and vitamin C?"
3. Verify session continuity across multiple questions
4. Check that products are properly ranked and displayed

Your conversational storefront is ready for production! 🎉
