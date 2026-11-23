# Example module knowledge pack

| Header | Value |
| --- | --- |
| Module | `example_module` |
| Owner | example-owner |
| Revision | 1 |
| Status | Draft for maintainers |

## 1. Purpose and scope

Read a generic series and report its retained records.

## 2. Inputs and outputs

Input is a synthetic series; output is a record count.

## 3. Method and references

Records are counted without changing their units. See #123.

## 4. Worked examples

Two invented records produce an expected count of two.

## 5. Detection checks

| Check | Test node ID |
| --- | --- |
| Missing input | `tests/unit/test_example.py::test_missing` |
| Empty input | `tests/unit/test_example.py::TestExample::test_empty` |

## 6. Silent-failure sweep

sweep: 2 found

| Location | Symptom | Detection |
| --- | --- | --- |
| Reader | Missing input raises | Missing input check |
| Counter | Empty input returns zero records | Empty input check |

## 7. Lessons log

Synthetic examples establish only the stated behavior.

## 8. Ownership

The maintainers arrange review before the maintainer merges.

## 9. Dependencies

Only the standard library is required.

## 10. Coverage and open items

Source accuracy remains open: issue pending (1).
