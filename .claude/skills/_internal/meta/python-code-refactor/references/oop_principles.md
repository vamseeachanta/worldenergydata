# OOP Principles for Python

> Object-Oriented Programming best practices with Python-specific examples.

---

## SOLID Principles

### S - Single Responsibility Principle (SRP)

**Definition**: A class should have only one reason to change.

**Bad Example**:
```python
class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def save_to_database(self):
        # Database logic - different reason to change
        db.execute("INSERT INTO users ...")

    def send_welcome_email(self):
        # Email logic - different reason to change
        smtp.send(self.email, "Welcome!")

    def generate_report(self):
        # Reporting logic - different reason to change
        return f"User Report: {self.name}"
```

**Good Example**:
```python
# Each class has one responsibility
@dataclass
class User:
    """Domain entity - only user data."""
    name: str
    email: str

class UserRepository:
    """Data access - only persistence."""
    def __init__(self, db: Database):
        self.db = db

    def save(self, user: User) -> None:
        self.db.execute("INSERT INTO users ...")

    def find_by_email(self, email: str) -> User | None:
        ...

class EmailService:
    """Communication - only sending emails."""
    def __init__(self, smtp_client: SMTPClient):
        self.smtp = smtp_client

    def send_welcome(self, user: User) -> None:
        self.smtp.send(user.email, "Welcome!")

class UserReportGenerator:
    """Reporting - only generating reports."""
    def generate(self, user: User) -> str:
        return f"User Report: {user.name}"
```

---

### O - Open/Closed Principle (OCP)

**Definition**: Open for extension, closed for modification.

**Bad Example**:
```python
class PaymentProcessor:
    def process(self, payment_type: str, amount: float):
        if payment_type == "credit_card":
            # Credit card logic
            return self._process_credit_card(amount)
        elif payment_type == "paypal":
            # PayPal logic
            return self._process_paypal(amount)
        elif payment_type == "bitcoin":
            # Adding new type requires modifying this class
            return self._process_bitcoin(amount)
        # Every new payment type = modification
```

**Good Example**:
```python
from abc import ABC, abstractmethod

class PaymentMethod(ABC):
    """Abstract base - defines the contract."""

    @abstractmethod
    def process(self, amount: float) -> PaymentResult:
        """Process payment and return result."""
        pass

class CreditCardPayment(PaymentMethod):
    """Concrete implementation - extends without modifying base."""

    def __init__(self, card_number: str, cvv: str):
        self.card_number = card_number
        self.cvv = cvv

    def process(self, amount: float) -> PaymentResult:
        # Credit card specific logic
        return PaymentResult(success=True, transaction_id="...")

class PayPalPayment(PaymentMethod):
    """Another extension - no modification needed."""

    def __init__(self, email: str):
        self.email = email

    def process(self, amount: float) -> PaymentResult:
        # PayPal specific logic
        return PaymentResult(success=True, transaction_id="...")

# New payment types just add new classes
class BitcoinPayment(PaymentMethod):
    def __init__(self, wallet_address: str):
        self.wallet_address = wallet_address

    def process(self, amount: float) -> PaymentResult:
        return PaymentResult(success=True, transaction_id="...")

# Processor works with any PaymentMethod
class PaymentProcessor:
    def process(self, method: PaymentMethod, amount: float) -> PaymentResult:
        return method.process(amount)
```

---

### L - Liskov Substitution Principle (LSP)

**Definition**: Subtypes must be substitutable for their base types.

**Bad Example**:
```python
class Bird:
    def fly(self) -> None:
        print("Flying...")

class Penguin(Bird):
    def fly(self) -> None:
        # Violates LSP - penguins can't fly!
        raise NotImplementedError("Penguins can't fly")

def make_bird_fly(bird: Bird) -> None:
    bird.fly()  # Will crash for Penguin!
```

