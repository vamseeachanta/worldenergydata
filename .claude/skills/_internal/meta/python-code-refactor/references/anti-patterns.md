# Anti-Pattern Detection Guide

> 16 common anti-patterns with detection criteria, examples, and fix strategies.

---

## Severity Levels

| Level | Impact | Action |
|-------|--------|--------|
| **CRITICAL** | Architectural debt, blocks scaling | Fix immediately |
| **HIGH** | Significant maintenance burden | Fix in current sprint |
| **MEDIUM** | Code smell, technical debt | Plan for refactoring |
| **LOW** | Minor issues, style concerns | Fix opportunistically |

---

## CRITICAL Anti-Patterns

### 1. Script-like / Procedural Code

**Severity**: CRITICAL

**Detection Criteria**:
- Code runs top-to-bottom without functions
- Uses `if __name__ == "__main__":` with 50+ lines
- Global variables modified throughout
- No classes or data structures
- Difficult to test individual parts

**Example**:
```python
# anti_pattern.py
import requests

API_URL = "https://api.example.com"
results = []

# 100+ lines of sequential code
data = requests.get(API_URL).json()
for item in data:
    if item["status"] == "active":
        processed = item["value"] * 2
        results.append(processed)

total = sum(results)
print(f"Total: {total}")

# Save to file
with open("output.txt", "w") as f:
    f.write(str(total))
```

**Fix Strategy**:
1. Identify distinct responsibilities
2. Extract functions for each responsibility
3. Create data classes for structures
4. Encapsulate state in classes
5. Add entry point function

**Fixed Example**:
```python
from dataclasses import dataclass
from typing import Iterator

@dataclass
class Item:
    id: str
    status: str
    value: float

class DataProcessor:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def fetch_items(self) -> list[Item]:
        return self.api_client.get_items()

    def filter_active(self, items: list[Item]) -> Iterator[Item]:
        return (item for item in items if item.status == "active")

    def process(self, items: list[Item]) -> float:
        active_items = self.filter_active(items)
        return sum(item.value * 2 for item in active_items)

def main():
    client = APIClient(API_URL)
    processor = DataProcessor(client)
    items = processor.fetch_items()
    total = processor.process(items)
    save_result(total, "output.txt")
```

---

### 2. God Object / God Class

**Severity**: CRITICAL

**Detection Criteria**:
- Class with 500+ lines
- More than 20 public methods
- Handles multiple unrelated responsibilities
- Difficult to name accurately (often named `Manager`, `Handler`, `Processor`, `Utils`)
- Many dependencies injected or created

**Example**:
```python
class ApplicationManager:
    def __init__(self):
        self.db = Database()
        self.cache = Cache()
        self.mailer = Mailer()
        self.logger = Logger()
        self.config = Config()
        # ... 10 more dependencies

    # User operations
    def create_user(self, data): ...
    def update_user(self, user_id, data): ...
    def delete_user(self, user_id): ...
    def get_user(self, user_id): ...

    # Order operations
    def create_order(self, data): ...
    def process_order(self, order_id): ...
    def cancel_order(self, order_id): ...

    # Payment operations
    def process_payment(self, payment_data): ...
    def refund_payment(self, payment_id): ...

    # Notification operations
    def send_email(self, to, subject, body): ...
    def send_sms(self, phone, message): ...

    # ... 50 more methods
```

**Fix Strategy**:
1. Identify cohesive groups of methods
2. Extract each group into its own class
3. Apply Single Responsibility Principle
4. Use composition to coordinate

**Fixed Example**:
```python
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def create(self, data: UserCreate) -> User: ...
    def update(self, user_id: str, data: UserUpdate) -> User: ...
    def delete(self, user_id: str) -> None: ...
    def get(self, user_id: str) -> User: ...

class OrderService:
    def __init__(self, repo: OrderRepository, payment: PaymentService):
        self.repo = repo
        self.payment = payment

    def create(self, data: OrderCreate) -> Order: ...
    def process(self, order_id: str) -> None: ...
    def cancel(self, order_id: str) -> None: ...

class NotificationService:
    def __init__(self, email_client: EmailClient, sms_client: SMSClient):
        self.email_client = email_client
        self.sms_client = sms_client

    def send_email(self, to: str, subject: str, body: str) -> None: ...
    def send_sms(self, phone: str, message: str) -> None: ...
```

