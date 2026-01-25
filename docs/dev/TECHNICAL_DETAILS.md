# 技術的詳細と実装上の課題

## 1. Cursor API/CLI の調査結果と対応方針

### 1.1 Cursor CLI の確認

**公式ドキュメント:**
- [Cursor CLI 公式ドキュメント](https://cursor.com/ja/docs/cli/overview)
- コマンド名: `agent` (not `cursor`)
- インストール: `curl https://cursor.com/install -fsS | bash`

**確認方法:**
```bash
which agent
agent --help
```

**非対話モード（スクリプト実行用）:**
```bash
# プロンプトを指定して実行（-p または --print）
agent -p "プロンプト内容" --model "gpt-5" --output-format text

# JSON形式で出力（パースしやすい）
agent -p "プロンプト内容" --output-format json

# Planモードで実行（計画作成用）
agent -p "プロンプト内容" --mode=plan --output-format text

# Askモードで実行（読み取り専用）
agent -p "プロンプト内容" --mode=ask --output-format text
```

**重要な注意事項:**
- 非対話モードでは、Cursorは**完全な書き込み権限**を持つ（ファイル編集、git commit等が可能）
- `.cursor/rules` ディレクトリのルールが自動的に読み込まれる
- `AGENTS.md` と `CLAUDE.md` も自動的に読み込まれる（プロジェクトルートに存在する場合）
- **認証**: API Keyではなく、OAuth認証を使用。初回実行時に認証URLが表示され、ブラウザで認証が必要

**セッション管理:**
```bash
# 過去のチャットを一覧表示
agent ls

# 最新の会話を再開
agent resume

# 特定の会話を再開
agent --resume="chat-id-here"
```

**実装での使用方法:**
```python
# プロンプトファイルを読み込んで実行
with open('prompts/planner.md', 'r') as f:
    prompt = f.read()

result = subprocess.run(
    ['agent', '-p', prompt, '--output-format', 'text'],
    capture_output=True,
    text=True,
    cwd=project_root
)
```

### 1.2 抽象化レイヤーの設計

**重要**: 初期実装ではCursor CLIのみを使用しますが、後からLLM API直接呼び出しに差し替え可能な設計にします。

**インターフェース設計:**
```python
# utils/llm_client.py
from abc import ABC, abstractmethod

class LLMClient(ABC):
    """LLMクライアントの抽象基底クラス"""
    
    @abstractmethod
    def call_agent(self, prompt: str, mode: str = "agent", **kwargs) -> str:
        """
        エージェントを呼び出してレスポンスを取得
        
        Args:
            prompt: プロンプト文字列
            mode: モード ("agent", "plan", "ask")
            **kwargs: その他のオプション（model等）
        
        Returns:
            エージェントの出力（文字列）
        """
        pass
    
    @abstractmethod
    def call_agent_from_file(self, prompt_file: str, mode: str = "agent", **kwargs) -> str:
        """プロンプトファイルから読み込んで実行"""
        pass
```

**実装方針:**
- Phase 1-3では `CursorCLIClient` のみを実装
- Phase 4以降で必要に応じて `OpenAIClient`, `AnthropicClient` などを追加可能
- 設定ファイル（`config.py`）でバックエンドを切り替え

### 1.3 将来の拡張: 直接LLM API呼び出し（Phase 4以降）

**注意**: 初期実装では実装しませんが、将来の拡張として設計に含めます。

**想定される実装:**
1. **OpenAI API (GPT-4, GPT-4 Turbo)**
   - 最も一般的
   - コード生成に優れている
   - レート制限あり

2. **Anthropic API (Claude)**
   - 長文コンテキストに強い
   - 指示遵守が良い

3. **その他 (Gemini, Llama等)**
   - コスト削減の選択肢

**実装方針:**
```python
# utils/cursor_client.py
import subprocess
import json

class CursorCLIClient:
    def __init__(self, project_root=".", output_format="text"):
        """
        Cursor CLIクライアント
        
        Args:
            project_root: プロジェクトのルートディレクトリ
            output_format: 出力形式 ("text" または "json")
        """
        self.project_root = project_root
        self.output_format = output_format
    
    def call_agent(self, prompt, mode="agent", model=None):
        """
        Cursor CLI経由でエージェントを実行
        
        Args:
            prompt: プロンプト文字列
            mode: モード ("agent", "plan", "ask")
            model: 使用するモデル（オプション）
        
        Returns:
            エージェントの出力（文字列）
        """
        cmd = ['agent', '-p', prompt, '--output-format', self.output_format]
        
        if mode != "agent":
            cmd.extend(['--mode', mode])
        
        if model:
            cmd.extend(['--model', model])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5分のタイムアウト
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Cursor CLI error: {result.stderr}")
            
            return result.stdout
        except subprocess.TimeoutExpired:
            raise RuntimeError("Cursor CLI timeout")
        except FileNotFoundError:
            raise RuntimeError("Cursor CLI not found. Install with: curl https://cursor.com/install -fsS | bash")
    
    def call_agent_from_file(self, prompt_file, mode="agent", model=None):
        """プロンプトファイルから読み込んで実行"""
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read()
        return self.call_agent(prompt, mode, model)

# 初期実装ではCursorCLIClientのみを使用
# 将来の拡張で、以下のようなファクトリーパターンで切り替え可能にする

class LLMClientFactory:
    """LLMクライアントのファクトリークラス（将来の拡張用）"""
    
    @staticmethod
    def create(backend="cursor_cli", **kwargs):
        """
        バックエンドに応じたLLMクライアントを作成
        
        Args:
            backend: バックエンド名 ("cursor_cli", "openai", "anthropic" 等)
            **kwargs: バックエンド固有の設定
        
        Returns:
            LLMClientのインスタンス
        """
        if backend == "cursor_cli":
            return CursorCLIClient(
                project_root=kwargs.get("project_root", "."),
                output_format=kwargs.get("output_format", "text")
            )
        # Phase 4以降で追加
        # elif backend == "openai":
        #     return OpenAIClient(api_key=kwargs.get("api_key"))
        # elif backend == "anthropic":
        #     return AnthropicClient(api_key=kwargs.get("api_key"))
        else:
            raise ValueError(f"Unknown backend: {backend}. Supported: cursor_cli")

# 使用例（初期実装）
# client = LLMClientFactory.create("cursor_cli", project_root=".")
# response = client.call_agent(prompt, mode="plan")
```

## 2. 状態管理の詳細設計

### 2.1 ファイルロック機構

**課題:**
複数のプロセスが同時に状態ファイルを更新すると、データ破損の可能性

**解決策:**
```python
import fcntl
import json

class StateManager:
    def update_tasks(self, update_func):
        with open('state/tasks.json', 'r+') as f:
            # ファイルロックを取得
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = json.load(f)
                updated_data = update_func(data)
                f.seek(0)
                f.truncate()
                json.dump(updated_data, f, indent=2, ensure_ascii=False)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**注意点:**
- Windowsでは`fcntl`が使えない → `msvcrt`を使用
- ロックが長時間保持されるとボトルネックになる（記事の教訓）

### 2.2 楽観的並行制御（推奨）

記事で言及されている楽観的並行制御を採用：

```python
class OptimisticStateManager:
    def update_tasks(self, update_func):
        max_retries = 5
        for attempt in range(max_retries):
            # 状態を読み込む
            with open('state/tasks.json', 'r') as f:
                data = json.load(f)
                version = data.get('version', 0)
            
            # 更新を試みる
            updated_data = update_func(data)
            updated_data['version'] = version + 1
            
            # 書き込み（バージョンチェック）
            try:
                with open('state/tasks.json', 'r+') as f:
                    current_data = json.load(f)
                    if current_data.get('version', 0) != version:
                        # 競合が発生
                        if attempt < max_retries - 1:
                            continue  # リトライ
                        else:
                            raise ConflictError("状態の競合が解決できませんでした")
                    
                    f.seek(0)
                    f.truncate()
                    json.dump(updated_data, f, indent=2, ensure_ascii=False)
                    return
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # 指数バックオフ
                    continue
                raise
```

## 3. エージェント実行の詳細

### 3.1 プロンプト構築

各エージェントは、現在の状態を読み込んでプロンプトを構築：

```python
class PlannerAgent(BaseAgent):
    def build_prompt(self, state):
        plan_content = self.read_file('state/plan.md')
        tasks_content = self.read_file('state/tasks.json')
        codebase_summary = self.get_codebase_summary()
        
        prompt_template = self.read_file('prompts/planner.md')
        
        prompt = prompt_template.format(
            current_plan=plan_content,
            existing_tasks=tasks_content,
            codebase_summary=codebase_summary,
            project_goal=self.config.project_goal
        )
        
        return prompt
```

### 3.2 レスポンスパース

LLMのレスポンスを構造化データに変換：

```python
class PlannerAgent(BaseAgent):
    def parse_response(self, response):
        # Markdown形式のレスポンスをパース
        # 例: ## 計画更新\n...\n## 新しいタスク\n1. ...
        
        # または、JSON形式で出力を要求
        # プロンプトで「JSON形式で出力してください」と指定
        
        try:
            # JSON部分を抽出
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except:
            pass
        
        # フォールバック: Markdownをパース
        return self.parse_markdown_response(response)
```

### 3.3 エラーハンドリング

```python
class BaseAgent:
    def run(self, max_retries=3):
        for attempt in range(max_retries):
            try:
                return self._run_internal()
            except APIError as e:
                if e.retryable and attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数バックオフ
                    self.logger.warning(f"APIエラー、{wait_time}秒後にリトライ: {e}")
                    time.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                self.logger.error(f"予期しないエラー: {e}")
                raise
```

## 4. コードベース操作

### 4.1 コードベースの探索

Plannerがコードベースを理解するために：

```python
class CodebaseExplorer:
    def get_summary(self, max_files=100):
        """コードベースの概要を取得"""
        files = self.list_code_files()
        
        # 重要なファイルを優先（README, メインファイル等）
        important_files = self.get_important_files(files)
        
        summaries = []
        for file in important_files[:max_files]:
            content = self.read_file(file)
            summary = self.summarize_file(file, content)
            summaries.append(summary)
        
        return "\n".join(summaries)
    
    def get_important_files(self, files):
        """重要度の高いファイルを特定"""
        priority_patterns = [
            r'README',
            r'main\.(py|ts|js)',
            r'package\.json',
            r'requirements\.txt',
            r'src/.*',
        ]
        # 優先順位付けロジック
        ...
```

### 4.2 Git操作

Workerがコード変更をコミット：

```python
class GitManager:
    def commit_changes(self, task_id, message):
        """変更をコミット"""
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run([
            'git', 'commit', 
            '-m', f"[{task_id}] {message}",
            '--author', 'Agent <agent@cursor-scage>'
        ], check=True)
    
    def get_diff(self):
        """現在の変更を取得"""
        result = subprocess.run(
            ['git', 'diff', '--cached'],
            capture_output=True,
            text=True
        )
        return result.stdout
```

## 5. ログとモニタリング

### 5.1 ログ構造

```python
class Logger:
    def log_agent_run(self, agent_name, iteration, prompt, response, duration):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'iteration': iteration,
            'prompt_length': len(prompt),
            'response_length': len(response),
            'duration_seconds': duration,
            'token_usage': self.get_token_usage(),  # APIから取得
        }
        
        # JSON形式でログファイルに追記
        with open(f'logs/execution_{datetime.now().strftime("%Y%m%d")}.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # 人間が読みやすい形式でも出力
        self.logger.info(f"[{agent_name}] Iteration {iteration} completed in {duration:.2f}s")
```

### 5.2 進捗モニタリング

```python
def print_status():
    """現在の状態を表示"""
    status = load_json('state/status.json')
    tasks = load_json('state/tasks.json')
    
    print(f"""
    === エージェント実行状況 ===
    イテレーション: {status['iteration']}
    継続判定: {status['should_continue']}
    総タスク数: {status['total_tasks']}
    完了タスク: {status['completed_tasks']}
    失敗タスク: {status['failed_tasks']}
    
    最後の実行:
      Planner: {status['last_planner_run']}
      Worker: {status['last_worker_run']}
      Judge: {status['last_judge_run']}
    """)
```

## 6. 実行環境の設計

### 6.1 Sandbox/DevContainerでの実行

**重要**: Cursor CLIは非対話モードでも、ファイル操作、git操作、シェルコマンド実行などの権限が必要です。利用できないコマンドが出てくると停止してしまうため、**必ずSandbox（Docker/DevContainer）で実行**します。

**実装方針:**
- DockerコンテナまたはDevContainerで実行
- コマンド制限をかけない（必要な権限をすべて許可）
- ホスト環境への影響を避ける
- プロジェクトディレクトリをボリュームマウント

詳細は [EXECUTION_ENVIRONMENT.md](./EXECUTION_ENVIRONMENT.md) を参照。

## 7. 対応が難しい部分

### 7.1 Cursor CLI の使用方法

**確認済み:**
- Cursor CLIは公式に公開されている（`agent` コマンド）
- 非対話モード（`-p` フラグ）でスクリプトから実行可能
- モード切り替え（`--mode=plan`, `--mode=ask`）が可能

**残っている課題:**
- 出力をファイルに直接保存する方法（`--output` フラグの有無）
- プロンプトファイルを直接指定する方法（現状は `-p` で文字列を渡す必要がある可能性）
- レート制限の詳細
- 認証方法（CLI経由の場合、Cursorアカウントとの連携方法）

**対応:**
- `subprocess` で `agent` コマンドを実行
- プロンプトファイルを読み込んで `-p` に渡す
- 出力をキャプチャしてファイルに保存
- エラーハンドリングとリトライロジックを実装

### 7.2 コンフリクト解決の自動化

**問題:**
- 複数のWorkerが同じファイルを変更した場合のコンフリクト解決
- Gitマージコンフリクトの自動解決は困難

**対応（最小構成）:**
- Workerは1つずつ順次実行（並列化しない）
- タスク単位でファイルの排他制御
- コンフリクトが発生した場合は、Judgeが判定して手動対応を促す

### 7.3 プロンプト設計の最適化

**問題:**
- エージェントが目標から逸脱する（ドリフト）
- 無意味な変更を繰り返す
- 無限ループに陥る

**対応:**
- プロンプトを外部ファイル化して、試行錯誤しやすくする
- Judgeが定期的にドリフトを検出
- 最大イテレーション数を設定
- 各エージェントの出力を検証するステップを追加

### 7.4 コスト管理

**問題:**
- 長時間動作でAPIコストが累積
- 予想外の高額請求

**対応:**
- 各API呼び出しのコストをログに記録
- 1日の上限を設定（設定ファイルで）
- トークン使用量を監視してアラート
- 低コストモデル（GPT-3.5等）を選択肢に含める

### 7.5 コード品質の保証

**問題:**
- 生成されたコードの品質が不安定
- バグが混入する可能性

**対応:**
- Workerの出力を検証するステップを追加
- 簡単なテストを実行（lint, 構文チェック等）
- Judgeがコードレビュー的な役割も担う
- 人間による最終レビューを前提とする（完全無人運用は目標外）

## 7. 実装時の注意点

### 7.1 状態の一貫性

- ファイル操作は必ずロックを使用
- エラー発生時も状態を破損させない
- 定期的にバックアップを取る

### 7.2 パフォーマンス

- 5分以上の待機時間を必ず設ける（API制限対策）
- 不要なAPI呼び出しを避ける
- キャッシュを活用（コードベースの要約等）

### 7.3 デバッグの容易さ

- 詳細なログを記録
- 各エージェントの入出力を保存
- 状態ファイルを人間が読みやすい形式で

### 7.4 拡張性

- 新しいエージェントタイプを追加しやすい設計
- プロンプトテンプレートを外部化
- 設定を外部ファイル化
