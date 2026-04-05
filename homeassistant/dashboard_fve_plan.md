{% set plan = state_attr('sensor.fve_plan_data', 'plan') %} {% set last_update = state_attr('sensor.fve_plan_data', 'last_update') %} {% set current_mode = state_attr('sensor.fve_plan_data', 'current_mode') %} {% set blokace = state_attr('sensor.fve_plan_data', 'blokace_text') %} {% set last_bal = states('input_datetime.last_pylontech_balanced') %} {% set bal_ok = states('input_boolean.pylontech_balancing_ok') %}
{# Načtení stavu sítě #} {% set grid_status = states('sensor.stav_rozvodne_site_grid_status') %}
{% set mode_icons = {
  'normal': '🟢', 'setrit': '🟡', 'nabijet_ze_site': '🔵',
  'prodavat': '🔴', 'prodavat_misto_nabijeni': '⚪', 'zakaz_pretoku': '🟣',
  'Balancování': '⚡',
  'zaporna_nakupni_cena': '💰'
} %}
{% set mode_names = {
  'normal': 'Normální', 'setrit': 'Šetřit', 'nabijet_ze_site': 'Nabíjet',
  'prodavat': 'Prodávat', 'prodavat_misto_nabijeni': 'Prodej přebytku', 'zakaz_pretoku': 'Zákaz přetoků',
  'Balancování': 'Balancování',
  'zaporna_nakupni_cena': 'Záporný nákup'
} %}
<b>Aktuální mód:</b> {{ mode_icons[current_mode] | default('⚫') }} {{ mode_names[current_mode] | default(current_mode) }} |  <b>Blokace:</b> {{ blokace | default('NE') }} |  <b>⚡ Poslední balancing:</b> {{ as_timestamp(last_bal) | timestamp_custom('%d.%m. %H:%M') if last_bal != 'unknown' else 'N/A' }} {{ '✅' if bal_ok == 'on' else '❌' if bal_ok == 'off' else '' }}
<b>Aktualizováno:</b> {% if last_update %}{{ as_timestamp(last_update) | timestamp_custom('%d.%m.%Y %H:%M:%S') }}{% else %}N/A{% endif %} |  <b>Síť:</b>  {%- if grid_status == 'Připojeno (OK)' -%} 🟢 OK {%- elif grid_status == 'Varování (Warning)' -%} 🟡 VAROVÁNÍ {%- elif grid_status == 'Výpadek (Grid Lost)' -%} 🔴 VÝPADEK {%- else -%} ⚪ NEZNÁMO ({{ grid_status }}) {%- endif -%} 
{% set fs = state_attr('sensor.fve_plan_data', 'filtrace_status') %} {% if fs %} | <b>Bazén:</b> {% if fs.met %}✅ OK ({{ fs.run }}/{{ fs.minReq }} min){% else %}❌ -{{ fs.remaining }} min{% endif %}{% endif %}
{% if plan and plan | length > 0 %} <table> <tr><th>Hodina</th><th>Mód</th><th>Důvod</th><th>Level</th><th>Cena nákup</th><th>Cena prodej</th></tr> {% for item in plan %} <tr> <td>{{ '%02d'
| format(item.hour) }}:00{% if item.isNextDay %} +1{% endif %}</td> <td>{{ mode_icons[item.mode] | default('⚫') }} {{ mode_names[item.mode] | default(item.mode) }}</td> <td>{{ item.reason }}</td> <td>{{ item.priceLevel }}</td> <td>{{ '%.2f' | format(item.priceBuy) }} Kč</td> <td>{{ '%.2f' | format(item.priceSell) }} Kč</td> </tr> {% endfor %} </table> {% else %} Plán není k dispozici {% endif %}
