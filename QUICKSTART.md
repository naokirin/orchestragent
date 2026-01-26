# クイックスタートガイド

このガイドでは、最小限の手順でエージェントシステムを実行する方法を説明します。

## 必要なファイル

実行に必要な最小限のファイル：

- `Dockerfile` - Dockerイメージの定義
- `docker-compose.yml` - Docker Composeの設定
- `.env.example` - 環境変数のテンプレート（初回実行時に`.env`として自動作成）
- `requirements.txt` - Python依存関係
- `main.py` - メインエントリーポイント
- `config.py` - 設定管理
- `agents/` - エージェント実装
- `utils/` - ユーティリティ
- `prompts/` - プロンプトテンプレート
- `scripts/setup.sh` - 初回セットアップスクリプト

## 実行手順

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd orchestragent
```

### 2. Dockerイメージをビルドして実行

```bash
docker compose up
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