---

## HIGH Severity Anti-Patterns

### 3. Complex Nesting (Deep Indentation)

**Severity**: HIGH

**Detection Criteria**:
- Indentation level > 4
- Nested if/else/for/while > 3 levels
- Cognitive complexity > 15
- Difficult to trace execution path

**Example**:
```python
def process_data(data):
    if data is not None:
        if data.get("items"):
            for item in data["items"]:
                if item.get("active"):
                    if item.get("value") > 0:
                        if item.get("type") == "premium":
                            # Finally doing something
                            result = item["value"] * 1.5
                        else:
                            result = item["value"]
```

**Fix Strategy**:
- Use guard clauses for early returns
- Extract nested blocks into functions
- Use list comprehensions where appropriate

---

### 4. Long Functions (> 50 lines)

**Severity**: HIGH

**Detection Criteria**:
- Function body > 50 lines
- Multiple levels of abstraction
- Multiple comments explaining sections
- Difficult to test as unit

**Example**:
```python
def generate_report(data):
    # Section 1: Validate (20 lines)
    # ...

    # Section 2: Transform (30 lines)
    # ...

    # Section 3: Format (25 lines)
    # ...

    # Section 4: Save (15 lines)
    # ...
```

**Fix Strategy**:
- Extract each section into its own function
- Name functions by their purpose
- Keep each function at one abstraction level

---

### 5. Magic Numbers / Strings

**Severity**: HIGH

**Detection Criteria**:
- Literal numbers in code (except 0, 1, -1)
- Literal strings for status/types
- Same value appears in multiple places
- No explanation for the value

**Example**:
```python
def calculate_price(quantity):
    if quantity > 100:
        return quantity * 9.99 * 0.85  # What is 0.85?
    elif quantity > 50:
        return quantity * 9.99 * 0.9   # What is 0.9?
    return quantity * 9.99

if status == "APR":  # What does APR mean?
    process_approved()
```

**Fix Strategy**:
- Define named constants
- Use Enums for related values
- Document the meaning

**Fixed Example**:
```python
UNIT_PRICE = 9.99
BULK_DISCOUNT = 0.85      # 15% off for 100+ items
VOLUME_DISCOUNT = 0.90    # 10% off for 50+ items
BULK_THRESHOLD = 100
VOLUME_THRESHOLD = 50

class OrderStatus(Enum):
    PENDING = "PND"
    APPROVED = "APR"
    REJECTED = "REJ"
```

---

### 6. Cryptic Names

**Severity**: HIGH

**Detection Criteria**:
- Single letter variables (except loop indices)
- Abbreviations not universally known
- Names that don't convey purpose
- Similar names for different things

**Example**:
```python
def calc(d, t, r):
    x = d * t
    y = x * r
    return y - (y * 0.1)

def proc_usr_dat(ud):
    for i in ud:
        if i["s"] == "a":
            # ...
```

**Fix Strategy**:
- Use descriptive names
- Spell out words
- Names should explain purpose

**Fixed Example**:
```python
def calculate_interest(principal: float, time_years: float, rate: float) -> float:
    gross_interest = principal * time_years
    total_amount = gross_interest * rate
    return total_amount - (total_amount * TAX_RATE)

def process_user_data(user_records: list[dict]) -> None:
    for user in user_records:
        if user["status"] == "active":
            # ...
```

---

### 7. Missing Type Hints

**Severity**: HIGH

**Detection Criteria**:
- Functions without parameter type annotations
- Functions without return type annotations
- Variables with unclear types
- Dynamic typing obscuring intent

**Example**:
```python
def process(data):
    results = []
    for item in data:
        if item.get("value"):
            results.append(transform(item))
    return results

def transform(item):
    return item["value"] * 2
```

**Fix Strategy**:
- Add type hints to all function signatures
- Use TypedDict for dictionary structures
- Define data classes for complex types

**Fixed Example**:
```python
from typing import TypedDict

class DataItem(TypedDict):
    id: str
    value: float

def process(data: list[DataItem]) -> list[float]:
    results: list[float] = []
    for item in data:
        if item.get("value"):
            results.append(transform(item))
    return results

def transform(item: DataItem) -> float:
    return item["value"] * 2
```

---

