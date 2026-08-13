# Optional automations

These depend on sensors and helpers that only exist in *your* house, so they
are not in the package. Copy what you like into your own `automations.yaml` and
swap the entity ids. All of them write to `input_select.vmc_speed` rather than
to Modbus directly, so the state of the selector always reflects what was asked
for, and they all check the `input_boolean.vmc_auto` master switch.

## Cooking boost

Induction-hob vibration sensor or kitchen humidity → boost, back to nominal
when things calm down. `mode: restart` means it extends itself while you cook.

```yaml
- id: vmc_cooking_boost
  alias: "VMC: boost while cooking"
  mode: restart
  triggers:
    - trigger: state
      entity_id: binary_sensor.kitchen_hob_vibration
      to: "on"
      for: { minutes: 1 }
    - trigger: numeric_state
      entity_id: sensor.kitchen_humidity
      above: 68
      for: { minutes: 3 }
  conditions:
    - condition: state
      entity_id: input_boolean.vmc_auto
      state: "on"
  actions:
    - action: input_select.select_option
      target: { entity_id: input_select.vmc_speed }
      data: { option: Boost }
    - wait_for_trigger:
        - trigger: template
          value_template: >
            {{ is_state('binary_sensor.kitchen_hob_vibration','off')
               and (states('sensor.kitchen_humidity') | float(0) < 62) }}
          for: { minutes: 15 }
      timeout: { minutes: 90 }
      continue_on_timeout: true
    - condition: state
      entity_id: input_boolean.vmc_auto
      state: "on"
    - action: input_select.select_option
      target: { entity_id: input_select.vmc_speed }
      data: { option: Nominal }
```

Calibrate the humidity threshold by watching your own sensor while cooking —
68 % works in a kitchen that idles around 55 %.

## Away / holidays

```yaml
- id: vmc_away
  alias: "VMC: minimum when nobody is home"
  triggers:
    - trigger: state
      entity_id: input_boolean.house_occupied
      to: "off"
      for: { minutes: 30 }
      id: away
    - trigger: state
      entity_id: input_boolean.house_occupied
      to: "on"
      id: back
  conditions:
    - condition: state
      entity_id: input_boolean.vmc_auto
      state: "on"
  actions:
    - choose:
        - conditions: [{ condition: trigger, id: away }]
          sequence:
            - action: input_select.select_option
              target: { entity_id: input_select.vmc_speed }
              data: { option: Away }
        - conditions: [{ condition: trigger, id: back }]
          sequence:
            - action: input_select.select_option
              target: { entity_id: input_select.vmc_speed }
              data: { option: Nominal }
```

## Summer night free-cooling

The one that actually saves money in a hot climate: at night the outside air is
cooler than the inside, so open the bypass (no heat recovery) and run high to
flush the house with it. Needs an `input_boolean.summer_mode` and an
`input_boolean.vmc_freecooling` flag to avoid re-triggering.

```yaml
- id: vmc_freecooling_start
  alias: "VMC: night free-cooling"
  triggers:
    - trigger: time_pattern
      minutes: "/15"
  conditions:
    - condition: state
      entity_id: input_boolean.vmc_auto
      state: "on"
    - condition: state
      entity_id: input_boolean.summer_mode
      state: "on"
    - condition: state
      entity_id: input_boolean.vmc_freecooling
      state: "off"
    - condition: time
      after: "22:00:00"
      before: "08:00:00"
    - condition: numeric_state
      entity_id: sensor.vmc_indoor_temperature
      above: 24
    - condition: template
      alias: Outside at least 2 K cooler
      value_template: >
        {{ (states('sensor.vmc_indoor_temperature') | float(99))
           - (states('sensor.vmc_outdoor_temperature') | float(0)) >= 2 }}
  actions:
    - action: input_boolean.turn_on
      target: { entity_id: input_boolean.vmc_freecooling }
    - action: input_select.select_option
      target: { entity_id: input_select.vmc_bypass }
      data: { option: Open }
    - action: input_select.select_option
      target: { entity_id: input_select.vmc_speed }
      data: { option: High }

- id: vmc_freecooling_stop
  alias: "VMC: end night free-cooling"
  triggers:
    - trigger: time_pattern
      minutes: "/15"
    - trigger: time
      at: "08:00:00"
  conditions:
    - condition: state
      entity_id: input_boolean.vmc_freecooling
      state: "on"
    - condition: or
      conditions:
        - condition: time
          after: "08:00:00"
          before: "22:00:00"
        - condition: numeric_state
          entity_id: sensor.vmc_indoor_temperature
          below: 23
        - condition: template
          value_template: >
            {{ (states('sensor.vmc_indoor_temperature') | float(0))
               - (states('sensor.vmc_outdoor_temperature') | float(99)) < 0.5 }}
  actions:
    - action: input_boolean.turn_off
      target: { entity_id: input_boolean.vmc_freecooling }
    - action: input_select.select_option
      target: { entity_id: input_select.vmc_bypass }
      data: { option: Auto }
    - action: input_select.select_option
      target: { entity_id: input_select.vmc_speed }
      data: { option: Nominal }
```

**Bypass ownership.** If Home Assistant drives free-cooling, leave the bypass
selector at `Closed` at rest rather than `Auto`, otherwise the unit's own logic
fights your automation. Switch back to `Auto` when you go away for a long time
or if HA is down.

## Quiet night

```yaml
- id: vmc_quiet_night
  alias: "VMC: quiet at night"
  triggers:
    - trigger: state
      entity_id: input_boolean.sleep_mode
      to: "on"
  conditions:
    - condition: state
      entity_id: input_boolean.vmc_auto
      state: "on"
    - condition: state
      entity_id: input_boolean.vmc_freecooling
      state: "off"
  actions:
    - action: input_select.select_option
      target: { entity_id: input_select.vmc_speed }
      data: { option: Low }
```

## Stop on smoke

Don't distribute smoke around the house.

```yaml
- id: vmc_stop_on_smoke
  alias: "VMC: stop on smoke"
  triggers:
    - trigger: state
      entity_id: binary_sensor.kitchen_smoke
      to: "on"
  actions:
    - action: input_select.select_option
      target: { entity_id: input_select.vmc_speed }
      data: { option: "Off" }
```

No `vmc_auto` condition here on purpose: safety should not depend on a switch.
