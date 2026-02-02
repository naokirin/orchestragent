## Output Format (Required)

Do not save the evaluation result to a file. Output only in the response text, in the following JSON format. This format is required.

```json
{{
  "decision": "accept",
  "score": 0.8,
  "issues": [
    {{
      "type": "duplication",
      "description": "Description of the issue",
      "related_task_ids": ["task_043", "task_049"]
    }}
  ],
  "suggested_changes": "High-level suggestions for how the Planner should revise the plan next"
}}
```

- **decision**: `"accept"` or `"revise"`
- **score**: 0.0 to 1.0
- **issues**: type is one of "duplication" | "coverage" | "granularity" | "dependency" | "priority" | "other"
- **Output only in the response text.** Do not create plan_judge_result.json or similar files.
