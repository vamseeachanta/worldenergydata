# Example: Complexity Reduction Techniques

> Before/after examples demonstrating complexity reduction patterns.

---

## 1. Nested Conditionals to Guard Clauses

### Before: Nested If/Else (Cognitive Complexity: 12)

```python
def process_order(order, user, inventory):
    """Process an order - deeply nested version."""
    if order is not None:
        if user is not None:
            if user.is_active:
                if user.has_permission("place_order"):
                    if order.items:
                        if inventory.has_stock(order.items):
                            if user.balance >= order.total:
                                # Finally process the order
                                user.balance -= order.total
                                inventory.reserve(order.items)
                                order.status = "confirmed"
                                return {"success": True, "order_id": order.id}
                            else:
                                return {"success": False, "error": "Insufficient balance"}
                        else:
                            return {"success": False, "error": "Items out of stock"}
                    else:
                        return {"success": False, "error": "Order has no items"}
                else:
                    return {"success": False, "error": "No permission"}
            else:
                return {"success": False, "error": "User inactive"}
        else:
            return {"success": False, "error": "User required"}
    else:
        return {"success": False, "error": "Order required"}
```

**Problems**:
- Deep nesting (8 levels)
- Hard to follow the logic
- Success case buried at the deepest level
- Difficult to add new validations

### After: Guard Clauses (Cognitive Complexity: 7)

```python
def process_order(order, user, inventory):
    """Process an order - guard clause version."""
    # Validate inputs upfront
    if order is None:
        return {"success": False, "error": "Order required"}

    if user is None:
        return {"success": False, "error": "User required"}

    if not user.is_active:
        return {"success": False, "error": "User inactive"}

    if not user.has_permission("place_order"):
        return {"success": False, "error": "No permission"}

    if not order.items:
        return {"success": False, "error": "Order has no items"}

    if not inventory.has_stock(order.items):
        return {"success": False, "error": "Items out of stock"}

    if user.balance < order.total:
        return {"success": False, "error": "Insufficient balance"}

    # Happy path - process the order
    user.balance -= order.total
    inventory.reserve(order.items)
    order.status = "confirmed"
    return {"success": True, "order_id": order.id}
```

**Benefits**:
- Flat structure (max 1 level of nesting)
- Easy to read top-to-bottom
- Clear separation of validation and logic
- Simple to add new checks

### Even Better: Extract Validation

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ValidationResult:
    """Result of order validation."""
    is_valid: bool
    error: Optional[str] = None

def validate_order(order, user, inventory) -> ValidationResult:
    """Validate order prerequisites."""
    if order is None:
        return ValidationResult(False, "Order required")
    if user is None:
        return ValidationResult(False, "User required")
    if not user.is_active:
        return ValidationResult(False, "User inactive")
    if not user.has_permission("place_order"):
        return ValidationResult(False, "No permission")
    if not order.items:
        return ValidationResult(False, "Order has no items")
    if not inventory.has_stock(order.items):
        return ValidationResult(False, "Items out of stock")
    if user.balance < order.total:
        return ValidationResult(False, "Insufficient balance")

    return ValidationResult(True)

def process_order(order, user, inventory):
    """Process an order - separated concerns."""
    validation = validate_order(order, user, inventory)

    if not validation.is_valid:
        return {"success": False, "error": validation.error}

    # Pure business logic
    user.balance -= order.total
    inventory.reserve(order.items)
    order.status = "confirmed"

    return {"success": True, "order_id": order.id}
