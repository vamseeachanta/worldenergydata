# Refactoring Patterns Catalog

> Proven patterns for transforming code into cleaner, more maintainable structures.

---

## Complexity Reduction Patterns

### 1. Guard Clauses

**Problem**: Deeply nested if/else blocks that are hard to follow.

**Solution**: Return early for edge cases, keeping the happy path at the main indentation level.

```python
# BEFORE: Nested conditionals (CC: 4)
def process_order(order):
    if order is not None:
        if order.is_valid:
            if order.items:
                if order.customer.is_active:
                    return calculate_total(order)
                else:
                    return None
            else:
                return None
        else:
            return None
    else:
        return None

# AFTER: Guard clauses (CC: 4, but linear flow)
def process_order(order):
    if order is None:
        return None
    if not order.is_valid:
        return None
    if not order.items:
        return None
    if not order.customer.is_active:
        return None

    return calculate_total(order)
```

**Benefits**:
- Linear reading flow (top to bottom)
- Each guard is independent and testable
- Easy to add new validations
- Reduced cognitive load

---

### 2. Extract Method

**Problem**: Long functions doing multiple things.

**Solution**: Extract cohesive blocks into well-named helper functions.

```python
# BEFORE: Long function (50+ lines)
def generate_report(data):
    # Validate input (10 lines)
    if not data:
        raise ValueError("No data")
    if not isinstance(data, list):
        data = [data]
    # ... more validation

    # Transform data (15 lines)
    transformed = []
    for item in data:
        transformed.append({
            'name': item['name'].upper(),
            'value': item['value'] * 100,
            # ... more transformations
        })

    # Format output (15 lines)
    output = "Report\n"
    output += "=" * 40 + "\n"
    for item in transformed:
        output += f"{item['name']}: {item['value']}\n"
    # ... more formatting

    return output

# AFTER: Extracted methods
def generate_report(data: list[dict]) -> str:
    validated_data = _validate_input(data)
    transformed_data = _transform_data(validated_data)
    return _format_report(transformed_data)

def _validate_input(data) -> list[dict]:
    if not data:
        raise ValueError("No data")
    if not isinstance(data, list):
        data = [data]
    return data

def _transform_data(data: list[dict]) -> list[dict]:
    return [
        {'name': item['name'].upper(), 'value': item['value'] * 100}
        for item in data
    ]

def _format_report(data: list[dict]) -> str:
    lines = ["Report", "=" * 40]
    lines.extend(f"{item['name']}: {item['value']}" for item in data)
    return "\n".join(lines)
```

**Guidelines**:
- Name functions by what they do, not how
- Keep extracted functions at same abstraction level
- Use `_` prefix for private helpers
- Target: 20-30 lines per function

---

### 3. Dictionary Dispatch

**Problem**: Long if/elif chains checking the same variable (high cyclomatic complexity).

**Solution**: Replace with dictionary lookup.

```python
# BEFORE: If/elif chain (CC: 8)
def get_handler(event_type):
    if event_type == "click":
        return handle_click
    elif event_type == "hover":
        return handle_hover
    elif event_type == "scroll":
        return handle_scroll
    elif event_type == "keypress":
        return handle_keypress
    elif event_type == "focus":
        return handle_focus
    elif event_type == "blur":
        return handle_blur
    elif event_type == "submit":
        return handle_submit
    else:
        return handle_unknown

# AFTER: Dictionary dispatch (CC: 1)
EVENT_HANDLERS = {
    "click": handle_click,
    "hover": handle_hover,
    "scroll": handle_scroll,
    "keypress": handle_keypress,
    "focus": handle_focus,
    "blur": handle_blur,
    "submit": handle_submit,
}

def get_handler(event_type: str):
    return EVENT_HANDLERS.get(event_type, handle_unknown)
```

**Advanced: With lambdas or partial functions**:

```python
from functools import partial

OPERATIONS = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    "divide": lambda a, b: a / b if b != 0 else None,
}

def calculate(operation: str, a: float, b: float) -> float | None:
    func = OPERATIONS.get(operation)
    if func is None:
        raise ValueError(f"Unknown operation: {operation}")
    return func(a, b)
```

---

