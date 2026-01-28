FROM python:3.11-slim

# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cursor CLIをインストール
RUN curl https://cursor.com/install -fsS | bash || (echo "Cursor CLI installation failed" && exit 1)

# PATHに ~/.local/bin を追加（Cursor CLIがインストールされる場所）
ENV PATH="/root/.local/bin:${PATH}"

# Cursor CLIのインストールを検証
RUN agent --version || (echo "Cursor CLI verification failed" && exit 1)

# 作業ディレクトリを設定
WORKDIR /workspace

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# Cursor CLIですべての操作を許可（コンテナ内のため、許可する）
ENV CURSOR_CONFIG_DIR "/root/.orchestragent"
RUN mkdir -p "$CURSOR_CONFIG_DIR" && \
    echo '{ "version": 1, "permissions": { "allow": [ "Shell(*)", "Read(**/*)", "Write(**/*)" ], "deny": [] } }' > "$CURSOR_CONFIG_DIR/cli-config.json"

# スクリプトを実行可能にする
RUN chmod +x scripts/setup.sh || true && \
    chmod +x scripts/entrypoint.sh || true

# エントリーポイント
# - scripts/entrypoint.sh 内で git のユーザー設定 / 初回セットアップ / ダッシュボード起動を行う
CMD ["scripts/entrypoint.sh"]
