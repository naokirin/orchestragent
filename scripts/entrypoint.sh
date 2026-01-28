#!/usr/bin/env bash
set -euo pipefail

# Git のユーザー情報を環境変数から設定
if [[ -n "${GIT_USER_NAME:-}" && -n "${GIT_USER_EMAIL:-}" ]]; then
  git config --global user.name "${GIT_USER_NAME}"
  git config --global user.email "${GIT_USER_EMAIL}"
fi

# 初回セットアップスクリプトがあれば実行
if [[ -f "scripts/setup.sh" ]]; then
  scripts/setup.sh
fi

# DASHBOARD 環境変数に応じてモードを切り替え
case "${DASHBOARD:-false}" in
  true|1|on|TRUE|On|ON)
    python main.py --dashboard
    ;;
  *)
    python main.py
    ;;
esac

