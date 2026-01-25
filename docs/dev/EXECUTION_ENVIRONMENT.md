# 実行環境の設計: Sandbox/DevContainer

## 設計方針

Cursor CLIは非対話モードでも、ファイル操作、git操作、シェルコマンド実行などの権限が必要です。利用できないコマンドが出てくると停止してしまうため、**必ずSandbox（Docker/DevContainer）で実行**します。

## 要件

### 必須要件
1. **DockerコンテナまたはDevContainerで実行**
2. **コマンド制限をかけない**（必要な権限をすべて許可）
3. **ホスト環境への影響を避ける**
4. **プロジェクトディレクトリをボリュームマウント**

### 必要なツール
- Python 3.8+
- Git
- Cursor CLI (`agent` コマンド)
- その他、エージェントが実行する可能性のあるコマンド（make, npm, pip等）

### 認証要件
- **OAuth認証**: 初回実行時にOAuth認証が必要
- **ホスト側ブラウザ**: 認証URLをホスト側のブラウザで開く必要がある
- **認証情報の永続化**: 認証情報をボリュームマウントで永続化

## 実装方法

### オプション1: Dockerfile + docker-compose（推奨）

#### Dockerfile

```dockerfile
FROM python:3.11-slim

# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cursor CLIをインストール
RUN curl https://cursor.com/install -fsS | bash

# 作業ディレクトリを設定
WORKDIR /workspace

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# エントリーポイント
COPY . .
CMD ["python", "main.py"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  agent:
    build: .
    volumes:
      # プロジェクトディレクトリをマウント
      - .:/workspace
      # 状態ファイルを永続化（オプション）
      - ./state:/workspace/state
      - ./logs:/workspace/logs
      # Cursor CLIの認証情報を永続化（重要）
      - cursor-config:/root/.cursor
    environment:
      # その他の環境変数（API Keyは不要、OAuth認証を使用）
      - PROJECT_ROOT=/workspace
      - LOG_LEVEL=INFO
    working_dir: /workspace
    # コマンド制限をかけない（すべての権限を許可）
    privileged: false
    # ネットワークアクセスを許可（API呼び出し用）
    network_mode: bridge
    # 長時間実行を許可
    restart: unless-stopped
    # インタラクティブモードで実行（初回認証用）
    stdin_open: true
    tty: true

volumes:
  cursor-config:
    # Cursor CLIの認証情報を永続化
```

#### 実行方法

```bash
# ビルド
docker compose build

# 初回実行（OAuth認証が必要）
docker compose run --rm agent agent login
# → 認証URLが表示されるので、ホスト側のブラウザで開いて認証

# 認証後、通常実行
docker compose up

# バックグラウンド実行
docker compose up -d

# ログ確認
docker compose logs -f
```

**初回認証の手順:**
1. コンテナを起動して `agent` コマンドを実行
2. 認証URLが表示される（例: `https://cursor.com/auth?code=...`）
3. ホスト側のブラウザでURLを開く
4. Cursorアカウントでログインして認証を完了
5. 認証情報は `/root/.cursor` に保存され、ボリュームで永続化される
6. 以降は認証不要で実行可能

### オプション2: DevContainer（開発環境向け）

#### .devcontainer/devcontainer.json

```json
{
  "name": "Cursor Agent Sandbox",
  "image": "python:3.11-slim",
  
  "features": {
    "ghcr.io/devcontainers/features/git:1": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  
  "postCreateCommand": "bash .devcontainer/setup.sh",
  
  "mounts": [
    "source=${localWorkspaceFolder},target=/workspace,type=bind"
  ],
  
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python"
      ]
    }
  },
  
  "remoteUser": "root",
  
  "runArgs": [
    "--privileged=false"
  ]
}
```

#### .devcontainer/setup.sh

```bash
#!/bin/bash
set -e

# システムパッケージをインストール
apt-get update
apt-get install -y \
    git \
    curl \
    build-essential

# Cursor CLIをインストール
curl https://cursor.com/install -fsS | bash

# Python依存関係をインストール
pip install -r requirements.txt

echo "Setup completed!"
```

### オプション3: スクリプト経由でのDocker実行

