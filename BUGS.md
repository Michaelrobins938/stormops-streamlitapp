# StormOps Bug Tracker & Hardening Log

| ID | Issue | Repro Steps | Expected vs Actual | Severity | Status |
|:---|:---|:---|:---|:---|:---|
| P0-1 | CRM 404 Error | Run smoke_test.py | Expected successful push; Got 404 (endpoint mismatch) | P0 | Mocked |
| P1-1 | Map data missing | Start app without pipeline | Should show clear "No Storm Data" state; UI feels broken | P1 | Fixed |
| P1-2 | Step logic mismatch | Click "Add to routes" | Should gate by MISSION_THRESHOLDS; needs tighter validation | P1 | Open |
| P2-1 | Copilot UI alignment | Open Copilot panel | Text overlaps or is too long for mobile view | P2 | Open |
