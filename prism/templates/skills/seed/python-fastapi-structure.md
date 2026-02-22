---
skill_id: python-fastapi-structure
type: skill
domain_tags: [python, fastapi, api, backend, structure]
scope: global
stack_context: [python, fastapi, pydantic]
created: 2026-02-20
last_used: 2026-02-20
reuse_count: 0
project_origin: prism-seed
status: active
verified_by: human
---

# Python FastAPI Project Structure

## Key Insight
Separate routers by domain, use dependency injection for shared resources (db session, auth), and let Pydantic schemas handle all validation at the boundary.

## Trigger
When starting or structuring a FastAPI project with more than 2 routes.

## Solution

```
project/
├── main.py              # app = FastAPI(); include_router(...)
├── routers/
│   ├── users.py         # APIRouter(prefix="/users")
│   └── items.py
├── schemas/
│   ├── user.py          # UserCreate, UserRead (Pydantic BaseModel)
│   └── item.py
├── models/
│   └── user.py          # SQLAlchemy ORM models
├── dependencies.py      # get_db(), get_current_user()
└── database.py          # engine, SessionLocal, Base
```

```python
# dependencies.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# routers/users.py
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
```

## Notes
- Use `response_model=` to control serialized output, not the ORM model directly
- `Depends()` chains are lazy — only called when route is invoked
- Always use `HTTPException` for error responses, not `ValueError`
