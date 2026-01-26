# Phase 1 動作確認手順

## 基本テスト（Cursor CLI不要）

基本的な機能のテストは、Cursor CLIなしで実行できます。

### Phase 1テスト

```bash
# Phase 1の基本機能テスト（削除済み）
# 以前は test_phase1.py で実行していました
```

### Phase 2テスト

```bash
python3 test_phase2.py
```

このテストでは以下を確認します：
- ✅ すべてのエージェント（Planner, Worker, Judge）のインポート
- ✅ プロンプトテンプレートファイルの存在確認
- ✅ StateManagerの拡張機能（タスク管理、割り当て、完了、失敗）
- ✅ メインループの構造確認

## Docker環境での動作確認（Cursor CLI必要）

### 1. Docker環境の準備

```bash
# Dockerイメージをビルド
docker compose build
```

### 2. Cursor CLIの認証（初回のみ）

**重要**: 認証情報は `cursor-config` ボリュームに保存されます。同じボリュームを使用する限り、認証は永続化されます。

```bash
# 認証を実行（認証URLが表示される）
docker compose run --rm agent agent login
```

表示されたURLをホスト側のブラウザで開いて、Cursorアカウントでログインして認証を完了してください。

**認証情報の確認**:
```bash
# 認証状態を確認
chmod +x scripts/check_auth.sh
./scripts/check_auth.sh

# または手動で確認
docker compose run --rm agent ls -la /root/.cursor
docker compose run --rm agent ls -la /root/.config/cursor
docker compose run --rm agent cat /root/.config/cursor/auth.json
docker compose run --rm agent agent --version
```

### 3. Phase 2の実行

```bash
# プロジェクト目標を設定して実行
PROJECT_GOAL="このプロジェクトのPhase 2動作確認" docker compose run --rm agent python main.py
```

**注意**: Phase 2はメインループを実行します。以下のサイクルが繰り返されます：
1. Planner実行（計画更新・タスク作成）
2. Worker実行（保留中のタスクを1つ実行）
3. Judge実行（進捗評価・継続判定）

各ステップの間に待機時間（デフォルト1分）があります。

または、`.env`ファイルを作成して設定：

```bash
# .envファイルを作成
cat > .env << EOF
PROJECT_GOAL=このプロジェクトのPhase 1動作確認
LOG_LEVEL=INFO
EOF

# 実行
docker compose run --rm agent python main.py
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
docker compose run --rm agent which agent
docker compose run --rm agent agent --version
```

### 認証エラー

**問題**: 認証情報がコンテナで保持されていない

**解決策**:

1. **認証情報の確認**:
```bash
# 認証情報が保存されているか確認（両方の場所を確認）
docker compose run --rm agent ls -la /root/.cursor
docker compose run --rm agent ls -la /root/.config/cursor
docker compose run --rm agent cat /root/.config/cursor/auth.json
```

2. **認証情報の再保存**:
```bash
# ボリュームを削除して再認証（両方のボリュームを削除）
docker volume rm cursor_scage_cursor-config cursor_scage_cursor-config-config
docker compose run --rm agent agent login
```

3. **認証情報の手動確認**:
```bash
# コンテナ内で直接確認
docker compose run --rm agent /bin/bash
# コンテナ内で:
# ls -la /root/.cursor
# ls -la /root/.config/cursor
# cat /root/.config/cursor/auth.json
# agent --version
# agent login  # 必要に応じて
```

4. **環境変数の確認**:
```bash
# CURSOR_API_KEYが設定されている場合、環境変数を削除
# docker-compose.ymlで環境変数を確認
```

### 実行エラー

```bash
# ログを確認
docker compose logs agent

# コンテナ内で直接実行してデバッグ
docker compose run --rm agent /bin/bash
# コンテナ内で:
# python main.py
```

## 期待される動作

### Phase 1（単体テスト）

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

### Phase 2（メインループ）

Phase 2が正常に動作すると、以下が実行されます：

1. **初期化**
   - Planner, Worker, Judgeエージェントの初期化
   - 設定の読み込み

2. **メインループ（各イテレーション）**
   - **Planner実行**: 計画更新・タスク作成
   - **待機**: 設定された時間（デフォルト1分）
   - **Worker実行**: 保留中のタスクを1つ実行・完了
   - **待機**: 設定された時間（デフォルト1分）
   - **Judge実行**: 進捗評価・継続判定
   - **待機**: 設定された時間（デフォルト1分）
   - **継続判定**: Judgeの判定に基づいて継続/停止

3. **最終状態の表示**
   - 総イテレーション数
   - タスクの統計（総数、完了、失敗、保留中）

## 認証情報の永続化について

認証情報は2つの場所に保存され、それぞれ別の名前付きボリュームで永続化されます：

1. **`/root/.cursor`** → `cursor-config` ボリューム
2. **`/root/.config/cursor/auth.json`** → `cursor-config-config` ボリューム

これらのボリュームは：

- **永続化**: コンテナを削除しても認証情報は保持されます
- **共有**: 同じボリュームを使用するすべてのコンテナで認証情報が共有されます
- **削除**: `docker volume rm cursor_scage_cursor-config cursor_scage_cursor-config-config` で削除できます

**重要**: 両方のボリュームが正しくマウントされている必要があります。認証情報が保持されない場合は、両方のボリュームが正しくマウントされているか確認してください。

## 次のステップ

### Phase 2の動作確認後

Phase 2の動作確認が完了したら、以下を確認してください：

1. **状態ファイルの確認**
   - `state/plan.md`: 計画が更新されているか
   - `state/tasks.json`: タスクが作成・更新されているか
   - `state/results/`: Workerの実行結果が保存されているか

2. **ログの確認**
   - `logs/execution_*.log`: 実行ログ
   - `logs/execution_*.jsonl`: 構造化ログ

3. **次のフェーズ**
   - Phase 3（安定化）の実装に進む
   - エラーハンドリングの強化
   - ログ機能の改善
   - 状態の永続化と復元
