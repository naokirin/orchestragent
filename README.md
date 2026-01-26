# プランナー・ワーカースタイル自律エージェントシステム

Cursorブログ記事「[長時間稼働する自律型コーディングをスケールさせる](https://cursor.com/ja/blog/scaling-agents)」で紹介されているプランナー・ワーカースタイルのエージェントシステムを、最小構成で実装するプロジェクトです。

## プロジェクト目標

- ✅ 複数エージェント（役割分離：Planner, Worker, Judge）
- ✅ 自律ループ（再計画 → 実行 → 判定）
- ✅ 長時間動作（数時間〜数日）
- ❌ 高スループット（不要）
- ❌ 完全無人運用（不要）

## ドキュメント

### 開発者向けドキュメント

詳細な設計ドキュメントは [`docs/dev/`](./docs/dev/) を参照してください。

- **[要件整理と全体計画](./docs/dev/PLANNING.md)**: プロジェクトの要件と全体計画
- **[技術的詳細と実装上の課題](./docs/dev/TECHNICAL_DETAILS.md)**: 技術的な詳細と課題
- **[プロンプト設計ガイド](./docs/dev/PROMPT_DESIGN.md)**: エージェントのプロンプト設計
- **[Cursor CLIリファレンス](./docs/dev/CURSOR_CLI_REFERENCE.md)**: Cursor CLIの使用方法
- **[抽象化レイヤーの設計](./docs/dev/ARCHITECTURE_DESIGN.md)**: 後からLLM APIに差し替え可能な設計
- **[実行環境の設計](./docs/dev/EXECUTION_ENVIRONMENT.md)**: Sandbox/DevContainerでの実行方法
- **[実装前チェックリスト](./docs/dev/IMPLEMENTATION_CHECKLIST.md)**: 実装開始前の確認項目

## クイックスタート

**最小限の手順で実行したい場合は、[QUICKSTART.md](./QUICKSTART.md)を参照してください。**

**DockerHubにイメージを公開すれば、docker-compose.ymlと.envファイルだけで実行可能です。詳細は[DOCKERHUB.md](./DOCKERHUB.md)を参照してください。**

### 基本的な実行手順（ローカルビルド）

```bash
git clone <repository-url>
cd cursor_scage
docker compose up
```

初回実行時に`.env`ファイルの作成や必要なディレクトリの作成が自動的に行われます。

### DockerHubからpullする場合（最小構成）

```bash
# docker-compose.pull.ymlと.envファイルだけあれば実行可能
docker compose -f docker-compose.pull.yml up
```

詳細は[DOCKERHUB.md](./DOCKERHUB.md)を参照してください。

## 前提条件

### Mac上でDockerを使用する場合

Mac上でDockerを実行する際、ホストのファイルシステムにアクセスする必要がある場合は、**Docker.appにフルディスクアクセス権限を付与**する必要があります。

#### 設定手順

1. **システム設定**を開く
2. **プライバシーとセキュリティ** → **フルディスクアクセス**を選択
3. 左下の鍵アイコンをクリックしてロックを解除
4. **+** ボタンをクリックし、`/Applications/Docker.app` を追加
5. Docker Desktopを再起動

> **注意**: この権限がない場合、コンテナからホストのファイルシステムへのマウントが正しく動作しない可能性があります。

## クイックスタート

### 最小限の手順で実行する

このシステムは、Dockerイメージとdocker-compose.yml、少数の設定ファイルだけで実行可能です。

#### 1. リポジトリをクローン（初回のみ）

```bash
git clone <repository-url>
cd cursor_scage
```

#### 2. 環境変数の設定（オプション）

`.env`ファイルは初回実行時に`.env.example`から自動作成されますが、事前に設定することもできます：

```bash
# .env.exampleをコピーして編集
cp .env.example .env
# 必要に応じて編集
nano .env  # またはお好みのエディタ
```

主要な設定項目：
- `PROJECT_GOAL`: プロジェクトの目標（必須）
- `TARGET_PROJECT`: 作業対象のプロジェクトディレクトリ（絶対パス推奨、未指定時はリポジトリ自体）
- `LOG_LEVEL`: ログレベル（デフォルト: `INFO`）

#### 3. Dockerイメージをビルドして実行

```bash
docker compose up
```

初回実行時は、以下の処理が自動的に行われます：
- `.env`ファイルの自動作成（存在しない場合）
- 必要なディレクトリの作成（`state/`, `logs/`）
- Cursor CLIの認証確認

#### 4. Cursor CLIの認証（初回のみ）

初回実行時にCursor CLIの認証が必要な場合、以下のコマンドで認証できます：

```bash
# 別のターミナルで実行
docker compose run --rm agent agent login
```

表示されたURLをブラウザで開いて認証を完了してください。

### 実行モード

#### モード1: リポジトリ自体を開発対象とする場合（デフォルト）

```bash
# .envファイルでPROJECT_GOALを設定
echo "PROJECT_GOAL=このリポジトリを改善する" >> .env
docker compose up
```

#### モード2: 外部プロジェクトを開発対象とする場合

```bash
# .envファイルまたは環境変数で設定
TARGET_PROJECT=/path/to/my-project \
PROJECT_GOAL="REST APIを実装する" \
docker compose up
```

または`.env`ファイルに設定：

```env
TARGET_PROJECT=/path/to/my-project
PROJECT_GOAL=REST APIを実装する
```

### 環境変数の詳細

主要な環境変数（`.env`ファイルまたは`docker-compose.yml`で設定可能）：

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `PROJECT_GOAL` | プロジェクトの目標（必須） | `プロジェクトの目標を設定してください` |
| `TARGET_PROJECT` | 作業対象のプロジェクトディレクトリ（絶対パス推奨） | `.`（リポジトリ自体） |
| `PROJECT_ROOT` | コンテナ内での作業対象ディレクトリ（通常は変更不要） | `/target` または `/workspace` |
| `LOG_LEVEL` | ログレベル | `INFO` |
| `WAIT_TIME_SECONDS` | エージェント間の待機時間（秒） | `60` |
| `MAX_ITERATIONS` | 最大イテレーション数 | `100` |
| `MAX_PARALLEL_WORKERS` | 最大並列Worker数 | `3` |
| `ENABLE_PARALLEL_EXECUTION` | 並列実行の有効化 | `true` |

### 注意事項

- `TARGET_PROJECT`には**絶対パス**を指定することを推奨します
- 指定されたディレクトリはコンテナ内の`/target`にマウントされます
- エージェントシステム自体のコードは`/workspace`にマウントされ、状態ファイル（`state/`、`logs/`）はリポジトリ内に保存されます
- Cursor CLIの認証情報はDockerボリュームに永続化されます（`cursor-config`、`cursor-config-config`）

## アーキテクチャ概要

```
main.py (メインループ)
├─ Planner: タスクを作成・計画を更新
├─ Worker: タスクを実行・コード変更をコミット
└─ Judge: 進捗を評価・継続判定

状態管理（ファイルベース）
├─ state/plan.md: 現在の計画
├─ state/tasks.json: タスクキュー
├─ state/results/: Worker成果物
└─ state/status.json: 進行状態
```

## 実装の優先順位

### Phase 1: 最小動作確認
1. ファイルベースの状態管理
2. 単一エージェント（Planner）の動作確認
3. Cursor CLI/API との統合確認

### Phase 2: 基本ループ
1. メインループの実装
2. Planner + Worker の連携
3. Judge の実装

### Phase 3: 安定化
1. エラーハンドリング
2. ログ機能
3. 状態の永続化と復元

### Phase 4: 最適化（後回し）
1. 複数Workerの並列実行
2. より高度なコンフリクト解決
3. パフォーマンス最適化

## 主要な課題と対応方針

### 1. Cursor API/CLI の仕様不明
**対応**: 抽象化レイヤーを設けて、Cursor CLI/API/直接LLM APIのいずれでも動作するようにする

### 2. コンフリクト管理
**対応（最小構成）**: Workerは1つずつ順次実行、タスク単位でファイルの排他制御

### 3. プロンプト設計の最適化
**対応**: プロンプトを外部ファイル化して試行錯誤しやすくする、Judgeが定期的にドリフトを検出

### 4. コスト管理
**対応**: 各API呼び出しのコストをログに記録、1日の上限を設定

## 次のステップ

1. **技術調査**
   - Cursor CLI/APIの仕様確認
   - 利用可能なLLM APIの選定

2. **プロトタイプ作成**
   - 最小構成での動作確認
   - 各エージェントのプロンプト設計

3. **段階的実装**
   - Phase 1から順次実装
   - 各フェーズで動作確認

4. **テストと改善**
   - 小規模プロジェクトでテスト
   - プロンプトの調整
   - バグ修正

## 参考資料

- [長時間稼働する自律型コーディングをスケールさせる - Cursor Blog](https://cursor.com/ja/blog/scaling-agents)
- [Cursor CLI 公式ドキュメント](https://cursor.com/ja/docs/cli/overview)
- [CLIでAgentを使用する](https://cursor.com/ja/docs/cli/using)

## ライセンス

（未定）
