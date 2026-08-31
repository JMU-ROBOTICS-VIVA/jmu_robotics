#!/usr/bin/env bash

set -euo pipefail

# Make sure required commands are available.
if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is not installed."
    exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
    echo "ERROR: GitHub CLI (gh) is not installed."
    exit 1
fi

echo "Logging in to GitHub..."
echo

gh auth login \
    --hostname github.com \
    --git-protocol https \
    --web

# Configure Git to use the GitHub CLI for HTTPS authentication.
gh auth setup-git --hostname github.com

# Get identity information from the authenticated GitHub account.
GIT_NAME=$(gh api user --jq '.name // ""')
GITHUB_LOGIN=$(gh api user --jq '.login')
GITHUB_ID=$(gh api user --jq '.id')

# GitHub profiles are not required to contain a display name.
if [ -z "$GIT_NAME" ]; then
    echo
    echo "Your GitHub profile does not contain a display name."
    printf "Enter your full name (for Git commits): "
    read -r GIT_NAME
fi

# Use GitHub's private noreply address rather than exposing the
# student's actual email address in Git commit history.
GIT_EMAIL="${GITHUB_ID}+${GITHUB_LOGIN}@users.noreply.github.com"

# Configure the identity recorded in Git commits.
git config --global --replace-all user.name "$GIT_NAME"
git config --global --replace-all user.email "$GIT_EMAIL"

echo
echo "GitHub login and Git configuration complete."
echo
echo "GitHub account:  $GITHUB_LOGIN"
echo "Commit name:     $GIT_NAME"
echo "Commit email:    $GIT_EMAIL"