```

---

## 2. If/Elif Chain to Dictionary Dispatch

### Before: If/Elif Chain (Cyclomatic Complexity: 12)

```python
def get_shipping_cost(country, weight, shipping_type):
    """Calculate shipping cost - if/elif version."""
    if shipping_type == "standard":
        if country == "US":
            if weight < 1:
                return 5.99
            elif weight < 5:
                return 9.99
            else:
                return 14.99
        elif country == "CA":
            if weight < 1:
                return 7.99
            elif weight < 5:
                return 12.99
            else:
                return 19.99
        elif country == "UK":
            if weight < 1:
                return 8.99
            elif weight < 5:
                return 14.99
            else:
                return 24.99
        else:
            return 29.99  # Default international
    elif shipping_type == "express":
        if country == "US":
            return 19.99
        elif country == "CA":
            return 24.99
        elif country == "UK":
            return 29.99
        else:
            return 49.99
    elif shipping_type == "overnight":
        if country == "US":
            return 39.99
        elif country == "CA":
            return 49.99
        elif country == "UK":
            return 59.99
        else:
            return None  # Not available
    else:
        raise ValueError(f"Unknown shipping type: {shipping_type}")
```

### After: Dictionary Dispatch (Cyclomatic Complexity: 3)

```python
from dataclasses import dataclass
from typing import Callable, Optional

# Define rate structures
STANDARD_RATES = {
    "US": [(1, 5.99), (5, 9.99), (float("inf"), 14.99)],
    "CA": [(1, 7.99), (5, 12.99), (float("inf"), 19.99)],
    "UK": [(1, 8.99), (5, 14.99), (float("inf"), 24.99)],
}
STANDARD_DEFAULT = 29.99

EXPRESS_RATES = {
    "US": 19.99,
    "CA": 24.99,
    "UK": 29.99,
}
EXPRESS_DEFAULT = 49.99

OVERNIGHT_RATES = {
    "US": 39.99,
    "CA": 49.99,
    "UK": 59.99,
}

def _get_standard_rate(country: str, weight: float) -> float:
    """Calculate standard shipping rate."""
    rates = STANDARD_RATES.get(country)
    if rates is None:
        return STANDARD_DEFAULT

    for max_weight, rate in rates:
        if weight < max_weight:
            return rate

    return rates[-1][1]  # Return highest tier

def _get_express_rate(country: str, weight: float) -> float:
    """Calculate express shipping rate."""
    return EXPRESS_RATES.get(country, EXPRESS_DEFAULT)

def _get_overnight_rate(country: str, weight: float) -> Optional[float]:
    """Calculate overnight shipping rate."""
    return OVERNIGHT_RATES.get(country)  # None if not available

# Dispatch table
SHIPPING_CALCULATORS: dict[str, Callable[[str, float], Optional[float]]] = {
    "standard": _get_standard_rate,
    "express": _get_express_rate,
    "overnight": _get_overnight_rate,
}

def get_shipping_cost(
    country: str,
    weight: float,
    shipping_type: str,
) -> Optional[float]:
    """Calculate shipping cost - dictionary dispatch version."""
    calculator = SHIPPING_CALCULATORS.get(shipping_type)

    if calculator is None:
        raise ValueError(f"Unknown shipping type: {shipping_type}")

    return calculator(country, weight)
```

**Benefits**:
- Data separated from logic
- Easy to add new countries or shipping types
- Each calculator is independently testable
- Configuration can be externalized

---

## 3. Long Function to Extracted Methods

### Before: Long Function (50+ lines)

```python
def generate_invoice(order, customer):
    """Generate invoice for an order - monolithic version."""
    # Section 1: Validate inputs
    if not order:
        raise ValueError("Order is required")
    if not customer:
        raise ValueError("Customer is required")
    if not order.items:
        raise ValueError("Order must have items")
    if order.status != "confirmed":
        raise ValueError("Order must be confirmed")

    # Section 2: Calculate line items
    line_items = []
    subtotal = 0
    for item in order.items:
        item_total = item.price * item.quantity
        if item.discount:
            item_total *= (1 - item.discount)
        subtotal += item_total
        line_items.append({
            "name": item.name,
            "quantity": item.quantity,
            "unit_price": item.price,
            "discount": item.discount or 0,
            "total": item_total,
        })

    # Section 3: Calculate taxes
    tax_rate = 0
    if customer.country == "US":
        if customer.state in ["CA", "NY", "TX"]:
            tax_rate = 0.08
        else:
            tax_rate = 0.05
    elif customer.country == "CA":
        tax_rate = 0.13
    elif customer.country in ["UK", "DE", "FR"]:
        tax_rate = 0.20

    tax_amount = subtotal * tax_rate

    # Section 4: Calculate shipping
    shipping = 0
    total_weight = sum(item.weight * item.quantity for item in order.items)
    if customer.country == "US":
        if total_weight < 1:
            shipping = 5.99
        elif total_weight < 5:
            shipping = 9.99
        else:
            shipping = 14.99
    else:
        shipping = 19.99

    if subtotal > 100:
        shipping = 0  # Free shipping over $100

    # Section 5: Build invoice
    grand_total = subtotal + tax_amount + shipping

    invoice = {
        "invoice_number": f"INV-{order.id}",
        "date": datetime.now().isoformat(),
        "customer": {
            "name": customer.name,
            "email": customer.email,
            "address": customer.address,
        },
        "line_items": line_items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "shipping": shipping,
        "grand_total": grand_total,
    }

    return invoice
