# Daily Git Commit Automation Setup

This guide explains how to set up automatic daily commits and pushes to GitHub for TradeNova.

## Overview

The daily git commit automation:
- ✅ Automatically commits all changes daily at 6:00 PM
- ✅ Pushes to GitHub automatically
- ✅ Respects `.gitignore` (won't commit sensitive files)
- ✅ Logs all activity
- ✅ Works on macOS using launchd

## Quick Start

### 1. Install the Automation

```bash
cd /Users/chavala/TradeNova
./scripts/install_daily_commit.sh
```

This will:
- Create a macOS launchd job
- Schedule daily commits at 6:00 PM
- Set up logging

### 2. Test Manually

Test the script before relying on automation:

```bash
./scripts/daily_git_commit.sh
```

### 3. Check Status

Check if the automation is running:

```bash
launchctl list | grep tradenova
```

### 4. View Logs

View the commit logs:

```bash
tail -f logs/git_auto_commit.log
```

## How It Works

### The Script (`scripts/daily_git_commit.sh`)

The script:
1. Checks if there are changes to commit
2. Adds all changes (respecting `.gitignore`)
3. Creates a commit with timestamp
4. Pushes to GitHub
5. Logs all activity

### The Schedule

- **Time**: Daily at 6:00 PM (18:00)
- **Method**: macOS launchd (system scheduler)
- **Location**: `~/Library/LaunchAgents/com.tradenova.dailycommit.plist`

### What Gets Committed

✅ **Will be committed:**
- All code files (`.py`, `.sh`, `.md`, etc.)
- Configuration files (except `.env`)
- Documentation
- Scripts

❌ **Will NOT be committed** (protected by `.gitignore`):
- `.env` files (API keys, secrets)
- `venv/` (virtual environment)
- `*.log` files
- `daily_balance.json`
- `__pycache__/`
- `*.pyc` files

## Configuration

### Change the Schedule

Edit the plist file to change the time:

```bash
# Edit the plist
nano ~/Library/LaunchAgents/com.tradenova.dailycommit.plist

# Change Hour and Minute:
#   <key>Hour</key>
#   <integer>18</integer>  # 6 PM
#   <key>Minute</key>
#   <integer>0</integer>

# Reload
launchctl unload ~/Library/LaunchAgents/com.tradenova.dailycommit.plist
launchctl load ~/Library/LaunchAgents/com.tradenova.dailycommit.plist
```

Or reinstall with the updated plist:

```bash
./scripts/install_daily_commit.sh
```

### Change Commit Message

Edit `scripts/daily_git_commit.sh` and modify the `COMMIT_MESSAGE` variable.

## Troubleshooting

### Script Not Running

1. **Check if job is loaded:**
   ```bash
   launchctl list | grep tradenova
   ```

2. **Check logs:**
   ```bash
   tail -f logs/git_auto_commit.log
   tail -f logs/git_auto_commit_stderr.log
   ```

3. **Test manually:**
   ```bash
   ./scripts/daily_git_commit.sh
   ```

### Push Fails

If push fails (e.g., authentication issues):
- The commit will still be made locally
- You'll need to push manually: `git push origin main`
- Check your SSH keys or GitHub credentials

### Too Many Commits

If you want to reduce commit frequency:
- Change the schedule in the plist file
- Or uninstall and commit manually

## Uninstall

To remove the automation:

```bash
./scripts/uninstall_daily_commit.sh
```

This will:
- Unload the launchd job
- Remove the plist file
- Stop automatic commits

## Manual Commits

You can still commit manually anytime:

```bash
git add -A
git commit -m "Your message"
git push origin main
```

The automation won't interfere with manual commits.

## Security Notes

✅ **Safe:**
- `.gitignore` protects sensitive files
- `.env` files are never committed
- API keys are excluded

⚠️ **Important:**
- Always review `.gitignore` before installing
- Never commit `.env` files manually
- Use SSH keys for GitHub (not passwords)

## Files Created

- `scripts/daily_git_commit.sh` - Main commit script
- `scripts/com.tradenova.dailycommit.plist` - Launchd configuration
- `scripts/install_daily_commit.sh` - Installation script
- `scripts/uninstall_daily_commit.sh` - Uninstallation script
- `logs/git_auto_commit.log` - Activity log
- `~/.Library/LaunchAgents/com.tradenova.dailycommit.plist` - System job

## Support

If you encounter issues:
1. Check the logs: `logs/git_auto_commit.log`
2. Test manually: `./scripts/daily_git_commit.sh`
3. Verify git remote: `git remote -v`
4. Check SSH keys: `ssh -T git@github.com`

---

**Status**: ✅ Ready to install

**Next Step**: Run `./scripts/install_daily_commit.sh`

