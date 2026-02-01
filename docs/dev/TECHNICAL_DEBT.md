# 技術的負債・コード品質レポート

> 作成日: 2026-02-01
> 対象: src/orchestragent 配下のPythonコード全体

## 概要

プロジェクト全体を精査した結果、**39件の課題**を特定しました。

| 優先度 | 件数 |
|--------|------|
| Critical（重大） | 5件 |
| High（高） | 12件 |
| Medium（中） | 15件 |
| Low（低） | 7件 |

---

## Critical（重大）- 5件

### 1. 広範な例外キャッチ

**問題**: `except Exception:` で詳細なエラーを握りつぶし、デバッグ困難

**該当箇所**:
- `src/orchestragent/tracking/git_helper.py`: 36, 73, 107, 133, 172, 211, 251, 278, 301, 324行
- `src/orchestragent/tracking/intent_manager.py`: 84行
- `src/orchestragent/agents/plan_judge.py`: 58行
- `src/orchestragent/llm/cursor_cli.py`: 128, 143, 152行

**推奨対応**: 具体的な例外クラスをキャッチし、スタックトレースをログに記録

---

### 2. 並列実行時のrace condition

**問題**: 複数ワーカーがファイルロック取得後に失敗すると部分的な状態が残る

**該当箇所**: `src/orchestragent/runner/loop.py`: 278-341行

**推奨対応**: トランザクションライクなセマンティクス実装、またはロールバック機構の追加

---

### 3. タスク完了時のrace condition

**問題**: 結果ファイル書き込み後にステータス更新が失敗するとデータ不整合

**該当箇所**: `src/orchestragent/state/manager.py`: 406-427行

```python
# 現状: 結果ファイル書き込み(419行) → ステータス更新(422行)
# 問題: 更新失敗時、結果ファイルは存在するがステータスは未更新
```

**推奨対応**: アトミックライトまたはトランザクションパターンの適用

---

### 4. StateManagerの責務過多（SRP違反）

**問題**: 1クラスに複数の責務が集中

**該当箇所**: `src/orchestragent/state/manager.py`: 24-705行

**現在の責務**:
- JSON/テキストファイルI/O（47-110行）
- タスク管理（236-435行）
- チェックポイント/バックアップ操作（461-704行）
- バリデーションロジック（634-705行）

**推奨対応**: 以下のクラスに分割
- `FileManager`: ファイルI/O操作
- `TaskManager`: タスクのCRUD操作
- `CheckpointManager`: チェックポイント管理
- `ValidationManager`: バリデーションロジック

---

### 5. run_main_loop()が497行の巨大関数

**問題**: テスト不可能、理解困難、保守性が低い

**該当箇所**: `src/orchestragent/runner/loop.py`: 29-525行

**推奨対応**: 以下の関数/クラスに分割
- `initialize_session()`: 設定の初期化
- `setup_agents()`: エージェントのセットアップ
- `run_plan_phase()`: 計画フェーズ
- `run_work_phase()`: 実行フェーズ
- `run_judge_phase()`: 評価フェーズ

---

## High（高）- 12件

### 1. グローバルconfig依存

**問題**: テスト困難な密結合

**該当箇所**: `src/orchestragent/agents/worker.py`: 12, 25-38行

```python
# 現状
from orchestragent import config
# WorkerAgent.__init__()内でconfig.XXXを直接参照
```

**推奨対応**: 依存性注入（DI）パターンの適用

---

### 2. JSONパース処理の重複

**問題**: 3箇所でほぼ同一のロジック

**該当箇所**:
- `src/orchestragent/agents/planner.py`: 124-150行
- `src/orchestragent/agents/judge.py`: 79-114行
- `src/orchestragent/agents/plan_judge.py`: 100-127行

**推奨対応**: `src/orchestragent/utils/json_parser.py` に共通ユーティリティとして抽出

---

### 3. タスク状態遷移の検証なし

**問題**: COMPLETED→IN_PROGRESSのような不正遷移が可能

**該当箇所**: `src/orchestragent/state/manager.py`: 398-435行

**推奨対応**: ステートマシンパターンの実装

```python
VALID_TRANSITIONS = {
    TaskStatus.PENDING: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED],
    TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED],
    TaskStatus.BLOCKED: [TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
    TaskStatus.COMPLETED: [],  # 完了後は遷移不可
    TaskStatus.FAILED: [TaskStatus.PENDING],  # リトライのみ許可
}
```

---

### 4. データモデルの検証不足

**問題**: 空文字列チェックなし、構造的なバリデーションなし

**該当箇所**:
- `src/orchestragent/models/task.py`: 68-101行
- `src/orchestragent/models/intent.py`: 39-76行

**推奨対応**: `__post_init__` での包括的バリデーション、Pydanticの導入検討

---

### 5. async安全性の問題

**問題**: ファイルロックでの原子性未保証

**該当箇所**: `src/orchestragent/runner/loop.py`: 278-341行

