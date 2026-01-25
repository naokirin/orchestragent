# アーキテクチャ設計: 抽象化レイヤー

## 設計方針

初期実装では**Cursor CLIのみ**を使用しますが、後からLLM API直接呼び出しに差し替え可能な設計にします。

## 抽象化レイヤーの設計

### インターフェース定義

```python
# utils/llm_client.py
from abc import ABC, abstractmethod
from typing import Optional

class LLMClient(ABC):
    """LLMクライアントの抽象基底クラス
    
    このインターフェースを実装することで、異なるバックエンド
    （Cursor CLI、OpenAI API、Anthropic API等）を切り替え可能にする。
    """
    
    @abstractmethod
    def call_agent(
        self, 
        prompt: str, 
        mode: str = "agent", 
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        エージェントを呼び出してレスポンスを取得
        
        Args:
            prompt: プロンプト文字列
            mode: モード ("agent", "plan", "ask")
            model: 使用するモデル（オプション、バックエンドによって異なる）
            **kwargs: その他のオプション
        
        Returns:
            エージェントの出力（文字列）
        
        Raises:
            RuntimeError: エージェント呼び出しに失敗した場合
        """
        pass
    
    @abstractmethod
    def call_agent_from_file(
        self, 
        prompt_file: str, 
        mode: str = "agent", 
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        プロンプトファイルから読み込んで実行
        
        Args:
            prompt_file: プロンプトファイルのパス
            mode: モード ("agent", "plan", "ask")
            model: 使用するモデル（オプション）
            **kwargs: その他のオプション
        
        Returns:
            エージェントの出力（文字列）
        """
        pass
```

### Cursor CLI実装（Phase 1-3で使用）

```python
# utils/cursor_cli_client.py
import subprocess
from pathlib import Path
from typing import Optional
from .llm_client import LLMClient

class CursorCLIClient(LLMClient):
    """Cursor CLI経由でエージェントを実行するクライアント"""
    
    def __init__(self, project_root: str = ".", output_format: str = "text"):
        """
        Args:
            project_root: プロジェクトのルートディレクトリ
            output_format: 出力形式 ("text" または "json")
        """
        self.project_root = Path(project_root).resolve()
        self.output_format = output_format
    
    def call_agent(
        self, 
        prompt: str, 
        mode: str = "agent", 
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Cursor CLI経由でエージェントを実行"""
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
                cwd=str(self.project_root),
                timeout=kwargs.get('timeout', 300)  # デフォルト5分
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Cursor CLI error: {result.stderr}")
            
            return result.stdout
        except subprocess.TimeoutExpired:
            raise RuntimeError("Cursor CLI timeout")
        except FileNotFoundError:
            raise RuntimeError(
                "Cursor CLI not found. Install with: "
                "curl https://cursor.com/install -fsS | bash"
            )
    
    def call_agent_from_file(
        self, 
        prompt_file: str, 
        mode: str = "agent", 
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """プロンプトファイルから読み込んで実行"""
        prompt_path = Path(prompt_file)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        return self.call_agent(prompt, mode, model, **kwargs)
```

### ファクトリーパターン

```python
# utils/llm_client_factory.py
from typing import Dict, Any
from .llm_client import LLMClient
from .cursor_cli_client import CursorCLIClient

class LLMClientFactory:
    """LLMクライアントのファクトリークラス"""
    
    @staticmethod
    def create(backend: str = "cursor_cli", **kwargs) -> LLMClient:
        """
        バックエンドに応じたLLMクライアントを作成
        
        Args:
            backend: バックエンド名
                - "cursor_cli": Cursor CLI経由（初期実装）
                - "openai": OpenAI API直接呼び出し（Phase 4以降）
                - "anthropic": Anthropic API直接呼び出し（Phase 4以降）
            **kwargs: バックエンド固有の設定
        
        Returns:
            LLMClientのインスタンス
        
        Raises:
            ValueError: サポートされていないバックエンドが指定された場合
        """
        if backend == "cursor_cli":
            return CursorCLIClient(
                project_root=kwargs.get("project_root", "."),
                output_format=kwargs.get("output_format", "text")
            )
        # Phase 4以降で追加可能
        # elif backend == "openai":
        #     return OpenAIClient(api_key=kwargs.get("api_key"))
        # elif backend == "anthropic":
        #     return AnthropicClient(api_key=kwargs.get("api_key"))
        else:
            supported = ["cursor_cli"]  # Phase 4以降で拡張
            raise ValueError(
                f"Unknown backend: {backend}. "
                f"Supported backends: {', '.join(supported)}"
            )
```

## エージェントでの使用例

```python
# agents/base.py
from utils.llm_client_factory import LLMClientFactory
from utils.llm_client import LLMClient

class BaseAgent:
    """エージェントの基底クラス"""
    
    def __init__(self, config):
        """
        Args:
            config: 設定オブジェクト（backend等を含む）
        """
        # 抽象化レイヤー経由でクライアントを取得
        self.llm_client: LLMClient = LLMClientFactory.create(
            backend=config.get("llm_backend", "cursor_cli"),
            project_root=config.get("project_root", "."),
            output_format=config.get("output_format", "text")
        )
    
    def run(self):
        """エージェントを実行"""
        # プロンプトを構築
        prompt = self.build_prompt()
        
        # 抽象化レイヤー経由で呼び出し（バックエンドに依存しない）
        response = self.llm_client.call_agent(
            prompt=prompt,
            mode=self.mode,
            model=self.config.get("model")
        )
        
        # レスポンスを処理
        return self.process_response(response)
```

## 設定ファイルでの切り替え

```python
# config.py
CONFIG = {
    "llm_backend": "cursor_cli",  # Phase 4以降で "openai" や "anthropic" に変更可能
    "project_root": ".",
    "output_format": "text",  # または "json"
    "model": None,  # Cursor CLIの場合はデフォルトモデルを使用
}

# Phase 4以降の例
# CONFIG = {
#     "llm_backend": "openai",
#     "api_key": os.getenv("OPENAI_API_KEY"),
#     "model": "gpt-4-turbo",
# }
```

## 将来の拡張（Phase 4以降）

### OpenAI API実装の例

```python
# utils/openai_client.py (Phase 4以降で実装)
from openai import OpenAI
from .llm_client import LLMClient

class OpenAIClient(LLMClient):
    """OpenAI API経由でエージェントを実行するクライアント"""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def call_agent(self, prompt: str, mode: str = "agent", **kwargs) -> str:
        # OpenAI APIを呼び出し
        # modeに応じたプロンプトエンジニアリング
        # ...
        pass
```

### 切り替え方法

設定ファイルを変更するだけで、バックエンドを切り替え可能：

```python
# config.py を変更
CONFIG["llm_backend"] = "openai"
CONFIG["api_key"] = os.getenv("OPENAI_API_KEY")

# エージェントのコードは変更不要
agent = PlannerAgent(config=CONFIG)
agent.run()  # 自動的にOpenAI APIを使用
```

## 設計の利点

1. **疎結合**: エージェントのコードはバックエンドに依存しない
2. **拡張性**: 新しいバックエンドを追加しやすい
3. **テスト容易性**: モッククライアントを簡単に作成可能
4. **設定による切り替え**: コード変更なしでバックエンドを切り替え可能

## 実装時の注意点

1. **インターフェースの一貫性**: すべての実装が同じインターフェースを満たすこと
2. **エラーハンドリング**: バックエンド固有のエラーを適切に処理
3. **設定の検証**: バックエンドに応じた必須設定のチェック
4. **ログ記録**: どのバックエンドを使用しているかをログに記録
