# TradeNova Scripts

This directory contains utility scripts for TradeNova.

## Daily Git Commit Automation

Automatically commits and pushes changes to GitHub daily.

### Files

- `daily_git_commit.sh` - Main commit script
- `install_daily_commit.sh` - Installation script (macOS)
- `uninstall_daily_commit.sh` - Uninstallation script
- `com.tradenova.dailycommit.plist` - Launchd configuration template

### Quick Start

```bash
# Install (runs daily at 6:00 PM)
./scripts/install_daily_commit.sh

# Test manually
./scripts/daily_git_commit.sh

# Uninstall
./scripts/uninstall_daily_commit.sh
```

### Documentation

See `DAILY_GIT_COMMIT_SETUP.md` for full documentation.