**Good Example**:
```python
from abc import ABC, abstractmethod

class Bird(ABC):
    """Base class with common behavior only."""

    @abstractmethod
    def move(self) -> None:
        pass

class FlyingBird(Bird):
    """Birds that can fly."""

    def move(self) -> None:
        self.fly()

    def fly(self) -> None:
        print("Flying...")

class SwimmingBird(Bird):
    """Birds that swim instead of fly."""

    def move(self) -> None:
        self.swim()

    def swim(self) -> None:
        print("Swimming...")

class Sparrow(FlyingBird):
    pass

class Penguin(SwimmingBird):
    pass

# Now any Bird can be substituted safely
def make_bird_move(bird: Bird) -> None:
    bird.move()  # Works for all birds!

make_bird_move(Sparrow())   # Flying...
make_bird_move(Penguin())   # Swimming...
```

---

### I - Interface Segregation Principle (ISP)

**Definition**: Many specific interfaces are better than one general interface.

**Bad Example**:
```python
from abc import ABC, abstractmethod

class Worker(ABC):
    """Fat interface - forces implementation of everything."""

    @abstractmethod
    def work(self) -> None:
        pass

    @abstractmethod
    def eat(self) -> None:
        pass

    @abstractmethod
    def sleep(self) -> None:
        pass

    @abstractmethod
    def attend_meeting(self) -> None:
        pass

class Robot(Worker):
    def work(self) -> None:
        print("Working...")

    def eat(self) -> None:
        # Robots don't eat!
        raise NotImplementedError()

    def sleep(self) -> None:
        # Robots don't sleep!
        raise NotImplementedError()

    def attend_meeting(self) -> None:
        # Maybe robots shouldn't attend meetings
        raise NotImplementedError()
```

**Good Example**:
```python
from abc import ABC, abstractmethod
from typing import Protocol

# Segregated interfaces (using Protocol for structural typing)
class Workable(Protocol):
    def work(self) -> None: ...

class Eatable(Protocol):
    def eat(self) -> None: ...

class Sleepable(Protocol):
    def sleep(self) -> None: ...

class MeetingAttendee(Protocol):
    def attend_meeting(self) -> None: ...

# Human implements all relevant interfaces
class Human:
    def work(self) -> None:
        print("Working...")

    def eat(self) -> None:
        print("Eating...")

    def sleep(self) -> None:
        print("Sleeping...")

    def attend_meeting(self) -> None:
        print("In meeting...")

# Robot only implements what it can do
class Robot:
    def work(self) -> None:
        print("Working efficiently...")

# Functions depend on minimal interfaces
def assign_work(worker: Workable) -> None:
    worker.work()

def schedule_break(entity: Eatable) -> None:
    entity.eat()

# Both work with Human, only assign_work works with Robot
assign_work(Human())      # Works
assign_work(Robot())      # Works
schedule_break(Human())   # Works
# schedule_break(Robot()) # Type error - Robot isn't Eatable
```

---

### D - Dependency Inversion Principle (DIP)

**Definition**: Depend on abstractions, not concretions.

**Bad Example**:
```python
class MySQLDatabase:
    def query(self, sql: str) -> list:
        # MySQL-specific implementation
        pass

class UserService:
    def __init__(self):
        # Direct dependency on concrete class
        self.db = MySQLDatabase()

    def get_users(self) -> list[User]:
        return self.db.query("SELECT * FROM users")

# Problem: Can't switch to PostgreSQL without changing UserService
```

**Good Example**:
```python
from abc import ABC, abstractmethod

# Abstract interface (the abstraction)
class Database(ABC):
    @abstractmethod
    def query(self, sql: str) -> list:
        pass

# Concrete implementations
class MySQLDatabase(Database):
    def query(self, sql: str) -> list:
        # MySQL-specific implementation
        pass

class PostgreSQLDatabase(Database):
    def query(self, sql: str) -> list:
        # PostgreSQL-specific implementation
        pass

# Depends on abstraction
class UserService:
    def __init__(self, db: Database):  # Inject the dependency
        self.db = db

    def get_users(self) -> list[User]:
        return self.db.query("SELECT * FROM users")

# Easy to switch implementations
mysql_service = UserService(MySQLDatabase())
postgres_service = UserService(PostgreSQLDatabase())

# Easy to test with mock
class MockDatabase(Database):
    def query(self, sql: str) -> list:
        return [{"id": 1, "name": "Test"}]

test_service = UserService(MockDatabase())
```