#### scripts/run_in_docker.sh

```bash
#!/bin/bash
set -e

# プロジェクトルートを取得
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Dockerイメージをビルド（初回のみ）
if ! docker images | grep -q cursor-agent; then
    echo "Building Docker image..."
    docker build -t cursor-agent "$PROJECT_ROOT"
fi

# コンテナ内で実行
docker run -it --rm \
    -v "$PROJECT_ROOT:/workspace" \
    -w /workspace \
    -e CURSOR_API_KEY="${CURSOR_API_KEY}" \
    cursor-agent \
    python main.py "$@"
```

## セキュリティ上の考慮事項

### 1. コンテナレベルのセキュリティ

- **ホスト環境への影響を避ける**: ボリュームマウントはプロジェクトディレクトリのみ
- **ネットワーク制限**: 必要に応じてネットワークを制限（API呼び出しは許可）
- **リソース制限**: メモリやCPUの制限を設定可能

### 2. コマンド実行の制御

**重要**: コンテナ内ではコマンド制限をかけません。代わりに：

- コンテナ自体を隔離された環境で実行
- プロジェクトディレクトリのみをマウント
- 必要に応じて、`.cursor/rules`でエージェントの動作を制限

### 3. 認証の管理

**重要**: Cursor CLIはAPI Keyではなく、OAuth認証を使用します。

#### 初回認証の手順

1. **コンテナを起動して認証を実行**
   ```bash
   docker compose run --rm agent agent login
   ```

2. **認証URLを取得**
   - コマンド実行時に認証URLが表示される

3. **ホスト側のブラウザで認証**
   - 表示されたURLをホスト側のブラウザで開く
   - Cursorアカウントでログイン
   - 認証を完了

4. **認証情報の永続化**
   - 認証情報は `/root/.cursor` に保存される
   - `cursor-config` ボリュームで永続化される
   - 以降は認証不要で実行可能

#### 認証情報の確認

```bash
# 認証情報が保存されているか確認
docker compose run --rm agent ls -la /root/.cursor
```

#### 環境変数（API Keyは不要）

```bash
# .env.example
PROJECT_ROOT=/workspace
LOG_LEVEL=INFO
# CURSOR_API_KEYは不要（OAuth認証を使用）
```

```bash
# .env（.gitignoreに追加）
PROJECT_ROOT=/workspace
LOG_LEVEL=INFO
```

## 実装での統合

### main.py での環境検出と認証確認

```python
import os
import subprocess
import sys

def is_running_in_container():
    """コンテナ内で実行されているか確認"""
    # Docker環境の検出
    if os.path.exists('/.dockerenv'):
        return True
    # cgroupの確認
    try:
        with open('/proc/self/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        pass
    return False

def check_cursor_cli():
    """Cursor CLIが利用可能か確認"""
    try:
        result = subprocess.run(
            ['agent', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def check_cursor_auth():
    """Cursor CLIの認証状態を確認"""
    try:
        # 認証情報が存在するか確認
        cursor_config_dir = os.path.expanduser('~/.cursor')
        if os.path.exists(cursor_config_dir):
            # 認証情報ファイルを確認
            config_files = os.listdir(cursor_config_dir)
            if any('auth' in f.lower() or 'token' in f.lower() for f in config_files):
                return True
        
        # 実際にコマンドを実行して認証状態を確認
        result = subprocess.run(
            ['agent', 'ls'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # 認証エラーでない場合は認証済み
        if 'auth' in result.stderr.lower() or 'login' in result.stderr.lower():
            return False
        
        return result.returncode == 0
    except Exception as e:
        print(f"Warning: Could not check auth status: {e}")
        return False

def authenticate_cursor():
    """Cursor CLIの認証を実行（初回のみ）"""
    print("=" * 60)
    print("Cursor CLI認証が必要です")
    print("=" * 60)
    print("\n以下のコマンドを実行して認証してください:")
    print("  docker compose run --rm agent agent login")
    print("\n表示されたURLをホスト側のブラウザで開いて認証を完了してください。")
    print("認証後、このスクリプトを再実行してください。")
    print("=" * 60)
    sys.exit(1)

def main():
    # 環境チェック
    if not is_running_in_container():
        print("Warning: Not running in container. Recommended to use Docker/DevContainer.")
    
    if not check_cursor_cli():
        raise RuntimeError(
            "Cursor CLI not found. "
            "Please run in Docker container or install Cursor CLI."
        )
    
    # 認証チェック
    if not check_cursor_auth():
        authenticate_cursor()
    
    # メインループを実行
    ...
```

