---
skill_id: error-handling-patterns
type: pattern
domain_tags: [error-handling, backend, api, reliability, python, nodejs]
scope: global
stack_context: [python, nodejs, typescript, fastapi, express]
created: 2026-02-20
last_used: 2026-02-20
reuse_count: 0
project_origin: prism-seed
status: active
verified_by: human
---

# Error Handling Patterns

## Key Insight
Fail fast at boundaries (user input, external APIs), be explicit about error types, and never swallow exceptions silently. Log context with errors, not just the message.

## Trigger
When writing code that calls external services, parses user input, or does I/O.

## Solution

**Python — Result type pattern:**
```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass
class Ok(Generic[T]):
    value: T

@dataclass
class Err:
    message: str
    code: str

Result = Ok[T] | Err

def get_user(user_id: int) -> Result[User]:
    user = db.get(User, user_id)
    if not user:
        return Err(message=f"User {user_id} not found", code="NOT_FOUND")
    return Ok(value=user)
```

**TypeScript — discriminated union:**
```typescript
type Result<T> = { ok: true; data: T } | { ok: false; error: string };

async function getUser(id: number): Promise<Result<User>> {
  const user = await db.findById(id);
  if (!user) return { ok: false, error: `User ${id} not found` };
  return { ok: true, data: user };
}
```

**API error response standard:**
```json
{ "error": { "code": "NOT_FOUND", "message": "User 42 not found" } }
```

## Notes
- Log the original exception + context before re-raising or converting
- Never `except Exception: pass` — at minimum log it
- HTTP error codes: 400 (bad input), 401 (no auth), 403 (forbidden), 404 (not found), 422 (validation), 500 (internal)
- Use structured logging: `logger.error("fetch failed", extra={"user_id": uid, "error": str(e)})`
