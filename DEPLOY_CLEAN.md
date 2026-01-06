# Clean Deployment Instructions

## Issues Fixed

1. ✅ **Enhanced .dockerignore** - More comprehensive exclusions
2. ✅ **Dockerfile cleanup** - Explicit removal of large files
3. ✅ **CMD syntax** - Fixed backslash continuation issue
4. ✅ **fly.toml** - Single process configuration

## Deployment Steps

### Step 1: Clean Build (Important!)
```bash
# Build locally to verify image size
docker build --no-cache -t tradenova-test .
docker images | grep tradenova-test
```

**Expected**: Image should be < 600 MB

### Step 2: Deploy to Fly.io
```bash
fly deploy --no-cache --wait-timeout 300
```

The `--no-cache` flag ensures Docker doesn't use cached layers that might include large files.

### Step 3: Watch Logs
```bash
fly logs --app tradenova
```

**Expected output:**
```
Starting Streamlit server...
You can now view your Streamlit app in your browser.
```

### Step 4: Set Memory (After First Successful Deploy)
```bash
fly scale memory 1024 --app tradenova
```

### Step 5: Verify
```bash
# Check status
fly status

# Access dashboard
open https://tradenova.fly.dev
```

## If Image Still Large

If the image is still > 1 GB after `--no-cache` build:

1. **Check what's being included:**
   ```bash
   docker run --rm tradenova-test du -sh /app/data /app/models 2>/dev/null || echo "Directories excluded"
   ```

2. **Verify .dockerignore is being read:**
   ```bash
   docker build --no-cache -t tradenova-test . 2>&1 | grep -i "excluding\|sending"
   ```

3. **Check build context size:**
   ```bash
   du -sh .
   ```

## Troubleshooting "2 machines" Issue

If Fly still tries to create 2 machines:

1. **Check fly.toml has only ONE [http_service]:**
   ```bash
   grep -c "\[http_service\]" fly.toml
   ```
   Should output: `1`

2. **Remove any old process groups:**
   ```bash
   # Check for process definitions
   grep -i "process" fly.toml
   ```

3. **Redeploy:**
   ```bash
   fly deploy --no-cache --wait-timeout 300
   ```

## Expected Results

- ✅ Image size: < 600 MB
- ✅ Single machine created
- ✅ Dashboard accessible
- ✅ Logs show Streamlit startup
- ✅ No timeout errors




