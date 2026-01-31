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
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; background: #1a1a1a; color: #e0e0e0; }
    #header { background: #2d3748; padding: 0.5rem 1rem; text-align: center; }
    #tabs { display: flex; gap: 0; background: #2d3748; padding: 0 1rem; border-bottom: 1px solid #4a5568; }
    #tabs button { background: none; border: none; color: #a0aec0; padding: 0.6rem 1rem; cursor: pointer; font-size: 0.9rem; }
    #tabs button:hover { color: #e2e8f0; }
    #tabs button.active { color: #63b3ed; border-bottom: 2px solid #63b3ed; margin-bottom: -1px; }
    #content { padding: 1rem; max-width: 1200px; margin: 0 auto; }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }
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
    #logs-container { height: 70vh; overflow: auto; background: #2d3748; padding: 1rem; font-family: ui-monospace, monospace; font-size: 0.8rem; white-space: pre-wrap; }
    .loading { color: #a0aec0; }
    .error { color: #fc8181; }
  </style>
</head>
<body>
  <div id="header">orchestragent Web ダッシュボード</div>
  <div id="tabs">
    <button type="button" data-tab="overview" class="active">概要</button>
    <button type="button" data-tab="logs">ログ</button>
    <button type="button" data-tab="tasks">タスク</button>
    <button type="button" data-tab="intents">Intent</button>
    <button type="button" data-tab="settings">設定</button>
  </div>
  <div id="content">
    <div id="pane-overview" class="tab-pane active">
      <div id="overview-goal" class="section"><h3>プロジェクト目標</h3><div class="text loading">読込中…</div></div>
      <div id="overview-progress" class="section"><h3>進行状況</h3><div class="text loading">読込中…</div></div>
      <div id="overview-stats" class="section"><h3>タスク統計</h3><div class="text loading">読込中…</div></div>
    </div>
    <div id="pane-logs" class="tab-pane">
      <div id="logs-container">読込中…</div>
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
          document.querySelector('#overview-goal .text').textContent = d.project_goal || '未設定';
          var s = d.status || {};
          document.querySelector('#overview-progress .text').textContent =
            'イテレーション: ' + (s.current_iteration ?? 0) + ' / ' + (s.max_iterations ?? 100) + '\\n' +
            '継続: ' + (s.should_continue ? '継続' : '停止') + '\\n理由: ' + (s.reason || 'N/A');
          var t = d.task_statistics || {};
          document.querySelector('#overview-stats .text').textContent =
            '総タスク数: ' + (t.total ?? 0) + '\\n完了: ' + (t.completed ?? 0) + ' 失敗: ' + (t.failed ?? 0) + ' 保留中: ' + (t.pending ?? 0) + ' 実行中: ' + (t.in_progress ?? 0) + '\\n完了率: ' + (t.completion_rate_percent ?? 0) + '%';
        }).catch(function(e) {
          document.querySelector('#overview-goal .text').textContent = '取得失敗: ' + e.message;
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