**推奨対応**: 適切な非同期プリミティブの使用、またはasyncio.Lockの導入

---

### 6. ファイル抽出パターンの重複（対応済み 2026-02-01）

**問題**: 3箇所で類似のregex

**対応内容**: `src/orchestragent/utils/file_extractor.py` に `extract_file_paths_from_text()` を追加。planner / task_scheduler / worker で共通利用。

---

### 7. テストインフラの欠如

**問題**: モック基盤なし、全エージェントが実インフラに依存

**該当箇所**: 全エージェントクラス

**推奨対応**:
- 依存性注入の導入
- モック実装の作成（MockLLMClient, MockStateManager等）

---

### 8. 循環参照のリスク

**問題**: 将来的なimport失敗の可能性

**該当箇所**:
- `src/orchestragent/agents/worker.py`: 12行
- `src/orchestragent/runner/loop.py`: 8-19行

**推奨対応**: ローカルインポートまたは依存関係の再設計

---

### 9. tests/ディレクトリなし

**問題**: ユニットテスト・結合テストの欠如

**推奨対応**: テストディレクトリの作成、pytest設定

---

### 10. 不十分なロギング

**問題**: スタックトレースの記録漏れ

**該当箇所**: 各所の`except`ブロック

**推奨対応**: `logging.exception()` または `traceback.format_exc()` の使用

---

### 11. プロンプト管理なし

**問題**: バージョニングやトラッキングの仕組みがない

**該当箇所**: `prompts/*.md`

**推奨対応**: プロンプトハブまたは専用管理クラスの導入

---

### 12. LLM I/Oの抽象化不足

**問題**: 各エージェントで個別にパース処理

**該当箇所**: `src/orchestragent/agents/*`

**推奨対応**: 共通のLLMクライアントクラスでパース・バリデーションを一元化

---

## Medium（中）- 15件

### 1. 型ヒントの不足

**該当箇所**:
- `src/orchestragent/agents/base.py`: 40-72行（`build_prompt()`の戻り値型なし）
- `src/orchestragent/agents/planner.py`: 110行（`_get_codebase_summary()`）
- `src/orchestragent/agents/judge.py`: 77行
- `src/orchestragent/scheduling/task_scheduler.py`: 105-115行

---

### 2. datetime importの不統一

**問題**: トップレベルとlazy importが混在

**該当箇所**:
- トップレベル: `intent_parser.py`, `task.py`
- Lazy: `planner.py:225`, `judge.py:140`, `worker.py:239`

**推奨対応**: モジュールレベルでの統一的なインポート

---

### 3. ファイルロックのbusy-waiting

**問題**: sleepによる非効率な待機

**該当箇所**: `src/orchestragent/state/file_lock.py`: 44-73行

**推奨対応**: `fcntl`を使用した適切なロック、またはイベントベースの待機

---

### 4. マジックナンバー

**該当箇所**: `src/orchestragent/llm/model_selector.py`: 65-78行

```python
# 現状
/ 1000.0  # 正規化係数
* 2.0     # ファイル数乗数
* 5.0     # 時間乗数
```

**推奨対応**: 設定ファイルまたは名前付き定数に移動

---

### 5. regexパターン未キャッシュ

**該当箇所**: `src/orchestragent/tracking/intent_parser.py`

**推奨対応**: クラスレベルでの事前コンパイル

---

### 6. 設定の不整合

**該当箇所**: `config.py`

**推奨対応**: dataclassベースの設定とバリデーション

---

### 7. 未使用メソッド

**該当箇所**: `src/orchestragent/agents/base.py`: 105-116行（`_get_priority_score()`）

**推奨対応**: 削除

---

### 8. 環境変数の検証なし

**該当箇所**: `config.py`: 127行

**推奨対応**: 起動時のバリデーションと明確なエラーメッセージ

---

### 9. ログローテーション制限なし

**該当箇所**: `src/orchestragent/core/logger.py`: 45-48行

**推奨対応**: バックアップファイル数の制限、古いログの自動削除

---

### 10. ファイル操作リトライなし

**該当箇所**: `src/orchestragent/state/manager.py`: 225-234行

**推奨対応**: 指数バックオフ付きリトライデコレータの追加

---

### 11. パストラバーサルリスク

**該当箇所**: `src/orchestragent/state/file_lock.py`: 39-42行

**推奨対応**: `pathlib.Path.resolve()`の使用と期待ディレクトリ内チェック

---

### 12. コマンドインジェクションリスク

**該当箇所**: `src/orchestragent/tracking/git_helper.py`: 51-56行

**推奨対応**: 入力フォーマットの検証、`--`セパレータの使用

---

### 13. タスク統計の非効率

**該当箇所**: `src/orchestragent/state/manager.py`: 334-343行

**問題**: 毎回全ファイル読み込み（O(n)）

**推奨対応**: インクリメンタル統計の維持またはTTL付きキャッシュ

