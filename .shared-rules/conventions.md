# Coding Conventions

## General Rules
- Prefer explicit over implicit
- Keep functions small and focused
- Write self-documenting code
- Add comments only for "why", not "what"

## TypeScript/JavaScript

### Naming
- Components: `PascalCase` (CouncilViewer.tsx)
- Functions/hooks: `camelCase` (useCouncil, fetchData)
- Constants: `UPPER_SNAKE_CASE` (MAX_RETRIES)
- Files: `PascalCase` for components, `camelCase` for utils

### Patterns
```typescript
// Prefer named exports
export function CouncilCard() {}

// Use async/await over .then()
const data = await fetchCouncil(id);

// Destructure props
function Card({ title, children }: CardProps) {}

// Use optional chaining
const name = user?.profile?.name ?? "Anonymous";
```

### Imports Order
1. External packages (react, react-router)
2. Internal absolute (@/components, @/lib)
3. Relative imports (./utils, ../types)
4. Type imports (type { Props })

## Python

### Naming
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_prefixed`
- Files: `snake_case.py`

### Patterns
```python
# Type hints always
def get_council(council_id: UUID) -> Council | None:
    pass

# Use pathlib for paths
from pathlib import Path
config_path = Path(__file__).parent / "config.yaml"

# Context managers for resources
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# Dataclasses/Pydantic for data
from pydantic import BaseModel

class CouncilConfig(BaseModel):
    preset: str
    models: list[str]
```

### Imports Order
1. Standard library
2. Third-party packages
3. Local imports

## Git Conventions

### Commit Messages
```
feat: add council preset selection
fix: resolve timeout in stage 2 review
docs: update API documentation
refactor: extract response parser
test: add council creation tests
chore: update dependencies
```

### Branch Naming
```
feature/council-streaming
bugfix/timeout-handling
hotfix/auth-crash
refactor/api-cleanup
```

## API Conventions

### Endpoints
- Plural nouns: `/councils`, `/users`
- Nested resources: `/councils/:id/responses`
- Actions as verbs: `/councils/:id/start`, `/councils/:id/cancel`

### Response Consistency
- Always wrap data in `{ "data": ... }`
- Include `meta` for pagination/timestamps
- Use `error` object for failures

## Database

### Table Naming
- Plural snake_case: `councils`, `user_sessions`
- Junction tables: `council_responses`

### Column Naming
- snake_case: `created_at`, `model_name`
- Foreign keys: `user_id`, `council_id`
- Booleans: `is_active`, `has_voted`

## Testing

### File Naming
- Python: `test_*.py` or `*_test.py`
- TypeScript: `*.test.ts` or `*.spec.ts`

### Test Structure
```python
# Arrange - Act - Assert
def test_council_creation():
    # Arrange
    config = CouncilConfig(preset="research")

    # Act
    council = create_council(config)

    # Assert
    assert council.status == "created"
```
