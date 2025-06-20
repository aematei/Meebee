# 🚀 Deployment Guide

This guide covers deploying your Personal AI Assistant to cloud platforms for 24/7 availability.

## 🏆 **Recommended: Railway.app (Free Tier)**

Railway.app is the easiest and most cost-effective option for this application.

### **Why Railway.app?**
- ✅ **Free:** 500 hours/month execution time (~20 days)
- ✅ **Always On:** No sleep behavior like other free platforms
- ✅ **Simple:** Direct GitHub integration
- ✅ **File Storage:** Persistent disk included
- ✅ **Environment Variables:** Built-in secrets management

### **Step-by-Step Railway Deployment**

#### 1. **Prepare Your Repository**
```bash
# Make sure your code is in a Git repository
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

#### 2. **Deploy to Railway**
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your `personal_assistant` repository
5. Railway will auto-detect it's a Python app

#### 3. **Configure Environment Variables**
In Railway dashboard, go to Variables tab and add:
```
TELEGRAM_TOKEN=your-telegram-bot-token
OPENAI_API_KEY=your-openai-api-key
TELEGRAM_CHAT_ID=your-telegram-chat-id
TAVILY_API_KEY=your-tavily-api-key
```

#### 4. **Upload Google Calendar Credentials**
Since Railway has persistent storage:
1. After first deployment, use Railway CLI or file manager
2. Upload your `google_credentials.json` to `/app/data/users/alex/`
3. Or modify the app to use environment variables for OAuth

#### 5. **Domain & Health Check**
- Railway will provide a `.railway.app` domain
- Health check available at: `https://your-app.railway.app/health`

### **Monthly Costs**
- **First 500 hours:** $0
- **After 500 hours:** ~$5/month (if you exceed)
- **Typical usage for this app:** ~200-300 hours/month

---

## 🥈 **Alternative: Render.com (Free Tier)**

Good backup option, but has sleep behavior.

### **Pros & Cons**
- ✅ **Free:** 750 hours/month
- ⚠️ **Sleep Issue:** Goes to sleep after 15 minutes of inactivity
- ✅ **Easy Setup:** GitHub integration
- ⚠️ **Scheduler Impact:** Sleep behavior disrupts timing

### **Deploy to Render**
1. Go to [render.com](https://render.com)
2. Connect GitHub repository
3. Select "Web Service"
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python3 main.py`

**Note:** Sleep behavior makes this less ideal for an ADHD assistant that needs consistent timing.

---

## 🛠️ **Advanced: Google Cloud Run**

For more technical users who want pay-per-use pricing.

### **Benefits**
- ✅ **Very Low Cost:** Pay only when running (~$0-2/month)
- ✅ **Google Integration:** Easy Calendar API setup
- ✅ **Scalable:** Handles traffic spikes
- ⚠️ **Complex:** Requires Docker knowledge

### **Quick Setup**
```bash
# Install Google Cloud CLI
# Build and deploy
gcloud run deploy personal-assistant \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 🔧 **Deployment Checklist**

### **Pre-Deployment**
- [ ] All environment variables documented
- [ ] Google Calendar credentials accessible
- [ ] Requirements.txt up to date
- [ ] Health check endpoint working (`/health`)

### **Post-Deployment**
- [ ] Test Telegram bot functionality
- [ ] Verify scheduler starts automatically
- [ ] Check Google Calendar integration
- [ ] Test all `/` commands
- [ ] Monitor logs for errors

### **Environment Variables Needed**
```bash
TELEGRAM_TOKEN=bot_token_from_botfather
OPENAI_API_KEY=openai_api_key
TELEGRAM_CHAT_ID=your_telegram_chat_id
TAVILY_API_KEY=tavily_search_api_key
PORT=8080  # Set automatically by most platforms
```

---

## 📊 **Cost Comparison**

| Platform | Free Tier | Monthly Cost | Availability | Setup Difficulty |
|----------|-----------|--------------|--------------|------------------|
| **Railway.app** | 500 hours | $0-5 | 24/7 | ⭐ Easy |
| **Render.com** | 750 hours | $0 | Sleeps | ⭐ Easy |
| **Fly.io** | Generous | $0-3 | 24/7 | ⭐⭐ Medium |
| **Cloud Run** | Pay-per-use | $0-2 | 24/7 | ⭐⭐⭐ Hard |

---

## 🔍 **Monitoring & Maintenance**

### **Health Monitoring**
- Health check: `GET /health`
- Expected response: `{"status": "healthy", "service": "personal-assistant"}`

### **Logs to Monitor**
- Scheduler phase transitions
- Telegram message processing
- Google Calendar API calls
- Error patterns

### **Backup Strategy**
- User data is stored in `data/users/alex/`
- Export this folder periodically
- Google Calendar is already cloud-backed

---

## 🚨 **Troubleshooting**

### **Common Issues**
1. **Environment Variables:** Double-check all API keys
2. **File Permissions:** Ensure app can write to `data/` directory
3. **Timezone:** App uses system timezone (should be UTC in cloud)
4. **Memory Limits:** Monitor usage, upgrade if needed

### **Railway-Specific Issues**
- **Build Failures:** Check `requirements.txt` format
- **Port Issues:** Railway sets PORT automatically
- **File Storage:** Use Railway's persistent disk feature

---

## 🎯 **Next Steps After Deployment**

1. **Test Evening/Tomorrow:** Deploy tonight, test the morning cycle
2. **Monitor Performance:** Watch logs for 24-48 hours
3. **Optimize Costs:** Monitor usage to stay within free tier
4. **Backup Strategy:** Export user data weekly
5. **Scale Up:** Consider paid tier if you exceed limits

**Recommended Action:** Start with Railway.app for immediate 24/7 operation with minimal setup.