---

### 14. 不要なシャローコピー

**該当箇所**: `src/orchestragent/state/manager.py`: 139行

**推奨対応**: `copy.deepcopy()`の使用または動作のドキュメント化

---

### 15. ハードコーディングされたパス

**該当箇所**: エージェント内のプロンプトテンプレートパス

**推奨対応**: 設定ファイルでの管理

---

## Low（低）- 7件

### 1. Planテンプレートのフォールバック不完全

**該当箇所**: `src/orchestragent/agents/planner.py`: 19-40行

---

### 2. 設定ホットリロードなし

**問題**: 変更に再起動が必要

---

### 3. チェックポイント圧縮なし（対応済み）

**該当箇所**: `src/orchestragent/state/checkpoint_manager.py`, `StateManager.compress_old_checkpoints`

**対応内容**: 最新以外の過去チェックポイントを `.tar.gz` に圧縮する `compress_old_checkpoints(keep_latest_n=1)` を追加。メインループではチェックポイント作成後に自動で古いものを圧縮（`RunnerConfig.compress_old_checkpoints`、デフォルト True）。復元時は `.tar.gz` を一時展開してから復元可能。

---

### 4. 大容量ファイルのサイズ制限なし

**該当箇所**: `src/orchestragent/tracking/git_helper.py`: 254-279行

---

### 5. ドキュメント不足

**問題**: モジュールレベルdocstringなし

---

### 6. 観測可能性の不足

**問題**: メトリクス収集なし（実行時間、トークン数、成功率等）

**推奨対応**: OpenTelemetryの導入検討

---

### 7. リトライ戦略の不足

**問題**: エラー種別に応じた戦略なし

---

## コード重複箇所サマリー

| パターン | 発生箇所 | 対応状況 |
|---------|---------|---------|
| JSON抽出ロジック | planner.py, judge.py, plan_judge.py | ✅ `utils/json_parser.py` に抽出済み |
| エージェント初期化 | loop.py (118-163) | ✅ `setup_agents()` に分離済み |
| ファイルパス抽出regex | planner.py, task_scheduler.py, worker.py | ✅ `utils/file_extractor.py` に統合済み（2026-02-01） |

---

## リファクタリング推奨順序

### Phase 1: 安全基盤の構築（1週目）

1. **テストハーネスの構築**
   - `tests/`ディレクトリ作成
   - pytest設定
   - 結合テストから開始

2. **ロギングの改善**
   - `except Exception:`でスタックトレースを記録
   - `logging.exception()`の使用

3. **型ヒントの拡充**
   - 関数シグネチャとクラス属性から開始

### Phase 2: 巨大関数の分割と依存整理（2-3週目）

1. **`run_main_loop()`の分割**
   - 初期化、エージェントセットアップ、1イテレーションに分離
   - 各関数を個別にテスト可能にし、テストコードを追加

2. **config依存性注入（DI）**
   - グローバルconfig参照を排除
   - コンストラクタで設定オブジェクトを受け取る
   - 詳細なテストコードを追加

### Phase 3: コアロジックの再設計（1-2ヶ月目）

1. **StateManagerの責務分割**
   - `TaskRepository`: タスクのCRUD
   - `StateSerializer`: シリアライズ/デシリアライズ
   - `MetricsTracker`: 統計情報

2. **LLM I/Oの抽象化**
   - Pydanticモデル導入
   - 共通パース処理の実装

---

## チェックリスト

### 即座に対応すべき項目（Phase 1 完了）

- [x] `except Exception:` → 具体的例外 + スタックトレース記録 ✅ 2026-02-01
- [x] `tests/` ディレクトリ作成 ✅ 2026-02-01
- [x] 型ヒントの追加（基本的な修正） ✅ 2026-02-01
- [x] 未使用メソッド `_get_priority_score()` の削除 ✅ 2026-02-01
- [x] JSONパース処理の共通化 ✅ 2026-02-01

### 短期対応項目

- [x] `run_main_loop()` の分割 ✅ 2026-02-01
- [x] タスク状態遷移の検証追加 ✅ 2026-02-01（VALID_TRANSITIONS・can_transition/validate_task_status_transition を models/task.py に追加、StateManager.update_task で検証、テスト追加）
- [x] config依存性注入 ✅ 2026-02-01（RunnerConfig 導入、WorkerAgent DI、loop は ctx.runner_config 参照）
- [x] ファイルパス抽出regexの共通化 ✅ 2026-02-01（utils/file_extractor.py に extract_file_paths_from_text を追加、planner / task_scheduler / worker で利用）

### 中長期対応項目

- [x] StateManager の責務分割 ✅ 2026-02-01（FileManager / TaskManager / CheckpointManager / ValidationManager に分割、StateManager はファサードで既存API維持）
- [ ] テストカバレッジの向上
- [ ] 観測可能性（メトリクス）の追加
- [ ] プロンプトバージョニング
