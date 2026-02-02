## 出力形式（必須）

評価結果をファイルに保存しないでください。応答テキストの中にだけ、以下のJSON形式で出力してください。この形式は必須です。

```json
{{
  "decision": "accept",
  "score": 0.8,
  "issues": [
    {{
      "type": "duplication",
      "description": "問題点の説明",
      "related_task_ids": ["task_043", "task_049"]
    }}
  ],
  "suggested_changes": "Plannerが次に計画を修正するときの高レベルな提案"
}}
```

- **decision**: `"accept"` または `"revise"`
- **score**: 0.0〜1.0
- **issues**: type は "duplication" | "coverage" | "granularity" | "dependency" | "priority" | "other" のいずれか
- **出力は応答テキストのみ。** plan_judge_result.json 等は作成しないでください。
- **ユーザー向け表示:** `issues[].description` と `suggested_changes` は**日本語**で書いてください。ダッシュボードやログに表示される場合があります。
