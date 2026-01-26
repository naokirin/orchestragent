# DockerHubでの実行方法

DockerHubにイメージを公開すれば、**docker-compose.ymlと.envファイルだけで実行可能**です。

## 前提条件

- DockerとDocker Composeがインストールされていること
- DockerHubアカウント（イメージを公開する場合）

## イメージの公開方法

### 1. イメージをビルド

```bash
docker build -t your-username/cursor-scage:latest .
```

### 2. DockerHubにログイン

```bash
docker login
```

### 3. イメージをプッシュ

```bash
docker push your-username/cursor-scage:latest
```

## 使用方法

### 最小限のファイル構成

DockerHubからイメージをpullする場合、以下のファイルだけあれば実行可能です：

```
your-project/
├── docker-compose.pull.yml  # または docker-compose.yml
└── .env                     # 環境変数設定（オプション、初回実行時に自動作成）
```

### 1. docker-compose.pull.ymlを準備

`docker-compose.pull.yml`をダウンロードまたは作成し、イメージ名を修正：

```yaml
services:
  agent:
    image: your-username/cursor-scage:latest  # ここを修正
    # ... 以下省略
```

### 2. .envファイルを準備（オプション）

`.env`ファイルを作成して設定：

```env
PROJECT_GOAL=あなたのプロジェクトの目標
TARGET_PROJECT=/path/to/your-project  # 作業対象プロジェクト（絶対パス推奨）
```

`.env`ファイルが存在しない場合、初回実行時に`.env.example`から自動作成されます（イメージ内に含まれています）。

### 3. 実行

```bash
docker compose -f docker-compose.pull.yml up
```

または、`docker-compose.pull.yml`を`docker-compose.yml`にリネーム：

```bash
mv docker-compose.pull.yml docker-compose.yml
docker compose up
```

## 実行時の動作

初回実行時に以下が自動的に行われます：

1. DockerHubからイメージをpull
2. `.env`ファイルの作成（存在しない場合、イメージ内の`.env.example`から）
3. 必要なディレクトリの作成（`state/`, `logs/`）
4. Cursor CLIの確認

## ファイル構成の比較

### ローカルビルドの場合（現在の方法）

```
cursor_scage/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── main.py
├── config.py
├── agents/
├── utils/
├── prompts/
└── scripts/
```

### DockerHubからpullする場合（最小構成）

```
your-project/
├── docker-compose.pull.yml  # または docker-compose.yml
└── .env                      # オプション（初回実行時に自動作成）
```

## 注意事項

1. **イメージ名の修正**: `docker-compose.pull.yml`の`image:`を実際のイメージ名に修正してください
2. **.envファイル**: 最低限`PROJECT_GOAL`を設定することを推奨します
3. **認証**: 初回実行時にCursor CLIの認証が必要です：
   ```bash
   docker compose -f docker-compose.pull.yml run --rm agent agent login
   ```
4. **状態ファイル**: `state/`と`logs/`ディレクトリはホスト側に作成され、永続化されます

## 利点

- **最小限のファイル**: docker-compose.ymlと.envだけで実行可能
- **バージョン管理不要**: イメージに全てのコードが含まれているため、リポジトリをクローンする必要がない
- **簡単なデプロイ**: 新しい環境でもすぐに実行可能
