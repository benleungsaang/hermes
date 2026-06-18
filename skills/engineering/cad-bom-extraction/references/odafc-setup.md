# ODA File Converter Setup (2026-06-18)

## Overview

ODA File Converter provides the bridge from proprietary DWG to open DXF format.
ezdxf 1.4.4 ships the `odafc` addon which wraps the ODAFileConverter AppImage.

## Files

- AppImage: ~/Apps/ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage (82MB)
- Download URL: https://www.opendesign.com/guestfiles/oda_file_converter
- Config: ~/.config/ezdxf/ezdxf.ini → [odafc-addon] unix_exec_path
- Python addon: /home/ubuntu/.local/lib/python3.12/site-packages/ezdxf/addons/odafc.py

## Installation steps

```bash
# 1. Install deps
sudo apt-get install -y libfuse2t64 xvfb

# 2. Place AppImage
mkdir -p ~/Apps
mv ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage ~/Apps/
chmod a+x ~/Apps/ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage

# 3. Generate default ezdxf config if not present
python3.12 -c "import ezdxf; ezdxf.options.write_home_config()"

# 4. Edit ~/.config/ezdxf/ezdxf.ini → set unix_exec_path
```

## How ezdxf calls the AppImage

From odafc.py source:
1. `_get_odafc_path()` reads `unix_exec_path` from ezdxf.ini
2. `_run_with_no_gui()` creates a dummy Xvfb display, runs AppImage with args
3. Arguments: [in_folder, out_folder, version, format, recurse, audit, filename]
4. AppImage converts file, ezdxf reads the temp result
5. On Linux, ODAFileConverter always crashes (core dumped) after success — ezdxf's `_odafc_failed()` treats `stderr == "Quit (core dumped)"` as success

## Test command

```bash
python3.12 -c "
from ezdxf.addons import odafc
doc = odafc.readfile('path/to/file.dwg')
print(f'OK: {len(doc.modelspace())} entities, version {doc.dxfversion}')
"
```

## Known failures

| Symptom | Cause | Fix |
|---|---|---|
| `dlopen(): error loading libfuse.so.2` | libfuse2 missing | `sudo apt install libfuse2t64` |
| AppImage opens GUI window | Xvfb missing | `sudo apt install xvfb` |
| `return code = 1` with no stderr | AppImage not executable | `chmod a+x AppImage` |
| `ODAFileConverter not found` | unix_exec_path wrong | Check ezdxf.ini path |