```

### After: Extracted Methods

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class LineItem:
    """Invoice line item."""
    name: str
    quantity: int
    unit_price: float
    discount: float
    total: float

@dataclass
class Invoice:
    """Generated invoice."""
    invoice_number: str
    date: str
    customer_name: str
    customer_email: str
    customer_address: str
    line_items: list[LineItem]
    subtotal: float
    tax_rate: float
    tax_amount: float
    shipping: float
    grand_total: float

class InvoiceGenerator:
    """Generates invoices for orders."""

    # Tax rates by region
    US_STATE_TAX_RATES = {"CA": 0.08, "NY": 0.08, "TX": 0.08}
    US_DEFAULT_TAX_RATE = 0.05
    COUNTRY_TAX_RATES = {"CA": 0.13, "UK": 0.20, "DE": 0.20, "FR": 0.20}

    # Shipping rates
    US_SHIPPING_TIERS = [(1, 5.99), (5, 9.99), (float("inf"), 14.99)]
    INTERNATIONAL_SHIPPING = 19.99
    FREE_SHIPPING_THRESHOLD = 100

    def generate(self, order, customer) -> Invoice:
        """Generate invoice for an order.

        Args:
            order: Order to generate invoice for.
            customer: Customer placing the order.

        Returns:
            Generated invoice.

        Raises:
            ValueError: If order or customer is invalid.
        """
        self._validate(order, customer)

        line_items = self._calculate_line_items(order.items)
        subtotal = sum(item.total for item in line_items)

        tax_rate = self._get_tax_rate(customer)
        tax_amount = subtotal * tax_rate

        shipping = self._calculate_shipping(order.items, customer, subtotal)

        grand_total = subtotal + tax_amount + shipping

        return Invoice(
            invoice_number=f"INV-{order.id}",
            date=datetime.now().isoformat(),
            customer_name=customer.name,
            customer_email=customer.email,
            customer_address=customer.address,
            line_items=line_items,
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            shipping=shipping,
            grand_total=grand_total,
        )

    def _validate(self, order, customer) -> None:
        """Validate order and customer."""
        if not order:
            raise ValueError("Order is required")
        if not customer:
            raise ValueError("Customer is required")
        if not order.items:
            raise ValueError("Order must have items")
        if order.status != "confirmed":
            raise ValueError("Order must be confirmed")

    def _calculate_line_items(self, items) -> list[LineItem]:
        """Calculate line items with totals."""
        return [self._calculate_line_item(item) for item in items]

    def _calculate_line_item(self, item) -> LineItem:
        """Calculate single line item."""
        total = item.price * item.quantity
        discount = item.discount or 0

        if discount:
            total *= (1 - discount)

        return LineItem(
            name=item.name,
            quantity=item.quantity,
            unit_price=item.price,
            discount=discount,
            total=total,
        )

    def _get_tax_rate(self, customer) -> float:
        """Get tax rate for customer location."""
        if customer.country == "US":
            return self.US_STATE_TAX_RATES.get(
                customer.state,
                self.US_DEFAULT_TAX_RATE,
            )

        return self.COUNTRY_TAX_RATES.get(customer.country, 0)

    def _calculate_shipping(self, items, customer, subtotal: float) -> float:
        """Calculate shipping cost."""
        if subtotal >= self.FREE_SHIPPING_THRESHOLD:
            return 0

        total_weight = sum(item.weight * item.quantity for item in items)

        if customer.country == "US":
            return self._get_us_shipping(total_weight)

        return self.INTERNATIONAL_SHIPPING

    def _get_us_shipping(self, weight: float) -> float:
        """Get US shipping rate by weight."""
        for max_weight, rate in self.US_SHIPPING_TIERS:
            if weight < max_weight:
                return rate

        return self.US_SHIPPING_TIERS[-1][1]
```

