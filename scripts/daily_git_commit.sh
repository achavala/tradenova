#!/bin/bash
#
# Daily Git Commit Script for TradeNova
# Automatically commits and pushes changes to GitHub daily
#
# This script:
# 1. Checks if there are changes to commit
# 2. Adds all changes (respecting .gitignore)
# 3. Commits with timestamp
# 4. Pushes to GitHub
# 5. Logs the activity
#

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Log file
LOG_FILE="$PROJECT_DIR/logs/git_auto_commit.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Daily Git Commit Started ==="

# Check if git is initialized
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log "ERROR: Not a git repository. Exiting."
    exit 1
fi

# Check if remote is configured
if ! git remote get-url origin > /dev/null 2>&1; then
    log "ERROR: No remote 'origin' configured. Exiting."
    exit 1
fi

# Check if there are any changes
if git diff --quiet && git diff --cached --quiet; then
    # Check if there are untracked files (that aren't ignored)
    if [ -z "$(git ls-files --others --exclude-standard)" ]; then
        log "No changes to commit. Repository is up to date."
        exit 0
    fi
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
log "Current branch: $CURRENT_BRANCH"

# Add all changes (respecting .gitignore)
log "Adding changes..."
git add -A

# Check if there are staged changes
if git diff --cached --quiet; then
    log "No staged changes. Nothing to commit."
    exit 0
fi

# Create commit message with timestamp
COMMIT_DATE=$(date '+%Y-%m-%d %H:%M:%S')
COMMIT_MESSAGE="Daily auto-commit: $COMMIT_DATE

Automated daily commit:
- Updated project files
- Preserved working state
- Timestamp: $COMMIT_DATE"

# Commit changes
log "Committing changes..."
if git commit -m "$COMMIT_MESSAGE"; then
    log "Commit successful."
else
    log "ERROR: Commit failed."
    exit 1
fi

# Push to remote
log "Pushing to origin/$CURRENT_BRANCH..."
if git push origin "$CURRENT_BRANCH"; then
    log "Push successful."
    log "=== Daily Git Commit Completed Successfully ==="
    exit 0
else
    log "ERROR: Push failed. Changes are committed locally but not pushed."
    log "You may need to push manually: git push origin $CURRENT_BRANCH"
    exit 1
fi

