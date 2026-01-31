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
    body { font-family: Inter, system-ui, sans-serif; margin: 0; background: #1a1a1a; color: #e0e0e0; }
    #header { background: #2d3748; padding: 8px 16px; height: 48px; display: flex; align-items: center; justify-content: center; }
    #header .header-title { color: #e0e0e0; font-size: 16px; font-weight: normal; margin: 0; }
    #tabs { display: flex; align-items: flex-end; gap: 0; background: #2d3748; padding: 0 16px; height: 44px; border-bottom: 1px solid #4a5568; }
    #tabs button { background: none; border: none; color: #a0aec0; padding: 10px 16px; cursor: pointer; font-size: 0.9rem; height: 40px; display: flex; align-items: center; justify-content: center; font-family: inherit; }
    #tabs button:hover { color: #e2e8f0; }
    #tabs button.active { color: #63b3ed; border-bottom: 2px solid #63b3ed; margin-bottom: -1px; }
    #content { padding: 16px; max-width: 1200px; margin: 0 auto; }
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
    .task-list { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    .task-table { width: 100%; border-collapse: collapse; }
    .task-table th, .task-table td { padding: 0.4rem 0.6rem; text-align: left; border-bottom: 1px solid #4a5568; }
    .task-table tr.selected { background: #2c5282; }
    .task-table tr:hover { background: #2d3748; }
    .task-detail { background: #2d3748; padding: 1rem; border-radius: 4px; }
    .status-pending { color: #ecc94b; }
    .status-in_progress { color: #63b3ed; }
    .status-completed { color: #68d391; }
    .status-failed { color: #fc8181; }
    /* Logs tab: .pen design */
    #pane-logs.tab-pane.active { display: flex; flex-direction: column; gap: 8px; }
    .logs-section { display: flex; flex-direction: column; gap: 8px; width: 100%; flex: 1; min-height: 0; }
    .logs-section-title { color: #63b3ed; font-size: 16px; font-weight: normal; margin: 0; font-family: inherit; }
    .logs-box { background: #2d3748; border-radius: 4px; padding: 16px; flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
    #logs-container { flex: 1; min-height: 300px; overflow: auto; color: #a0aec0; font-family: Inter, ui-monospace, monospace; font-size: 13px; white-space: pre-wrap; margin: 0; }
    .loading { color: #a0aec0; }
    .error { color: #fc8181; }
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
      <div class="task-list">
        <div><h3>タスク一覧</h3><div id="task-table-wrap"><table class="task-table"><thead><tr><th>ステータス</th><th>ID</th><th>タイトル</th><th>優先度</th></tr></thead><tbody id="task-tbody"></tbody></table></div></div>
        <div><h3>タスク詳細</h3><div id="task-detail" class="task-detail">一覧から選択してください</div></div>
      </div>
    </div>
    <div id="pane-intents" class="tab-pane">
      <div class="task-list">
        <div><h3>変更意図一覧</h3><div id="intent-table-wrap"><table class="task-table"><thead><tr><th>Task ID</th><th>目標</th><th>コミット数</th><th>ADR</th></tr></thead><tbody id="intent-tbody"></tbody></table></div></div>
        <div><h3>詳細</h3><div id="intent-detail" class="task-detail">一覧から選択してください</div></div>
      </div>
    </div>
    <div id="pane-settings" class="tab-pane">
      <div id="settings-content" class="section"><div class="text loading">読込中…</div></div>
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
            document.getElementById('task-detail').textContent = selectedTaskId ? 'タスクが見つかりません' : '一覧から選択してください';
          }
        }).catch(function(e) {
          document.getElementById('task-tbody').innerHTML = '<tr><td colspan="4" class="error">取得失敗: ' + e.message + '</td></tr>';
        });
      }

      function fetchTaskDetail(id) {
        fetch('/api/tasks/' + encodeURIComponent(id)).then(function(r) { return r.json(); }).then(function(t) {
          var el = document.getElementById('task-detail');
          if (!t.id) { el.textContent = 'タスクが見つかりません'; return; }
          var s = 'ID: ' + t.id + '\\nタイトル: ' + (t.title || '') + '\\nステータス: ' + (t.status || '') + '\\n優先度: ' + (t.priority || '') + '\\n作成: ' + (t.created_at || '') + '\\n更新: ' + (t.updated_at || '') + '\\n\\n説明: ' + (t.description || '') + '\\n\\nファイル: ' + (t.files && t.files.length ? t.files.join(', ') : 'なし');
          if (t.result && t.result.report) s += '\\n\\n結果: ' + t.result.report;
          if (t.error) s += '\\n\\nエラー: ' + t.error;
          el.textContent = s;
        }).catch(function(e) {
          document.getElementById('task-detail').textContent = '取得失敗: ' + e.message;
        });
      }

      function fetchIntents() {
        fetch('/api/intents').then(function(r) { return r.json(); }).then(function(data) {
          var tbody = document.getElementById('intent-tbody');
          var intents = data.intents || [];
          tbody.innerHTML = '';
          intents.forEach(function(i) {
            var tr = document.createElement('tr');
            tr.dataset.taskId = i.task_id;
            if (i.task_id === selectedIntentTaskId) tr.classList.add('selected');
            tr.innerHTML = '<td>' + (i.task_id || '') + '</td><td>' + (i.goal_display || '').slice(0, 40) + '</td><td>' + (i.commit_count ?? 0) + '</td><td>' + (i.related_adr || '-') + '</td>';
            tr.onclick = function() {
              selectedIntentTaskId = i.task_id;
              document.querySelectorAll('#intent-tbody tr').forEach(function(r) { r.classList.remove('selected'); });
              tr.classList.add('selected');
              fetchIntentDetail(i.task_id);
            };
            tbody.appendChild(tr);
          });
          if (selectedIntentTaskId && intents.some(function(i) { return i.task_id === selectedIntentTaskId; })) {
            fetchIntentDetail(selectedIntentTaskId);
          } else {
            document.getElementById('intent-detail').textContent = selectedIntentTaskId ? 'Intentが見つかりません' : '一覧から選択してください';
          }
        }).catch(function(e) {
          document.getElementById('intent-tbody').innerHTML = '<tr><td colspan="4" class="error">取得失敗: ' + e.message + '</td></tr>';
        });
      }

      function fetchIntentDetail(taskId) {
        fetch('/api/intents/' + encodeURIComponent(taskId)).then(function(r) { return r.json(); }).then(function(d) {
          var el = document.getElementById('intent-detail');
          if (!d.task_id) { el.textContent = 'Intentが見つかりません'; return; }
          var i = d.intent || {};
          var ec = (d.intent && d.intent.expected_change) || [];
var s = 'Task ID: ' + d.task_id + '\\n目標: ' + (i.goal || '') + '\\n理由: ' + (i.rationale || '') + '\\n期待される変更: ' + (Array.isArray(ec) ? ec.join(', ') : ec) + '\\nコミット: ' + (d.commits && d.commits.length ? d.commits.length + '件' : 'なし') + '\\n関連ADR: ' + (d.related_adr || 'なし');
          if (d.diff_text) s += '\\n\\n--- Diff ---\\n' + d.diff_text.slice(0, 3000);
          el.textContent = s;
        }).catch(function(e) {
          document.getElementById('intent-detail').textContent = '取得失敗: ' + e.message;
        });
      }

      function fetchSettings() {
        fetch('/api/settings').then(function(r) { return r.json(); }).then(function(d) {
          var lines = [];
          if (d.project) {
            lines.push('【プロジェクト】');
            Object.keys(d.project).forEach(function(k) { lines.push('  ' + k + ': ' + d.project[k]); });
          }
          if (d.llm) {
            lines.push('【LLM】');
            Object.keys(d.llm).forEach(function(k) { lines.push('  ' + k + ': ' + d.llm[k]); });
          }
          if (d.loop) {
            lines.push('【メインループ】');
            Object.keys(d.loop).forEach(function(k) { lines.push('  ' + k + ': ' + d.loop[k]); });
          }
          if (d.environment) {
            lines.push('【環境】');
            lines.push('  コンテナ: ' + d.environment.running_in_container);
            lines.push('  Cursor CLI: ' + d.environment.cursor_cli_available);
            lines.push('  Python: ' + d.environment.python_version);
          }
          if (d.git) {
            lines.push('【Git】');
            lines.push('  user_name: ' + (d.git.user_name || '(未設定)'));
            lines.push('  user_email: ' + (d.git.user_email || '(未設定)'));
          }
          document.querySelector('#settings-content .text').textContent = lines.join('\\n');
        }).catch(function(e) {
          document.querySelector('#settings-content .text').textContent = '取得失敗: ' + e.message;
        });
      }

      document.querySelectorAll('#tabs button').forEach(function(btn) {
        btn.addEventListener('click', function() {
          setTab(btn.getAttribute('data-tab'));
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
