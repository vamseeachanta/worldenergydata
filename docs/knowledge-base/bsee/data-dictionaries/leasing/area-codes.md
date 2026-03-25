# OCS Area/Protraction Codes

> **Usage**: Identifies geographic areas within OCS regions
> **Scope**: All federal Outer Continental Shelf planning areas

---

## Gulf of America Areas

### Western Planning Area

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| AC | Alaminos Canyon | 5,000-10,000 | Deepwater |
| BM | Brazos | 50-200 | Shelf |
| EB | East Breaks | 500-3,000 | Slope |
| GA | Galveston | 50-500 | Shelf |
| GB | Garden Banks | 500-5,000 | Slope to deepwater |
| GI | Galveston Island | 50-200 | Shelf |
| HI | High Island | 50-500 | Shelf to slope |
| KW | Keathley Canyon | 5,000-10,000 | Ultra-deepwater |
| MA | Matagorda | 50-200 | Shelf |
| MU | Mustang Island | 50-200 | Shelf |
| PI | Port Isabel | 500-2,000 | Slope |
| SA | Sabine Pass | 50-200 | Shelf |
| WC | West Cameron | 50-500 | Shelf |

### Central Planning Area

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| AT | Atwater Valley | 4,000-8,000 | Deepwater |
| DC | DeSoto Canyon | 500-3,000 | Slope |
| EC | East Cameron | 50-500 | Shelf |
| EI | Eugene Island | 50-500 | Shelf |
| EW | Ewing Bank | 500-3,000 | Slope |
| GC | Green Canyon | 1,500-8,000 | Deepwater; major production |
| LL | Lund | 3,000-7,000 | Deepwater |
| MC | Mississippi Canyon | 1,000-8,000 | Major deepwater hub |
| MP | Main Pass | 50-500 | Shelf |
| SM | South Marsh Island | 50-200 | Shelf |
| SS | Ship Shoal | 50-200 | Shelf |
| ST | South Timbalier | 50-500 | Shelf |
| SP | South Pelto | 50-200 | Shelf |
| VK | Viosca Knoll | 500-3,000 | Slope |
| VR | Vermilion | 50-500 | Shelf |
| WD | Walker Ridge | 5,000-10,000 | Ultra-deepwater |
| WR | West Delta | 50-500 | Shelf |

### Eastern Planning Area

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| DD | Destin Dome | 100-500 | Limited activity |
| PN | Pensacola | 100-500 | Limited activity |
| LU | Lloyd Ridge | 3,000-8,000 | Deepwater |
| PE | Perdido | 8,000-10,000 | Ultra-deepwater |
| FG | Florida Gateway | 500-2,000 | Limited |
| HN | Henderson | 500-2,000 | Limited |

---

## Alaska Areas

### Beaufort Sea

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| BF | Beaufort Sea | 50-500 | Arctic; ice conditions |
| HB | Harrison Bay | 50-200 | Shallow; state/federal boundary |
| CA | Camden Bay | 50-300 | Seasonal operations |
| FK | Flaxman Island | 50-200 | Shallow |

### Chukchi Sea

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| CH | Chukchi Sea | 100-300 | Arctic; limited season |
| BG | Burger | 100-200 | Major prospect area |
| HS | Hanna Shoal | 100-200 | Environmental sensitivity |

### Cook Inlet

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| CI | Cook Inlet | 50-300 | Mature production area |
| LT | Lower Cook Inlet | 100-400 | Active leasing |
| UK | Upper Cook Inlet | 50-200 | State/federal interface |

### Other Alaska

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| NO | Norton Sound | 50-200 | Limited exploration |
| SG | St. George | 200-500 | Bering Sea |
| NA | Navarin | 300-1,000 | Bering Sea |
| AL | Aleutian | 500-2,000 | Limited |

---

## Pacific Areas

### Southern California

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| SC | Santa Cruz | 500-2,000 | Active platforms |
| SM | Santa Maria | 200-1,500 | Active production |
| SB | Santa Barbara | 100-1,000 | Historical development |
| SR | Santa Rosa | 200-1,000 | Established leases |
| SN | San Nicolas | 500-2,000 | Limited activity |
| SC | San Clemente | 1,000-3,000 | Limited |
| PT | Point Arguello | 200-1,000 | Active production |

### Central California

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| CC | Central California | 500-2,500 | Limited exploration |
| SL | Sur | 1,000-3,000 | Limited |

### Northern California

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| NC | Northern California | 200-1,500 | Limited |
| BH | Bodega Head | 200-1,000 | No current activity |
| EB | Eel River | 500-2,000 | Historical only |

### Washington/Oregon

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| WA | Washington | 500-2,000 | No current leasing |
| OR | Oregon | 500-2,000 | No current leasing |

---

## Atlantic Areas

### North Atlantic

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| NA | North Atlantic | 200-3,000 | No active leases |
| GB | Georges Bank | 200-1,000 | Historical exploration |

### Mid-Atlantic

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| MA | Mid-Atlantic | 200-2,500 | No active leases |
| BA | Baltimore Canyon | 500-2,500 | Historical exploration |

### South Atlantic

| Code | Area Name | Typical Depth (ft) | Notes |
|------|-----------|-------------------|-------|
| SA | South Atlantic | 200-3,000 | No active leases |
| BL | Blake Plateau | 2,000-5,000 | No activity |

---

## Area Code Usage

### In Lease Numbers
Area codes combine with block numbers:
```
Lease Location: MC 252 (Mississippi Canyon Block 252)
Full Reference: G33203 / MC / 252 / Gulf of America
```

### In Well API Numbers
Area codes encoded in API numbers via lease reference.

### Query String Format
```
?BottomArea=MC
?BottomArea=GC
?Area=Mississippi%20Canyon
```

---

## Water Depth Categories

| Category | Depth Range (ft) | Typical Areas |
|----------|------------------|---------------|
| Shelf | 0-600 | SM, SS, EI, VR |
| Slope | 600-4,000 | VK, GB, EB |
| Deepwater | 4,000-7,500 | GC, MC, AT |
| Ultra-deepwater | >7,500 | WR, KC, AC |

---

## Related Documents

- [Lease Fields](lease-fields.md) - Lease data dictionary
- [Block Numbering](block-numbering.md) - Block system explained
- [Region Codes](../common/region-codes.md) - Region definitions
- [Gulf of America](../../regions/gulf-of-america.md) - Regional overview
