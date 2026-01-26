# ダッシュボード形式CLI表示の技術選定

## 要件

1. **全体の概要一覧**
   - 最初の指示内容（PROJECT_GOAL）
   - タスク一覧
   - 各ステータス（pending, in_progress, completed, failed）
   - 現在の進行状況（イテレーション数、完了率など）

2. **現在進行中のログ**
   - リアルタイムで更新されるログ表示
   - エージェントの実行ログ
   - エラーログ

3. **各タスクの内容の確認**
   - タスクの詳細情報
   - タスクの実行結果
   - タスクの履歴

4. **読み込んだ設定**
   - 環境変数
   - 設定ファイルの内容
   - 実行環境情報

5. **インタラクティブな切り替え**
   - キーボード操作で画面を切り替え
   - リアルタイム更新

## 技術選定

### 候補ライブラリ

#### 1. **rich + textual** ⭐ 推奨

**メリット:**
- モダンで活発に開発されている（2024年時点で最新）
- 美しいUIが簡単に作れる
- タブ切り替え、リアルタイム更新が容易
- ドキュメントが充実している
- richは既に多くのプロジェクトで使われている
- 日本語対応が良好
- パフォーマンスが良い

**デメリット:**
- Python 3.7以上が必要（既存プロジェクトは対応済み想定）

**使用例:**
```python
from textual.app import App
from textual.widgets import Header, Footer, Tabs, Tab
from textual.containers import Container

class DashboardApp(App):
    def compose(self):
        yield Header()
        yield Tabs("概要", "ログ", "タスク", "設定")
        yield Container(id="content")
        yield Footer()
```

#### 2. **prompt_toolkit**

**メリット:**
- 非常に柔軟で強力
- 複雑なインタラクションが可能

**デメリット:**
- 学習コストが高い
- タブ切り替えなどのUI構築がやや複雑
- ドキュメントがやや不足

#### 3. **blessed/blessings**

**メリット:**
- 低レベルな制御が可能

**デメリット:**
- UI構築が手動で大変
- モダンなUIコンポーネントがない

#### 4. **asciimatics**

**メリット:**
- アニメーション対応

**デメリット:**
- メンテナンスが活発でない
- タブ切り替えなどの機能が限定的

#### 5. **urwid**

**メリット:**
- 古くからある安定したライブラリ

**デメリット:**
- 開発が活発でない
- モダンな機能が少ない
- ドキュメントが古い

### 選定結果: **rich + textual**

**理由:**
1. モダンで活発に開発されている
2. タブ切り替えなどの要件を満たす機能が豊富
3. 日本語対応が良好
4. ドキュメントが充実している
5. 既存のコードとの統合が容易

## アーキテクチャ設計

### 要件の追加

- **コマンドラインオプションで切り替え可能**
  - `python main.py` → 既存の簡易ログ形式（デフォルト）
  - `python main.py --dashboard` → ダッシュボード形式
- **既存のコードを保持**
  - `main.py`の既存ロジックを維持
  - 既存のprint文ベースの表示をそのまま使用可能

### 選定方式: コマンドラインオプションによる分岐

```
main.py
├─ argparseでコマンドラインオプションを解析
├─ --dashboard オプションがない場合（デフォルト）
│  └─ 既存のprint文ベースの表示（変更なし）
└─ --dashboard オプションがある場合
   └─ DashboardApp (textual App) を起動
      ├─ メインループを別スレッドで実行
      └─ 状態をリアルタイムで監視・表示
```

**メリット:**
- 既存のコードへの影響が最小限
- 既存の表示方法を完全に保持
- ユーザーが選択可能
- 後方互換性を維持

**実装方針:**
1. `main.py`にargparseを追加
2. 既存のメインループロジックを`run_main_loop()`関数に抽出
3. ダッシュボードモードの場合は`DashboardApp`を起動
4. `DashboardApp`内で`run_main_loop()`を別スレッドで実行
5. 通常モードの場合は`run_main_loop()`を直接実行

### コード構造

```python
# main.py
import argparse
from dashboard.app import DashboardApp

def run_main_loop():
    """既存のメインループロジック（print文ベース）"""
    # 既存のコードをそのまま移動
    ...

def main():
    parser = argparse.ArgumentParser(description='自律エージェントシステム')
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='ダッシュボード形式で表示'
    )
    args = parser.parse_args()
    
    if args.dashboard:
        # ダッシュボードモード
        app = DashboardApp()
        app.run()
    else:
        # 通常モード（既存の動作）
        run_main_loop()
```

### ダッシュボードアプリの構造

```python
# dashboard/app.py
from textual.app import App
import threading
from main import run_main_loop

class DashboardApp(App):
    def on_mount(self):
        # メインループを別スレッドで実行
        self.main_loop_thread = threading.Thread(
            target=run_main_loop,
            daemon=True
        )
        self.main_loop_thread.start()
        
        # 状態監視を開始
        self.set_interval(0.5, self.update_display)
    
    def update_display(self):
        # 状態ファイルを読み込んで表示を更新
        ...
```

## 実装計画

### Phase 0: リファクタリング（既存コードの整理）
1. `main.py`のメインループロジックを`run_main_loop()`関数に抽出
2. argparseでコマンドラインオプションを追加
3. 既存の動作が維持されることを確認

### Phase 1: 基本構造の作成
1. `rich`と`textual`のインストール
2. `dashboard/`ディレクトリの作成
3. 基本的なダッシュボードアプリの作成
4. タブ切り替え機能の実装
5. メインループを別スレッドで実行する機能

### Phase 2: 各画面の実装
1. **概要画面**
   - プロジェクト目標の表示
   - タスク統計の表示
   - 進行状況の表示

2. **ログ画面**
   - リアルタイムログの表示
   - ログのフィルタリング
   - ログの検索

3. **タスク画面**
   - タスク一覧の表示
   - タスク詳細の表示
   - タスクの選択と詳細表示

4. **設定画面**
   - 設定の表示
   - 環境情報の表示

### Phase 3: リアルタイム更新
1. 状態ファイルの監視
2. ログファイルの監視
3. 自動更新機能の実装

### Phase 4: インタラクション強化
1. キーボードショートカット
2. タスクの詳細表示
3. ログのフィルタリング

## 依存関係

```txt
rich>=13.0.0
textual>=0.40.0
```

## 参考資料

- [Textual Documentation](https://textual.textualize.io/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Textual Examples](https://github.com/Textualize/textual/tree/main/examples)
