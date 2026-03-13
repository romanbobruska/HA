{% set plan = state_attr('sensor.fve_plan_data', 'plan') %}
{% set last_update = state_attr('sensor.fve_plan_data', 'last_update') %}
{% set current_mode = state_attr('sensor.fve_plan_data', 'current_mode') %}
{% set blokace = state_attr('sensor.fve_plan_data', 'blokace_text') %}

{% set mode_icons = {
  'normal': '🟢',
  'setrit': '🟡',
  'nabijet_ze_site': '🔵',
  'prodavat': '🔴',
  'prodavat_misto_nabijeni': '⚪',
  'zakaz_pretoku': '🟣'
} %}

{% set mode_names = {
  'normal': 'Normální',
  'setrit': 'Šetřit',
  'nabijet_ze_site': 'Nabíjet',
  'prodavat': 'Prodávat',
  'prodavat_misto_nabijeni': 'Prodej přebytku',
  'zakaz_pretoku': 'Zákaz přetoků'
} %}

<b>Aktuální mód:</b> {{ mode_icons[current_mode] | default('⚫') }} {{ mode_names[current_mode] | default(current_mode) }} | <b>Blokace vybíjení baterie:</b> {{ blokace | default('NE') }}

<b>Aktualizováno:</b> {% if last_update %}{{ as_timestamp(last_update) | timestamp_custom('%d.%m.%Y %H:%M:%S') }}{% else %}N/A{% endif %} | {% set fs = state_attr('sensor.fve_plan_data', 'filtrace_status') %}{% if fs %}<b>Bazén:</b> {% if fs.met %}✅ OK ({{ fs.run }}/{{ fs.minReq }} min){% else %}❌ -{{ fs.remaining }} min{% endif %}{% endif %}

{% if plan and plan | length > 0 %}
<table>
<tr><th>Hodina</th><th>Mód</th><th>Důvod</th><th>Level</th><th>Cena nákup</th><th>Cena prodej</th></tr>
{% for item in plan %}
<tr>
<td>{{ '%02d' | format(item.hour) }}:00{% if item.isNextDay %} +1{% endif %}</td>
<td>{{ mode_icons[item.mode] | default('⚫') }} {{ mode_names[item.mode] | default(item.mode) }}</td>
<td>{{ item.reason }}</td>
<td>{{ item.priceLevel }}</td>
<td>{{ '%.2f' | format(item.priceBuy) }} Kč</td>
<td>{{ '%.2f' | format(item.priceSell) }} Kč</td>
</tr>
{% endfor %}
</table>
{% else %}
Plán není k dispozici
{% endif %}
