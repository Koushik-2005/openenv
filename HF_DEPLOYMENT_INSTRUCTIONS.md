# HuggingFace Spaces Deployment Guide

## Quick Start - Two Options

### **OPTION A: Using GitHub (Recommended for HF)**

1. **Create GitHub Repository**
   ```bash
   # Go to https://github.com/new
   # Create repo: email-triage-env
   # Initialize with README (optional)
   ```

2. **Add GitHub Remote & Push**
   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/email-triage-env.git
   git branch -M main
   git push -u origin main
   ```

3. **Create HF Space Connected to GitHub**
   - Go to: https://huggingface.co/spaces
   - Click "Create new Space"
   - Name: `email-triage-env`
   - License: MIT
   - SDK: Docker
   - Visibility: Public
   - **Repository URL**: Paste GitHub repo URL
   - Click "Create Space"
   
   HF will automatically clone from GitHub and build!

---

### **OPTION B: Direct Push to HuggingFace (Faster)**

1. **Get HF Token**
   - Go to: https://huggingface.co/settings/tokens
   - Create new token (write access)
   - Copy token

2. **Create HF Space First**
   - Go to: https://huggingface.co/spaces
   - Click "Create new Space"
   - Name: `email-triage-env`
   - License: MIT
   - SDK: Docker
   - Visibility: Public
   - Click "Create Space"

3. **Add HF Remote & Push**
   ```powershell
   # Set your HF username
   $HF_USERNAME = "your-hf-username"
   $HF_TOKEN = "your-hf-token-from-step-1"
   
   # Add remote
   git remote add hf https://huggingface.co/spaces/$HF_USERNAME/email-triage-env
   
   # Stage credentials (optional, or will prompt)
   git config credential.helper store
   
   # Push to HF
   git push hf main
   # When prompted for password, use: $HF_TOKEN
   ```

---

## After Deployment

1. Wait for build to complete (check Space settings: Docker)
2. Once "Space is running", visit your Space URL
3. Test the API:
   ```powershell
   curl -Uri https://your-username-email-triage-env.hf.space/api/health -Method GET
   ```

4. Test reset:
   ```powershell
   curl -Uri https://your-username-email-triage-env.hf.space/reset `
     -Method POST `
     -ContentType "application/json" `
     -Body '{}'
   ```

---

## Local Repository is Now Ready

Your local git repository contains:
- ✅ All environment code
- ✅ Full documentation
- ✅ Validation scripts
- ✅ Baseline inference
- ✅ Docker configuration
- ✅ OpenEnv specification

Next: Push to GitHub or HF Spaces using commands above.
