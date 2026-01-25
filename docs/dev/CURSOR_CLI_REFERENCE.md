# Cursor CLI リファレンス

このドキュメントは、実装時に参照するためのCursor CLIの主要な機能と使用方法をまとめたものです。

## 公式ドキュメント

- [Cursor CLI 概要](https://cursor.com/ja/docs/cli/overview)
- [CLIでAgentを使用する](https://cursor.com/ja/docs/cli/using)
- [インストール](https://cursor.com/ja/docs/cli/installation)

## インストール

```bash
curl https://cursor.com/install -fsS | bash
```

## 基本コマンド

### インタラクティブモード

```bash
# 対話セッションを開始
agent

# 初期プロンプトを指定して開始
agent "認証モジュールをJWTトークンを使用するようにリファクタリング"
```

### 非対話モード（スクリプト実行用）

```bash
# 基本的な非対話実行
agent -p "プロンプト内容"
agent --print "プロンプト内容"

# 出力形式を指定
agent -p "プロンプト内容" --output-format text   # プレーンテキスト
agent -p "プロンプト内容" --output-format json   # JSON形式（パースしやすい）

# モデルを指定
agent -p "プロンプト内容" --model "gpt-5"
```

## モード

| モード | 説明 | フラグ |
|--------|------|--------|
| **Agent** | 複雑なコーディングタスク向け、すべてのツールにフルアクセス | デフォルト |
| **Plan** | コーディング前にアプローチを設計 | `--mode=plan` |
| **Ask** | 読み取り専用で探索、コードを変更しない | `--mode=ask` |

### 使用例

```bash
# Planモード（計画作成用）
agent -p "プロンプト内容" --mode=plan --output-format text

# Askモード（読み取り専用）
agent -p "プロンプト内容" --mode=ask --output-format text
```

## セッション管理

```bash
# 過去のチャットを一覧表示
agent ls

# 最新の会話を再開
agent resume

# 特定の会話を再開
agent --resume="chat-id-here"
```

## 重要な注意事項

### 非対話モードの権限

- **非対話モードでは、Cursorは完全な書き込み権限を持ちます**
- ファイルの編集、git commit、シェルコマンドの実行などが可能
- スクリプトから実行する場合は、十分に注意が必要

### ルールとコンテキスト

Cursor CLIは以下のファイル/ディレクトリを自動的に読み込みます：

1. **`.cursor/rules/`** ディレクトリ
   - プロジェクト固有のルールを定義
   - エージェントの挙動をカスタマイズ

2. **`AGENTS.md`**（プロジェクトルート）
   - エージェント向けの指示を記述

3. **`CLAUDE.md`**（プロジェクトルート）
   - Claude向けの指示を記述

これらのファイルは、エージェントの動作に大きな影響を与えるため、適切に設定する必要があります。

## 実装での使用例

### Pythonから実行

```python
import subprocess

def run_cursor_agent(prompt, mode="agent", output_format="text", project_root="."):
    """Cursor CLIを実行"""
    cmd = ['agent', '-p', prompt, '--output-format', output_format]
    
    if mode != "agent":
        cmd.extend(['--mode', mode])
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=300
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Cursor CLI error: {result.stderr}")
    
    return result.stdout

# 使用例
prompt = "現在のタスクリストを確認し、次のタスクを計画してください"
output = run_cursor_agent(prompt, mode="plan", output_format="json")
```

### プロンプトファイルから実行

```python
def run_cursor_agent_from_file(prompt_file, mode="agent", project_root="."):
    """プロンプトファイルから読み込んで実行"""
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt = f.read()
    
    return run_cursor_agent(prompt, mode, project_root=project_root)

# 使用例
output = run_cursor_agent_from_file('prompts/planner.md', mode="plan")
```

## エラーハンドリング

```python
import subprocess

try:
    result = subprocess.run(
        ['agent', '-p', prompt],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        # エラー処理
        print(f"Error: {result.stderr}")
        return None
    
    return result.stdout

except subprocess.TimeoutExpired:
    print("Cursor CLI timeout")
    return None

except FileNotFoundError:
    print("Cursor CLI not found. Install with: curl https://cursor.com/install -fsS | bash")
    return None
```

## 認証

### OAuth認証

Cursor CLIは**API Keyではなく、OAuth認証**を使用します。

#### 初回認証の手順

1. **初回実行時に認証が必要**
   ```bash
   agent login
   # → 認証URLが表示される
   ```

2. **認証URLをブラウザで開く**
   - 表示されたURL（例: `https://cursor.com/auth?code=ABC123`）をブラウザで開く
   - Cursorアカウントでログイン
   - 認証を完了

3. **認証情報の保存**
   - 認証情報は `~/.cursor` に保存される
   - 以降は認証不要で実行可能

#### Dockerコンテナ内での認証

コンテナ内で実行する場合：

1. **コンテナを起動して認証**
   ```bash
   docker compose run --rm agent agent login
   ```

2. **認証URLをホスト側のブラウザで開く**
   - コンテナ内で表示されたURLをコピー
   - ホスト側のブラウザで開いて認証

3. **認証情報の永続化**
   - `cursor-config` ボリュームで `/root/.cursor` を永続化
   - 以降は認証不要

詳細は [EXECUTION_ENVIRONMENT.md](./EXECUTION_ENVIRONMENT.md) を参照。

## 制限事項と注意点

1. **レート制限**: 公式ドキュメントに詳細が記載されていないため、実装時に確認が必要
2. **認証**: OAuth認証を使用（API Keyではない）。初回実行時に認証URLが表示される
3. **出力の保存**: `--output` フラグは存在しないため、`subprocess`でキャプチャする必要がある
4. **プロンプトファイル**: 直接指定するフラグはないため、ファイルを読み込んで `-p` に渡す必要がある
5. **コンテナ内での認証**: ホスト側のブラウザで認証を行う必要がある

## 参考リンク

- [Cursor CLI 概要](https://cursor.com/ja/docs/cli/overview)
- [CLIでAgentを使用する](https://cursor.com/ja/docs/cli/using)
- [Agent モード](https://cursor.com/ja/docs/agent/modes)
- [ルールシステム](https://cursor.com/ja/docs/context/rules)
