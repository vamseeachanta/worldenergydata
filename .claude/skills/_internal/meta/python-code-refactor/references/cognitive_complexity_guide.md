# Cognitive Complexity Guide

> Understanding and reducing the mental effort required to understand code.

---

## What is Cognitive Complexity?

**Cognitive Complexity** measures how difficult code is to **understand**, not just how many paths exist through it. It was developed by SonarSource as an improvement over Cyclomatic Complexity.

### Key Insight

```python
# Same cyclomatic complexity (2), different cognitive complexity

# Low cognitive complexity - easy to understand
def is_eligible(user):
    return user.age >= 18 and user.is_verified

# Higher cognitive complexity - harder to follow
def is_eligible(user):
    if user.age >= 18:
        if user.is_verified:
            return True
        else:
            return False
    else:
        return False
```

---

## Cognitive vs Cyclomatic Complexity

| Aspect | Cyclomatic Complexity | Cognitive Complexity |
|--------|----------------------|---------------------|
| **Measures** | Number of execution paths | Mental effort to understand |
| **Focus** | Testing difficulty | Reading difficulty |
| **Nesting** | Not penalized | Heavily penalized |
| **Early returns** | Increases count | Does not increase |
| **Boolean logic** | Each condition counts | Sequences count once |
| **Best for** | Test coverage planning | Code readability |

### Example Comparison

```python
# Cyclomatic: 4 (4 decision points)
# Cognitive: 7 (nested structure)
def complex_nested(a, b, c, d):
    if a:                    # +1 CC, +1 Cog
        if b:                # +1 CC, +2 Cog (nesting penalty)
            if c:            # +1 CC, +3 Cog (deeper nesting)
                return d
    return None

# Cyclomatic: 4 (same paths)
# Cognitive: 4 (linear structure)
def simple_guards(a, b, c, d):
    if not a:               # +1 CC, +1 Cog
        return None
    if not b:               # +1 CC, +1 Cog
        return None
    if not c:               # +1 CC, +1 Cog
        return None
    return d                # +1 CC, +1 Cog
```

---

## How Cognitive Complexity is Calculated

### Basic Increments (+1)

The following structures add **+1** to complexity:

| Structure | Increment |
|-----------|-----------|
| `if`, `elif`, `else` | +1 each |
| `for`, `while` | +1 each |
| `try`, `except`, `finally` | +1 each |
| `and`, `or` in conditions | +1 for each sequence |
| Recursion | +1 |
| `break`, `continue` | +1 |
| Nested functions/lambdas | +1 |

### Nesting Penalty

**Each level of nesting adds an additional penalty to structures inside it.**

```python
def calculate_total(orders):      # Level 0
    total = 0
    for order in orders:          # +1 (for) at level 0
        if order.is_valid:        # +2 (if + 1 nesting) at level 1
            for item in order:    # +3 (for + 2 nesting) at level 2
                if item.in_stock: # +4 (if + 3 nesting) at level 3
                    total += item.price
    return total

# Total Cognitive Complexity: 1 + 2 + 3 + 4 = 10
```

### Nesting Level Calculation

```
Nesting Level = Number of enclosing structures

Level 0: Top-level function body
Level 1: Inside first if/for/while/try
Level 2: Inside nested if/for/while/try
Level 3: Inside doubly nested structure
...
```

### Increment Formula

```
Increment = Base Increment (1) + Current Nesting Level
```

---

## Detailed Calculation Example

```python
def process_order(order):                          # Function start
    if order is None:                              # +1 (if, level 0)
        return None

    results = []
    for item in order.items:                       # +1 (for, level 0)
        if item.quantity > 0:                      # +2 (if + 1 nesting)
            if item.in_stock:                      # +3 (if + 2 nesting)
                price = item.price * item.quantity
                if item.discount:                  # +4 (if + 3 nesting)
                    price *= (1 - item.discount)
                results.append(price)
            else:                                  # +1 (else, no nesting penalty)
                log_out_of_stock(item)

    return sum(results) if results else 0          # +1 (ternary)

# Total: 1 + 1 + 2 + 3 + 4 + 1 + 1 = 13
```

---

## Nesting Penalty Explanation

### Why Nesting is Penalized

Nested structures require keeping multiple contexts in mind:

```python
# Each level requires tracking:
# - Which condition brought us here
# - What values we're working with
# - How to exit properly

if user:                          # Track: user exists
    if user.is_active:            # Track: user + is_active
        if user.has_permission:   # Track: user + is_active + has_permission
            if resource.available: # Track: user + is_active + has_permission + resource
                do_action()       # 4 conditions to remember!
```

### The "Christmas Tree" Problem

```python
# High cognitive load - "Christmas tree" shape
def bad_example(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return "success"
                    else:
                        return "e failed"
                else:
                    return "d failed"
            else:
                return "c failed"
        else:
            return "b failed"
    else:
        return "a failed"
```

---

## Complexity Targets

### Recommended Thresholds

