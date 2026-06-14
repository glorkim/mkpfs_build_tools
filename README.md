# MkPFS Build Tool — GUI Guide v1.38

**Created by: Xenogear**

![GUI](gui_screen.png)

A Windows GUI for converting PS5 game dumps into compressed `.ffpfsc` containers —
with built-in `param.json` / icon editing and AMPR index generation.

Everything is drag-and-drop. No file extraction to disk is required, and the tool
uses all CPU cores during compression.

> Based on [MkPFS 0.0.8](https://github.com/PSBrew/MkPFS) by PSBrew.

---

## Table of Contents

1. [Launch & Drag-and-Drop](#1-launch--drag-and-drop)
2. [Tabs Overview](#2-tabs-overview)
3. [Build Tab](#3-build-tab)
4. [AMPR Index Tab](#4-ampr-index-tab)
5. [param.json Edit Tab](#5-paramjson-edit-tab)
6. [Unpack Tab](#6-unpack-tab)
7. [Folder Settings Tab](#7-folder-settings-tab)
8. [Supported Formats](#8-supported-formats)
9. [Using on PS5](#9-using-on-ps5)
10. [FAQ](#10-faq)

---

## 1. Launch & Drag-and-Drop

1. Double-click **`mkpfs_gui.exe`**.
2. Drop a game folder or file onto the tab's drop zone (or click to browse).
3. Press the action button on that tab.

> **Do not run as Administrator.** Windows blocks drag-and-drop for elevated apps.

---

## 2. Tabs Overview

| Tab | Purpose |
|-----|---------|
| **Build** | Folder / archive / image → compressed `.ffpfsc` (with a build queue) |
| **AMPR Index** | Generate `ampr_emu.index` |
| **param.json Edit** | Edit titleId / titleName / userDefinedParam + replace icon |
| **Unpack** | Extract an image back to a folder |
| **Folder Settings** | Output / temp / unpack folders, language |

---

## 3. Build Tab

Drop a **game folder**, **archive** (`.rar` `.zip` `.7z` `.zip.001` `.7z.001`),
or an existing image (`pfs_image.dat` `.exfat` `.ffpkg` `.ffpfsc`), then
**+ Add to queue** and **Build**.

- Folder / archive → `pfs_image.dat` → `<title>.ffpfsc` (two-step, no disk extraction).
- `pfs_image.dat` / `.exfat` / `.ffpkg` → compressed to `.ffpfsc` as-is.

**Options**

| Control | Effect |
|---------|--------|
| Compression level / CPU | Passed to the packer |
| **Edit param.json** (checkbox) | Inline editor for titleId / titleName / userDefinedParam + icon box; applied at build time |
| **Inject AMPR index** (checkbox) | Generates and injects `ampr_emu.index` during the build |

Icon replacement: drop an image onto the icon box. It is letterboxed to 512×512
and converted to BC7 DDS; both `icon0.png` and `icon0.dds` are replaced.

---

## 4. AMPR Index Tab

Drop a **folder** or **archive** to generate `/app0/ampr_emu.index` used by the
AMPR/fakelib file resolver.

| Input | Behavior |
|-------|----------|
| Folder | `ampr_emu.index` created **inside the folder** |
| Archive | `ampr_emu.index` created **next to the archive** |

---

## 5. param.json Edit Tab

Drop a **game folder**, **`pfs_image.dat`**, or **`.exfat`** to edit `titleId`,
`titleName` (localized entry), and `userDefinedParam*`, and to replace the icon.

- **Edit fields** → **Save changes** writes back in place.
- **Replace icon**: drop an image onto the icon box (applied on Save changes).

| Target | param.json | Icon |
|--------|-----------|------|
| Game folder | direct file write | full-resolution overwrite |
| `pfs_image.dat` | in-place patch | in-place |
| `.exfat` | in-place patch | in-place |

> Signed images cannot be patched and are reported as such.

---

## 6. Unpack Tab

Drop **`.ffpfsc` / `.ffpfs` / `pfs_image.dat` / `.exfat`** to extract it to a folder.

| Input | Extractor |
|-------|-----------|
| `.ffpfsc` / `.ffpfs` / `pfs_image.dat` | mkpfs (PFS) |
| `.exfat` | built-in exFAT parser |

---

## 7. Folder Settings Tab

| Setting | Description |
|---------|-------------|
| Output folder | Where `.ffpfsc` is written |
| Temp work folder | Used for `pfs_image.dat` creation (must be empty) |
| Unpack folder | Default extraction location |
| Language | Korean / English |
| Compression level / CPU | Defaults for the build |

Settings are saved to `mkpfs_config.json`.

---

## 8. Supported Formats

| Extension | Filesystem | Notes |
|-----------|-----------|-------|
| `pfs_image.dat` | PFS (uncompressed) | Sony PlayStation File System |
| `.ffpfsc` / `.ffpfs` | PFS (compressed) | Final build output |
| `.exfat` | exFAT | Raw PS5 dump image |
| `.ffpkg` | UFS2 | Compressed to `.ffpfsc` as input |

---

## 9. Using on PS5

You need the latest **ShadowMountPlus** to mount converted files.

> Download: [https://github.com/drakmor/ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus)

1. Copy the converted `.ffpfsc` to the ShadowMountPlus scan path.
2. Run the ShadowMountPlus payload to mount automatically.

---

## 10. FAQ

**Q. Drag-and-drop doesn't work.**
A. Don't run as Administrator — Windows disables drag-and-drop for elevated apps.

**Q. The game is not recognized on PS5.**
A. Make sure the latest ShadowMountPlus payload is running and the `.ffpfsc` is in
its scan path.

**Q. It says the temp work folder has insufficient space.**
A. Switch the temp folder to a drive with more free space in Folder Settings.

**Q. Why is solid 7z slow?**
A. Solid archives can't be parallelized. Extract first and drop the folder.
