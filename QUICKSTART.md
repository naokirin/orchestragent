# クイックスタートガイド

このガイドでは、最小限の手順でエージェントシステムを実行する方法を説明します。

## どの compose ファイルを使うか

| 用途 | ファイル | 実行場所 |
|------|----------|----------|
| **開発用**（リポジトリ内でコードを編集しながら動かす） | `docker-compose.yml` | リポジトリのルート |
| **実行用**（別ディレクトリのプロジェクトを対象に動かす） | `docker-compose.exec.yml` | 作業対象プロジェクトのディレクトリ |

- **開発用** (`docker-compose.yml`): リポジトリをカレントにして実行。ソースがマウントされ、state / logs はリポジトリ内に保存されます。
- **実行用** (`docker-compose.exec.yml`): 任意のディレクトリで実行。カレントディレクトリが作業対象として `/target` にマウントされます。state / logs / docs/adr のホスト側パスは **`ORCHESTRAGENT_STATE_DIR`** / **`ORCHESTRAGENT_LOG_DIR`** / **`ORCHESTRAGENT_ADR_DIR`** で指定（絶対パス推奨）。コンテナ内では常に `/workspace/state`、`/workspace/logs`、`/workspace/docs/adr` を使用します。

**`.env` について**: Docker Compose の v1 と v2、および `-f` の有無で `.env` の読み込み場所が異なります。確実に読み込ませるため、**`--env-file .env`** の指定を推奨します（`.env` が無い場合は省略可）。

## 必要なファイル（開発用・リポジトリ内で実行する場合）

実行に必要な最小限のファイル：

- `Dockerfile` - Dockerイメージの定義
- `docker-compose.yml` - 開発用 Docker Compose の設定
- `docker-compose.exec.yml` - リポジトリ外実行用 Docker Compose の設定
- `.env.example` - 環境変数のテンプレート（初回実行時に`.env`として自動作成）
- `requirements.txt` - Python依存関係
- `main.py` - メインエントリーポイント
- `config.py` - 設定管理
- `agents/` - エージェント実装
- `utils/` - ユーティリティ
- `prompts/` - プロンプトテンプレート
- `scripts/setup.sh` - 初回セットアップスクリプト

## 実行手順（開発用・リポジトリ内）

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd orchestragent
```

### 2. Dockerイメージをビルドして実行

```bash
docker compose up
# .env を確実に読み込ませる場合（Compose v1/v2 で読み込み場所が異なるため推奨）:
# docker compose --env-file .env up
```

これだけです！

初回実行時に以下が自動的に行われます：
- `.env`ファイルの作成（`.env.example`から）
- 必要なディレクトリの作成（`state/`, `logs/`）
- Cursor CLIの確認

### 3. 環境変数の設定（オプション）

必要に応じて`.env`ファイルを編集：

```bash
# .envファイルを編集
nano .env
```

最低限、`PROJECT_GOAL`を設定してください：

```env
PROJECT_GOAL=あなたのプロジェクトの目標をここに記述
```

### 4. Cursor CLIの認証（初回のみ）

初回実行時に認証が必要な場合：

```bash
# 別のターミナルで実行
docker compose run --rm agent agent login
```

## 実行モード

### モード1: リポジトリ自体を開発対象とする

```bash
# .envファイルで設定
PROJECT_GOAL=このリポジトリを改善する
docker compose up
```

### モード2: 外部プロジェクトを開発対象とする

```bash
# 環境変数で設定
TARGET_PROJECT=/path/to/my-project \
PROJECT_GOAL="REST APIを実装する" \
docker compose up
```

または`.env`ファイルに設定：

```env
TARGET_PROJECT=/path/to/my-project
PROJECT_GOAL=REST APIを実装する
```

## リポジトリ外での実行（実行用・docker-compose.exec.yml）

別のディレクトリでエージェントを動かす場合は、`docker-compose.exec.yml` を使います。カレントディレクトリがそのまま作業対象プロジェクトとして `/target` にマウントされます。state / logs / docs/adr は **`ORCHESTRAGENT_STATE_DIR`** / **`ORCHESTRAGENT_LOG_DIR`** / **`ORCHESTRAGENT_ADR_DIR`** でホスト側のパスを指定します（Compose v2 で `-f` を使うと相対パスは compose ファイルのあるディレクトリ基準になるため、任意の場所に置く場合は絶対パス指定を推奨）。

### 1. イメージを用意する（リポジトリで1回だけ）

```bash
cd /path/to/orchestragent
docker build -t orchestragent:latest .
```

### 2. 作業対象プロジェクトのディレクトリで起動

```bash
cd /path/to/your/target-project
docker-compose -f /path/to/orchestragent/docker-compose.exec.yml --env-file .env up -d
```

`.env` を使う場合は `--env-file .env` を指定することを推奨します。state / logs を任意の場所に置く場合は `.env` に絶対パスを指定してください：

```env
ORCHESTRAGENT_STATE_DIR=/path/to/your/project/state
ORCHESTRAGENT_LOG_DIR=/path/to/your/project/logs
ORCHESTRAGENT_ADR_DIR=/path/to/your/project/docs/adr
```

### 3. 環境変数（オプション）

`.env` を作業対象プロジェクトのディレクトリに置き、`--env-file .env` で読み込ませることを推奨します（Compose v1/v2 で `.env` の読み込み場所が異なるため）。起動時に環境変数だけ指定することもできます：

```bash
PROJECT_GOAL="REST APIを実装する" \
docker-compose -f /path/to/orchestragent/docker-compose.exec.yml --env-file .env up -d
```

イメージ名を変えたい場合（例: Docker Hub のイメージを使う）：

```bash
ORCHESTRAGENT_IMAGE=your-registry/orchestragent:tag \
docker-compose -f /path/to/orchestragent/docker-compose.exec.yml up -d
```

### 4. Cursor CLIの認証（初回のみ・実行用）

実行用 compose でも認証は共有ボリュームで永続化されます。初回のみ：

```bash
docker-compose -f /path/to/orchestragent/docker-compose.exec.yml run --rm agent agent login
```

## トラブルシューティング

### Cursor CLIが見つからない

Dockerイメージのビルド時にCursor CLIのインストールに失敗している可能性があります。ログを確認してください：

```bash
docker compose build --no-cache
docker compose up
```

### 認証エラー

Cursor CLIの認証が必要です：

```bash
docker compose run --rm agent agent login
```

### 権限エラー（Mac）

MacでDockerを使用する場合、Docker.appにフルディスクアクセス権限を付与する必要があります：

1. システム設定 → プライバシーとセキュリティ → フルディスクアクセス
2. Docker.appを追加
3. Docker Desktopを再起動

## 詳細情報

詳細な使用方法は[README.md](./README.md)を参照してください。