### 4. Match Statement (Python 3.10+)

**Problem**: Complex conditionals with pattern matching needs.

**Solution**: Use structural pattern matching for cleaner code.

```python
# BEFORE: Nested type checking
def process_response(response):
    if isinstance(response, dict):
        if "error" in response:
            return handle_error(response["error"])
        elif "data" in response:
            if isinstance(response["data"], list):
                return handle_list_data(response["data"])
            else:
                return handle_single_data(response["data"])
    elif isinstance(response, list):
        return handle_batch(response)
    else:
        return handle_unknown(response)

# AFTER: Match statement
def process_response(response):
    match response:
        case {"error": error}:
            return handle_error(error)
        case {"data": list() as items}:
            return handle_list_data(items)
        case {"data": data}:
            return handle_single_data(data)
        case list() as batch:
            return handle_batch(batch)
        case _:
            return handle_unknown(response)
```

---

## OOP Transformation Patterns

### 1. Encapsulate Global State

**Problem**: Global variables scattered throughout module.

**Solution**: Wrap globals in a class with controlled access.

```python
# BEFORE: Global state
_config = {}
_cache = {}
_connection = None

def init_app(config):
    global _config, _connection
    _config = config
    _connection = create_connection(config["db_url"])

def get_user(user_id):
    if user_id in _cache:
        return _cache[user_id]
    user = _connection.query(f"SELECT * FROM users WHERE id={user_id}")
    _cache[user_id] = user
    return user

# AFTER: Encapsulated in class
class ApplicationContext:
    def __init__(self, config: dict):
        self._config = config
        self._cache: dict = {}
        self._connection = create_connection(config["db_url"])

    def get_user(self, user_id: int) -> User:
        if user_id in self._cache:
            return self._cache[user_id]
        user = self._connection.query(f"SELECT * FROM users WHERE id={user_id}")
        self._cache[user_id] = user
        return user

    @property
    def config(self) -> dict:
        return self._config.copy()  # Return copy to prevent mutation
```

---

### 2. Group Related Functions into Classes

**Problem**: Module with many functions operating on the same data.

**Solution**: Create a class that encapsulates the data and operations.

```python
# BEFORE: Procedural functions
def create_order(customer_id, items):
    return {"customer_id": customer_id, "items": items, "status": "pending"}

def add_item(order, item):
    order["items"].append(item)
    return order

def calculate_total(order):
    return sum(item["price"] * item["quantity"] for item in order["items"])

def submit_order(order):
    order["status"] = "submitted"
    order["submitted_at"] = datetime.now()
    return order

# AFTER: Order class
@dataclass
class OrderItem:
    product_id: str
    price: float
    quantity: int

class Order:
    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self.items: list[OrderItem] = []
        self.status = "pending"
        self.submitted_at: datetime | None = None

    def add_item(self, item: OrderItem) -> None:
        self.items.append(item)

    @property
    def total(self) -> float:
        return sum(item.price * item.quantity for item in self.items)

    def submit(self) -> None:
        if not self.items:
            raise ValueError("Cannot submit empty order")
        self.status = "submitted"
        self.submitted_at = datetime.now()
```

---

### 3. Create Domain Models (Dataclasses)

**Problem**: Data passed as raw dictionaries without validation.

**Solution**: Define explicit data structures with dataclasses.

```python
# BEFORE: Dictionary-based data
def process_user(user_data):
    name = user_data.get("name", "Unknown")
    email = user_data.get("email")
    age = user_data.get("age", 0)
    # No validation, easy to pass invalid data

# AFTER: Dataclass models
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class User:
    name: str
    email: str
    age: int = 0
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.email or "@" not in self.email:
            raise ValueError(f"Invalid email: {self.email}")
        if self.age < 0:
            raise ValueError(f"Age cannot be negative: {self.age}")

    @property
    def is_adult(self) -> bool:
        return self.age >= 18

# Usage with validation
user = User(name="Alice", email="alice@example.com", age=25)
```

---

### 4. Apply Dependency Injection

**Problem**: Functions create their own dependencies, making testing difficult.

**Solution**: Inject dependencies through constructors or function parameters.

