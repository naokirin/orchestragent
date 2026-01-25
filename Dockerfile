FROM python:3.11-slim

# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cursor CLIをインストール
RUN curl https://cursor.com/install -fsS | bash

# PATHに ~/.local/bin を追加（Cursor CLIがインストールされる場所）
ENV PATH="/root/.local/bin:${PATH}"

# 作業ディレクトリを設定
WORKDIR /workspace

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# エントリーポイント
COPY . .
CMD ["python", "main.py"]