### 8. Missing Docstrings

**Severity**: HIGH

**Detection Criteria**:
- Public functions without docstrings
- Classes without docstrings
- Modules without docstrings
- Complex logic without explanation

**Example**:
```python
class DataProcessor:
    def __init__(self, config):
        self.config = config

    def process(self, data):
        return [self._transform(x) for x in data if self._validate(x)]

    def _transform(self, item):
        return item * self.config["multiplier"]
```

**Fix Strategy**:
- Add module docstrings
- Add class docstrings explaining purpose
- Add function docstrings with args/returns

**Fixed Example**:
```python
"""Data processing utilities for transforming raw input."""

class DataProcessor:
    """Processes and transforms data according to configuration rules.

    Attributes:
        config: Configuration dictionary with processing parameters.
    """

    def __init__(self, config: dict) -> None:
        """Initialize processor with configuration.

        Args:
            config: Dictionary containing 'multiplier' key.
        """
        self.config = config

    def process(self, data: list[float]) -> list[float]:
        """Process and transform valid data items.

        Args:
            data: List of numeric values to process.

        Returns:
            List of transformed values that passed validation.
        """
        return [self._transform(x) for x in data if self._validate(x)]
```

---

## MEDIUM Severity Anti-Patterns

### 9. Duplicate Code

**Severity**: MEDIUM

**Detection Criteria**:
- Similar code blocks in multiple places
- Copy-paste with minor modifications
- Same logic with different variable names
- Parallel class hierarchies

**Example**:
```python
def create_user(data):
    if not data.get("email"):
        raise ValueError("Email required")
    if not data.get("name"):
        raise ValueError("Name required")
    return User(**data)

def create_admin(data):
    if not data.get("email"):
        raise ValueError("Email required")
    if not data.get("name"):
        raise ValueError("Name required")
    return Admin(**data)
```

**Fix Strategy**:
- Extract common logic into shared function
- Use base classes for shared behavior
- Apply template method pattern

---

### 10. Primitive Obsession

**Severity**: MEDIUM

**Detection Criteria**:
- Using strings for structured data (emails, phone numbers)
- Using tuples for related values
- Passing multiple related primitives together
- Validation logic scattered throughout codebase

**Example**:
```python
def send_email(to: str, subject: str, body: str) -> None:
    if "@" not in to:  # Email validation everywhere
        raise ValueError("Invalid email")
    # ...

def create_user(name: str, email: str, phone: str, address: str,
                city: str, state: str, zip_code: str) -> User:
    # Too many string parameters
    pass
```

**Fix Strategy**:
- Create value objects for domain concepts
- Use dataclasses for grouped data
- Centralize validation in constructors

**Fixed Example**:
```python
@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self):
        if "@" not in self.value:
            raise ValueError(f"Invalid email: {self.value}")

@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str

def create_user(name: str, email: Email, phone: Phone, address: Address) -> User:
    pass
```

---

### 11. Long Parameter Lists (> 5 parameters)

**Severity**: MEDIUM

**Detection Criteria**:
- Functions with more than 5 parameters
- Many boolean flags as parameters
- Related parameters often passed together
- Difficult to remember parameter order

**Example**:
```python
def create_report(title, author, date, format, include_header,
                  include_footer, page_size, orientation, margins,
                  font_size, color_scheme):
    pass
```

**Fix Strategy**:
- Group related parameters into objects
- Use configuration objects
- Apply builder pattern for complex construction

**Fixed Example**:
```python
@dataclass
class PageSettings:
    size: str = "A4"
    orientation: str = "portrait"
    margins: tuple[int, int, int, int] = (20, 20, 20, 20)

@dataclass
class ReportOptions:
    include_header: bool = True
    include_footer: bool = True
    font_size: int = 12
    color_scheme: str = "default"

def create_report(
    title: str,
    author: str,
    date: datetime,
    page_settings: PageSettings | None = None,
    options: ReportOptions | None = None,
) -> Report:
    pass
```

---

### 12. Mixed Abstraction Levels

**Severity**: MEDIUM

**Detection Criteria**:
- High-level business logic mixed with low-level details
- Database queries alongside business rules
- HTTP handling mixed with domain logic
- Formatting mixed with calculation

