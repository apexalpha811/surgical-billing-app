# Quick Start: Deploy to Railway in 5 Minutes

## The 5-Minute Version

### 1. Push to GitHub (2 minutes)

```bash
cd C:\Users\kv8n11\Downloads\culver
git init
git config --global user.name "Your Name"
git config --global user.email "kadenvu@outlook.com"
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/surgical-billing-app.git
git push -u origin main
```

**Replace `YOUR_USERNAME` with your GitHub username**

### 2. Deploy to Railway (3 minutes)

1. Go to https://railway.app
2. Sign up / Log in
3. Click **New Project** → **Deploy from GitHub**
4. Authorize Railway, select your `surgical-billing-app` repository
5. Click **Deploy**
6. Wait 5 minutes for deployment to complete

### 3. Add Tesseract Support

1. Create `Dockerfile` in your folder with content from our provided Dockerfile
2. Push to GitHub:
```bash
git add Dockerfile
git commit -m "Add Tesseract support"
git push origin main
```
3. In Railway Dashboard, click **Redeploy**
4. Wait 5 minutes

### 4. Test Your App

1. Railway shows your app URL like: `https://surgical-billing-app-prod.up.railway.app`
2. Open that URL in a browser
3. Upload a test document and process it

## Done! 🎉

Your surgical billing app is now live on the internet.

---

## Detailed Instructions?

Read `DEPLOYMENT_GUIDE.md` for step-by-step guidance with screenshots and troubleshooting.

## Need Help?

- **Deployment issues?** Check Railway logs (Deployments tab)
- **Code issues?** Check browser console (F12)
- **Tesseract not working?** Make sure Dockerfile is deployed and you've redeployed
