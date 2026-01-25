# プロジェクト計画

## 概要
プランナー・ワーカースタイル自律エージェントシステムのPhase 1（最小動作確認）を完了させる。

## Phase 1: 最小動作確認（現在）

### 実装済み
- ✅ ファイルベースの状態管理（StateManager）
- ✅ ロギング機能（AgentLogger）
- ✅ LLM抽象化レイヤー（LLMClient, CursorCLIClient, LLMClientFactory）
- ✅ Plannerエージェントの基本実装
- ✅ Docker環境設定
- ✅ 基本テストスクリプト（test_phase1.py）

### 残タスク
- [ ] モックLLMクライアントの実装（Cursor CLI不要のテスト用）
- [ ] Plannerエージェントの単体テスト強化
- [ ] Cursor CLI連携のエンドツーエンドテスト
- [ ] エラーハンドリングの改善
- [ ] StateManagerのタスク管理機能拡張

## Phase 2: 基本ループ（次フェーズ）
- Workerエージェントの実装
- Judgeエージェントの実装
- メインループの実装（再計画 → 実行 → 判定）

## 技術的な決定事項
1. バックエンドはCursor CLI優先、抽象化レイヤーで差し替え可能
2. 状態管理はファイルベース（JSON/Markdown）
3. エージェント間通信は状態ファイル経由