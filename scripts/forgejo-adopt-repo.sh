#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    echo "Usage: forgejo-adopt-repo.sh <repo_path> <forgejo_repo_name> [github_repo_url]" >&2
    exit 1
fi

REPO_PATH="$1"
FORGE_NAME="$2"
GITHUB_URL="${3:-}"
FORGE_BASE_URL="${LOCAL_FORGE_URL:-http://100.94.10.36:3002}"
FORGEJO_URL="${FORGE_BASE_URL%/}/api/v1"
FORGE_ORG="${LOCAL_FORGE_ORG:-cha0tik}"
FORGE_SSH="git@cha0tikforge:${FORGE_ORG}/${FORGE_NAME}.git"
REAL_HOME="${REAL_HOME:-${DINO_HOME:-/home/dino}}"
VAULT="$REAL_HOME/.vault/vault.sh"

if [ ! -d "$REPO_PATH/.git" ]; then
    echo "Not a git repo: $REPO_PATH" >&2
    exit 1
fi

if [ -z "$GITHUB_URL" ]; then
    GITHUB_URL="$(git -C "$REPO_PATH" remote get-url origin 2>/dev/null || true)"
fi

if [ -z "$GITHUB_URL" ]; then
    echo "No GitHub URL provided and origin is missing" >&2
    exit 1
fi

PASS="$("$VAULT" get forgejo_admin_password)"

curl -sf -u dino:"$PASS" "$FORGEJO_URL/repos/${FORGE_ORG}/${FORGE_NAME}" >/dev/null 2>&1 || \
curl -sf -u dino:"$PASS" -H 'Content-Type: application/json' \
    -d "{\"name\":\"${FORGE_NAME}\",\"private\":true,\"auto_init\":false,\"default_branch\":\"main\"}" \
    "$FORGEJO_URL/orgs/${FORGE_ORG}/repos" >/dev/null

if git -C "$REPO_PATH" remote get-url github >/dev/null 2>&1; then
    git -C "$REPO_PATH" remote set-url github "$GITHUB_URL"
else
    if git -C "$REPO_PATH" remote get-url origin >/dev/null 2>&1; then
        git -C "$REPO_PATH" remote rename origin github
    fi
    git -C "$REPO_PATH" remote add origin "$FORGE_SSH"
fi

git -C "$REPO_PATH" remote set-url origin "$FORGE_SSH"
git -C "$REPO_PATH" remote set-url --push origin "$FORGE_SSH"
git -C "$REPO_PATH" remote set-url --add --push origin "$GITHUB_URL"

BRANCH="$(git -C "$REPO_PATH" branch --show-current)"
git -C "$REPO_PATH" push -u origin "$BRANCH"
git -C "$REPO_PATH" push origin --tags >/dev/null 2>&1 || true

echo "Adopted $REPO_PATH -> $FORGE_SSH"