```python
# BEFORE: Hard-coded dependencies
class UserService:
    def __init__(self):
        self.db = DatabaseConnection("postgresql://localhost/mydb")
        self.cache = RedisCache("localhost:6379")
        self.mailer = SMTPMailer("smtp.gmail.com")

    def create_user(self, email: str) -> User:
        user = User(email=email)
        self.db.save(user)
        self.cache.invalidate("users")
        self.mailer.send_welcome(user)
        return user

# AFTER: Dependency injection
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def save(self, entity) -> None: ...

class Cache(ABC):
    @abstractmethod
    def invalidate(self, key: str) -> None: ...

class Mailer(ABC):
    @abstractmethod
    def send_welcome(self, user: User) -> None: ...

class UserService:
    def __init__(
        self,
        db: Database,
        cache: Cache,
        mailer: Mailer,
    ):
        self.db = db
        self.cache = cache
        self.mailer = mailer

    def create_user(self, email: str) -> User:
        user = User(email=email)
        self.db.save(user)
        self.cache.invalidate("users")
        self.mailer.send_welcome(user)
        return user

# Easy to test with mocks
def test_create_user():
    mock_db = MockDatabase()
    mock_cache = MockCache()
    mock_mailer = MockMailer()

    service = UserService(mock_db, mock_cache, mock_mailer)
    user = service.create_user("test@example.com")

    assert mock_db.saved_entities == [user]
```

---

### 5. Organize into Layers

**Problem**: Mixed concerns - database, business logic, and presentation in one place.

**Solution**: Separate into distinct layers.

```
┌─────────────────────────────┐
│      Presentation Layer     │  ← API routes, CLI, UI
├─────────────────────────────┤
│       Service Layer         │  ← Business logic, orchestration
├─────────────────────────────┤
│      Repository Layer       │  ← Data access, persistence
├─────────────────────────────┤
│       Domain Layer          │  ← Entities, value objects
└─────────────────────────────┘
```

```python
# domain/user.py - Domain entities
@dataclass
class User:
    id: str
    email: str
    name: str

# repository/user_repository.py - Data access
class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    def find_by_id(self, user_id: str) -> User | None:
        row = self.db.query("SELECT * FROM users WHERE id = ?", user_id)
        return User(**row) if row else None

    def save(self, user: User) -> None:
        self.db.execute("INSERT INTO users ...", user)

# service/user_service.py - Business logic
class UserService:
    def __init__(self, repo: UserRepository, mailer: Mailer):
        self.repo = repo
        self.mailer = mailer

    def register(self, email: str, name: str) -> User:
        user = User(id=generate_id(), email=email, name=name)
        self.repo.save(user)
        self.mailer.send_welcome(user)
        return user

# api/routes.py - Presentation
@app.post("/users")
def create_user(request: CreateUserRequest):
    user = user_service.register(request.email, request.name)
    return UserResponse.from_domain(user)
```

---

## Naming Patterns

### Boolean Variables

Use prefixes that make conditionals read naturally:

| Prefix | Usage | Example |
|--------|-------|---------|
| `is_` | State/condition | `is_active`, `is_valid`, `is_empty` |
| `has_` | Possession/contains | `has_permission`, `has_items` |
| `can_` | Capability | `can_edit`, `can_delete` |
| `should_` | Recommendation | `should_retry`, `should_cache` |

```python
# Good boolean naming
if user.is_active and user.has_permission("edit"):
    if document.can_be_edited:
        if should_notify_subscribers:
            notify_all()
```

### Functions

Use verb + object pattern:

```python
# Good function names
def calculate_total(items: list[Item]) -> float: ...
def validate_email(email: str) -> bool: ...
def send_notification(user: User, message: str) -> None: ...
def fetch_user_by_id(user_id: str) -> User | None: ...
def parse_config_file(path: Path) -> Config: ...

# Avoid vague names
def process(data): ...  # Process how?
def handle(event): ...  # Handle how?
def do_stuff(): ...     # What stuff?
```

### Constants

Use UPPERCASE_WITH_UNDERSCORES:

```python
# Configuration constants
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30
API_BASE_URL = "https://api.example.com"

# Status constants
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

# Better: Use Enum for related constants
from enum import Enum

class OrderStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
```