**Example**:
```python
def process_order(order_data):
    # High level: business logic
    if order_data["total"] > 1000:
        discount = 0.1
    else:
        discount = 0

    # Low level: database operations
    conn = psycopg2.connect("postgresql://localhost/db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (total, discount) VALUES (%s, %s)",
        (order_data["total"], discount)
    )
    conn.commit()

    # Low level: email formatting
    html = f"<html><body><h1>Order Confirmed</h1>"
    html += f"<p>Total: ${order_data['total']}</p></body></html>"
    send_email(order_data["email"], "Order Confirmation", html)
```

**Fix Strategy**:
- Separate into distinct layers
- Keep functions at one abstraction level
- Use dependency injection

---

## LOW Severity Anti-Patterns

### 13. Inconsistent Naming

**Severity**: LOW

**Detection Criteria**:
- Mixed naming conventions (camelCase and snake_case)
- Inconsistent abbreviations
- Similar things named differently
- Different things named similarly

**Example**:
```python
def getUserData(userId):  # camelCase
    pass

def get_user_profile(user_id):  # snake_case
    pass

class userService:  # lowercase class
    pass
```

**Fix Strategy**:
- Follow PEP 8 consistently
- Use snake_case for functions and variables
- Use PascalCase for classes

---

### 14. Redundant Comments

**Severity**: LOW

**Detection Criteria**:
- Comments that restate the obvious
- Outdated comments that don't match code
- Commented-out code
- TODO without ticket or owner

**Example**:
```python
# Increment counter by 1
counter += 1

# Loop through items
for item in items:
    pass

# TODO: fix this later
# old_function()
```

**Fix Strategy**:
- Delete obvious comments
- Update or remove outdated comments
- Remove commented-out code
- Add ticket numbers to TODOs

---

### 15. Unused Imports

**Severity**: LOW

**Detection Criteria**:
- Imported modules not used
- Wildcard imports (`from x import *`)
- Duplicate imports
- Circular import potential

**Example**:
```python
import os
import sys
import json  # Not used
from typing import *  # Wildcard
from collections import OrderedDict  # Not used
```

**Fix Strategy**:
- Remove unused imports
- Use explicit imports
- Run `ruff check --select F401`

---

### 16. Dead Code

**Severity**: LOW

**Detection Criteria**:
- Unreachable code after return/raise
- Unused functions or classes
- Variables assigned but never read
- Conditions that are always true/false

**Example**:
```python
def process(data):
    return data * 2
    print("Done")  # Unreachable

def unused_helper():  # Never called
    pass

DEBUG = True
if DEBUG:
    logging.debug("Always runs")  # Condition always true
```

**Fix Strategy**:
- Remove unreachable code
- Delete unused functions
- Remove dead conditions
- Use static analysis to detect

---

## Quick Reference Table

| # | Anti-Pattern | Severity | Detection | Primary Fix |
|---|--------------|----------|-----------|-------------|
| 1 | Script-like Code | CRITICAL | No functions/classes | Extract functions, create classes |
| 2 | God Object | CRITICAL | Class > 500 lines, > 20 methods | Split by responsibility |
| 3 | Complex Nesting | HIGH | Indent > 4, CC > 15 | Guard clauses, extract methods |
| 4 | Long Functions | HIGH | > 50 lines | Extract methods |
| 5 | Magic Numbers | HIGH | Unexplained literals | Named constants, Enums |
| 6 | Cryptic Names | HIGH | Single letters, abbreviations | Descriptive names |
| 7 | Missing Types | HIGH | No type annotations | Add type hints |
| 8 | Missing Docstrings | HIGH | No documentation | Add docstrings |
| 9 | Duplicate Code | MEDIUM | Similar blocks | Extract common logic |
| 10 | Primitive Obsession | MEDIUM | Strings for domain concepts | Value objects |
| 11 | Long Parameters | MEDIUM | > 5 parameters | Parameter objects |
| 12 | Mixed Abstraction | MEDIUM | High/low level mixed | Layer separation |
| 13 | Inconsistent Naming | LOW | Mixed conventions | Follow PEP 8 |
| 14 | Redundant Comments | LOW | Obvious/outdated comments | Remove or update |
| 15 | Unused Imports | LOW | Imports not used | Remove imports |
| 16 | Dead Code | LOW | Unreachable/unused code | Delete dead code |
