## Output Format (Required)

Do not write the task result to a file. Output only in the response text, in the following format. This format is required.

```markdown
# Task Report: {task_id}

## Intent
### Goal
[What you aimed to achieve in this task]

### Rationale
[Why this change was needed]

### Expected Change
- [Expected effects of the change]

### Non-Goals
- [What this task does not do]

### Risk
- [Potential risks or concerns]

## Implementation
[Description of what was implemented]

## Changed Files
- file1.py: [Summary of changes]

## Commit Info
- Commit hash: [hash]
- Commit message: [message]

## Test Results
[Tests run and their results]

## Related ADR
[Existing ADR number if any; otherwise "None"]

## New ADR (only when there was an important design decision; otherwise "None")

## Notes / Issues
[Problems noticed during implementation or future improvements]
```

- **Output only in the response text.** Do not create task_xxx_result.md or similar files.
- Commit **only the files you changed for this task.** Do not use `git add .`.
- You may write the report content (Goal, Rationale, Implementation, etc.) in Japanese when the end users are Japanese.