**Benefits**:
- Each method has single responsibility
- Easy to understand at a glance
- Individual methods are testable
- Constants are named and configurable
- Data structures are explicit

---

## 4. Complex Boolean Logic Simplification

### Before: Complex Boolean Expressions

```python
def can_access_resource(user, resource, context):
    """Check if user can access resource - complex version."""
    # Check if user is valid and active
    if user is not None and user.is_active and not user.is_banned:
        # Check if resource is public or user is owner
        if resource.is_public or resource.owner_id == user.id:
            return True
        # Check if user has explicit permission
        elif user.role == "admin" or user.role == "superuser":
            return True
        elif resource.id in user.accessible_resources:
            return True
        # Check team access
        elif user.team_id is not None and resource.team_id is not None:
            if user.team_id == resource.team_id:
                if resource.team_access == "read" or resource.team_access == "write":
                    return True
        # Check time-based access
        elif resource.access_window is not None:
            if context.current_time >= resource.access_window.start:
                if context.current_time <= resource.access_window.end:
                    if user.id in resource.access_window.allowed_users:
                        return True

    return False
```

### After: Decomposed with Named Conditions

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class AccessContext:
    """Context for access check."""
    current_time: datetime

class AccessChecker:
    """Checks resource access permissions."""

    def can_access(self, user, resource, context: AccessContext) -> bool:
        """Check if user can access resource.

        Args:
            user: User requesting access.
            resource: Resource being accessed.
            context: Access context (time, etc.).

        Returns:
            True if access is allowed.
        """
        if not self._is_valid_user(user):
            return False

        return (
            self._is_public_access(resource)
            or self._is_owner(user, resource)
            or self._is_privileged_user(user)
            or self._has_explicit_permission(user, resource)
            or self._has_team_access(user, resource)
            or self._has_time_window_access(user, resource, context)
        )

    def _is_valid_user(self, user) -> bool:
        """Check if user is valid and active."""
        return (
            user is not None
            and user.is_active
            and not user.is_banned
        )

    def _is_public_access(self, resource) -> bool:
        """Check if resource is publicly accessible."""
        return resource.is_public

    def _is_owner(self, user, resource) -> bool:
        """Check if user owns the resource."""
        return resource.owner_id == user.id

    def _is_privileged_user(self, user) -> bool:
        """Check if user has privileged role."""
        return user.role in {"admin", "superuser"}

    def _has_explicit_permission(self, user, resource) -> bool:
        """Check if user has explicit access permission."""
        return resource.id in user.accessible_resources

    def _has_team_access(self, user, resource) -> bool:
        """Check if user has team-based access."""
        if user.team_id is None or resource.team_id is None:
            return False

        if user.team_id != resource.team_id:
            return False

        return resource.team_access in {"read", "write"}

    def _has_time_window_access(
        self,
        user,
        resource,
        context: AccessContext,
    ) -> bool:
        """Check if user has time-window access."""
        window = resource.access_window

        if window is None:
            return False

        is_within_window = (
            context.current_time >= window.start
            and context.current_time <= window.end
        )

        return is_within_window and user.id in window.allowed_users