---

## OOP Best Practices in Python

### 1. Prefer Composition Over Inheritance

```python
# Inheritance - tight coupling
class Animal:
    def speak(self) -> str:
        pass

class Dog(Animal):
    def speak(self) -> str:
        return "Woof!"

class RobotDog(Dog):  # Awkward - is a robot really an animal?
    def speak(self) -> str:
        return "Beep boop woof!"

# Composition - flexible
class Speaker(Protocol):
    def speak(self) -> str: ...

class DogVoice:
    def speak(self) -> str:
        return "Woof!"

class RobotVoice:
    def speak(self) -> str:
        return "Beep boop!"

class Pet:
    def __init__(self, voice: Speaker):
        self.voice = voice

    def make_sound(self) -> str:
        return self.voice.speak()

# Flexible combinations
real_dog = Pet(DogVoice())
robot_pet = Pet(RobotVoice())
```

### 2. Use Dataclasses for Data Containers

```python
from dataclasses import dataclass, field
from datetime import datetime

# Before dataclasses
class OrderOld:
    def __init__(self, id, customer_id, items, created_at=None):
        self.id = id
        self.customer_id = customer_id
        self.items = items
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        return f"Order(id={self.id}, customer_id={self.customer_id})"

    def __eq__(self, other):
        return self.id == other.id

# With dataclasses - automatic __init__, __repr__, __eq__
@dataclass
class Order:
    id: str
    customer_id: str
    items: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_items(self) -> int:
        return len(self.items)
```

### 3. Use Properties for Computed Attributes

```python
class Rectangle:
    def __init__(self, width: float, height: float):
        self._width = width
        self._height = height

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        if value <= 0:
            raise ValueError("Width must be positive")
        self._width = value

    @property
    def area(self) -> float:
        """Computed property - no setter needed."""
        return self._width * self._height

    @property
    def perimeter(self) -> float:
        """Another computed property."""
        return 2 * (self._width + self._height)

rect = Rectangle(10, 5)
print(rect.area)       # 50 - accessed like attribute
print(rect.perimeter)  # 30
```

### 4. Use Abstract Base Classes for Contracts

```python
from abc import ABC, abstractmethod

class Serializable(ABC):
    """Contract for serializable objects."""

    @abstractmethod
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Serializable":
        """Create from dictionary."""
        pass

@dataclass
class User(Serializable):
    name: str
    email: str

    def to_dict(self) -> dict:
        return {"name": self.name, "email": self.email}

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(name=data["name"], email=data["email"])
```

---

## When to Use Classes vs Functions

### Use Classes When:

| Scenario | Example |
|----------|---------|
| Managing state | `DatabaseConnection`, `Session` |
| Grouping related operations | `UserService`, `PaymentProcessor` |
| Implementing interfaces | `FileStorage implements Storage` |
| Need multiple instances | `User`, `Order`, `Product` |
| Complex initialization | Builder pattern, Factory pattern |

### Use Functions When:

| Scenario | Example |
|----------|---------|
| Stateless transformation | `calculate_tax(amount)` |
| Simple utility | `format_date(date)` |
| One-off operation | `send_notification(user, message)` |
| Pure computation | `fibonacci(n)` |
| No shared state needed | `validate_email(email)` |

```python
# Function is better here - stateless, pure
def calculate_discount(price: float, percentage: float) -> float:
    return price * (1 - percentage / 100)

# Class is better here - manages state and operations
class ShoppingCart:
    def __init__(self):
        self._items: list[CartItem] = []

    def add_item(self, item: CartItem) -> None:
        self._items.append(item)

    def remove_item(self, item_id: str) -> None:
        self._items = [i for i in self._items if i.id != item_id]

    @property
    def total(self) -> float:
        return sum(item.price * item.quantity for item in self._items)
```

---

## Dependency Injection in Python

### Constructor Injection (Preferred)

