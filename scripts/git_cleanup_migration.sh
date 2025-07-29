#!/bin/bash

# Git Cleanup Migration Script
# This script helps clean up git tracking after updating .gitignore

echo "🧹 Git Cleanup Migration Script"
echo "================================"

# Function to check if directory/file is tracked
is_tracked() {
    git ls-files --error-unmatch "$1" &>/dev/null
    return $?
}

# Clean up hive-mind directory
if [ -d ".hive-mind" ]; then
    if is_tracked ".hive-mind"; then
        echo "📦 Removing .hive-mind from git tracking..."
        git rm -r --cached .hive-mind
    else
        echo "✅ .hive-mind is already untracked"
    fi
else
    echo "ℹ️  .hive-mind directory not found"
fi

# Clean up swarm directory
if [ -d ".swarm" ]; then
    if is_tracked ".swarm"; then
        echo "📦 Removing .swarm from git tracking..."
        git rm -r --cached .swarm
    else
        echo "✅ .swarm is already untracked"
    fi
else
    echo "ℹ️  .swarm directory not found"
fi

# Clean up root level test files
echo ""
echo "🔍 Checking for root level test_*.py files..."
for file in test_*.py; do
    if [ -f "$file" ]; then
        if is_tracked "$file"; then
            echo "📦 Removing $file from git tracking..."
            git rm --cached "$file"
        else
            echo "✅ $file is already untracked"
        fi
    fi
done

# Check for any other files that should be untracked
echo ""
echo "🔍 Checking for other temporary files..."

# Cleanup any .pyc files if tracked (shouldn't be, but just in case)
tracked_pyc=$(git ls-files "*.pyc" 2>/dev/null)
if [ -n "$tracked_pyc" ]; then
    echo "⚠️  Found tracked .pyc files, removing..."
    git rm --cached $tracked_pyc
fi

# Show current git status
echo ""
echo "📊 Current git status:"
git status --short

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Next steps:"
echo "1. Review the changes with: git status"
echo "2. Commit the changes with: git commit -m 'chore: update .gitignore and clean tracked files'"
echo "3. Push to remote: git push"