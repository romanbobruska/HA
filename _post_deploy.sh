#!/bin/sh
echo "=== A) Lovelace na disku - ktere senzory ma aktualne Grid tile? ==="
sudo grep -E '"consumption":|"production":' /homeassistant/.storage/lovelace.lovelace | head -20
echo ""
echo "=== B) Timestamp posledni zapisu lovelace ==="
sudo stat /homeassistant/.storage/lovelace.lovelace | grep -E "Modify|Size"
echo ""
echo "=== C) Template sensory po HA restart - existuji vsechny? ==="
for e in fve_net_odber_ze_site fve_net_dodavka_do_site fve_celkovy_odber_ze_site fve_celkovy_prodej_do_site; do
  v=$(curl -s -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyYzg3OGM0MGM4MzU0MzI1OGZiZDcxODFhM2ZlZTQyZiIsImlhdCI6MTc3MTg4NzE0MywiZXhwIjoyMDg3MjQ3MTQzfQ.y2NTKxC9b67IlReCS6e-S2TVNCiv1mc1-RGSFUcnwuc" http://localhost:8123/api/states/sensor.$e | python3 -c 'import sys,json
try: d=json.load(sys.stdin); print(d.get("state"))
except: print("NOT_FOUND")' 2>/dev/null)
  printf "  sensor.%-35s = %s\n" "$e" "$v"
done
echo ""
echo "=== D) HA log - posledni chyby template ==="
sudo tail -200 /homeassistant/home-assistant.log 2>/dev/null | grep -iE "error|template|grid_loads" | tail -15 || echo "  log nedostupny nebo zadne chyby"