| Level | Cognitive Complexity | Action |
|-------|---------------------|--------|
| **Good** | 1-10 | Acceptable |
| **Acceptable** | 11-15 | Consider refactoring |
| **Warning** | 16-20 | Should refactor |
| **Critical** | 21+ | Must refactor |

### Per-Function Guidelines

```python
# Target: < 15 per function
# Warning: > 20 per function
# Maximum: 25 (hard limit, should never exceed)
```

---

## Reduction Strategies

### 1. Guard Clauses (Flatten Nesting)

```python
# BEFORE: CC = 10 (nested)
def process(data):
    if data is not None:
        if data.is_valid:
            if len(data.items) > 0:
                return calculate(data)
    return None

# AFTER: CC = 3 (flat)
def process(data):
    if data is None:
        return None
    if not data.is_valid:
        return None
    if len(data.items) == 0:
        return None
    return calculate(data)
```

### 2. Extract Method

```python
# BEFORE: CC = 12 (complex function)
def generate_report(data):
    # Validation (CC: 4)
    if not data:
        raise ValueError("No data")
    for item in data:
        if not item.get("value"):
            raise ValueError("Missing value")

    # Processing (CC: 5)
    results = []
    for item in data:
        if item["type"] == "A":
            results.append(item["value"] * 2)
        elif item["type"] == "B":
            results.append(item["value"] * 3)

    # Formatting (CC: 3)
    output = []
    for result in results:
        if result > 100:
            output.append(f"HIGH: {result}")
        else:
            output.append(f"NORMAL: {result}")

    return output

# AFTER: Each function CC < 5
def generate_report(data):
    validate_data(data)
    results = process_items(data)
    return format_results(results)

def validate_data(data):
    if not data:
        raise ValueError("No data")
    for item in data:
        if not item.get("value"):
            raise ValueError("Missing value")

def process_items(data):
    return [process_single(item) for item in data]

def process_single(item):
    multipliers = {"A": 2, "B": 3}
    return item["value"] * multipliers.get(item["type"], 1)

def format_results(results):
    return [format_single(r) for r in results]

def format_single(result):
    prefix = "HIGH" if result > 100 else "NORMAL"
    return f"{prefix}: {result}"
```

### 3. Dictionary Dispatch

```python
# BEFORE: CC = 8 (if/elif chain)
def get_discount(customer_type):
    if customer_type == "regular":
        return 0.0
    elif customer_type == "silver":
        return 0.05
    elif customer_type == "gold":
        return 0.10
    elif customer_type == "platinum":
        return 0.15
    elif customer_type == "diamond":
        return 0.20
    elif customer_type == "vip":
        return 0.25
    else:
        return 0.0

# AFTER: CC = 1 (dictionary lookup)
DISCOUNT_RATES = {
    "regular": 0.0,
    "silver": 0.05,
    "gold": 0.10,
    "platinum": 0.15,
    "diamond": 0.20,
    "vip": 0.25,
}

def get_discount(customer_type):
    return DISCOUNT_RATES.get(customer_type, 0.0)
```

### 4. Polymorphism

```python
# BEFORE: CC = 6 (type checking)
def calculate_area(shape):
    if shape["type"] == "circle":
        return 3.14159 * shape["radius"] ** 2
    elif shape["type"] == "rectangle":
        return shape["width"] * shape["height"]
    elif shape["type"] == "triangle":
        return 0.5 * shape["base"] * shape["height"]
    else:
        raise ValueError(f"Unknown shape: {shape['type']}")

# AFTER: CC = 1 per class
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        pass

class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius

    def area(self) -> float:
        return 3.14159 * self.radius ** 2

class Rectangle(Shape):
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height
```

### 5. Boolean Expression Simplification

```python
# BEFORE: CC = 4 (complex boolean)
def is_eligible(user, product):
    if user.age >= 18:
        if user.is_verified:
            if product.in_stock:
                if not user.is_banned:
                    return True
    return False

# AFTER: CC = 1 (combined expression)
def is_eligible(user, product):
    return (
        user.age >= 18
        and user.is_verified
        and product.in_stock
        and not user.is_banned
    )
```

---

## Measuring Cognitive Complexity

### Using Ruff

```bash
# Check cognitive complexity with ruff
uv run ruff check --select C901 src/

# Set threshold in pyproject.toml
[tool.ruff.lint.mccabe]
max-complexity = 15
```

### Using Flake8

```bash
# Using flake8 with cognitive-complexity plugin
pip install flake8-cognitive-complexity
flake8 --max-cognitive-complexity=15 src/
```

### Using radon

```bash
# Install and run radon
pip install radon
radon cc src/ -a -s  # Cyclomatic complexity
```

---

## Quick Reference

```
+1 for each:
  - if, elif, else
  - for, while
  - try, except, finally
  - and, or (per sequence)
  - recursion
  - break, continue

+ Nesting Level for:
  - Every structure inside another structure

Targets:
  - < 15: Acceptable
  - > 20: Refactor required
```
