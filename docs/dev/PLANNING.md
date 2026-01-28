# プランナー・ワーカースタイル自律エージェントシステム 要件整理と計画書

## 1. プロジェクト概要

### 1.1 目標
Cursorブログ記事「長時間稼働する自律型コーディングをスケールさせる」で紹介されているプランナー・ワーカースタイルのエージェントシステムを、最小構成で実装する。

### 1.2 成功基準
- ✅ 複数エージェント（役割分離：Planner, Worker, Judge）
- ✅ 自律ループ（再計画 → 実行 → 判定）
- ✅ 長時間動作（数時間〜数日）
- ❌ 高スループット（不要）
- ❌ 完全無人運用（不要）

## 2. 技術選定

### 2.1 プログラミング言語
**推奨: Python**

**理由:**
- ファイルI/O、JSON処理が簡単
- Markdown処理ライブラリが豊富（markdown, mistune等）
- エラーハンドリングが容易
- 長時間動作のためのスリープ処理が簡単
- Cursor CLIとの統合が容易（subprocess実行）

**代替案: TypeScript/Node.js**
- 型安全性が高い
- 非同期処理が強力
- ただし、ファイル操作がやや冗長

### 2.2 Cursor API/CLI の使用方法

**公式ドキュメント確認済み:**
- [Cursor CLI 公式ドキュメント](https://cursor.com/ja/docs/cli/overview)
- コマンド名: `agent` (not `cursor`)
- インストール: `curl https://cursor.com/install -fsS | bash`

**実装アプローチ:**

1. **Cursor CLI経由（初期実装）**
   - `agent -p "プロンプト" --output-format text` で非対話実行
   - `--mode=plan` でPlanner用、通常モードでWorker用
   - プロンプトファイルを読み込んで `-p` に渡す
   - 出力を `subprocess` でキャプチャしてファイルに保存
   - **認証**: OAuth認証を使用（API Keyではない）。初回実行時に認証URLが表示され、ホスト側のブラウザで認証が必要

2. **将来の拡張: 直接LLM API呼び出し（Phase 4以降）**
   - OpenAI API / Anthropic APIを直接使用
   - より細かい制御が必要な場合や、コスト最適化が必要な場合
   - **注意**: 初期実装では考慮しないが、抽象化レイヤーで切り替え可能にする

**実装方針:**
- **Phase 1-3: Cursor CLIのみで実装**（`agent` コマンド使用）
- 抽象化レイヤー（`LLMClient`インターフェース）を設計し、後からLLM API直接呼び出しに差し替え可能にする
- 設定ファイルでバックエンドを切り替え可能にする設計

### 2.3 実行環境

**重要: Sandbox/DevContainerでの実行**

Cursor CLIは非対話モードでも、ファイル操作、git操作、シェルコマンド実行などの権限が必要です。利用できないコマンドが出てくると停止してしまうため、**必ずSandbox（Docker/DevContainer）で実行**します。

**実行環境の要件:**
- DockerコンテナまたはDevContainerで実行
- コマンド制限をかけない（必要な権限をすべて許可）
- ホスト環境への影響を避ける
- プロジェクトディレクトリをボリュームマウント

**実装方針:**
- Dockerfileまたは`.devcontainer/devcontainer.json`を提供
- 必要なツール（git, python, cursor CLI等）をインストール
- セキュリティはコンテナレベルで制御

### 2.4 状態管理

**ファイルベース（推奨）**
- `state/plan.md`: 現在の計画（Markdown形式）
- `state/tasks.json`: タスクキュー（JSON形式）
- `state/results/`: Worker成果物（各タスクごとのファイル）
- `state/status.json`: 進行状態（JSON形式）
- `logs/`: 実行ログ（テキストファイル）

**理由:**
- シンプルでデバッグしやすい
- バージョン管理可能
- 人間が直接確認・編集可能
- 外部依存なし

## 3. アーキテクチャ設計

### 3.1 ディレクトリ構造

```
orchestragent/
├── main.py                 # メインループ
├── config.py               # 設定ファイル
├── state/
│   ├── plan.md            # 現在の計画
│   ├── tasks.json         # タスクキュー
│   ├── results/           # Worker成果物
│   │   └── task_*.md      # 各タスクの結果
│   └── status.json        # 進行状態
├── logs/
│   └── execution_*.log    # 実行ログ
├── agents/
│   ├── __init__.py
│   ├── base.py            # ベースエージェントクラス
│   ├── planner.py         # Plannerエージェント
│   ├── worker.py          # Workerエージェント
│   └── judge.py           # Judgeエージェント
├── prompts/
│   ├── planner.md         # Planner用プロンプト
│   ├── worker.md          # Worker用プロンプト
│   └── judge.md           # Judge用プロンプト
├── utils/
│   ├── state_manager.py   # 状態管理ユーティリティ
│   ├── cursor_client.py   # Cursor CLI/API クライアント
│   └── logger.py          # ロギングユーティリティ
└── README.md
```

### 3.2 エージェント間の通信フロー

```
┌─────────────┐
│  Main Loop  │
└──────┬──────┘
       │
       ├─→ [Planner] ──→ plan.md, tasks.json を更新
       │
       ├─→ [Worker] ──→ tasks.json からタスク取得
       │                 └─→ results/task_*.md に結果出力
       │
       └─→ [Judge] ──→ status.json を更新
                       └─→ should_continue: true/false
```

### 3.3 データ構造

#### `state/tasks.json`
```json
{
  "tasks": [
    {
      "id": "task_001",
      "title": "機能Xの実装",
      "priority": "high|medium|low",
      "created_at": "2026-01-26T10:00:00Z"
    }
  ],
  "next_task_id": 2
}
```

**注意**: `tasks.json` はタスクのインデックス（IDとメタ情報のみ）を保持します。
- **状態管理**: ステータス（`status`）や実行情報（`assigned_to`, `started_at`, `completed_at` など）は個別タスクファイル（`state/tasks/task_XXX.json`）に保存されます。
- **理由**: 複数のWorkerが並列実行する際、`tasks.json` への同時書き込みによる競合を避けるため、状態更新は個別ファイルのみで行います。

#### `state/status.json`
```json
{
  "iteration": 1,
  "last_planner_run": "2026-01-26T10:00:00Z",
  "last_worker_run": "2026-01-26T10:05:00Z",
  "last_judge_run": "2026-01-26T10:10:00Z",
  "should_continue": true,
  "reason": "タスクが残っているため継続",
  "total_tasks": 10,
  "completed_tasks": 3,
  "failed_tasks": 0
}
```

## 4. 各エージェントの詳細設計

### 4.1 Planner（プランナー）

**役割:**
- コードベースを探索してタスクを作成
- 既存の計画を更新
- タスクを優先順位付け

**入力:**
- 現在のコードベース状態
- 既存の計画（plan.md）
- 既存のタスクリスト（tasks.json）

**出力:**
- 更新された計画（plan.md）
- 新しいタスク（tasks.jsonに追加）

**プロンプト設計のポイント:**
- コードベース全体の理解を促す
- タスクを適切な粒度に分割
- 依存関係を考慮した優先順位付け
- 既存のタスクとの重複を避ける

### 4.2 Worker（ワーカー）

**役割:**
- タスクを受け取り、実装を実行
- コード変更をコミット
- 結果を記録

**入力:**
- 割り当てられたタスク（tasks.jsonから取得）
- 関連するコードファイル

**出力:**
- 実装結果（results/task_*.md）
- コード変更（git commit）
- タスク状態の更新

**プロンプト設計のポイント:**
- タスクに集中させる
- 他のワーカーとの調整は不要（シンプルに保つ）
- エラーハンドリングを促す
- 完了条件を明確にする

### 4.3 Judge（判定者）

**役割:**
- 全体の進捗を評価
- 継続すべきか判定
- 品質チェック

**入力:**
- 現在の計画（plan.md）
- タスクリスト（tasks.json）
- 完了したタスクの結果（results/）

**出力:**
- 継続判定（status.json）
- 必要に応じて推奨事項

**プロンプト設計のポイント:**
- 客観的な評価を促す
- ドリフト（目標からの逸脱）を検出
- 完了条件を明確に判断

## 5. 実装フロー

### 5.1 メインループ

```python
def main_loop():
    while True:
        # 1. Planner実行
        planner.run()
        wait(1 minutes)
        
        # 2. Worker実行（利用可能なタスクがある限り）
        while has_pending_tasks():
            worker.run()
            wait(1 minutes)
        
        # 3. Judge実行
        judge.run()
        
        # 4. 継続判定
        if not should_continue():
            break
        
        # 5. 次のイテレーション前に待機
        wait(5 minutes)
```

### 5.2 エージェント実行の抽象化

```python
class BaseAgent:
    def run(self):
        # 1. 状態を読み込む
        state = self.load_state()
        
        # 2. プロンプトを構築
        prompt = self.build_prompt(state)
        
        # 3. Cursor/LLM APIを呼び出す
        response = self.call_llm(prompt)
        
        # 4. レスポンスをパース
        result = self.parse_response(response)
        
        # 5. 状態を更新
        self.update_state(result)
        
        # 6. ログを記録
        self.log(result)
```

## 6. 実行環境

### 6.1 Sandbox/DevContainerでの実行

**重要**: Cursor CLIは非対話モードでも、ファイル操作、git操作、シェルコマンド実行などの権限が必要です。利用できないコマンドが出てくると停止してしまうため、**必ずSandbox（Docker/DevContainer）で実行**します。

**実装方針:**
- DockerコンテナまたはDevContainerで実行
- コマンド制限をかけない（必要な権限をすべて許可）
- ホスト環境への影響を避ける
- プロジェクトディレクトリをボリュームマウント

詳細は [EXECUTION_ENVIRONMENT.md](./EXECUTION_ENVIRONMENT.md) を参照。

## 7. 制約と課題

### 7.1 Cursor CLI の制約

**確認済み:**
- Cursor CLIは公式に公開されている（`agent` コマンド）
- 非対話モードでスクリプトから実行可能

**残っている課題:**
- 出力をファイルに直接保存する方法（`subprocess` でキャプチャする必要がある可能性）
- プロンプトファイルを直接指定する方法（現状は `-p` で文字列を渡す）
- レート制限の詳細
- 認証方法（Cursorアカウントとの連携）

**対応策:**
- `subprocess` で `agent` コマンドを実行し、出力をキャプチャ
- プロンプトファイルを読み込んで `-p` に渡す
- 抽象化レイヤーを設けて、Cursor CLI/直接LLM APIのいずれでも動作するようにする
- 設定ファイルで切り替え可能にする
- フォールバック機能を実装

### 7.2 長時間動作の安定性

**課題:**
- プロセスが異常終了する可能性
- メモリリーク
- ネットワークエラー

**対応策:**
- 定期的に状態を保存（各エージェント実行後）
- エラーハンドリングとリトライロジック
- ログを詳細に記録
- 再起動時に状態を復元できるようにする

### 7.3 コンフリクト管理

**課題:**
- 複数のWorkerが同じファイルを変更する可能性
- Gitコンフリクトの解決

**対応策（最小構成では簡略化）:**
- タスク単位でファイルロック（簡易版）
- Workerは1つずつ順次実行（並列化は後回し）
- コンフリクトが発生した場合は、Judgeが判定

### 7.4 プロンプト設計の難しさ

**課題:**
- エージェントが目標から逸脱（ドリフト）
- 病的な挙動（無限ループ、無意味な変更）

**対応策:**
- プロンプトを外部ファイル化して、試行錯誤しやすくする
- 各エージェントの出力を検証するステップを追加
- Judgeが定期的にドリフトを検出

### 7.5 コスト管理

**課題:**
- LLM API呼び出しのコストが累積
- 長時間動作で予想外のコスト

**対応策:**
- 各API呼び出しのコストをログに記録
- 1日の上限を設定
- トークン使用量を監視

## 7. 実装の優先順位

### Phase 1: 最小動作確認
1. ファイルベースの状態管理
2. 単一エージェント（Planner）の動作確認
3. Cursor CLI/API との統合確認

### Phase 2: 基本ループ
1. メインループの実装
2. Planner + Worker の連携
3. Judge の実装

### Phase 3: 安定化
1. エラーハンドリング
2. ログ機能
3. 状態の永続化と復元

### Phase 4: 最適化・拡張（後回し）
1. 複数Workerの並列実行
2. より高度なコンフリクト解決
3. パフォーマンス最適化
4. **LLM API直接呼び出しの実装**（必要に応じて）
   - OpenAI API / Anthropic APIの直接呼び出し
   - 抽象化レイヤー経由で切り替え可能

## 8. 次のステップ

1. **技術調査**
   - ✅ Cursor CLIの仕様確認（完了）
   - ~~利用可能なLLM APIの選定~~（Phase 4で検討）

2. **プロトタイプ作成**
   - 最小構成での動作確認
   - 各エージェントのプロンプト設計
   - 抽象化レイヤー（`LLMClient`インターフェース）の設計

3. **段階的実装**
   - Phase 1から順次実装（Cursor CLIのみ使用）
   - 各フェーズで動作確認
   - 抽象化レイヤーを維持して、将来の拡張に備える

4. **テストと改善**
   - 小規模プロジェクトでテスト
   - プロンプトの調整
   - バグ修正
