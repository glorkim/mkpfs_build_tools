# MkPFS Build Tool — GUI Guide v1.38

**Created by: Xenogear**

![GUI](gui_screen.png)

A Windows GUI for converting PS5 game dumps into mountable images and compressed
`.ffpfsc` containers — with built-in `param.json` / icon editing and AMPR index generation.

Everything is drag-and-drop. No file extraction to disk is required for the
PFS/exFAT build paths, and the tool uses all CPU cores during compression.

> Based on [MkPFS 0.0.8](https://github.com/PSBrew/MkPFS) by PSBrew.

---

## Table of Contents

1. [Launch & Drag-and-Drop](#1-launch--drag-and-drop)
2. [Tabs Overview](#2-tabs-overview)
3. [Build Tab](#3-build-tab)
4. [exFAT / ffpkg Create Tab](#4-exfat--ffpkg-create-tab)
5. [AMPR Index Tab](#5-ampr-index-tab)
6. [param.json Edit Tab](#6-paramjson-edit-tab)
7. [Unpack Tab](#7-unpack-tab)
8. [Folder Settings Tab](#8-folder-settings-tab)
9. [Image Formats & Filesystems](#9-image-formats--filesystems)
10. [External Tools & Permissions (UAC)](#10-external-tools--permissions-uac)
11. [Using on PS5](#11-using-on-ps5)
12. [FAQ](#12-faq)

---

## 1. Launch & Drag-and-Drop

1. Double-click **`mkpfs_gui.exe`**.
2. Drop a game folder or file onto the tab's drop zone (or click to browse).
3. Press the action button on that tab.

> **Do not run as Administrator.** Windows blocks drag-and-drop for elevated
> apps. Run it normally; the tool requests elevation only for the specific
> operations that need it (see [section 10](#10-external-tools--permissions-uac)).

---

## 2. Tabs Overview

| Tab | Purpose |
|-----|---------|
| **Build** | Folder / archive / image → compressed `.ffpfsc` (with a build queue) |
| **exFAT / ffpkg Create** | Folder / archive → `.exfat` or `.ffpkg` image |
| **AMPR Index** | Generate / inject `ampr_emu.index` |
| **param.json Edit** | Edit titleId / titleName / userDefinedParam + replace icon |
| **Unpack** | Extract an image back to a folder |
| **Folder Settings** | Output / temp / unpack folders, tool paths, language |

---

## 3. Build Tab

Drop a **game folder**, **archive** (`.rar` `.zip` `.7z` `.zip.001` `.7z.001`),
or an existing image (`pfs_image.dat` `.exfat` `.ffpkg` `.ffpfsc`), then
**+ Add to queue** and **Build**.

**Options**

| Control | Effect |
|---------|--------|
| Compression level / CPU | Passed to the packer |
| **Image format** (radio) | Intermediate image for **folder / archive** input: **PFS** / **exFAT** / **ffpkg (folder only)** |
| **Edit param.json** (checkbox) | Shows an inline editor + icon box; applied at build time |
| **Inject AMPR index** (checkbox) | Generates and injects `ampr_emu.index` during the build |

**How input type affects the format radio**

- **Folder / archive** → the radio chooses the intermediate image:
  - **PFS** → `pfs_image.dat` → `<title>_pfs_L<level>.ffpfsc`
  - **exFAT** → `.exfat` image → `<title>_exfat_L<level>.ffpfsc` (uses OSFMount)
  - **ffpkg** → UFS2 image → `<title>_ffpkg_L<level>.ffpfsc` (**folder input only**; uses UFS2Tool)
- **pfs_image.dat / .exfat / .ffpkg / .ffpfsc** → already an image, the radio is
  **ignored** and the file is compressed as-is.

> Selecting **ffpkg** with an archive (non-folder) input is blocked with a log
> message — extract the archive to a folder first.

`param.json` edits and icon replacement (when checked) are applied to the image
before packing.

---

## 4. exFAT / ffpkg Create Tab

Drop a **folder** or **archive**; the tab shows the detected game info
(titleId / titleName / version) and lets you edit `param.json` fields and the
icon before creating the image.

**Output format (radio)**

| Format | Output | Tool | Archive input |
|--------|--------|------|---------------|
| **exFAT image** | `<title>.exfat` | OSFMount | Streamed directly into the mounted volume (no temp extraction) |
| **ffpkg image (folder only)** | `<title>.ffpkg` (UFS2) | UFS2Tool | Not supported — folder input only |

- The icon (if a new image was dropped onto the icon box) and `param.json` edits
  are written into the created image.
- **exFAT**: mount → format → fill → icon → dismount, all in **one elevated
  session** with a live progress / ETA display.
- **ffpkg**: `newfs -D <folder>` creates the UFS2 image from a folder.

---

## 5. AMPR Index Tab

Drop a **folder**, **archive**, **`.exfat`**, or **`.ffpkg`** to generate the
`/app0/ampr_emu.index` used by the AMPR/fakelib file resolver. The game info is
shown on drop.

| Input | Behavior |
|-------|----------|
| Folder | `ampr_emu.index` created **inside the folder** |
| Archive | `ampr_emu.index` created **next to the archive** |
| `.exfat` | Mounted (OSFMount), index built on the volume and **injected into the image** |
| `.ffpkg` (UFS2) | File table parsed directly (no extraction); index **injected via UFS2Tool** |

---

## 6. param.json Edit Tab

Drop a **game folder**, **`pfs_image.dat`**, **`.exfat`**, or **`.ffpkg`**.
The tab loads `titleId`, `titleName` (localized entry — `ko-KR` when the UI is
Korean, otherwise the default language) and `userDefinedParam*` for editing,
and shows the current icon.

- **Edit fields** → **Save changes** writes back in place.
- **Replace icon**: drop an image onto the icon box (PNG/JPG/DDS/etc.). It is
  letterboxed to 512×512 and converted to BC7 DDS (via texconv); both
  `icon0.png` and `icon0.dds` are replaced. Applied only on **Save changes**.

| Target | param.json | Icon |
|--------|-----------|------|
| Game folder | direct file write | full-resolution overwrite |
| `pfs_image.dat` / PFS | in-place patch | in-place (auto-downscaled to fit) |
| `.exfat` | in-place patch | mounted (full resolution) |
| `.ffpkg` (UFS2) | UFS2Tool replace | UFS2Tool replace (full resolution) |

> Signed images cannot be patched and are reported as such.

---

## 7. Unpack Tab

Drop **`.ffpfsc` / `.ffpfs` / `pfs_image.dat` / `.exfat` / `.ffpkg`** to extract
it to a folder. Game info is shown on drop (when readable).

| Input | Extractor |
|-------|-----------|
| `.ffpfsc` / `.ffpfs` / `pfs_image.dat` | mkpfs (PFS) |
| `.exfat` | built-in exFAT parser |
| `.ffpkg` | built-in UFS2 parser (no UFS2Tool / no admin needed) |

The output folder name follows the `TITLEID-Title (Version)` rule when
`param.json` is readable.

---

## 8. Folder Settings Tab

| Setting | Description |
|---------|-------------|
| Output folder | Where `.ffpfsc` / `.exfat` / `.ffpkg` are written |
| Temp work folder | Used for `pfs_image.dat` creation and intermediates (must be empty) |
| Unpack folder | Default extraction location |
| **OSFMount path** | Auto-detected; **Dismount all virtual drives** button cleans up leftover mounts |
| **UFS2Tool path** | Auto-filled after first download/cache |
| Language | Korean / English |
| Compression level / CPU | Defaults for the build |

Settings are saved to `mkpfs_config.json`.

---

## 9. Image Formats & Filesystems

| Extension | Filesystem | Notes |
|-----------|-----------|-------|
| `pfs_image.dat` | **PFS** (uncompressed) | Sony PlayStation File System |
| `.ffpfsc` / `.ffpfs` | **PFS** (compressed) | Final build output |
| `.exfat` | **exFAT** | Microsoft FS; raw PS5 dump image |
| `.ffpkg` | **UFS2** | FreeBSD filesystem (Fake FPKG) |

> `.ffpkg` is always UFS2. PFS images use `pfs_image.dat` / `.ffpfsc`.

---

## 10. External Tools & Permissions (UAC)

The GUI downloads/uses helper tools on demand:

| Tool | Used for | Bundled? |
|------|----------|----------|
| 7za / UnRAR | Archive reading/extraction | Bundled |
| texconv | Icon BC7 DDS encoding | Bundled |
| **OSFMount** | exFAT image create / mount / `.exfat` AMPR | Auto-download + silent install |
| **UFS2Tool** | ffpkg (UFS2) create / param / icon / index **write** | Auto-download to `%LOCALAPPDATA%\UFS2Tool` (one time) |

**Permissions**

- Run the app **normally** (not as Administrator) so drag-and-drop works.
- **Reads** (param.json / icon preview / file listing / unpack) need **no
  elevation** — done with built-in parsers.
- **Writes** that touch a kernel driver or UFS2Tool prompt a **UAC** once per
  operation:
  - exFAT mount/format (OSFMount, kernel driver)
  - ffpkg create / param / icon / index inject (UFS2Tool)

---

## 11. Using on PS5

You need the latest **ShadowMountPlus** to mount converted files.

> Download: [https://github.com/drakmor/ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus)

1. Copy the converted file (`.ffpfsc` / `.exfat` / `.ffpkg`) to the
   ShadowMountPlus scan path.
2. Run the ShadowMountPlus payload to mount automatically.

---

## 12. FAQ

**Q. Drag-and-drop doesn't work.**
A. Don't run as Administrator — Windows disables drag-and-drop for elevated apps.

**Q. A UAC prompt appears during exFAT / ffpkg work.**
A. Expected. exFAT uses the OSFMount kernel driver and ffpkg writing uses
UFS2Tool, both of which require elevation. Reading and unpacking do not.

**Q. ffpkg creation says "folder only".**
A. UFS2Tool builds a UFS2 image from a directory tree, so archives must be
extracted to a folder first (use the Unpack tab, then drop the folder).

**Q. Leftover virtual drives after an exFAT build.**
A. Open **Folder Settings → Dismount all virtual drives**.

**Q. Why is solid 7z slow?**
A. Solid archives can't be parallelized. Extract first and drop the folder.
