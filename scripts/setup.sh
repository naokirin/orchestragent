#!/bin/bash
# Initial setup script: create .env from example and required directories

# Continue on error (main.py can still run if some steps fail)
set +e

echo "=========================================="
echo "初回セットアップを実行中..."
echo "=========================================="

# Create .env from .env.example if missing
if [ ! -f .env ]; then
    echo "[セットアップ] .envファイルが見つかりません。.env.exampleから作成します..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[セットアップ] .envファイルを作成しました"
    else
        echo "[警告] .env.exampleが見つかりません。デフォルト設定で続行します。"
    fi
else
    echo "[セットアップ] .envファイルは既に存在します"
fi

# Create required directories
echo "[セットアップ] 必要なディレクトリを作成中..."
mkdir -p state/results
mkdir -p state/checkpoints
mkdir -p state/tasks
mkdir -p state/locks
mkdir -p logs

echo "[セットアップ] ディレクトリの作成が完了しました"

# Check Cursor CLI availability
echo "[セットアップ] Cursor CLIの確認中..."
if command -v agent &> /dev/null; then
    echo "[セットアップ] Cursor CLI: $(agent --version 2>&1 || echo '利用可能')"
else
    echo "[警告] Cursor CLIが見つかりません"
fi

echo "=========================================="
echo "セットアップ完了"
echo "=========================================="
