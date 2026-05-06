# Surgical Billing Automation - GitHub + Railway Deployment Guide

Complete step-by-step instructions to deploy the surgical billing application to the cloud using GitHub and Railway.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Part 1: Prepare Your Local Code](#part-1-prepare-your-local-code)
3. [Part 2: Create GitHub Repository](#part-2-create-github-repository)
4. [Part 3: Set Up Railway Project](#part-3-set-up-railway-project)
5. [Part 4: Deploy to Railway](#part-4-deploy-to-railway)
6. [Part 5: Configure Tesseract-OCR](#part-5-configure-tesseract-ocr)
7. [Part 6: Test Your Deployment](#part-6-test-your-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, you need:

- **GitHub Account** (free at https://github.com)
- **Railway Account** (free at https://railway.app)
- **Git installed** on your computer (https://git-scm.com)
- **Local project folder** with all application files

### Verify Your Installed Files

Your `C:\Users\kv8n11\Downloads\culver` folder should contain:

```
culver/
├── app.py                    # Flask web application
├── surgical_billing_extractor.py
├── billing_form_generator.py
├── templates/
│   └── index.html           # Web interface
├── requirements.txt         # Python dependencies
├── Procfile                 # Railway configuration
├── runtime.txt              # Python version specification
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
└── DEPLOYMENT_GUIDE.md      # This file
```

---

## Part 1: Prepare Your Local Code

### Step 1.1: Open Command Prompt

Press `Win + R`, type `cmd`, and press Enter.

### Step 1.2: Navigate to Your Project

```bash
cd C:\Users\kv8n11\Downloads\culver
```

### Step 1.3: Initialize Git Repository (if not already done)

```bash
git init
```

You should see:
```
Initialized empty Git repository in C:\Users\kv8n11\Downloads\culver\.git\
```

### Step 1.4: Configure Git (first time only)

```bash
git config --global user.name "Your Name"
git config --global user.email "kadenvu@outlook.com"
```

Replace "Your Name" with your actual name.

### Step 1.5: Add All Files to Git

```bash
git add .
```

### Step 1.6: Create Initial Commit

```bash
git commit -m "Initial commit: surgical billing application"
```

You should see output like:
```
[master (root-commit) abc1234] Initial commit: surgical billing application
 8 files changed, 1000 insertions(+)
```

---

## Part 2: Create GitHub Repository

### Step 2.1: Go to GitHub

Open https://github.com and sign in with your account.

### Step 2.2: Create New Repository

1. Click the **+** icon in the top right corner
2. Select **New repository**
3. Fill in the details:
   - **Repository name:** `surgical-billing-app`
   - **Description:** `Surgical billing automation with OCR extraction and CMS-1500/UB-04 generation`
   - **Public/Private:** Public (required for free Railway deployment)
   - **Initialize with README:** NO (we already have files)
   - **Add .gitignore:** NO (we already have one)
   - **Add license:** Optional

4. Click **Create repository**

### Step 2.3: Connect Local Repository to GitHub

GitHub will show you commands. Copy the HTTPS link from the line:
```
git remote add origin https://github.com/YOUR_USERNAME/surgical-billing-app.git
```

Run this in Command Prompt:
```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/surgical-billing-app.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

### Step 2.4: Verify Upload

Go to your GitHub repository URL: `https://github.com/YOUR_USERNAME/surgical-billing-app`

You should see all your files listed there.

---

## Part 3: Set Up Railway Project

### Step 3.1: Create Railway Account

Go to https://railway.app and click **Start Project** (free option available).

### Step 3.2: Create New Project

1. Click **Create a new project**
2. Select **Deploy from GitHub repo**
3. Click **Configure GitHub App**

### Step 3.3: Authorize Railway with GitHub

1. Click **Install Railway on GitHub**
2. Select your GitHub account
3. Choose to install on:
   - **All repositories** (easier), OR
   - **Only select repositories** (select `surgical-billing-app`)
4. Click **Install & Authorize**

### Step 3.4: Select Your Repository

After authorization, Railway will show your repositories:
1. Search for and select **surgical-billing-app**
2. Click **Deploy**

Railway will automatically detect it's a Python project and begin deployment.

---

## Part 4: Deploy to Railway

### Step 4.1: Monitor Initial Deployment

Railway will start deploying. You'll see:

```
Building surgical-billing-app...
Installing dependencies from requirements.txt...
Installing Python 3.11.0...
```

This takes **2-5 minutes**. Watch the **Build Logs** tab.

### Step 4.2: Wait for Deployment Complete

When complete, you'll see:
```
✓ Deployment successful
Your app is running at: https://surgical-billing-app-prod.up.railway.app
```

Note your app URL (it will be different from this example).

### Step 4.3: Test Initial Deployment

Open your app URL in a browser. You should see the Surgical Billing interface load.

**If you see an error**, go to Part 5 (Tesseract configuration) before testing.

---

## Part 5: Configure Tesseract-OCR

Tesseract-OCR must be installed on the Railway server to perform document scanning.

### Step 5.1: Create Dockerfile (for Tesseract)

In your `C:\Users\kv8n11\Downloads\culver` folder, create a new file called `Dockerfile`:

1. Right-click in the folder
2. New → Text Document
3. Name it `Dockerfile` (no extension)
4. Paste this content:

```dockerfile
FROM python:3.11-slim

# Install Tesseract-OCR and other system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "app:app"]
```

### Step 5.2: Push Dockerfile to GitHub

In Command Prompt:
```bash
cd C:\Users\kv8n11\Downloads\culver
git add Dockerfile
git commit -m "Add Dockerfile with Tesseract-OCR support"
git push origin main
```

### Step 5.3: Configure Railway to Use Docker

1. Go to your Railway project dashboard
2. Click on your **surgical-billing-app** service
3. Go to **Settings**
4. Find **Docker** section
5. Ensure **Dockerfile** is selected as the build method

Railway will automatically detect and use your Dockerfile for the next deployment.

### Step 5.4: Trigger Redeployment

1. Go back to **Deployments** tab
2. Click **Redeploy**
3. Watch the build logs—installing Tesseract may take **3-5 minutes**

When complete, you'll see:
```
✓ Deployment successful with Tesseract-OCR installed
```

---

## Part 6: Test Your Deployment

### Step 6.1: Access Your Live App

Open your Railway app URL in a browser.

### Step 6.2: Test Upload Function

1. Click **Choose Files** or drag-and-drop a test document (PDF, PNG, JPG)
2. Click **Process Case**
3. Wait for processing (OCR extraction may take 10-30 seconds depending on document quality)

### Step 6.3: Verify Results

You should see:
- **Patient Info tab**: Extracted patient name, DOB, SSN
- **Insurance tab**: Insurance member ID, group number, plan type
- **Procedure tab**: Procedure name, date, CPT codes, diagnosis codes
- **Provider tab**: Surgeon name, NPI, facility information
- **Charges tab**: Base charge, anesthesia charge, facility charge
- **CMS-1500 tab**: Draft billing form
- **UB-04 tab**: Draft facility billing form

### Step 6.4: Test Export

1. Click **Export to JSON** button
2. Verify the JSON file downloads with extracted data

---

## Troubleshooting

### Issue: "No module named 'pytesseract'" or OCR fails

**Solution:**
1. Check that Dockerfile was properly committed and pushed
2. In Railway Dashboard, go to **Settings** → check Docker is enabled
3. Redeploy the application
4. Check deployment logs for Tesseract installation

### Issue: App loads but processing fails

**Check the browser console:**
1. Press `F12` to open Developer Tools
2. Go to **Console** tab
3. Look for error messages
4. Try uploading a simpler document (single page PDF)

### Issue: "413 Payload Too Large"

**Solution:** The file is larger than 50MB
- Upload a smaller document (under 50MB)
- Contact support if legitimate large files need to be processed

### Issue: Deployment takes very long

**What's normal:**
- Initial deployment: 3-5 minutes
- With Tesseract installation: 5-10 minutes

**If stuck over 15 minutes:**
1. Go to **Deployments** tab
2. Click the failed deployment
3. Check **Build Logs** for errors
4. Click **Redeploy** to try again

### Issue: Railway showing "Railway is out of credit"

**Solution:**
Railway provides free compute hours monthly. If exceeded:
1. Go to **Account Settings**
2. Check usage
3. Either wait for monthly reset or upgrade to paid plan

---

## Manual Testing (Advanced)

To test locally before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Open browser to http://localhost:5000
```

---

## Environment Variables (Optional)

If needed, set environment variables in Railway:

1. Go to your service **Settings**
2. Scroll to **Variables**
3. Add:
   - `FLASK_ENV`: `production`
   - `FLASK_DEBUG`: `False`

---

## Next Steps

Once deployed and tested:

1. **Share your app:** Send the Railway URL to users
2. **Monitor performance:** Check Railway Dashboard for usage
3. **Update code:** Push changes to GitHub, Railway auto-redeploys
4. **Scale up:** If needed, upgrade Railway plan for more resources

---

## Quick Reference Commands

```bash
# Check git status
git status

# View commit history
git log --oneline

# Push changes to GitHub
git add .
git commit -m "Your message"
git push origin main

# Check local app
python app.py
```

---

**Support:** If you encounter issues not covered here, check:
- Railway docs: https://docs.railway.app
- GitHub docs: https://docs.github.com
- Flask docs: https://flask.palletsprojects.com
- Tesseract docs: https://github.com/UB-Mannheim/tesseract/wiki
