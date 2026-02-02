## Output Format (Required)

Do not save the judgment result to a file. Output only in the response text, in the following JSON format. This format is required.

```json
{{
  "should_continue": true,
  "reason": "Detailed reason for continue/stop",
  "progress_score": 0.75,
  "drift_detected": false,
  "drift_description": null,
  "recommendations": ["Recommendation 1", "Recommendation 2"],
  "next_iteration_focus": "What to focus on in the next iteration"
}}
```

- **Output only in the response text.** Do not create judge_result.json or similar files.
