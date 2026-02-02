## 出力形式（必須）

判定結果をファイルに保存しないでください。応答テキストの中にだけ、以下のJSON形式で出力してください。この形式は必須です。

```json
{{
  "should_continue": true,
  "reason": "継続/停止の理由（詳細に説明）",
  "progress_score": 0.75,
  "drift_detected": false,
  "drift_description": null,
  "recommendations": ["推奨事項1", "推奨事項2"],
  "next_iteration_focus": "次回のイテレーションで重点的に取り組むべきこと"
}}
```

- **出力は応答テキストのみ。** judge_result.json 等は作成しないでください。
- **ユーザー向け表示:** `reason`、`drift_description`、`recommendations`、`next_iteration_focus` の値は**日本語**で書いてください。ダッシュボードやログにそのまま表示されます。
