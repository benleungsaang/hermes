# ODA File Converter Installation

## Download

Open Design Alliance provides a free ODAFileConverter for Linux (AppImage, ~82MB).

```bash
# Direct from ODA (URL may change — verify at opendesign.com)
mkdir -p ~/Apps
cd ~/Apps
wget -O ODAFileConverter.AppImage \
  "https://www.opendesign.com/guestfiles/ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage"
chmod a+x ODAFileConverter.AppImage
```

Versioned filenames: `ODAFileConverter_QT5_lnxX64_8.3dll_23.9.AppImage` (older), `ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage` (newer, requires Ubuntu 20.04+). Pick the one matching your system — older Ubuntu may need the QT5 build.

## FUSE dependency

AppImage requires FUSE to run. On Ubuntu 24.04 the package is `libfuse2t64` (renamed from `libfuse2` due to the t64 transition):

```bash
sudo apt install -y libfuse2t64
# Older Ubuntu: sudo apt install -y libfuse2
```

If you can't install FUSE (e.g. restricted environment), you can extract the AppImage and run the binary directly:

```bash
cd ~/Apps && ./ODAFileConverter.AppImage --appimage-extract
# Then point ezdxf at: ~/Apps/squashfs-root/AppRun
```

## Configure ezdxf to find ODA

In `~/.hermes/config.yaml` (NOT a Hermes-managed section — the `ezdxf` key is for the ezdxf library's own config, not Hermes' own config):

```yaml
ezdxf:
  odafc:
    unix_exec_path: /home/ubuntu/Apps/ODAFileConverter.AppImage
```

Or set it via environment variable (also supported by ezdxf):
```bash
export ODAFC_EXEC=/home/ubuntu/Apps/ODAFileConverter.AppImage
```

## Verify

```bash
~/Apps/ODAFileConverter.AppImage --help
# Should print usage info. If it complains about FUSE, re-install libfuse2t64.
```

```python
import ezdxf
doc = ezdxf.odafc.readfile("test.dwg")
print(f"OK: {len(list(doc.modelspace().query()))} entities")
```

## Common failure modes

| Error | Cause | Fix |
|---|---|---|
| `AppImage needs FUSE` | libfuse2(t64) missing | `sudo apt install -y libfuse2t64` |
| `cannot open display` | No X server / DISPLAY unset | Wrap with `xvfb-run -a` |
| `ODAFC conversion failed` | Wrong AppImage path or version | Check `ezdxf.odafc.unix_exec_path`, try older QT5 build |
| `Unsupported DWG version` | DWG newer than ODA supports | Update ODA, or save DWG in older AutoCAD version first |
