# WorldEnergyData Scheduler Safe Probe Results — 2026-04-26

Mode: no-op/dry-run/endpoint probes only. No full refreshes.

Note: uv baseline probe is included because earlier safe-probe attempts timed out while invoking uv run; bounded probes below use the existing local virtualenv when possible.

## uv baseline probe
```
[exit_code=124]
```

## A.1 Scheduler module usage
```
[TIMEOUT after 30s]
```

## A.1 refresh_bsee_all help
```
[TIMEOUT after 30s]
```

## A.1 ALL_JOBS
```
[TIMEOUT after 30s]
```

## A.2 Scheduler status
```
[TIMEOUT after 30s]
```

## A.3 Config validation
```
[TIMEOUT after 30s]
```

## A.4 BSEE refresh dry-run
```
[TIMEOUT after 60s]
```

## A.5 BSEE HEAD probes
```
https://www.data.bsee.gov/Platform/Files/PlatStrucRawData.zip 200 1715648
https://www.data.bsee.gov/Pipeline/Files/PipePermRawData.zip 200 9486725
https://www.data.bsee.gov/Platform/Files/PermStrucRawData.zip 200 28122
https://www.data.bsee.gov/Pipeline/Files/PipeLocAllRawData.zip 200 28124

[exit_code=0]
```

## A.5 SODIR factmaps bounded GET
```
400 646 bytes text/html; charset=utf-8

[exit_code=0]
```

## A.5 EIA v2 root
```
403 application/json 163

[exit_code=0]
```

## A.5 Open-Meteo Marine single coord
```
200 834

[exit_code=0]
```

## A.5 GIE ALSI HEAD
```
200 https://alsi.gie.eu/api

[exit_code=0]
```
