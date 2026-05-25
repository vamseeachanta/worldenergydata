# worldenergydata CLI Smoke Verification

- Date: 2026-05-11
- Issue: #352
- Scope: bounded-safe and fixture-only commands only
- Excluded: network scrapes, refresh/download commands, credentialed commands, and server starts

| Command | Safety | Exit | Status |
|---|---:|---:|---|
| `worldenergydata --help` | bounded-safe | 0 | pass |
| `worldenergydata version` | bounded-safe | 0 | pass |
| `worldenergydata info` | bounded-safe | 0 | pass |
| `worldenergydata status` | bounded-safe | 0 | pass |
| `worldenergydata bsee --help` | bounded-safe | 0 | pass |
| `worldenergydata dashboard --help` | bounded-safe | 0 | pass |
| `worldenergydata eia --help` | bounded-safe | 0 | pass |
| `worldenergydata marine-safety --help` | bounded-safe | 0 | pass |
| `worldenergydata fdas --help` | bounded-safe | 0 | pass |
| `worldenergydata lower-tertiary --help` | bounded-safe | 0 | pass |
| `worldenergydata forecast --help` | bounded-safe | 0 | pass |
| `worldenergydata sodir --help` | bounded-safe | 0 | pass |
| `worldenergydata metocean --help` | bounded-safe | 0 | pass |
| `worldenergydata ndbc --help` | bounded-safe | 0 | pass |
| `worldenergydata texas-rrc --help` | bounded-safe | 0 | pass |
| `worldenergydata canada --help` | bounded-safe | 0 | pass |
| `worldenergydata mexico-cnh --help` | bounded-safe | 0 | pass |
| `worldenergydata landman --help` | bounded-safe | 0 | pass |
| `worldenergydata lng-terminals --help` | bounded-safe | 0 | pass |
| `worldenergydata safety-analysis --help` | bounded-safe | 0 | pass |
| `worldenergydata fdas calculate-npv --cashflows [-1000,100,200,300] --discount-rate 0.10` | fixture-only | 0 | pass |
| `worldenergydata fdas calculate-all --cashflows [-5000,1000,1500,2000]` | fixture-only | 0 | pass |
| `worldenergydata fdas classify 5000` | fixture-only | 0 | pass |
| `worldenergydata marine-safety db init --dev-mode --dry-run` | bounded-safe | 0 | pass |
