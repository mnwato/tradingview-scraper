#!/bin/bash
set -e

# Configuration
# Default to the publishable "latest" symlink.
SUMMARY_DIR="${SUMMARY_DIR:-artifacts/summaries/latest}"
GIST_ID="${GIST_ID:-e888e1eab0b86447c90c26e92ec4dc36}"
TEMP_DIR=".temp_gist_$(date +%s)"

# Safety: avoid wiping the remote gist when summaries are absent/empty.
# `rsync --delete` mirrors local state, so an empty directory would delete everything.
if [ ! -d "$SUMMARY_DIR" ]; then
    echo "ℹ️ '$SUMMARY_DIR/' not found; skipping Gist sync."
    exit 0
fi

if ! compgen -G "$SUMMARY_DIR/*" > /dev/null; then
    if [ "${GIST_ALLOW_EMPTY:-0}" = "1" ]; then
        echo "⚠️ '$SUMMARY_DIR/' is empty; proceeding because GIST_ALLOW_EMPTY=1."
    else
        echo "⚠️ '$SUMMARY_DIR/' is empty; skipping Gist sync to avoid deleting remote files."
        echo "   Set GIST_ALLOW_EMPTY=1 to override."
        exit 0
    fi
fi

if [ -z "$GIST_ID" ]; then
    echo "Error: GIST_ID not set. Please provide it as an environment variable."
    exit 1
fi

echo "🚀 Syncing summaries to Gist: $GIST_ID"

# 1. Clone the gist repository
git clone "https://gist.github.com/$GIST_ID.git" "$TEMP_DIR"

# 2. Sync files from SUMMARY_DIR to the temp dir
# Gist does not support directories, so we flatten all subdirectories.
# We first remove everything in the temp dir except .git to handle deletions.
find "$TEMP_DIR" -mindepth 1 -maxdepth 1 -not -name '.git' -exec rm -rf {} +
# Then copy and flatten all files from SUMMARY_DIR, excluding binaries
# Use -L to follow symlinks (like 'latest')
find -L "$SUMMARY_DIR" -type f -not -path '*/.*' -not -name '*.pkl' -exec cp {} "$TEMP_DIR/" \;

# 3. Commit and push
cd "$TEMP_DIR"
git add -A
if git diff --staged --quiet; then
    echo "✅ No changes to push."
else
    git commit -m "update portfolio summaries - $(date +'%Y-%m-%d %H:%M:%S')"
    git push
    echo "✅ Successfully updated Gist."
fi

# 4. Cleanup
cd ..
rm -rf "$TEMP_DIR"
