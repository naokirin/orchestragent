## Output Format (Required)

Do not write to a file. Output only in the response text, in the following JSON format. This format is required.

```json
{{
  "plan_update": "Updated plan in Markdown",
  "new_tasks": [
    {{
      "id": "task_XXX",
      "title": "Task title",
      "description": "Detailed description",
      "priority": "high|medium|low",
      "dependencies": ["task_001"],
      "files": ["src/main.py"],
      "estimated_hours": 2
    }}
  ],
  "updated_tasks": [
    {{
      "id": "task_041",
      "title": "Updated title",
      "description": "Updated description",
      "priority": "high|medium|low",
      "dependencies": [],
      "files": [],
      "estimated_hours": 1,
      "status": "pending"
    }}
  ],
  "reasoning": "Explanation of why these tasks were added or updated"
}}
```

- **Output only in the response text.** Do not create plan.json or similar files.
- **files**: List paths of files to edit or create for the task.
- **dependencies**: List IDs of tasks this task depends on.