```python
class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        payment_processor: PaymentProcessor,
        notification_service: NotificationService,
    ):
        self._repository = repository
        self._payment = payment_processor
        self._notifications = notification_service

    def place_order(self, order: Order) -> None:
        self._repository.save(order)
        self._payment.charge(order.total)
        self._notifications.send_confirmation(order)
```

### Using a Container (for complex apps)

```python
from dataclasses import dataclass

@dataclass
class Container:
    """Simple DI container."""
    db: Database
    cache: Cache
    mailer: Mailer

    def user_service(self) -> UserService:
        return UserService(
            repository=UserRepository(self.db),
            cache=self.cache,
        )

    def order_service(self) -> OrderService:
        return OrderService(
            repository=OrderRepository(self.db),
            payment=PaymentProcessor(),
            notification=NotificationService(self.mailer),
        )

# Usage
container = Container(
    db=PostgreSQLDatabase(config.db_url),
    cache=RedisCache(config.redis_url),
    mailer=SMTPMailer(config.smtp_settings),
)

user_service = container.user_service()
order_service = container.order_service()
```

---

## Common OOP Anti-Patterns

### 1. Anemic Domain Model

```python
# Anti-pattern: Class with only data, no behavior
class Order:
    def __init__(self):
        self.items = []
        self.status = "pending"
        self.total = 0

# Logic lives elsewhere
class OrderService:
    def calculate_total(self, order):
        order.total = sum(i.price for i in order.items)

    def submit(self, order):
        if order.total > 0:
            order.status = "submitted"

# Better: Domain model with behavior
class Order:
    def __init__(self):
        self._items: list[OrderItem] = []
        self._status = "pending"

    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self._items)

    def add_item(self, item: OrderItem) -> None:
        self._items.append(item)

    def submit(self) -> None:
        if not self._items:
            raise ValueError("Cannot submit empty order")
        self._status = "submitted"
```

### 2. Inappropriate Intimacy

```python
# Anti-pattern: Classes know too much about each other
class Order:
    def calculate_shipping(self):
        # Reaches into customer's internals
        if self.customer._address._city == "NYC":
            if self.customer._membership._level == "gold":
                return 0
        return 10

# Better: Ask, don't tell
class Order:
    def calculate_shipping(self):
        if self.customer.qualifies_for_free_shipping():
            return 0
        return self.customer.get_shipping_rate()

class Customer:
    def qualifies_for_free_shipping(self) -> bool:
        return self.address.is_local and self.membership.is_gold

    def get_shipping_rate(self) -> float:
        return self.address.get_shipping_rate()
```

### 3. Feature Envy

```python
# Anti-pattern: Method more interested in another class
class OrderReport:
    def generate(self, order):
        # Uses order's data more than its own
        lines = []
        for item in order.items:
            lines.append(f"{item.name}: {item.price * item.quantity}")
        lines.append(f"Subtotal: {sum(i.price * i.quantity for i in order.items)}")
        lines.append(f"Tax: {order.tax_rate * sum(i.price * i.quantity for i in order.items)}")
        return "\n".join(lines)

# Better: Move behavior to where data lives
class Order:
    def get_line_items(self) -> list[str]:
        return [f"{item.name}: {item.subtotal}" for item in self.items]

    @property
    def subtotal(self) -> float:
        return sum(item.subtotal for item in self.items)

    @property
    def tax(self) -> float:
        return self.subtotal * self.tax_rate

class OrderReport:
    def generate(self, order: Order) -> str:
        lines = order.get_line_items()
        lines.append(f"Subtotal: {order.subtotal}")
        lines.append(f"Tax: {order.tax}")
        return "\n".join(lines)
```

---

## Summary

| Principle | Key Takeaway |
|-----------|--------------|
| **SRP** | One class = one responsibility |
| **OCP** | Extend, don't modify |
| **LSP** | Subtypes must be substitutable |
| **ISP** | Small, focused interfaces |
| **DIP** | Depend on abstractions |
| **Composition** | Prefer over inheritance |
| **DI** | Inject dependencies, don't create |
