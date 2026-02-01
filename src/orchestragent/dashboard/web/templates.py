"""Render the single-page dashboard HTML (tabs + API-driven content)."""


def render_dashboard() -> str:
    """Return full HTML for the dashboard (overview, logs, tasks, intents, settings tabs)."""
    return _DASHBOARD_HTML


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>orchestragent Web ダッシュボード</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet" />
  <style>
    * { box-sizing: border-box; }
    html, body { height: 100%; margin: 0; }
    body { font-family: Inter, system-ui, sans-serif; background: #1a1a1a; color: #e0e0e0; display: flex; flex-direction: column; }
    #header { background: #2d3748; padding: 8px 16px; height: 48px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
    #header .header-title { color: #e0e0e0; font-size: 16px; font-weight: normal; margin: 0; }
    #tabs { display: flex; align-items: flex-end; gap: 0; background: #2d3748; padding: 0 16px; height: 44px; border-bottom: 1px solid #4a5568; flex-shrink: 0; }
    #tabs button { background: none; border: none; color: #a0aec0; padding: 10px 16px; cursor: pointer; font-size: 0.9rem; height: 40px; display: flex; align-items: center; justify-content: center; font-family: inherit; }
    #tabs button:hover { color: #e2e8f0; }
    #tabs button.active { color: #63b3ed; border-bottom: 2px solid #63b3ed; margin-bottom: -1px; }
    #content { padding: 16px; max-width: 1200px; margin: 0 auto; flex: 1; min-height: 0; display: flex; flex-direction: column; width: 100%; }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }
    /* Overview tab: .pen design (flex only when active so .tab-pane display:none wins when inactive) */
    #pane-overview.tab-pane.active { display: flex; flex-direction: column; gap: 16px; }
    .overview-section { display: flex; flex-direction: column; gap: 8px; width: 100%; }
    .overview-section-title { color: #63b3ed; font-size: 16px; font-weight: normal; margin: 0; font-family: inherit; }
    .overview-box { background: #2d3748; border-radius: 4px; padding: 12px; width: 100%; }
    .overview-box .text { color: #a0aec0; font-size: 14px; white-space: pre-wrap; margin: 0; }
    .overview-progress-row { display: flex; gap: 24px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
    .overview-progress-item { display: flex; gap: 8px; align-items: center; }
    .overview-progress-label { color: #a0aec0; font-size: 13px; margin: 0; }
    .overview-progress-value { color: #63b3ed; font-size: 16px; font-weight: bold; margin: 0; }
    .overview-status-badge { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: #1a1a1a; }
    .overview-status-badge.continue { background: #68d391; }
    .overview-status-badge.stop { background: #fc8181; }
    .overview-reason-row { display: flex; flex-direction: column; gap: 4px; }
    .overview-reason-label { color: #a0aec0; font-size: 13px; margin: 0; }
    .overview-reason-box { background: #1a1a1a; border-radius: 4px; padding: 10px; }
    .overview-reason-box .text { color: #e0e0e0; font-size: 12px; white-space: pre-wrap; margin: 0; }
    .overview-stats-row { display: flex; gap: 16px; justify-content: space-between; flex-wrap: wrap; }
    .overview-stat-card { background: #1a1a1a; border-radius: 6px; padding: 12px; flex: 1; min-width: 80px; display: flex; flex-direction: column; gap: 4px; align-items: center; }
    .overview-stat-value { font-size: 24px; font-weight: bold; margin: 0; }
    .overview-stat-value.total { color: #63b3ed; }
    .overview-stat-value.completed { color: #68d391; }
    .overview-stat-value.failed { color: #fc8181; }
    .overview-stat-value.pending { color: #ecc94b; }
    .overview-stat-value.in_progress { color: #63b3ed; }
    .overview-stat-value.rate { color: #63b3ed; }
    .overview-stat-label { color: #a0aec0; font-size: 11px; margin: 0; }
    .section { margin-bottom: 1rem; }
    .section h3 { color: #63b3ed; margin: 0 0 0.5rem 0; font-size: 1rem; }
    .section pre, .section .text { background: #2d3748; padding: 0.75rem; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; font-size: 0.85rem; }
    /* Tasks tab: .pen design — 高さはビューポートに合わせ、詳細はインラインでスクロール */
    #pane-tasks.tab-pane.active { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 16px; flex: 1; min-height: 0; }
    .tasks-left, .tasks-right { display: flex; flex-direction: column; gap: 8px; min-width: 0; min-height: 0; }
    .tasks-right { flex: 1; }
    .tasks-section-title { color: #63b3ed; font-size: 16px; font-weight: normal; margin: 0 0 0 0; font-family: inherit; flex-shrink: 0; }
    .task-table-wrap { background: #2d3748; border-radius: 4px; overflow: hidden; flex: 1; min-height: 0; }
    .task-table { width: 100%; border-collapse: collapse; font-family: inherit; font-size: 12px; }
    .task-table thead { background: #2d3748; border-bottom: 1px solid #4a5568; }
    .task-table th { padding: 6px 8px; text-align: left; color: #e0e0e0; font-weight: normal; }
    .task-table td { padding: 6px 8px; text-align: left; color: #e0e0e0; border-bottom: 1px solid #4a5568; }
    .task-table tbody tr { height: 36px; }
    .task-table tbody tr.selected { background: #2c5282; }
    .task-table tbody tr:hover { background: #2d3748; cursor: pointer; }
    .task-table .status-pending { color: #ecc94b; }
    .task-table .status-in_progress { color: #63b3ed; }
    .task-table .status-completed { color: #68d391; }
    .task-table .status-failed { color: #fc8181; }
    .task-detail-box { background: #2d3748; border-radius: 4px; padding: 16px; display: flex; flex-direction: column; gap: 0; flex: 1; min-height: 0; overflow: hidden; }
    .task-detail-placeholder { color: #a0aec0; font-size: 13px; margin: 0; }
    .task-detail-content { display: none; flex-direction: column; gap: 0; flex: 1; min-height: 0; overflow: hidden; }
    .task-detail-content.visible { display: flex; }
    .task-detail-fixed { flex-shrink: 0; display: flex; flex-direction: column; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid #4a5568; }
    .task-detail-header { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .task-detail-id-badge { background: #4a5568; border-radius: 4px; padding: 4px 8px; font-size: 12px; font-weight: bold; color: #e0e0e0; }
    .task-detail-title { font-size: 16px; font-weight: bold; color: #e0e0e0; margin: 0; }
    .task-detail-badges { display: flex; gap: 8px; align-items: center; justify-content: space-between; flex-wrap: wrap; width: 100%; }
    .task-detail-badge-group { display: flex; gap: 8px; flex-wrap: wrap; }
    .task-detail-badge { border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold; color: #1a1a1a; }
    .task-detail-intent-btn { background: #3182ce; color: #ffffff; border: none; border-radius: 4px; padding: 6px 12px; font-size: 12px; font-family: inherit; cursor: pointer; flex-shrink: 0; }
    .task-detail-intent-btn:hover { background: #4299e1; }
    .task-detail-intent-btn.hidden { display: none; }
    .task-detail-badge.status-pending { background: #ecc94b; }
    .task-detail-badge.status-in_progress { background: #63b3ed; }
    .task-detail-badge.status-completed { background: #68d391; }
    .task-detail-badge.status-failed { background: #fc8181; }
    .task-detail-badge.priority-high { background: #fc8181; }
    .task-detail-badge.priority-medium { background: #ecc94b; }
    .task-detail-badge.priority-low { background: #68d391; }
    .task-detail-scroll { flex: 1; min-height: 0; overflow: auto; display: flex; flex-direction: column; gap: 12px; padding-top: 12px; }
    .task-detail-desc-row, .task-detail-files-row { display: flex; flex-direction: column; gap: 4px; }
    .task-detail-desc-label, .task-detail-files-label { color: #a0aec0; font-size: 12px; margin: 0; }
    .task-detail-desc-text { color: #e0e0e0; font-size: 13px; margin: 0; }
    .task-detail-files-text { color: #63b3ed; font-size: 12px; margin: 0; }
    /* Markdown rendering styles */
    .md-content { line-height: 1.6; }
    .md-content h1 { font-size: 1.4em; font-weight: bold; color: #63b3ed; margin: 16px 0 8px 0; border-bottom: 1px solid #4a5568; padding-bottom: 4px; }
    .md-content h2 { font-size: 1.2em; font-weight: bold; color: #63b3ed; margin: 14px 0 6px 0; }
    .md-content h3 { font-size: 1.1em; font-weight: bold; color: #63b3ed; margin: 12px 0 4px 0; }
    .md-content h4, .md-content h5, .md-content h6 { font-size: 1em; font-weight: bold; color: #a0aec0; margin: 10px 0 4px 0; }
    .md-content p { margin: 8px 0; }
    .md-content strong { font-weight: bold; color: #ffffff; }
    .md-content em { font-style: italic; color: #e2e8f0; }
    .md-content code { background: #1a1a1a; color: #f6ad55; padding: 2px 6px; border-radius: 3px; font-family: ui-monospace, monospace; font-size: 0.9em; }
    .md-content pre { background: #0d1117; border-radius: 6px; padding: 12px; margin: 8px 0; overflow-x: auto; }
    .md-content pre code { background: none; padding: 0; color: #c9d1d9; display: block; white-space: pre; }
    .md-content ul, .md-content ol { margin: 8px 0; padding-left: 24px; }
    .md-content li { margin: 4px 0; }
    .md-content blockquote { border-left: 3px solid #4a5568; padding-left: 12px; margin: 8px 0; color: #a0aec0; font-style: italic; }
    .md-content hr { border: none; border-top: 1px solid #4a5568; margin: 16px 0; }
    .md-content a { color: #63b3ed; text-decoration: underline; }
    .md-content .md-section { margin-top: 16px; padding-top: 12px; border-top: 1px solid #4a5568; }
    .md-content .md-section:first-child { margin-top: 0; padding-top: 0; border-top: none; }
    /* バッジ内の文字は常に暗色（テーブル用 .status-* の color がバッジに効かないよう上書き） */
    .task-detail-content .task-detail-badge { color: #1a1a1a; }
    .task-list { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    /* Logs tab: .pen design — 高さはビューポートに合わせ、ログはインラインでスクロール */
    #pane-logs.tab-pane.active { display: flex; flex-direction: column; gap: 8px; flex: 1; min-height: 0; }
    .logs-section { display: flex; flex-direction: column; gap: 8px; width: 100%; flex: 1; min-height: 0; }
    .logs-section-title { color: #63b3ed; font-size: 16px; font-weight: normal; margin: 0; font-family: inherit; flex-shrink: 0; }
    .logs-box { background: #2d3748; border-radius: 4px; padding: 16px; flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
    #logs-container { flex: 1; min-height: 0; overflow: auto; color: #a0aec0; font-family: Inter, ui-monospace, monospace; font-size: 13px; white-space: pre-wrap; margin: 0; }
    /* Intent tab: .pen design, list-only then detail with sub-tabs */
    #pane-intents.tab-pane.active { display: flex; flex-direction: column; gap: 16px; padding: 16px; }
    #intent-list-view { display: flex; flex-direction: column; gap: 12px; width: 100%; }
    #intent-detail-view { display: none; flex-direction: column; gap: 0; width: 100%; flex: 1; min-height: 0; }
    #intent-detail-view.visible { display: flex; }
    .intent-list-header { background: #2d3748; border-radius: 8px 8px 0 0; padding: 12px 16px; display: flex; align-items: center; gap: 12px; }
    .intent-list-header-title { color: #e0e0e0; font-size: 16px; font-weight: bold; margin: 0; }
    .intent-list-header-badge { background: #4a5568; border-radius: 12px; padding: 4px 10px; color: #a0aec0; font-size: 12px; }
    .intent-table-wrap { background: #2d3748; border-radius: 0 0 8px 8px; overflow: hidden; border: 1px solid #4a5568; border-top: none; }
    .intent-sub-header { background: #2d3748; border-bottom: 1px solid #4a5568; padding: 12px 16px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
    .intent-back-btn { background: #4a5568; border-radius: 4px; padding: 6px 12px; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; border: none; color: #e0e0e0; font-size: 13px; font-family: inherit; }
    .intent-back-btn:hover { background: #5a6578; }
    .intent-info { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .intent-id-badge { background: #3182ce; color: #ffffff; border-radius: 4px; padding: 4px 8px; font-size: 12px; font-weight: bold; }
    .intent-detail-title { color: #e0e0e0; font-size: 16px; font-weight: bold; margin: 0; }
    .intent-sub-tabs { background: #252525; border-bottom: 1px solid #4a5568; padding: 0 16px; display: flex; align-items: flex-end; }
    .intent-sub-tabs button { background: none; border: none; color: #a0aec0; padding: 10px 20px; cursor: pointer; font-size: 14px; height: 40px; font-family: inherit; }
    .intent-sub-tabs button:hover { color: #e2e8f0; }
    .intent-sub-tabs button.active { color: #63b3ed; border-bottom: 2px solid #63b3ed; margin-bottom: -1px; }
    .intent-detail-content { background: #1a1a1a; padding: 24px; flex: 1; overflow: auto; display: flex; flex-direction: column; gap: 24px; }
    .intent-detail-pane { display: none; }
    .intent-detail-pane.active { display: block; }
    #intent-pane-diff.active { display: flex; flex-direction: column; flex: 1; min-height: 0; }
    .intent-card { background: #2a2a2a; border-radius: 8px; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
    .intent-card-header { color: #a0aec0; font-size: 14px; font-weight: bold; margin: 0; }
    .intent-card-body { color: #e0e0e0; font-size: 14px; margin: 0; }
    /* Diff タブ: .pen の codePanel / codeArea に準拠 */
    .intent-diff-wrapper { background: #1a1a1a; border-radius: 8px; overflow: hidden; display: flex; flex-direction: row; flex: 1; min-height: 0; }
    /* ファイルツリー（左側） */
    .diff-file-tree { background: #1e1e1e; width: 280px; min-width: 280px; display: flex; flex-direction: column; border-right: 1px solid #4a5568; overflow: hidden; }
    .diff-file-tree-header { background: #2a2a2a; padding: 12px 16px; display: flex; align-items: center; gap: 8px; }
    .diff-file-tree-title { color: #a0aec0; font-size: 13px; font-weight: bold; margin: 0; }
    .diff-file-tree-count { background: #4a5568; border-radius: 10px; padding: 3px 8px; color: #a0aec0; font-size: 11px; }
    .diff-file-tree-list { flex: 1; overflow-y: auto; padding: 8px 0; }
    .diff-folder-header { display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer; }
    .diff-folder-header:hover { background: #2a2a2a; }
    .diff-folder-icon { color: #718096; font-size: 10px; }
    .diff-folder-name { color: #e0e0e0; font-size: 13px; }
    .diff-folder-children { padding-left: 16px; }
    .diff-file-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer; }
    .diff-file-item:hover { background: #2a2a2a; }
    .diff-file-item.selected { background: rgba(49, 130, 206, 0.13); }
    .diff-file-icon { color: #a0aec0; font-size: 12px; }
    .diff-file-name { color: #e0e0e0; font-size: 13px; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .diff-file-name.deleted { color: #718096; }
    .diff-file-badge { display: flex; gap: 4px; }
    .diff-file-add { color: #48bb78; font-size: 11px; }
    .diff-file-del { color: #fc8181; font-size: 11px; }
    .diff-file-tag { border-radius: 3px; padding: 2px 6px; font-size: 10px; font-weight: bold; color: #ffffff; }
    .diff-file-tag.new { background: #48bb78; }
    .diff-file-tag.deleted { background: #e53e3e; }
    /* コードパネル（右側） */
    .diff-code-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #1a1a1a; padding: 16px; gap: 16px; }
    .diff-code-section { display: flex; flex-direction: column; }
    .diff-file-header { background: #2a2a2a; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; border-radius: 8px 8px 0 0; }
    .diff-file-header.continued { border-radius: 0; border-top: 1px solid #4a5568; }
    .diff-file-header-left { display: flex; align-items: center; gap: 12px; }
    .diff-file-header-path { color: #e0e0e0; font-size: 14px; font-weight: bold; margin: 0; }
    .diff-file-header-path.deleted { color: #718096; }
    .diff-file-header-stats { display: flex; align-items: center; gap: 16px; }
    .diff-file-header-add { color: #48bb78; font-size: 12px; }
    .diff-file-header-del { color: #fc8181; font-size: 12px; }
    .diff-code-area { background: #0d1117; overflow-x: auto; }
    .diff-code-area.last { border-radius: 0 0 8px 8px; }
    .diff-code-line { display: flex; align-items: center; padding: 4px 8px; font-family: ui-monospace, monospace; font-size: 12px; }
    .diff-code-line.add { background: #1c3d2e; }
    .diff-code-line.del { background: #3d1c1c; }
    .diff-code-line.hunk { background: #1a365d; }
    .diff-line-num { color: #6e7681; min-width: 32px; text-align: right; padding-right: 8px; user-select: none; }
    .diff-line-marker { min-width: 16px; user-select: none; }
    .diff-line-marker.add { color: #48bb78; }
    .diff-line-marker.del { color: #fc8181; }
    .diff-line-marker.hunk { color: #63b3ed; }
    .diff-line-code { color: #c9d1d9; white-space: pre; }
    .diff-line-code.add { color: #aff5b4; }
    .diff-line-code.del { color: #ffa198; }
    .diff-line-code.hunk { color: #63b3ed; }
    .diff-empty-state { color: #a0aec0; font-size: 14px; text-align: center; padding: 40px; }
    .loading { color: #a0aec0; }
    .error { color: #fc8181; }
    /* Settings tab: .pen design */
    #pane-settings.tab-pane.active { display: flex; flex-direction: column; gap: 16px; }
    .settings-pane { display: flex; flex-direction: column; gap: 16px; width: 100%; }
    .settings-card { background: #2d3748; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
    .settings-card-title { color: #63b3ed; font-size: 14px; font-weight: bold; margin: 0; }
    .settings-grid { display: flex; flex-direction: column; gap: 8px; width: 100%; }
    .settings-row { display: flex; gap: 8px; width: 100%; }
    .settings-label { color: #a0aec0; font-size: 13px; min-width: 140px; }
    .settings-value { color: #e0e0e0; font-size: 13px; }
    .settings-value.highlight { color: #63b3ed; }
    .settings-value.success { color: #68d391; }
    .settings-goal-box { background: #1a1a1a; border-radius: 4px; padding: 8px; width: 100%; }
    .settings-goal-text { color: #e0e0e0; font-size: 12px; white-space: pre-wrap; margin: 0; }
    .settings-two-col { display: flex; gap: 32px; width: 100%; }
    .settings-col { display: flex; flex-direction: column; gap: 8px; flex: 1; }
    .settings-bottom-row { display: flex; gap: 16px; width: 100%; }
    .settings-bottom-row .settings-card { flex: 1; }
  </style>
</head>
<body>
  <div id="header"><h1 class="header-title">orchestragent Web ダッシュボード</h1></div>
  <div id="tabs">
    <button type="button" data-tab="overview" class="active">概要</button>
    <button type="button" data-tab="logs">ログ</button>
    <button type="button" data-tab="tasks">タスク</button>
    <button type="button" data-tab="intents">Intent</button>
    <button type="button" data-tab="settings">設定</button>
  </div>
  <div id="content">
    <div id="pane-overview" class="tab-pane active">
      <div id="overview-goal" class="overview-section">
        <h3 class="overview-section-title">プロジェクト目標</h3>
        <div class="overview-box"><p id="overview-goal-text" class="text loading">読込中…</p></div>
      </div>
      <div id="overview-progress" class="overview-section">
        <h3 class="overview-section-title">進行状況</h3>
        <div class="overview-box">
          <div class="overview-progress-row">
            <div class="overview-progress-item">
              <span class="overview-progress-label">イテレーション</span>
              <span id="overview-iter-value" class="overview-progress-value">—</span>
            </div>
            <div class="overview-progress-item">
              <span class="overview-progress-label">継続</span>
              <span id="overview-status-badge" class="overview-status-badge stop">—</span>
            </div>
          </div>
          <div class="overview-reason-row">
            <span class="overview-reason-label">理由</span>
            <div class="overview-reason-box"><p id="overview-reason-text" class="text">—</p></div>
          </div>
        </div>
      </div>
      <div id="overview-stats" class="overview-section">
        <h3 class="overview-section-title">タスク統計</h3>
        <div class="overview-box">
          <div class="overview-stats-row">
            <div class="overview-stat-card"><span id="overview-stat-total" class="overview-stat-value total">0</span><span class="overview-stat-label">総タスク数</span></div>
            <div class="overview-stat-card"><span id="overview-stat-completed" class="overview-stat-value completed">0</span><span class="overview-stat-label">完了</span></div>
            <div class="overview-stat-card"><span id="overview-stat-failed" class="overview-stat-value failed">0</span><span class="overview-stat-label">失敗</span></div>
            <div class="overview-stat-card"><span id="overview-stat-pending" class="overview-stat-value pending">0</span><span class="overview-stat-label">保留中</span></div>
            <div class="overview-stat-card"><span id="overview-stat-in-progress" class="overview-stat-value in_progress">0</span><span class="overview-stat-label">実行中</span></div>
            <div class="overview-stat-card"><span id="overview-stat-rate" class="overview-stat-value rate">0%</span><span class="overview-stat-label">完了率</span></div>
          </div>
        </div>
      </div>
    </div>
    <div id="pane-logs" class="tab-pane">
      <div class="logs-section">
        <h3 class="logs-section-title">ログ</h3>
        <div class="logs-box">
          <div id="logs-container">読込中…</div>
        </div>
      </div>
    </div>
    <div id="pane-tasks" class="tab-pane">
      <div class="tasks-left">
        <h3 class="tasks-section-title">タスク一覧</h3>
        <div id="task-table-wrap" class="task-table-wrap">
          <table class="task-table"><thead><tr><th>ステータス</th><th>ID</th><th>タイトル</th><th>優先度</th></tr></thead><tbody id="task-tbody"></tbody></table>
        </div>
      </div>
      <div class="tasks-right">
        <h3 class="tasks-section-title">タスク詳細</h3>
        <div id="task-detail" class="task-detail-box">
          <p id="task-detail-placeholder" class="task-detail-placeholder">一覧から選択してください</p>
          <div id="task-detail-content" class="task-detail-content">
            <div class="task-detail-fixed">
              <div class="task-detail-header">
                <span id="task-detail-id" class="task-detail-id-badge"></span>
                <h4 id="task-detail-title" class="task-detail-title"></h4>
              </div>
              <div class="task-detail-badges">
                <div class="task-detail-badge-group">
                  <span id="task-detail-status" class="task-detail-badge"></span>
                  <span id="task-detail-priority" class="task-detail-badge"></span>
                </div>
                <button type="button" id="task-detail-intent-btn" class="task-detail-intent-btn hidden" aria-label="Intent詳細">Intent詳細</button>
              </div>
            </div>
            <div class="task-detail-scroll">
              <div class="task-detail-desc-row">
                <span class="task-detail-desc-label">説明</span>
                <div id="task-detail-description" class="task-detail-desc-text md-content"></div>
              </div>
              <div class="task-detail-files-row">
                <span class="task-detail-files-label">対象ファイル</span>
                <p id="task-detail-files" class="task-detail-files-text"></p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div id="pane-intents" class="tab-pane">
      <div id="intent-list-view" class="intent-list-view">
        <div class="intent-list-header">
          <h3 class="intent-list-header-title">変更意図一覧</h3>
          <span id="intent-list-count" class="intent-list-header-badge">0 件</span>
        </div>
        <div id="intent-table-wrap" class="intent-table-wrap">
          <table class="task-table"><thead><tr><th>Task ID</th><th>目標</th><th>コミット数</th><th>ADR</th></tr></thead><tbody id="intent-tbody"></tbody></table>
        </div>
      </div>
      <div id="intent-detail-view" class="intent-detail-view">
        <div class="intent-sub-header">
          <button type="button" id="intent-back-btn" class="intent-back-btn" aria-label="一覧へ戻る">← 一覧へ戻る</button>
          <div class="intent-info">
            <span id="intent-detail-id-badge" class="intent-id-badge"></span>
            <h4 id="intent-detail-title" class="intent-detail-title"></h4>
          </div>
        </div>
        <div class="intent-sub-tabs">
          <button type="button" data-intent-sub="detail" id="intent-sub-detail" class="active">詳細</button>
          <button type="button" data-intent-sub="diff" id="intent-sub-diff">Diff</button>
          <button type="button" data-intent-sub="adr" id="intent-sub-adr">関連ADR</button>
        </div>
        <div class="intent-detail-content">
          <div id="intent-pane-detail" class="intent-detail-pane active">
            <div class="intent-card"><h4 class="intent-card-header">変更意図</h4><div id="intent-detail-goal" class="intent-card-body md-content"></div></div>
            <div class="intent-card"><h4 class="intent-card-header">理由</h4><div id="intent-detail-rationale" class="intent-card-body md-content"></div></div>
            <div class="intent-card"><h4 class="intent-card-header">期待される変更</h4><div id="intent-detail-expected" class="intent-card-body md-content"></div></div>
            <div class="intent-card"><h4 class="intent-card-header">コミット</h4><div id="intent-detail-commits" class="intent-card-body md-content"></div></div>
          </div>
          <div id="intent-pane-diff" class="intent-detail-pane">
            <div class="intent-diff-wrapper">
              <div class="diff-file-tree">
                <div class="diff-file-tree-header">
                  <span class="diff-file-tree-title">変更ファイル</span>
                  <span id="diff-file-count" class="diff-file-tree-count">0</span>
                </div>
                <div id="diff-file-tree-list" class="diff-file-tree-list"></div>
              </div>
              <div id="diff-code-panel" class="diff-code-panel">
                <div id="diff-empty-state" class="diff-empty-state">（Diff なし）</div>
              </div>
            </div>
          </div>
          <div id="intent-pane-adr" class="intent-detail-pane">
            <div class="intent-card"><h4 class="intent-card-header">関連ADR</h4><div id="intent-adr-content" class="intent-card-body md-content"></div></div>
          </div>
        </div>
      </div>
    </div>
    <div id="pane-settings" class="tab-pane">
      <div class="settings-pane">
        <div id="settings-project-card" class="settings-card">
          <h4 class="settings-card-title">プロジェクト</h4>
          <div class="settings-grid">
            <div class="settings-row"><span class="settings-label">project_root</span><span id="settings-project-root" class="settings-value">—</span></div>
            <div class="settings-row"><span class="settings-label">target_project</span><span id="settings-target-project" class="settings-value">—</span></div>
            <div class="settings-row"><span class="settings-label">state_dir</span><span id="settings-state-dir" class="settings-value">—</span></div>
            <div class="settings-row"><span class="settings-label">log_dir</span><span id="settings-log-dir" class="settings-value">—</span></div>
            <div class="settings-row"><span class="settings-label">adr_dir</span><span id="settings-adr-dir" class="settings-value">—</span></div>
            <div class="settings-row"><span class="settings-label">log_level</span><span id="settings-log-level" class="settings-value">—</span></div>
            <div class="settings-row" style="flex-direction: column; gap: 4px;"><span class="settings-label">project_goal</span><div class="settings-goal-box"><p id="settings-project-goal" class="settings-goal-text">—</p></div></div>
          </div>
        </div>
        <div id="settings-llm-card" class="settings-card">
          <h4 class="settings-card-title">LLM</h4>
          <div class="settings-grid">
            <div class="settings-row"><span class="settings-label">backend</span><span id="settings-llm-backend" class="settings-value">—</span></div>
            <div class="settings-row"><span class="settings-label">output_format</span><span id="settings-llm-format" class="settings-value">—</span></div>
            <div class="settings-row"><span class="settings-label">default_model</span><span id="settings-llm-model" class="settings-value">—</span></div>
          </div>
        </div>
        <div id="settings-loop-card" class="settings-card">
          <h4 class="settings-card-title">メインループ</h4>
          <div class="settings-two-col">
            <div class="settings-col">
              <div class="settings-row"><span class="settings-label">wait_time_seconds</span><span id="settings-loop-wait" class="settings-value">—</span></div>
              <div class="settings-row"><span class="settings-label">max_iterations</span><span id="settings-loop-iter" class="settings-value">—</span></div>
              <div class="settings-row"><span class="settings-label">max_retries</span><span id="settings-loop-retries" class="settings-value">—</span></div>
            </div>
            <div class="settings-col">
              <div class="settings-row"><span class="settings-label">enable_parallel</span><span id="settings-loop-parallel" class="settings-value">—</span></div>
              <div class="settings-row"><span class="settings-label">max_parallel_workers</span><span id="settings-loop-workers" class="settings-value">—</span></div>
            </div>
          </div>
        </div>
        <div class="settings-bottom-row">
          <div id="settings-env-card" class="settings-card">
            <h4 class="settings-card-title">環境</h4>
            <div class="settings-grid">
              <div class="settings-row"><span class="settings-label">コンテナ</span><span id="settings-env-container" class="settings-value">—</span></div>
              <div class="settings-row"><span class="settings-label">Cursor CLI</span><span id="settings-env-cursor" class="settings-value">—</span></div>
              <div class="settings-row"><span class="settings-label">Python</span><span id="settings-env-python" class="settings-value">—</span></div>
            </div>
          </div>
          <div id="settings-git-card" class="settings-card">
            <h4 class="settings-card-title">Git</h4>
            <div class="settings-grid">
              <div class="settings-row"><span class="settings-label">user_name</span><span id="settings-git-name" class="settings-value">—</span></div>
              <div class="settings-row"><span class="settings-label">user_email</span><span id="settings-git-email" class="settings-value">—</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <script>
    (function() {
      var POLL_INTERVAL_MS = 5000;
      var currentTab = (function() {
        var h = window.location.hash.slice(1) || 'overview';
        return ['overview','logs','tasks','intents','settings'].indexOf(h) >= 0 ? h : 'overview';
      })();
      var selectedTaskId = null;
      var selectedIntentTaskId = null;
      var intentSubTab = 'detail';
      var cachedIntentDetail = null;
      var logsScrollBottom = true;
      var pollTimer = null;

      function setTab(tab) {
        currentTab = tab;
        window.location.hash = tab;
        document.querySelectorAll('#tabs button').forEach(function(b) {
          b.classList.toggle('active', b.getAttribute('data-tab') === tab);
        });
        document.querySelectorAll('.tab-pane').forEach(function(p) {
          p.classList.toggle('active', p.id === 'pane-' + tab);
        });
        fetchTab(tab);
      }

      function fetchTab(tab) {
        if (tab === 'overview') fetchOverview();
        else if (tab === 'logs') fetchLogs();
        else if (tab === 'tasks') fetchTasks();
        else if (tab === 'intents') fetchIntents();
        else if (tab === 'settings') fetchSettings();
      }

      function fetchOverview() {
        fetch('/api/overview').then(function(r) { return r.json(); }).then(function(d) {
          document.getElementById('overview-goal-text').textContent = d.project_goal || '未設定';
          var s = d.status || {};
          document.getElementById('overview-iter-value').textContent = (s.current_iteration ?? 0) + ' / ' + (s.max_iterations ?? 100);
          var badge = document.getElementById('overview-status-badge');
          badge.textContent = s.should_continue ? '継続' : '停止';
          badge.className = 'overview-status-badge ' + (s.should_continue ? 'continue' : 'stop');
          document.getElementById('overview-reason-text').textContent = s.reason || 'N/A';
          var t = d.task_statistics || {};
          document.getElementById('overview-stat-total').textContent = t.total ?? 0;
          document.getElementById('overview-stat-completed').textContent = t.completed ?? 0;
          document.getElementById('overview-stat-failed').textContent = t.failed ?? 0;
          document.getElementById('overview-stat-pending').textContent = t.pending ?? 0;
          document.getElementById('overview-stat-in-progress').textContent = t.in_progress ?? 0;
          document.getElementById('overview-stat-rate').textContent = (t.completion_rate_percent ?? 0) + '%';
        }).catch(function(e) {
          document.getElementById('overview-goal-text').textContent = '取得失敗: ' + e.message;
        });
      }

      function fetchLogs() {
        fetch('/api/logs').then(function(r) { return r.json(); }).then(function(d) {
          var el = document.getElementById('logs-container');
          var wasBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 50;
          el.textContent = d.content != null ? d.content : '(ログなし)';
          if (logsScrollBottom || wasBottom) {
            el.scrollTop = el.scrollHeight;
          }
        }).catch(function(e) {
          document.getElementById('logs-container').textContent = '取得失敗: ' + e.message;
        });
      }

      function fetchTasks() {
        fetch('/api/tasks').then(function(r) { return r.json(); }).then(function(data) {
          var tbody = document.getElementById('task-tbody');
          var tasks = data.tasks || [];
          tbody.innerHTML = '';
          tasks.forEach(function(t) {
            var tr = document.createElement('tr');
            tr.dataset.taskId = t.id;
            if (t.id === selectedTaskId) tr.classList.add('selected');
            tr.innerHTML = '<td class="status-' + (t.status || '') + '">' + (t.status || '') + '</td><td>' + (t.id || '') + '</td><td>' + (t.title || '').slice(0, 40) + '</td><td>' + (t.priority || '') + '</td>';
            tr.onclick = function() {
              selectedTaskId = t.id;
              document.querySelectorAll('#task-tbody tr').forEach(function(r) { r.classList.remove('selected'); });
              tr.classList.add('selected');
              fetchTaskDetail(t.id);
            };
            tbody.appendChild(tr);
          });
          if (selectedTaskId && tasks.some(function(t) { return t.id === selectedTaskId; })) {
            fetchTaskDetail(selectedTaskId);
          } else {
            showTaskDetailPlaceholder(selectedTaskId ? 'タスクが見つかりません' : '一覧から選択してください');
          }
        }).catch(function(e) {
          document.getElementById('task-tbody').innerHTML = '<tr><td colspan="4" class="error">取得失敗: ' + e.message + '</td></tr>';
        });
      }

      function showTaskDetailPlaceholder(msg) {
        document.getElementById('task-detail-placeholder').textContent = msg;
        document.getElementById('task-detail-placeholder').style.display = '';
        document.getElementById('task-detail-content').classList.remove('visible');
      }

      function fetchTaskDetail(id) {
        fetch('/api/tasks/' + encodeURIComponent(id)).then(function(r) { return r.json(); }).then(function(t) {
          if (!t.id) { showTaskDetailPlaceholder('タスクが見つかりません'); return; }
          document.getElementById('task-detail-placeholder').style.display = 'none';
          document.getElementById('task-detail-content').classList.add('visible');
          document.getElementById('task-detail-id').textContent = t.id;
          document.getElementById('task-detail-title').textContent = t.title || '';
          var statusEl = document.getElementById('task-detail-status');
          statusEl.textContent = t.status || '';
          statusEl.className = 'task-detail-badge status-' + (t.status || '');
          var priorEl = document.getElementById('task-detail-priority');
          priorEl.textContent = t.priority || '';
          priorEl.className = 'task-detail-badge priority-' + ((t.priority === 'high' || t.priority === 'medium' || t.priority === 'low') ? t.priority : 'low');
          var descHtml = renderMarkdown(t.description || '');
          if (t.result && t.result.report) {
            descHtml += '<div class="md-section"><h3>結果</h3>' + renderMarkdown(t.result.report) + '</div>';
          }
          if (t.error) {
            descHtml += '<div class="md-section"><h3>エラー</h3>' + renderMarkdown(t.error) + '</div>';
          }
          document.getElementById('task-detail-description').innerHTML = descHtml || '<p>（説明なし）</p>';
          document.getElementById('task-detail-files').textContent = t.files && t.files.length ? t.files.join(', ') : 'なし';
          var intentBtn = document.getElementById('task-detail-intent-btn');
          if (t.status === 'completed') {
            intentBtn.classList.remove('hidden');
            intentBtn.onclick = function() {
              selectedIntentTaskId = t.id;
              setTab('intents');
              showIntentDetailView();
              fetchIntentDetail(t.id);
            };
          } else {
            intentBtn.classList.add('hidden');
            intentBtn.onclick = null;
          }
        }).catch(function(e) {
          showTaskDetailPlaceholder('取得失敗: ' + e.message);
        });
      }

      function showIntentListView() {
        document.getElementById('intent-list-view').style.display = 'flex';
        document.getElementById('intent-detail-view').classList.remove('visible');
      }

      function showIntentDetailView() {
        document.getElementById('intent-list-view').style.display = 'none';
        document.getElementById('intent-detail-view').classList.add('visible');
      }

      function setIntentSubTab(tab) {
        intentSubTab = tab;
        document.querySelectorAll('.intent-sub-tabs button').forEach(function(b) {
          b.classList.toggle('active', b.getAttribute('data-intent-sub') === tab);
        });
        document.querySelectorAll('.intent-detail-pane').forEach(function(p) {
          p.classList.toggle('active', p.id === 'intent-pane-' + tab);
        });
      }

      function parseDiffText(raw) {
        var files = [];
        var currentFile = null;
        var lines = raw.split('\\n');
        for (var i = 0; i < lines.length; i++) {
          var line = lines[i];
          if (line.indexOf('diff --git') === 0) {
            if (currentFile) files.push(currentFile);
            var match = line.match(/diff --git a\\/(.*?) b\\/(.*)/);
            var path = match ? match[2] : 'unknown';
            currentFile = { path: path, adds: 0, dels: 0, lines: [], isNew: false, isDeleted: false };
          } else if (currentFile) {
            if (line.indexOf('new file mode') === 0) {
              currentFile.isNew = true;
            } else if (line.indexOf('deleted file mode') === 0) {
              currentFile.isDeleted = true;
            } else if (line.indexOf('@@') === 0) {
              currentFile.lines.push({ type: 'hunk', text: line });
            } else if (line.indexOf('+') === 0 && line.indexOf('+++') !== 0) {
              currentFile.adds++;
              currentFile.lines.push({ type: 'add', text: line.slice(1) });
            } else if (line.indexOf('-') === 0 && line.indexOf('---') !== 0) {
              currentFile.dels++;
              currentFile.lines.push({ type: 'del', text: line.slice(1) });
            } else if (line.indexOf('+++') !== 0 && line.indexOf('---') !== 0 && line.indexOf('index ') !== 0) {
              currentFile.lines.push({ type: 'ctx', text: line.slice(1) || line });
            }
          }
        }
        if (currentFile) files.push(currentFile);
        return files;
      }

      function escapeHtml(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      }

      function renderMarkdown(text) {
        if (!text) return '';
        var escaped = escapeHtml(text);
        var lines = escaped.split('\\n');
        var html = [];
        var inCodeBlock = false;
        var codeBlockContent = [];
        var inList = false;
        var listItems = [];

        function flushList() {
          if (inList && listItems.length > 0) {
            html.push('<ul>' + listItems.join('') + '</ul>');
            listItems = [];
            inList = false;
          }
        }

        function processInline(line) {
          // Bold: **text** or __text__
          line = line.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
          line = line.replace(/__(.+?)__/g, '<strong>$1</strong>');
          // Italic: *text* or _text_
          line = line.replace(/\\*([^*]+)\\*/g, '<em>$1</em>');
          line = line.replace(/_([^_]+)_/g, '<em>$1</em>');
          // Inline code: `code`
          line = line.replace(/`([^`]+)`/g, '<code>$1</code>');
          // Links: [text](url)
          line = line.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
          return line;
        }

        for (var i = 0; i < lines.length; i++) {
          var line = lines[i];

          // Code block (```)
          if (line.indexOf('```') === 0) {
            if (inCodeBlock) {
              html.push('<pre><code>' + codeBlockContent.join('\\n') + '</code></pre>');
              codeBlockContent = [];
              inCodeBlock = false;
            } else {
              flushList();
              inCodeBlock = true;
            }
            continue;
          }

          if (inCodeBlock) {
            codeBlockContent.push(line);
            continue;
          }

          // Horizontal rule
          if (/^---+$/.test(line.trim()) || /^\\*\\*\\*+$/.test(line.trim())) {
            flushList();
            html.push('<hr>');
            continue;
          }

          // Headers (# ## ### etc.)
          var headerMatch = line.match(/^(#{1,6})\\s+(.+)$/);
          if (headerMatch) {
            flushList();
            var level = headerMatch[1].length;
            html.push('<h' + level + '>' + processInline(headerMatch[2]) + '</h' + level + '>');
            continue;
          }

          // Blockquote (>)
          var quoteMatch = line.match(/^>\\s*(.*)$/);
          if (quoteMatch) {
            flushList();
            html.push('<blockquote>' + processInline(quoteMatch[1]) + '</blockquote>');
            continue;
          }

          // Unordered list (- or *)
          var listMatch = line.match(/^[\\-\\*]\\s+(.+)$/);
          if (listMatch) {
            inList = true;
            listItems.push('<li>' + processInline(listMatch[1]) + '</li>');
            continue;
          }

          // Ordered list (1. 2. etc.)
          var orderedListMatch = line.match(/^\\d+\\.\\s+(.+)$/);
          if (orderedListMatch) {
            if (!inList) {
              inList = true;
            }
            listItems.push('<li>' + processInline(orderedListMatch[1]) + '</li>');
            continue;
          }

          // Empty line
          if (line.trim() === '') {
            flushList();
            continue;
          }

          // Regular paragraph
          flushList();
          html.push('<p>' + processInline(line) + '</p>');
        }

        // Handle unclosed code block
        if (inCodeBlock && codeBlockContent.length > 0) {
          html.push('<pre><code>' + codeBlockContent.join('\\n') + '</code></pre>');
        }
        flushList();

        return html.join('');
      }

      function buildFileTree(files) {
        var tree = {};
        files.forEach(function(f, idx) {
          var parts = f.path.split('/');
          var current = tree;
          for (var i = 0; i < parts.length - 1; i++) {
            var part = parts[i];
            if (!current[part]) current[part] = { __children: {} };
            current = current[part].__children;
          }
          var fileName = parts[parts.length - 1];
          current[fileName] = { __file: f, __index: idx };
        });
        return tree;
      }

      function collectFileOrder(tree, orderList) {
        var folders = [];
        var fileItems = [];
        Object.keys(tree).sort().forEach(function(k) {
          if (tree[k].__file) {
            fileItems.push({ name: k, data: tree[k] });
          } else {
            folders.push({ name: k, children: tree[k].__children });
          }
        });
        folders.forEach(function(folder) {
          collectFileOrder(folder.children, orderList);
        });
        fileItems.forEach(function(item) {
          orderList.push(item.data.__index);
        });
      }

      function renderFileTreeNode(tree, depth, displayIdx) {
        var html = '';
        var folders = [];
        var fileItems = [];
        Object.keys(tree).sort().forEach(function(k) {
          if (tree[k].__file) {
            fileItems.push({ name: k, data: tree[k] });
          } else {
            folders.push({ name: k, children: tree[k].__children });
          }
        });
        folders.forEach(function(folder) {
          html += '<div class="diff-folder-header" style="padding-left:' + (12 + depth * 16) + 'px"><span class="diff-folder-icon">▼</span><span class="diff-folder-name">' + escapeHtml(folder.name) + '/</span></div>';
          html += '<div class="diff-folder-children">' + renderFileTreeNode(folder.children, depth + 1, displayIdx) + '</div>';
        });
        fileItems.forEach(function(item) {
          var f = item.data.__file;
          var currentDisplayIdx = displayIdx.current++;
          var nameClass = f.isDeleted ? 'diff-file-name deleted' : 'diff-file-name';
          var badge = '';
          if (f.isNew) {
            badge = '<span class="diff-file-tag new">NEW</span>';
          } else if (f.isDeleted) {
            badge = '<span class="diff-file-tag deleted">DEL</span>';
          } else {
            badge = '<span class="diff-file-badge"><span class="diff-file-add">+' + f.adds + '</span><span class="diff-file-del">-' + f.dels + '</span></span>';
          }
          html += '<div class="diff-file-item" data-file-idx="' + currentDisplayIdx + '" style="padding-left:' + (12 + depth * 16) + 'px"><span class="diff-file-icon">📄</span><span class="' + nameClass + '">' + escapeHtml(item.name) + '</span>' + badge + '</div>';
        });
        return html;
      }

      function renderDiffCodePanel(files, fileOrder) {
        var html = '';
        fileOrder.forEach(function(origIdx, displayIdx) {
          var f = files[origIdx];
          var isFirst = displayIdx === 0;
          var headerClass = isFirst ? 'diff-file-header' : 'diff-file-header continued';
          var pathClass = f.isDeleted ? 'diff-file-header-path deleted' : 'diff-file-header-path';
          var tagHtml = '';
          if (f.isNew) {
            tagHtml = '<span class="diff-file-tag new">NEW</span>';
          } else if (f.isDeleted) {
            tagHtml = '<span class="diff-file-tag deleted">DELETED</span>';
          }
          var statsHtml = '';
          if (f.adds > 0) statsHtml += '<span class="diff-file-header-add">+' + f.adds + ' 追加</span>';
          if (f.dels > 0) statsHtml += '<span class="diff-file-header-del">-' + f.dels + ' 削除</span>';
          html += '<div class="diff-code-section" id="diff-section-' + displayIdx + '">';
          html += '<div class="' + headerClass + '"><div class="diff-file-header-left"><span class="' + pathClass + '">' + escapeHtml(f.path) + '</span>' + tagHtml + '</div><div class="diff-file-header-stats">' + statsHtml + '</div></div>';
          html += '<div class="diff-code-area">';
          var lineNum = 1;
          f.lines.forEach(function(ln) {
            var lineClass = 'diff-code-line';
            var markerClass = 'diff-line-marker';
            var codeClass = 'diff-line-code';
            var marker = ' ';
            if (ln.type === 'add') {
              lineClass += ' add'; markerClass += ' add'; codeClass += ' add'; marker = '+';
            } else if (ln.type === 'del') {
              lineClass += ' del'; markerClass += ' del'; codeClass += ' del'; marker = '-';
            } else if (ln.type === 'hunk') {
              lineClass += ' hunk'; markerClass += ' hunk'; codeClass += ' hunk'; marker = '';
            }
            var numText = ln.type === 'hunk' ? '' : lineNum++;
            html += '<div class="' + lineClass + '"><span class="diff-line-num">' + numText + '</span><span class="' + markerClass + '">' + marker + '</span><span class="' + codeClass + '">' + escapeHtml(ln.text) + '</span></div>';
          });
          html += '</div></div>';
        });
        return html;
      }

      function renderDiffPane(diffText) {
        var fileTreeList = document.getElementById('diff-file-tree-list');
        var codePanel = document.getElementById('diff-code-panel');
        var fileCount = document.getElementById('diff-file-count');
        if (!diffText) {
          fileTreeList.innerHTML = '';
          codePanel.innerHTML = '<div class="diff-empty-state">（Diff なし）</div>';
          fileCount.textContent = '0';
          return;
        }
        var files = parseDiffText(diffText.slice(0, 50000));
        fileCount.textContent = files.length.toString();
        if (files.length === 0) {
          fileTreeList.innerHTML = '';
          codePanel.innerHTML = '<div class="diff-empty-state">（Diff なし）</div>';
          return;
        }
        var tree = buildFileTree(files);
        var fileOrder = [];
        collectFileOrder(tree, fileOrder);
        var displayIdx = { current: 0 };
        fileTreeList.innerHTML = renderFileTreeNode(tree, 0, displayIdx);
        codePanel.innerHTML = renderDiffCodePanel(files, fileOrder);
        fileTreeList.querySelectorAll('.diff-file-item').forEach(function(el) {
          el.addEventListener('click', function() {
            var idx = el.getAttribute('data-file-idx');
            fileTreeList.querySelectorAll('.diff-file-item').forEach(function(e) { e.classList.remove('selected'); });
            el.classList.add('selected');
            var section = document.getElementById('diff-section-' + idx);
            if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
          });
        });
      }

      function arrayToMarkdownList(arr) {
        if (!arr || !Array.isArray(arr) || arr.length === 0) return '';
        return arr.map(function(item) { return '- ' + item; }).join('\\n');
      }

      function renderIntentDetailPanels(d) {
        if (!d || !d.task_id) return;
        var i = d.intent || {};

        // expected_change を箇条書き形式に変換
        var ecText = '';
        if (i.expected_change && Array.isArray(i.expected_change) && i.expected_change.length > 0) {
          ecText = arrayToMarkdownList(i.expected_change);
        } else if (i.expected_change) {
          ecText = i.expected_change;
        }

        // commits を箇条書き形式に変換
        var commitsText = '';
        if (d.commits && Array.isArray(d.commits) && d.commits.length > 0) {
          var commitLines = d.commits.map(function(c) {
            return '`' + (c.hash || '').slice(0, 7) + '` ' + (c.message || '');
          });
          commitsText = arrayToMarkdownList(commitLines);
        }

        document.getElementById('intent-detail-id-badge').textContent = d.task_id;
        document.getElementById('intent-detail-title').textContent = (i.goal || '').slice(0, 60);
        document.getElementById('intent-detail-goal').innerHTML = renderMarkdown(i.goal) || '<p>（なし）</p>';
        document.getElementById('intent-detail-rationale').innerHTML = renderMarkdown(i.rationale) || '<p>（なし）</p>';
        document.getElementById('intent-detail-expected').innerHTML = renderMarkdown(ecText) || '<p>（なし）</p>';
        document.getElementById('intent-detail-commits').innerHTML = renderMarkdown(commitsText) || '<p>（なし）</p>';
        renderDiffPane(d.diff_text);
        document.getElementById('intent-adr-content').innerHTML = renderMarkdown(d.related_adr) || '<p>（なし）</p>';
      }

      function fetchIntents() {
        fetch('/api/intents').then(function(r) { return r.json(); }).then(function(data) {
          var intents = data.intents || [];
          document.getElementById('intent-list-count').textContent = intents.length + ' 件';
          var tbody = document.getElementById('intent-tbody');
          tbody.innerHTML = '';
          intents.forEach(function(i) {
            var tr = document.createElement('tr');
            tr.dataset.taskId = i.task_id;
            tr.innerHTML = '<td>' + (i.task_id || '') + '</td><td>' + (i.goal_display || '').slice(0, 40) + '</td><td>' + (i.commit_count ?? 0) + '</td><td>' + (i.related_adr || '-') + '</td>';
            tr.onclick = function() {
              selectedIntentTaskId = i.task_id;
              showIntentDetailView();
              fetchIntentDetail(i.task_id);
            };
            tbody.appendChild(tr);
          });
          if (selectedIntentTaskId && intents.some(function(i) { return i.task_id === selectedIntentTaskId; })) {
            showIntentDetailView();
            if (cachedIntentDetail && cachedIntentDetail.task_id === selectedIntentTaskId) {
              renderIntentDetailPanels(cachedIntentDetail);
              setIntentSubTab(intentSubTab);
            } else {
              fetchIntentDetail(selectedIntentTaskId);
            }
          } else {
            selectedIntentTaskId = null;
            cachedIntentDetail = null;
            showIntentListView();
          }
        }).catch(function(e) {
          document.getElementById('intent-list-count').textContent = '0 件';
          document.getElementById('intent-tbody').innerHTML = '<tr><td colspan="4" class="error">取得失敗: ' + e.message + '</td></tr>';
        });
      }

      function fetchIntentDetail(taskId) {
        fetch('/api/intents/' + encodeURIComponent(taskId)).then(function(r) { return r.json(); }).then(function(d) {
          if (!d.task_id) return;
          cachedIntentDetail = d;
          renderIntentDetailPanels(d);
          setIntentSubTab(intentSubTab);
        }).catch(function(e) {
          document.getElementById('intent-detail-goal').textContent = '取得失敗: ' + e.message;
        });
      }

      function setSettingsValue(id, value, isHighlight, isSuccess) {
        var el = document.getElementById(id);
        if (!el) return;
        el.textContent = value != null ? value : '—';
        el.classList.remove('highlight', 'success');
        if (isSuccess) el.classList.add('success');
        else if (isHighlight) el.classList.add('highlight');
      }

      function fetchSettings() {
        fetch('/api/settings').then(function(r) { return r.json(); }).then(function(d) {
          var p = d.project || {};
          setSettingsValue('settings-project-root', p.project_root);
          setSettingsValue('settings-target-project', p.target_project);
          setSettingsValue('settings-state-dir', p.state_dir);
          setSettingsValue('settings-log-dir', p.log_dir);
          setSettingsValue('settings-adr-dir', p.adr_dir);
          var logLevel = p.log_level || '';
          setSettingsValue('settings-log-level', logLevel, false, logLevel === 'DEBUG');
          document.getElementById('settings-project-goal').textContent = p.project_goal || '未設定';
          var l = d.llm || {};
          setSettingsValue('settings-llm-backend', l.backend);
          setSettingsValue('settings-llm-format', l.output_format);
          var model = l.default_model || '';
          setSettingsValue('settings-llm-model', model, model === 'auto' || model.indexOf('auto') >= 0);
          var lp = d.loop || {};
          setSettingsValue('settings-loop-wait', lp.wait_time_seconds);
          setSettingsValue('settings-loop-iter', lp.max_iterations);
          setSettingsValue('settings-loop-retries', lp.max_retries);
          var parallel = lp.enable_parallel_execution;
          setSettingsValue('settings-loop-parallel', parallel != null ? String(parallel) : '—', false, parallel === true);
          setSettingsValue('settings-loop-workers', lp.max_parallel_workers);
          var e = d.environment || {};
          setSettingsValue('settings-env-container', e.running_in_container != null ? String(e.running_in_container) : '—', false, e.running_in_container === true);
          setSettingsValue('settings-env-cursor', e.cursor_cli_available != null ? String(e.cursor_cli_available) : '—', false, e.cursor_cli_available === true);
          setSettingsValue('settings-env-python', e.python_version);
          var g = d.git || {};
          setSettingsValue('settings-git-name', g.user_name || '(未設定)');
          setSettingsValue('settings-git-email', g.user_email || '(未設定)');
        }).catch(function(e) {
          console.error('Settings fetch failed:', e);
        });
      }

      document.querySelectorAll('#tabs button').forEach(function(btn) {
        btn.addEventListener('click', function() {
          setTab(btn.getAttribute('data-tab'));
        });
      });
      document.getElementById('intent-back-btn').addEventListener('click', function() {
        selectedIntentTaskId = null;
        cachedIntentDetail = null;
        showIntentListView();
      });
      document.querySelectorAll('.intent-sub-tabs button').forEach(function(btn) {
        btn.addEventListener('click', function() {
          setIntentSubTab(btn.getAttribute('data-intent-sub'));
        });
      });
      window.addEventListener('hashchange', function() {
        var t = window.location.hash.slice(1) || 'overview';
        if (['overview','logs','tasks','intents','settings'].indexOf(t) >= 0) setTab(t);
      });
      document.getElementById('logs-container').addEventListener('scroll', function() {
        var el = this;
        logsScrollBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 50;
      });

      setTab(currentTab);
      pollTimer = setInterval(function() {
        fetchTab(currentTab);
      }, POLL_INTERVAL_MS);
    })();
  </script>
</body>
</html>
"""
