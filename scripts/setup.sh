#!/bin/bash
# 初回セットアップスクリプト
# .envファイルの作成、必要なディレクトリの作成を行う

# エラーが発生しても続行（一部の処理が失敗してもmain.pyは実行可能）
set +e

echo "=========================================="
echo "初回セットアップを実行中..."
echo "=========================================="

# .envファイルが存在しない場合、.env.exampleから作成
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

# 必要なディレクトリを作成
echo "[セットアップ] 必要なディレクトリを作成中..."
mkdir -p state/results
mkdir -p state/checkpoints
mkdir -p state/tasks
mkdir -p state/locks
mkdir -p logs

echo "[セットアップ] ディレクトリの作成が完了しました"

# Cursor CLIの確認
echo "[セットアップ] Cursor CLIの確認中..."
if command -v agent &> /dev/null; then
    echo "[セットアップ] Cursor CLI: $(agent --version 2>&1 || echo '利用可能')"
else
    echo "[警告] Cursor CLIが見つかりません"
fi

echo "=========================================="
echo "セットアップ完了"
echo "=========================================="
