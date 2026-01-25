#!/bin/bash
# 認証状態を確認するスクリプト

echo "=== Cursor CLI認証状態の確認 ==="
echo ""

# コンテナ内で認証情報を確認
echo "1. 認証情報ディレクトリの確認:"
echo "  /root/.cursor:"
docker compose run --rm agent ls -la /root/.cursor 2>&1 || echo "    .cursor ディレクトリが見つかりません"
echo "  /root/.config/cursor:"
docker compose run --rm agent ls -la /root/.config/cursor 2>&1 || echo "    .config/cursor ディレクトリが見つかりません"

echo ""
echo "2. 認証情報ファイルの確認:"
echo "  /root/.cursor 内のファイル:"
docker compose run --rm agent find /root/.cursor -type f 2>&1 | head -10 || echo "    ファイルが見つかりません"
echo "  /root/.config/cursor/auth.json:"
docker compose run --rm agent cat /root/.config/cursor/auth.json 2>&1 | head -5 || echo "    auth.json が見つかりません"

echo ""
echo "3. Cursor CLIのバージョン確認:"
docker compose run --rm agent agent --version 2>&1 || echo "  agent コマンドが見つかりません"

echo ""
echo "4. 認証状態の確認（軽量コマンド）:"
docker compose run --rm agent agent --version 2>&1 | grep -i "auth\|login\|error" || echo "  認証エラーは検出されませんでした"

echo ""
echo "=== 確認完了 ==="
echo ""
echo "認証が必要な場合:"
echo "  docker compose run --rm agent agent login"