```

**Benefits**:
- Each condition is named and self-documenting
- Easy to test individual access rules
- New access rules can be added easily
- Main logic reads like documentation

---

## 5. Switch/Case Refactoring with Polymorphism

### Before: Type-Based Switch

```python
def calculate_area(shape):
    """Calculate area of shape - switch version."""
    shape_type = shape.get("type")

    if shape_type == "circle":
        return 3.14159 * shape["radius"] ** 2

    elif shape_type == "rectangle":
        return shape["width"] * shape["height"]

    elif shape_type == "triangle":
        return 0.5 * shape["base"] * shape["height"]

    elif shape_type == "trapezoid":
        return 0.5 * (shape["top"] + shape["bottom"]) * shape["height"]

    elif shape_type == "ellipse":
        return 3.14159 * shape["major_axis"] * shape["minor_axis"]

    else:
        raise ValueError(f"Unknown shape type: {shape_type}")
```

### After: Polymorphism

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import pi

class Shape(ABC):
    """Abstract base class for shapes."""

    @abstractmethod
    def area(self) -> float:
        """Calculate the area of the shape."""
        pass

    @abstractmethod
    def perimeter(self) -> float:
        """Calculate the perimeter of the shape."""
        pass

@dataclass
class Circle(Shape):
    """A circle shape."""
    radius: float

    def area(self) -> float:
        return pi * self.radius ** 2

    def perimeter(self) -> float:
        return 2 * pi * self.radius

@dataclass
class Rectangle(Shape):
    """A rectangle shape."""
    width: float
    height: float

    def area(self) -> float:
        return self.width * self.height

    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

@dataclass
class Triangle(Shape):
    """A triangle shape."""
    base: float
    height: float
    side_a: float = 0
    side_b: float = 0

    def area(self) -> float:
        return 0.5 * self.base * self.height

    def perimeter(self) -> float:
        return self.base + self.side_a + self.side_b

@dataclass
class Trapezoid(Shape):
    """A trapezoid shape."""
    top: float
    bottom: float
    height: float
    side_left: float = 0
    side_right: float = 0

    def area(self) -> float:
        return 0.5 * (self.top + self.bottom) * self.height

    def perimeter(self) -> float:
        return self.top + self.bottom + self.side_left + self.side_right

@dataclass
class Ellipse(Shape):
    """An ellipse shape."""
    major_axis: float
    minor_axis: float

    def area(self) -> float:
        return pi * self.major_axis * self.minor_axis

    def perimeter(self) -> float:
        # Approximation using Ramanujan's formula
        a, b = self.major_axis, self.minor_axis
        h = ((a - b) ** 2) / ((a + b) ** 2)
        return pi * (a + b) * (1 + (3 * h) / (10 + (4 - 3 * h) ** 0.5))

# Factory for creating shapes from dictionaries
class ShapeFactory:
    """Factory for creating shape instances."""

    _creators = {
        "circle": lambda d: Circle(radius=d["radius"]),
        "rectangle": lambda d: Rectangle(width=d["width"], height=d["height"]),
        "triangle": lambda d: Triangle(
            base=d["base"],
            height=d["height"],
            side_a=d.get("side_a", 0),
            side_b=d.get("side_b", 0),
        ),
        "trapezoid": lambda d: Trapezoid(
            top=d["top"],
            bottom=d["bottom"],
            height=d["height"],
        ),
        "ellipse": lambda d: Ellipse(
            major_axis=d["major_axis"],
            minor_axis=d["minor_axis"],
        ),
    }

    @classmethod
    def create(cls, shape_dict: dict) -> Shape:
        """Create a shape from a dictionary.

        Args:
            shape_dict: Dictionary with 'type' and shape parameters.

        Returns:
            Shape instance.

        Raises:
            ValueError: If shape type is unknown.
        """
        shape_type = shape_dict.get("type")
        creator = cls._creators.get(shape_type)

        if creator is None:
            raise ValueError(f"Unknown shape type: {shape_type}")

        return creator(shape_dict)

# Usage
def calculate_total_area(shapes: list[dict]) -> float:
    """Calculate total area of all shapes."""
    return sum(ShapeFactory.create(s).area() for s in shapes)
```

**Benefits**:
- Each shape is self-contained
- Adding new shapes doesn't modify existing code
- Each shape can have its own validation
- Type hints work properly
- Easy to test individual shapes
