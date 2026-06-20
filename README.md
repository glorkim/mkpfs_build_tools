# MkPFS Build Tool — GUI Guide v1.40

**Created by: Xenogear**

![GUI](gui_screen.png)

A Windows GUI for converting PS5 game dumps into mountable images and compressed
`.ffpfsc` containers — with built-in `param.json` / icon editing and AMPR index generation.

Everything is drag-and-drop. No file extraction to disk is required for the
PFS/exFAT build paths, and the tool uses all CPU cores during compression.

---

## Table of Contents

1. [Launch & Drag-and-Drop](#1-launch--drag-and-drop)
2. [Tabs Overview](#2-tabs-overview)
3. [Build Tab](#3-build-tab)
4. [exFAT / ffpkg Create Tab](#4-exfat--ffpkg-create-tab)
5. [AMPR Index Tab](#5-ampr-index-tab)
6. [param.json Edit Tab](#6-paramjson-edit-tab)
7. [File Info / Unpack Tab](#7-file-info--unpack-tab)
8. [Folder Settings Tab](#8-folder-settings-tab)
9. [Image Formats & Filesystems](#9-image-formats--filesystems)
10. [External Tools & Permissions (UAC)](#10-external-tools--permissions-uac)
11. [Using on PS5](#11-using-on-ps5)
12. [FAQ](#12-faq)

---

## 1. Launch & Drag-and-Drop

1. Double-click **`mkpfs_gui.exe`**.
2. Drop a game folder or file onto the tab's drop zone. **Clicking** a drop zone
   pops a small chooser so you can pick either a **file** or a **folder**.
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
| **File Info / Unpack** | Inspect an image (editable info, compression stats), rename it, or extract it to a folder |
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
| **Image format** (radio) | Intermediate image for **folder / archive** input: **PFS** / **exFAT** / **ffpkg (folder only)**. Defaults to **exFAT**. |
| **Edit param.json** (checkbox) | Shows an inline editor + icon box (right column); applied at build time |
| **Include extra files/folders** (checkbox) | Shows an extra-files box (right column, below the param editor); the dropped files/folders are added into the built image |
| **Inject AMPR index** (checkbox) | Regenerates and injects `ampr_emu.index` during the build — **also includes the extra files/folders** |

**Include extra files/folders**

When checked, a box appears in the right column (below the param.json editor)
with a one-line drop zone and a list. Drop or pick (click → file/folder chooser)
any files and folders to add into the image:

- Files go to the image root keeping their name (`update.pkg → /update.pkg`).
- Folders keep their structure (`patch → /patch/...`).
- Captured **per queue item** when you press **+ Add to queue**.
- Supported input: **folder, rar / 7z / zip** (already-built `pfs_image.dat` /
  `.exfat` / `.ffpkg` inputs are compressed as-is — extras are not injected).
- The box title has an **AMPR index regenerate** checkbox that is synced with the
  **Inject AMPR index** option (toggling either toggles both). With it on, the
  AMPR index is regenerated to include the extra files/folders too.

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

## 7. File Info / Unpack Tab

Drop **`.ffpfsc` / `.ffpfs` / `pfs_image.dat` / `.exfat` / `.ffpkg`** to inspect,
rename, or extract it.

**Info panel (shown on drop)**

- **File Info** — the input file name. For a **`.ffpfsc`** it changes to
  **Container Info** and shows the wrapped image member name (`pfs_image.dat` /
  `*.exfat` / `*.ffpkg`), plus a compression sub-panel: **original size /
  compressed size / ratio % / FLEVEL (level range)** — read straight from the
  PFSC metadata without unpacking.
- **Title ID / Version** are shown as editable boxes; **Title Name** is a
  combobox listing every localized title (the local-language entry is selected
  by default). `userDefinedParam*` are listed in two columns. The current icon
  is previewed on the right.

**Rename file** (yellow button) — builds a name from the on-screen info using the
tool's `TITLEID-Title (vVersion)` rule and renames the dropped file on disk
(keeping its extension). Edits you make in the info boxes are reflected in the
new name. Names are kept within the length the PS5 loader accepts (measured in
**UTF-8 bytes**, so Korean/Japanese titles count more) by trimming only the end
of the title — the title ID, version, level suffix, and extension are preserved.

**Unpack** — extracts to a folder.

| Input | Extractor |
|-------|-----------|
| `.ffpfsc` / `.ffpfs` / `pfs_image.dat` | mkpfs (PFS) |
| `.exfat` | built-in exFAT parser |
| `.ffpkg` | built-in UFS2 parser (no UFS2Tool / no admin needed) |

The output folder name follows the `TITLEID-Title (Version)` rule when
`param.json` is readable. Before extracting a `.ffpfsc`, free space on the
destination drive is checked against the size it will unpack to, and you are
warned if it may not fit.

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

**Q. A long game name got cut off in the output file name.**
A. Very long names aren't recognized by the PS5 loader, so the output / rename
name is capped (measured in UTF-8 bytes). Only the end of the title is trimmed —
the title ID, version, compression level, and extension are always kept.
