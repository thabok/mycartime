#!/bin/bash
# Bumps the app version, commits and pushes the frontend submodule, then
# commits (incl. the updated submodule pointer), tags and pushes the main repo.
#
# AGENTS: never run this script unless the user explicitly asks for a release.
# It stages everything (git add -A) and pushes to the remotes.
#
# Usage: ./scripts/release.sh <version> <message>
#   version: digits only, e.g. "1.0.0" (tag: "v1.0.0")
set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <version> <message>" >&2
    exit 1
fi

VERSION="$1"
MESSAGE="$2"

if ! [[ "$VERSION" =~ ^[0-9]+(\.[0-9]+)*$ ]]; then
    echo "Invalid version '$VERSION': expected numbers like 1.0.0 (no 'v' prefix)." >&2
    exit 1
fi

TAG="v$VERSION"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/src/frontend"

if git -C "$ROOT_DIR" rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    echo "Tag $TAG already exists, aborting before anything is committed." >&2
    exit 1
fi

# Bump the version in every place the app carries it (first match only where
# the file has other "version" keys, e.g. dependencies).
export VERSION
SRC_DIR="$ROOT_DIR/src"
perl -0pi -e 's/("name": "mycartime",[^{}]*?"version": ")[^"]*/$1$ENV{VERSION}/g' \
    "$SRC_DIR/package.json" "$SRC_DIR/package-lock.json"
perl -0pi -e 's/^(version = ")[^"]*/$1$ENV{VERSION}/m' "$SRC_DIR/src-tauri/Cargo.toml"
perl -0pi -e 's/(name = "mycartime"\nversion = ")[^"]*/$1$ENV{VERSION}/' "$SRC_DIR/src-tauri/Cargo.lock"
perl -0pi -e 's/("version": ")[^"]*/$1$ENV{VERSION}/' "$SRC_DIR/src-tauri/tauri.conf.json"

# Frontend: commit (if there is anything) and push. HEAD:main also works when
# the submodule is in detached-HEAD state.
git -C "$FRONTEND_DIR" add -A
if ! git -C "$FRONTEND_DIR" diff --cached --quiet; then
    git -C "$FRONTEND_DIR" commit -m "$MESSAGE"
else
    echo "Frontend: nothing to commit."
fi
git -C "$FRONTEND_DIR" pull --rebase origin main
git -C "$FRONTEND_DIR" push origin HEAD:main

# Main repo: includes the updated submodule pointer.
git -C "$ROOT_DIR" add -A
if ! git -C "$ROOT_DIR" diff --cached --quiet; then
    git -C "$ROOT_DIR" commit -m "$MESSAGE"
else
    echo "Main repo: nothing to commit, tagging the current HEAD."
fi
git -C "$ROOT_DIR" tag "$TAG"
git -C "$ROOT_DIR" push origin HEAD "$TAG"
