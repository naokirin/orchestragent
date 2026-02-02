#!/usr/bin/env bash
set -euo pipefail

# Set Git user info from environment variables
if [[ -n "${GIT_USER_NAME:-}" && -n "${GIT_USER_EMAIL:-}" ]]; then
  git config --global user.name "${GIT_USER_NAME}"
  git config --global user.email "${GIT_USER_EMAIL}"
fi

# Run initial setup script if present
if [[ -f "scripts/setup.sh" ]]; then
  scripts/setup.sh
fi

# Switch mode based on DASHBOARD env var
case "${DASHBOARD:-false}" in
  true|1|on|TRUE|On|ON)
    python main.py --dashboard
    ;;
  *)
    python main.py
    ;;
esac

