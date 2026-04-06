# Email Triage Environment - Deployment Guide

This guide walks through deploying the Email Triage OpenEnv environment to Hugging Face Spaces.

## Prerequisites

- GitHub account with repository created
- Hugging Face account (https://huggingface.co)
- Git CLI installed locally
- Docker installed (for local testing)

## Step 1: Prepare Repository

Ensure all files are committed:

```bash
git status
git add .
git commit -m "Initial Email Triage Environment OpenEnv submission"
```

Required files (already in place):
- `openenv.yaml` - Environment specification
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration
- `README.md` - Comprehensive documentation
- `inference.py` - Baseline inference script
- `email_triage_env/` - Core environment package
- `scripts/validate.py` - Pre-submission validator
- `.dockerignore` - Docker build optimization

## Step 2: Test Locally

### Test Environment Functionality

```bash
# Install dependencies
pip install pydantic pyyaml

# Run validation script
python scripts/validate.py

# Run local environment tests
python scripts/test_local.py
```

Expected output: All checks pass, 3 tasks functional.

### Test Docker Build

```bash
# Build image
docker build -t email-triage:latest .

# Run container
docker run -p 7860:7860 \
  -e OPENAI_API_KEY="test-key" \
  email-triage:latest
```

### Test API Endpoints

```bash
# In another terminal
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{}'

curl http://localhost:7860/api/health
```

## Step 3: Set Up Hugging Face Space

### Create Space on HF

1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Fill in:
   - **Owner**: Your username or organization
   - **Space name**: `email-triage-env` (or preferred name)
   - **License**: MIT
   - **Space SDK**: Docker
   - **Visibility**: Public (required for evaluation)
4. Click "Create Space"

### Push Repository to HF

```bash
# Add HF remote
git remote add hf https://huggingface.co/spaces/<username>/<space-name>

# Push to HF (authenticates via HF credentials)
git push hf main

# Or if using main branch:
git push hf HEAD:main
```

HF will automatically build and deploy the Docker image.

### Monitor Deployment

1. Go to your Space URL: `https://huggingface.co/spaces/<username>/<space-name>`
2. Check "Docker" tab for build logs
3. Wait for "Space is running" status
4. Click Space URL to test

## Step 4: Validate Deployment

### Test HF Space API

```bash
SPACE_URL="https://your-space.hf.space"

# Test reset endpoint
curl -X POST ${SPACE_URL}/reset \
  -H "Content-Type: application/json" \
  -d '{}'

# Test health endpoint
curl ${SPACE_URL}/api/health
```

### Test with Inference Script

```bash
# Set environment variables
export OPENAI_API_KEY="your-key"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export API_BASE_URL="https://router.huggingface.co/v1"
export TASK_NAME="multiclass_medium"

# Run baseline inference (this will make real API calls)
python inference.py
```

Expected stdout format:
```
[START] task=multiclass_medium env=email-triage-v1 model=...
[STEP] step=1 action=... reward=0.00 done=false error=null
...
[END] success=true steps=20 score=0.72 rewards=0.00,...
```

## Step 5: Submit to Scaler Platform

### Pre-Submission Checklist

Run the pre-submission validator:

```bash
python scripts/validate.py
```

All should pass:
- [✓] File structure complete
- [✓] openenv.yaml valid
- [✓] All imports work
- [✓] inference.py has required logging
- [✓] Dockerfile builds
- [✓] Requirements complete
- [✓] README has all sections
- [✓] Environment functions correctly
- [✓] 3 tasks with graders

### Manual Verification

1. **HF Space Running**: Visit space URL and verify it responds
2. **OpenEnv CLI**: Run `openenv validate` (if installed)
3. **Docker Build**: Verify Dockerfile builds locally
4. **Baseline**: Run inference.py and verify it completes
5. **Tasks**: All 3 tasks executable and return scores 0.0-1.0

### Submission Form

Go to: https://www.scaler.com/openenv

Fill in:
- **Environment Name**: Email Triage v1
- **GitHub Repo**: (if applicable)
- **HF Space URL**: https://huggingface.co/spaces/<username>/<space-name>
- **Description**: Real-world email classification and triage task
- **Model Used**: Reference implementation uses Qwen 2.5
- **Paper/Blog** (optional): Link to any documentation

Click "Submit"

## Troubleshooting

### Docker Build Fails

```bash
# Check what's needed
pip list | grep -E 'pydantic|openai'

# Install missing packages
pip install -r requirements.txt

# Try building locally first
docker build --progress=plain -t email-triage:test .
```

### Space Not Responding

1. Check Space logs on HF website
2. Ensure Dockerfile cmd is correct
3. Verify port 7860 is exposed  
4. Check server.py has no syntax errors
5. Restart space from settings

### Inference Script Fails

1. Check API key is valid: `echo $OPENAI_API_KEY`
2. Verify model name: `$MODEL_NAME`
3. Test API directly: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $API_KEY"`
4. Check Python environment: `python scripts/test_local.py`
5. Run with debug: `python -u inference.py 2>&1`

### Validation Script Issues

```bash
# Re-run with verbose output
python scripts/validate.py 2>&1 | tee validation.log

# Check file encodings if text issues
file README.md openenv.yaml

# Verify JSON/YAML syntax
python -m json.tool < file.json  # if JSON
python -c "import yaml; yaml.safe_load(open('openenv.yaml'))"
```

## Performance Optimization

For machines with limited resources (2 vCPU, 8GB RAM):

1. **Reduce Batch Size**: Modify `max_steps=10` in inference.py
2. **Use Simpler Model**: Try smaller model than Qwen 72B
3. **Cache Results**: Store API responses if running multiple times
4. **Timeout Settings**: Increase from 30s if getting timeouts

## Monitoring

After deployment, monitor:

1. **Space Activity**: Check HF Spaces dashboard for usage stats
2. **API Logs**: Monitor /logs endpoint if exposed
3. **Success Rate**: Track score distribution across runs
4. **Error Rates**: Monitor for API failures or timeout issues

## Support

If issues occur:

1. Check this guide's Troubleshooting section
2. Review README.md for environment details
3. Check OpenEnv official docs: https://docs.open-env.io/
4. Review Hugging Face Spaces docs: https://huggingface.co/docs/hub/spaces

---

**Deployment ready! You can now proceed to submit your environment.**
