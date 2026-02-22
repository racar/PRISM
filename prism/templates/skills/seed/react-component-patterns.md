---
skill_id: react-component-patterns
type: skill
domain_tags: [react, frontend, components, typescript, hooks]
scope: global
stack_context: [react, typescript, javascript]
created: 2026-02-20
last_used: 2026-02-20
reuse_count: 0
project_origin: prism-seed
status: active
verified_by: human
---

# React Component Patterns

## Key Insight
Prefer composition over inheritance. Keep components small (< 100 lines), extract custom hooks for logic, and colocate state as close to its usage as possible.

## Trigger
When creating React components, especially ones that start growing beyond a single responsibility.

## Solution

```tsx
// Custom hook — extracts logic for easy testing
function useUserData(userId: string) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUser(userId).then(setUser).finally(() => setLoading(false));
  }, [userId]);

  return { user, loading };
}

// Component — only UI concerns
function UserCard({ userId }: { userId: string }) {
  const { user, loading } = useUserData(userId);
  if (loading) return <Skeleton />;
  if (!user) return <NotFound />;
  return <Card title={user.name} subtitle={user.email} />;
}
```

## Notes
- Avoid `useEffect` for derived data — use `useMemo` instead
- Prefer controlled components (value + onChange) for forms
- Use `React.memo()` only after profiling shows re-render cost
- Co-locate test files: `UserCard.test.tsx` next to `UserCard.tsx`
