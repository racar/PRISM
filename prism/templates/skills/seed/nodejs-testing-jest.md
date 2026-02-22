---
skill_id: nodejs-testing-jest
type: skill
domain_tags: [nodejs, testing, jest, javascript, typescript]
scope: global
stack_context: [nodejs, javascript, typescript]
created: 2026-02-20
last_used: 2026-02-20
reuse_count: 0
project_origin: prism-seed
status: active
verified_by: human
---

# Node.js Testing with Jest

## Key Insight
Use `describe`/`it` blocks for structure, `beforeEach` for setup, and `jest.mock()` for isolating dependencies. Prefer `mockResolvedValue` over `mockReturnValue` for async code.

## Trigger
When writing unit or integration tests in a Node.js or TypeScript project.

## Solution

```javascript
// Unit test structure
describe('UserService', () => {
  let service;

  beforeEach(() => {
    jest.clearAllMocks();
    service = new UserService(mockRepo);
  });

  it('returns user by id', async () => {
    mockRepo.findById.mockResolvedValue({ id: 1, name: 'Alice' });
    const result = await service.getUser(1);
    expect(result.name).toBe('Alice');
  });

  it('throws when user not found', async () => {
    mockRepo.findById.mockResolvedValue(null);
    await expect(service.getUser(999)).rejects.toThrow('Not found');
  });
});
```

## Notes
- Run with coverage: `jest --coverage`
- TypeScript: install `@types/jest` + configure `ts-jest` in `jest.config.ts`
- Mock entire module: `jest.mock('./path/to/module')`
- Spy without mocking: `jest.spyOn(obj, 'method')`