## ディレクトリ構造

```
cursor_scage/
├── Dockerfile
├── docker-compose.yml
├── .devcontainer/
│   ├── devcontainer.json
│   └── setup.sh
├── scripts/
│   └── run_in_docker.sh
├── .env.example
├── .dockerignore
└── ...
```

## .dockerignore

```
# Git関連
.git
.gitignore

# Python関連
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/

# 状態ファイル（マウントするため除外しない）
# state/
# logs/

# IDE関連
.vscode/
.idea/
*.swp
*.swo

# その他
.DS_Store
*.log
```

## トラブルシューティング

### Cursor CLIが見つからない

```bash
# コンテナ内で確認
docker compose exec agent which agent
docker compose exec agent agent --version
```

### 認証エラー

```bash
# 認証情報を確認
docker compose run --rm agent ls -la /root/.cursor

# 認証情報を削除して再認証
docker compose run --rm agent rm -rf /root/.cursor
docker compose run --rm agent agent login
# → 認証URLをホスト側のブラウザで開く
```

### 認証URLが表示されない

```bash
# インタラクティブモードで実行
docker compose run --rm -it agent agent login

# または、ログを確認
docker compose logs agent | grep -i auth
```

### 権限エラー

```bash
# ファイルの権限を確認
docker compose exec agent ls -la /workspace

# 必要に応じて権限を修正
docker compose exec agent chmod -R 755 /workspace
```

### ネットワークエラー

```bash
# ネットワーク接続を確認
docker compose exec agent curl -I https://cursor.com

# DNS設定を確認
docker compose exec agent cat /etc/resolv.conf
```

## Cursor CLIの設定

### .cursor/rules/execution.md

コンテナ内で実行する際のルールを定義：

```markdown
# 実行環境のルール

## 実行環境
- このプロジェクトはDockerコンテナ内で実行されます
- すべてのコマンドが利用可能です（制限なし）
- ファイル操作、git操作、シェルコマンドの実行が可能です

## コマンド実行
- 必要なコマンドは自由に実行してください
- エラーが発生した場合は、詳細なエラーメッセージを記録してください
- コマンドが利用できない場合は、代替手段を検討してください

## セキュリティ
- コンテナ内での実行のため、ホスト環境への影響はありません
- プロジェクトディレクトリ内での操作のみを行ってください
```

### AGENTS.md（プロジェクトルート）

エージェント向けの全体的な指示：

```markdown
# エージェント実行環境

このプロジェクトはDockerコンテナ内で実行されます。

## 利用可能なコマンド
- git: バージョン管理
- python: Python実行環境
- pip: パッケージ管理
- npm/yarn: Node.jsパッケージ管理（必要に応じて）
- make: ビルドツール（必要に応じて）
- その他、必要なコマンドはすべて利用可能

## 制限事項
- コマンドの実行に制限はありません
- ファイル操作に制限はありません
- ネットワークアクセスは許可されています（API呼び出し用）

## エラーハンドリング
- コマンドが失敗した場合は、詳細なエラーメッセージを記録
- 代替手段を検討して再試行
- 解決できない場合は、エラーを明確に報告
```

## ベストプラクティス

1. **常にコンテナで実行**: ホスト環境で直接実行しない
2. **状態ファイルのバックアップ**: 定期的に状態ファイルをバックアップ
3. **ログの監視**: コンテナのログを定期的に確認
4. **リソース監視**: メモリやCPUの使用状況を監視
5. **環境変数の管理**: 機密情報は環境変数で管理
6. **.cursor/rulesの設定**: エージェントの動作を適切に制御

## 参考リンク

- [Docker Documentation](https://docs.docker.com/)
- [Dev Containers](https://containers.dev/)
- [Cursor CLI Installation](https://cursor.com/ja/docs/cli/installation)
