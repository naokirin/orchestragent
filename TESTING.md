# Phase 1 動作確認手順

## 基本テスト（Cursor CLI不要）

基本的な機能のテストは、Cursor CLIなしで実行できます。

```bash
python3 test_phase1.py
```

このテストでは以下を確認します：
- ✅ すべてのモジュールのインポート
- ✅ 設定ファイルの読み込み
- ✅ StateManagerの機能（JSON/テキストの保存・読み込み、タスク管理）
- ✅ Loggerの機能

## Docker環境での動作確認（Cursor CLI必要）

### 1. Docker環境の準備

```bash
# Dockerイメージをビルド
docker-compose build
```

### 2. Cursor CLIの認証（初回のみ）

```bash
# 認証を実行（認証URLが表示される）
docker-compose run --rm agent agent --help
```

表示されたURLをホスト側のブラウザで開いて、Cursorアカウントでログインして認証を完了してください。

認証情報は `cursor-config` ボリュームに保存され、以降は認証不要で実行できます。

### 3. Phase 1の実行

```bash
# プロジェクト目標を設定して実行
PROJECT_GOAL="このプロジェクトのPhase 1動作確認" docker-compose run --rm agent python main.py
```

または、`.env`ファイルを作成して設定：

```bash
# .envファイルを作成
cat > .env << EOF
PROJECT_GOAL=このプロジェクトのPhase 1動作確認
LOG_LEVEL=INFO
EOF

# 実行
docker-compose run --rm agent python main.py
```

### 4. 結果の確認

実行後、以下を確認してください：

- **状態ファイル**: `state/plan.md` に計画が記録されているか
- **タスク**: `state/tasks.json` にタスクが追加されているか
- **ログ**: `logs/` ディレクトリにログファイルが作成されているか

```bash
# 計画を確認
cat state/plan.md

# タスクを確認
cat state/tasks.json | python3 -m json.tool

# ログを確認
ls -la logs/
tail -20 logs/execution_*.log
```

## トラブルシューティング

### Cursor CLIが見つからない

```bash
# コンテナ内で確認
docker-compose run --rm agent which agent
docker-compose run --rm agent agent --version
```

### 認証エラー

```bash
# 認証情報を確認
docker-compose run --rm agent ls -la /root/.cursor

# 認証情報を削除して再認証
docker volume rm cursor_scage_cursor-config
docker-compose run --rm agent agent --help
```

### 実行エラー

```bash
# ログを確認
docker-compose logs agent

# コンテナ内で直接実行してデバッグ
docker-compose run --rm agent /bin/bash
# コンテナ内で:
# python main.py
```

## 期待される動作

Phase 1が正常に動作すると、以下が実行されます：

1. **環境チェック**
   - コンテナ内で実行されているか確認
   - Cursor CLIが利用可能か確認
   - 認証状態を確認

2. **Plannerエージェントの実行**
   - プロンプトを構築
   - Cursor CLI経由でLLMを呼び出し
   - レスポンスをパース
   - 計画とタスクを状態ファイルに保存

3. **結果の表示**
   - 作成されたタスク数
   - 更新された計画の概要

## 次のステップ

Phase 1の動作確認が完了したら、Phase 2（基本ループ）の実装に進みます。
