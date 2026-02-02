## 出力形式（必須）

ファイルに書き込まないでください。応答テキストの中にだけ、以下のJSON形式で出力してください。この形式は必須です。

```json
{{
  "plan_update": "更新された計画のMarkdown形式のテキスト",
  "new_tasks": [
    {{
      "id": "task_XXX",
      "title": "タスクのタイトル",
      "description": "詳細な説明",
      "priority": "high|medium|low",
      "dependencies": ["task_001"],
      "files": ["src/main.py"],
      "estimated_hours": 2
    }}
  ],
  "updated_tasks": [
    {{
      "id": "task_041",
      "title": "更新後のタイトル",
      "description": "更新後の説明",
      "priority": "high|medium|low",
      "dependencies": [],
      "files": [],
      "estimated_hours": 1,
      "status": "pending"
    }}
  ],
  "reasoning": "なぜこれらのタスクを追加・更新したかの説明"
}}
```

- **出力は応答テキストのみ。** plan.json 等は作成しないでください。
- **files**: タスクで編集・作成するファイルのパスを明示してください。
- **dependencies**: 依存するタスクIDを指定してください。
- **ユーザー向け表示:** `plan_update`、`reasoning`、タスクの `title`/`description` は**日本語**で書いてください。ダッシュボードやログに表示されます。
