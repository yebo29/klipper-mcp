# Input Shaper Calibration Guide - StealthChanger Multi-Tool

> **Purpose**: Step-by-step guide for calibrating input shaper for each toolhead on a Voron 2.4 StealthChanger setup.

## Overview

With StealthChanger, each toolhead has different mass and resonance characteristics. For optimal print quality, you should calibrate input shaper **separately for each tool** and store unique values in their respective config files.

## Prerequisites

- ADXL345 accelerometer mounted and configured
- Printer homed and heated to typical printing temperature (resonance can change with temp)
- All tools docked

## Toolhead Configuration Files

| Tool | Config File | Color |
| ------ | ------------ | ------- |
| T0 | `~/printer_data/config/Toolheads/T0.cfg` | Red |
| T1 | `~/printer_data/config/Toolheads/T1.cfg` | Orange |
| T2 | `~/printer_data/config/Toolheads/T2.cfg` | White |

Each file contains these input shaper parameters:

```ini
params_input_shaper_freq_x: 62.2
params_input_shaper_freq_y: 44.0
params_input_shaper_type_x: mzv
params_input_shaper_type_y: mzv
```

## Calibration Procedure

### Step 1: Prepare the Printer

```gcode
; Home and heat
G28
M104 S200  ; Heat nozzle (optional but recommended)
M140 S60   ; Heat bed (optional)
```

### Step 2: Calibrate T0 (Red)

```gcode
; Select T0
T0

; Run calibration (runs both X and Y axes)
SHAPER_CALIBRATE
```

Wait for the calibration to complete. This takes 2-5 minutes per axis.

**Read the results from the console output:**

```text
Recommended shaper is mzv @ 62.4 Hz
Recommended shaper is mzv @ 88.6 Hz
```

**Save to T0.cfg:**

```ini
[tool T0]
params_input_shaper_freq_x: 62.4    ; Your X result
params_input_shaper_freq_y: 88.6    ; Your Y result
params_input_shaper_type_x: mzv     ; Recommended type for X
params_input_shaper_type_y: mzv     ; Recommended type for Y
```

### Step 3: Calibrate T1 (Orange)

```gcode
; Switch to T1
T1

; Run calibration
SHAPER_CALIBRATE
```

Record the results and update `T1.cfg` with the unique values.

### Step 4: Calibrate T2 (White)

```gcode
; Switch to T2
T2

; Run calibration
SHAPER_CALIBRATE
```

Record the results and update `T2.cfg` with the unique values.

### Step 5: Save Configuration

After updating all config files:

```gcode
RESTART
```

Or from Mainsail/Fluidd, use the "Save & Restart" button.

## Verifying Per-Tool Shaper Application

The `toolchanger.cfg` automatically applies the correct shaper settings when switching tools via the `after_change_gcode`:

```jinja2
{% if tool.params_input_shaper_freq_x %}
  {% set shaper_type_x = tool.params_input_shaper_type_x|default("mzv") %}
  {% set shaper_type_y = tool.params_input_shaper_type_y|default("mzv") %}
  SET_INPUT_SHAPER SHAPER_FREQ_X={tool.params_input_shaper_freq_x} SHAPER_FREQ_Y={tool.params_input_shaper_freq_y} SHAPER_TYPE_X={shaper_type_x} SHAPER_TYPE_Y={shaper_type_y}
{% endif %}
```

**To verify active shaper settings:**

```gcode
; Check current input shaper status
GET_INPUT_SHAPER
```

Or use the MCP server endpoint:

```text
http://192.168.2.87:8000/shaper.html
```

## Troubleshooting

### "Accelerometer not found"

- Check ADXL345 wiring
- Verify `[adxl345]` section in printer.cfg
- Run `ACCELEROMETER_QUERY` to test connection

### "Could not home" during calibration

- Ensure the printer is homed (`G28`) before running `SHAPER_CALIBRATE`
- Check that the correct tool is active

### Very different values between tools

This is **normal**! Different toolheads have different masses and will resonate at different frequencies. Typical differences:

- 5-15 Hz variation between tools is common
- Different shaper types (mzv vs ei) may be recommended for different tools

### Ringing still visible after calibration

- Try running calibration with the bed and nozzle at printing temperature
- Consider using a more aggressive shaper type (e.g., `ei` instead of `mzv`)
- Check for mechanical issues (loose belts, wobble in toolhead mount)

## Shaper Types Reference

| Type | Vibration Reduction | Smoothing | Best For |
| ------ | --------------------- | ----------- | ---------- |
| `zv` | Minimal | Lowest | Very stiff frames |
| `mzv` | Good | Low | Most printers (default) |
| `zvd` | Better | Medium | Moderate ringing |
| `ei` | Very Good | Higher | Significant ringing |
| `2hump_ei` | Maximum | Highest | Severe ringing issues |

## Quick Reference Commands

| Command | Description |
| --------- | ------------- |
| `SHAPER_CALIBRATE` | Full calibration (both axes) |
| `SHAPER_CALIBRATE AXIS=X` | Calibrate X axis only |
| `SHAPER_CALIBRATE AXIS=Y` | Calibrate Y axis only |
| `GET_INPUT_SHAPER` | Show current shaper settings |
| `SET_INPUT_SHAPER SHAPER_FREQ_X=60` | Manually set X frequency |
| `SET_INPUT_SHAPER SHAPER_TYPE_X=ei` | Manually set X shaper type |

## Expected Calibration Results

For a typical Voron 2.4 with StealthChanger:

| Tool | Freq X (Hz) | Freq Y (Hz) | Notes |
| ------ | ------------- | ------------- | ------- |
| T0 | 55-70 | 40-55 | Lightest tool typically highest freq |
| T1 | 50-65 | 38-52 | Varies with hotend weight |
| T2 | 50-65 | 38-52 | Similar to T1 if same hotend |

*Your values will vary based on toolhead mass, belt tension, and frame stiffness.*

---

**Last Updated**: January 2026  
**Applies To**: Voron 2.4 350mm with StealthChanger (T0, T1, T2)
