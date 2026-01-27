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

# 初回セットアップスクリプトを実行可能にする
RUN chmod +x scripts/setup.sh || true

# エントリーポイント（セットアップスクリプト経由で実行）
# setup.shが存在する場合は実行、存在しない場合は直接main.pyを実行
# DASHBOARD環境変数が設定されている場合はダッシュボードモードで起動
CMD ["/bin/bash", "-c", "if [ -f scripts/setup.sh ]; then scripts/setup.sh; fi && if [ \"$DASHBOARD\" = \"true\" ] || [ \"$DASHBOARD\" = \"1\" ] || [ \"$DASHBOARD\" = \"on\" ]; then python main.py --dashboard; else python main.py; fi"]
