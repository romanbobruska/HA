# Debug instrukce pro FVE plán

Prosím, pošli mi **celý plán** (všech 12 hodin) včetně debug informací.

## Kde najít plán

1. V Home Assistant: `/homeassistant/fve_plan.json`
2. Nebo v Node-RED: Debug panel → "Plan Debug" node

## Co potřebuji

Celý JSON výstup z plánovače, zejména:
- `plan` (všech 12 hodin s offsety, levely, módy)
- `proteus` (firstChargingOffset, peakDischargeHoursCount, expensiveHoursCount)
- `smartCharging` (targetSocFromGrid, hoursNeeded, assignedHours)
- `status` (soc, remainingSolar, forecastZitra)

## Příklad

```json
{
  "currentMode": "normal",
  "currentHour": 16,
  "plan": [
    {"hour": 16, "offset": 0, "mode": "normal", "levelBuy": 21, ...},
    {"hour": 17, "offset": 1, "mode": "normal", "levelBuy": 19, ...},
    ...
  ],
  "proteus": {
    "firstChargingOffset": 12,
    "expensiveHoursCount": 8,
    ...
  },
  "status": {
    "soc": 59,
    ...
  }
}
```

S těmito daty zjistím, proč level 12 a 13 nejsou označené jako expensive.
