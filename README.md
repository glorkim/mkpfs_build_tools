# MkPFS Build Tool v1.32

**Created by: Xenogear**

An automated build tool using MkPFS that converts PS5 game images into compressed `.ffpfsc` format.  
Drag a folder or file (`.exfat` `.ffpkg` `.rar` `.zip` `.7z` `.zip.001` `.7z.001` `pfs_image.dat` `.ffpfsc`) to process it automatically.  
Compression reduces file size by approximately **40~60%**.  
Archived games (RAR / ZIP / 7z) can be built directly — no extraction required.  
(param.json userDefinedParam can also be edited during the build process for archived games.)

> Based on [MkPFS 0.0.7](https://github.com/PSBrew/MkPFS) by PSBrew.

---

## Table of Contents

1. [Using on PS5](#1-using-on-ps5)
2. [How to Use](#2-how-to-use)
3. [Supported Formats](#3-supported-formats)
4. [Compression Details](#4-compression-details)
5. [Conversion Examples](#5-conversion-examples)
6. [Temp Work Folder](#6-temp-work-folder)
7. [Advanced Usage (CLI)](#7-advanced-usage-cli)
8. [FAQ](#8-faq)
9. [File Structure](#9-file-structure)
10. [Version History](#10-version-history)

---

## 1. Using on PS5

You need the latest version of **ShadowMountPlus** to mount converted files on your PS5.

> Download: [https://github.com/drakmor/ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus)

**Steps**
1. Copy the converted file (`.ffpfsc`) to the ShadowMountPlus scan path.
2. Run the ShadowMountPlus payload to mount automatically.

---

## 2. How to Use

### Method 1 — Run then drag

1. Double-click `mkpfs_builds.exe` to launch.
2. Drag your game folder or file into the window.
3. Press `Enter` to start conversion.
4. Press `ESC` at any prompt to cancel.

```
  --------------------------------------------------
   MkPFS - Auto Compress / Unpack
  --------------------------------------------------
   folder : PPSA04610-app\  ->  {title}/pfs_image.dat + TITLEID-Title (Ver).ffpfsc
   archive: game.part01.rar / .zip / .7z  ->  TITLEID-Title (Ver).ffpfsc
   file   : pfs_image.dat    ->  TITLEID-Title (Ver).ffpfsc
   file   : PPSA04610.exfat  ->  PPSA04610.ffpfsc
   file   : PPSA04610.ffpkg  ->  PPSA04610.ffpfsc
   unpack : PPSA04610.ffpfsc ->  PPSA04610-extracted\
          : pfs_image.dat    ->  PPSA04610-extracted\
  --------------------------------------------------
   mkpfs_builds -h : command CLI Help
  --------------------------------------------------

  0:  Set output folder   :  D:\output
  1:  Temp work folder    :  D:\work_tmp
  2:  Edit param.json (userDefinedParam) : PPSAxxxxx-app\, pfs_image.dat, .exfat
  3:  Unpack folder       :  (auto - file location)
  99: Reset temp folder

  Drag and drop a folder or file, then press Enter:
  =>
```

| Input | Function |
|-------|----------|
| `0`   | Change output folder |
| `1`   | Change temp work folder |
| `2`   | Edit userDefinedParam (game folder, pfs_image.dat, or .exfat) |
| `3`   | Change unpack folder |
| `99`  | Reset temp work folder setting |

Settings are saved automatically to `mkpfs_config.json`.

### Menu option 2 — Edit userDefinedParam

Enter `2` from the main menu to edit `userDefinedParam` fields inside a game folder, `pfs_image.dat`, or `.exfat`.

```
  Drag game folder or pfs_image.dat: [drag here]

  Reading param.json...

  ──────────────────────────────────────────────────
  titleId   : PPSA12345
  titleName : Elden Ring
  version   : 01.10
  ──────────────────────────────────────────────────

  1: userDefinedParam1 : 0
  2: userDefinedParam2 : 0
  3: userDefinedParam3 : 0
  4: userDefinedParam4 : 0

  Enter number to edit (Enter: save, ESC: cancel): 1
  1: userDefinedParam1 : MyCustomValue

  1: userDefinedParam1 : MyCustomValue
  2: userDefinedParam2 : 0
  ...

  Enter number to edit (Enter: save, ESC: cancel): [Enter]
  param.json patched successfully.
```

| Input | Behavior |
|-------|----------|
| Game folder | Reads and saves `sce_sys\param.json` directly |
| `pfs_image.dat` | Reads via PFS internal API, patches in-place |

> After editing `pfs_image.dat`, drag it again to recompress to `.ffpfsc` (Step 2 only).

---

## 3. Supported Formats

| Input | Output |
|-------|--------|
| Game folder (e.g. `PPSA04610-app\`) | `[Temp folder]` TITLEID-Title (Ver)\**pfs_image.dat**<br>`[Output folder]` TITLEID-Title (Ver)**.ffpfsc** |
| Archive (RAR / ZIP / 7z)<br>e.g. `game.part01.rar`, `game.zip`, `game.7z` | `[Temp folder]` TITLEID-Title (Ver)\**pfs_image.dat**<br>`[Output folder]` TITLEID-Title (Ver)**.ffpfsc** |
| `pfs_image.dat` | `[Output folder]` TITLEID-Title (Ver)**.ffpfsc** |
| `.exfat` | `[Output folder]` same name**.ffpfsc** |
| `.ffpkg` | `[Output folder]` same name**.ffpfsc** |
| `.ffpfsc` | `[Unpack folder]` {name}-extracted\ |
| `pfs_image.dat` (unpack) | `[Unpack folder]` {name}-extracted\ (enter `2` at prompt) |

---

## 4. Compression Details

### Folder Compression

Dragging a folder triggers a two-step process.

#### Step 1: Create uncompressed nested PFS image

```
Input:  PPSA04610-app\
Output: [Temp folder] PPSA04610-Elden Ring (01.10)\pfs_image.dat
```

The folder name is generated automatically from `sce_sys\param.json`.

| param.json field | Example |
|---|---|
| `titleId` | `PPSA04610` |
| `en-US.titleName` | `Elden Ring` |
| `applicationVersion` | `01.10` |

> Falls back to the folder name if `param.json` is not found.

#### Step 2: Pack into compressed PFS container

```
Input:  [Temp folder]   PPSA04610-Elden Ring (01.10)\pfs_image.dat
Output: [Output folder] PPSA04610-Elden Ring (01.10).ffpfsc
```

#### Output name preview

After dragging a folder and pressing Enter, the output filename is shown before the compression level selection.

```
  Output name : PPSA04610-Elden Ring (01.10)
```

#### Reusing pfs_image.dat

The `pfs_image.dat` is kept in the title folder inside the temp work folder after completion.  
Drag it again to run **Step 2 only** and recreate the `.ffpfsc`.  
The output name is determined by the parent folder name (title).

```
Input:  PPSA04610-Elden Ring (01.10)\pfs_image.dat
Output: PPSA04610-Elden Ring (01.10).ffpfsc
```

#### PFS file check on startup

If title folders (containing `pfs_image.dat`) exist in the temp work folder at startup, they are listed.

```
  PFS file(s) found in temp work folder.: D:\work_tmp

  PPSA04610-Elden Ring (01.10)/pfs_image.dat  (45.2 GB)

  Delete? [Enter: keep / y: delete]:
```

> When clearing leftover files, title folders (`pfs_image.dat`) are always preserved.

---

### Archive Compression (RAR / ZIP / 7z)

Archives follow the same two-step process as folder compression.

#### Step 1: Archive → uncompressed PFS image

```
Input:  game.part01.rar  (or game.zip / game.7z)
Output: [Temp folder] PPSA04610-Elden Ring (01.10)\pfs_image.dat
```

Archive contents are **streamed directly** into the PFS image — no disk extraction required.

> If `sce_sys/param.json` is not found inside the archive, the file is rejected as unsupported.

> **Solid archives** (common in 7z) cannot be parallelized and must be read sequentially, which makes processing significantly slower. It is recommended to extract solid archives first and drag the resulting game folder instead.

Before Step 1 begins, you choose the action to perform after it completes:

```
  --------------------------------------------------
   Select action after Step 1 (pfs_image.dat creation)
  --------------------------------------------------

  0: compress to ffpfsc
  1: edit param.json then compress to ffpfsc

  Select action (default Enter = 0, ESC → cancel): 
```

#### Step 2: Pack into compressed PFS container

Same as folder compression Step 2.

```
Input:  [Temp folder]   PPSA04610-Elden Ring (01.10)\pfs_image.dat
Output: [Output folder] PPSA04610-Elden Ring (01.10).ffpfsc
```

#### param.json edit option

If you selected `1` before Step 1, the editor opens automatically once Step 1 finishes.  
After editing, you can re-open the editor or proceed to Step 2:

```
  Enter: proceed to compress  /  n: edit param.json  /  ESC: cancel
```

---

### Edit param.json userDefinedParam

`userDefinedParam` fields can be edited for game folders, `pfs_image.dat`, and `.exfat` files.

**How to access**

| Method | Input | Behavior |
|--------|-------|----------|
| Menu option `2` from the main screen | Game folder | Reads and saves `sce_sys\param.json` directly |
| Menu option `2` from the main screen | `pfs_image.dat` | Patches PFS internal structure in-place |
| Menu option `2` from the main screen | `.exfat` | Patches exFAT filesystem param.json in-place |
| Select `1` before Step 1 (folder drag) | Game folder | Edits `sce_sys\param.json`, then proceeds to Step 1 → Step 2 |
| Select `1` before Step 1 (archive drag) | RAR / ZIP / 7z | Runs Step 1, then edits the resulting `pfs_image.dat`, then Step 2 |

**Editing process**

```
  Drag game folder or pfs_image.dat: [drag here]

  Reading param.json...

  ──────────────────────────────────────────────────
  titleId   : PPSA12345
  titleName : Elden Ring
  version   : 01.10
  ──────────────────────────────────────────────────

  1: userDefinedParam1 : 0
  2: userDefinedParam2 : 0
  3: userDefinedParam3 : 0
  4: userDefinedParam4 : 0

  Enter number to edit (Enter: save, ESC: cancel): 1
  1: userDefinedParam1 : MyCustomValue

  Enter number to edit (Enter: save, ESC: cancel): [Enter]
  param.json patched successfully.
```

**After editing via menu option 2**

| Input edited | Next step |
|---|---|
| Game folder | Drag the folder again to compress (Step 1 → Step 2) |
| `pfs_image.dat` | Drag it again to run **Step 2 only** and recreate the `.ffpfsc` |

```
Input:  PPSA04610-Elden Ring (01.10)\pfs_image.dat   ← edited
Output: PPSA04610-Elden Ring (01.10).ffpfsc
```

---

## 5. Conversion Examples

**Folder compression**
```
Input:  D:\PS5\PPSA04610-app\
Temp:   D:\work_tmp\PPSA04610-Elden Ring (01.10)\pfs_image.dat
Output: D:\output\PPSA04610-Elden Ring (01.10).ffpfsc
```

**Archive compression (RAR / ZIP / 7z)**  
Archives must contain a game folder structure (same as dragging a game folder directly).  
Split archives are supported. Drag the file listed in the table below:

| Format | Drag this file | Notes |
|--------|---------------|-------|
| RAR split | `game.part01.rar` | Remaining parts found automatically |
| ZIP split (`.zip` + `.z01`) | `game.zip` | `.zip` is the last part; `.z01`, `.z02`... are the earlier parts |
| ZIP split (`.zip.001`) | `game.zip.001` | First part |
| 7z split | `game.7z.001` | First part |

```
Input:  D:\PS5\game.part01.rar  (or game.zip / game.zip.001 / game.7z.001)
Temp:   D:\work_tmp\PPSA04610-Elden Ring (01.10)\pfs_image.dat
Output: D:\output\PPSA04610-Elden Ring (01.10).ffpfsc
```

**File compression (.exfat / .ffpkg)**
```
Input:  D:\PS5\PPSA04610.exfat
Output: D:\output\PPSA04610.ffpfsc
```

**Re-compress pfs_image.dat**
```
Input:  D:\work_tmp\PPSA04610-Elden Ring (01.10)\pfs_image.dat
Output: D:\output\PPSA04610-Elden Ring (01.10).ffpfsc
```

**Unpack**
```
Input:  D:\output\PPSA04610-Elden Ring (01.10).ffpfsc
Output: D:\output\PPSA04610-Elden Ring (01.10)-extracted\
```

---

## 6. Temp Work Folder

The temp work folder is used for Step 1 `pfs_image.dat` creation and mkpfs internals.

### Changing the folder

- Enter `1` from the main menu to change the temp work folder.
- If not set, `work_tmp` in the same drive as the exe is used automatically.
- **The selected folder must be empty.**  
  If it contains any files or folders, an error is shown and the setting is kept.

```
  [Error] Folder is not empty. Please select an empty folder.
```

### Space check

The program compares input size against free space on the temp drive.  
If there is not enough space, an error is shown and the input prompt returns.

```
  [Error] Not enough free space in the temp work folder.
  Required  : 45.2 GB
  Available : 12.8 GB  (D:\work_tmp)
```

> Folder compression requires free space equal to the input folder size.

---

## 7. Advanced Usage (CLI)

```bat
# Help
mkpfs_builds.exe -h
mkpfs_builds.exe pack --help

# Compress a folder
mkpfs_builds.exe pack folder D:\PS5\PPSA04610-app D:\PS5\PPSA04610.ffpfs

# Compress a file
mkpfs_builds.exe pack file D:\PS5\PPSA04610.exfat D:\PS5\PPSA04610.ffpfsc
mkpfs_builds.exe pack file D:\PS5\PPSA04610.ffpkg D:\PS5\PPSA04610.ffpfsc

# Set compression level (0~9, default 7)
mkpfs_builds.exe pack file --compression-level 9 input.exfat output.ffpfsc

# Verify image
mkpfs_builds.exe verify D:\PS5\PPSA04610.ffpfs

# Inspect image info
mkpfs_builds.exe inspect D:\PS5\PPSA04610.ffpfs

# View file list
mkpfs_builds.exe tree D:\PS5\PPSA04610.ffpfs

# Unpack image
mkpfs_builds.exe unpack D:\PS5\PPSA04610.ffpfs D:\PS5\output\
```

---

## 8. FAQ

**Q. Conversion is taking a long time.**  
A. Larger games take more time. All CPU cores are used, so avoid heavy tasks during conversion.

**Q. The game is not recognized on PS5.**  
A. Make sure the latest ShadowMountPlus payload is running.  
Check that the converted file is placed in the ShadowMountPlus scan path.

**Q. I can't drag files or folders into the window.**  
A. Running the program as Administrator disables drag-and-drop on Windows.  
Run it as a normal user (double-click without "Run as Administrator").

**Q. It says the temp work folder has insufficient space.**  
A. Enter `1` from the menu to switch the temp folder to a drive with more free space.  
Folder compression needs free space equal to the input folder size.

**Q. Can I delete the pfs_image.dat after folder compression?**  
A. Yes, once the `.ffpfsc` is created. However, keeping it lets you drag it again to skip Step 1 and quickly recreate the `.ffpfsc`.

---

## 9. File Structure

```
mkpfs_builds.exe      Executable
mkpfs_config.json     Settings file (auto created)
output\               Default output folder (auto created)
work_tmp\             Default temp work folder (auto created)
```

---

## 10. Version History

### v1.32 (current)
- GUI version added (`mkpfs_gui.exe`)
- Upgraded base to MkPFS 0.0.7
- `.exfat` param.json userDefinedParam in-place editing support

### v1.30
- Upgraded base to MkPFS 0.0.7 (cross-drive hard link support)
- ZIP / 7z archive drag support (`.zip`, `.zip.001`, `.7z`, `.7z.001`)
- Compression level appended to output filename (e.g. `PPSA04610-Elden Ring (01.10)_L9.ffpfsc`)
- Phase 2 status improved: shows archive format (RAR/RAR5/ZIP/7z), sequential or parallel processing
- Confirmation prompt when existing `pfs_image.dat` would be overwritten
- Elapsed time summary after completion (image / compress / total)
- Folder/archive drag: choose action after Step 1 (compress to ffpfsc / edit param.json then compress)

### v1.22
- Split RAR drag support (`.rar` → `pfs_image.dat` → `.ffpfsc`)
  - Streams RAR content directly into PFS image — no disk extraction required
  - Filename generated from `sce_sys/param.json` inside the RAR
  - Same two-step process and folder structure as game folder compression

### v1.20
- Read param.json directly from pfs_image.dat
- userDefinedParam editor added (game folder and pfs_image.dat)

### v1.17
- Temp folder structure changed to `{title}\pfs_image.dat` for ShadowMountPlus compatibility
- `pfs_image.dat` drag support (runs Step 2 only)
- Removed direct `.pfs` file compression support
- Windows console forced to UTF-8, Unicode filename encoding error prevention added

### v1.16b
- Fixed Unicode character encoding error in title names (™ ® © etc.)

### v1.16
- Drive root selection blocked for all folder pickers (output / temp / unpack)
- Temp work folder cleanup default changed: `Enter`=keep, `y`=clear
- Temp work folder must be empty when selected (error shown if not empty)

### v1.15
- Two-step folder compression
  - Step 1: Create uncompressed nested PFS image
  - Step 2: Pack into compressed PFS container (`.ffpfsc`)
- Auto filename generation from `sce_sys\param.json` (`TITLEID-EnglishTitle (Version)`)
- Output filename preview before compression level selection
- Auto disk space check against temp work folder before compression
- `ESC` key support at all input prompts

### v1.13
- Separate settings for output, temp work, and unpack folders
- Auto copy fallback for exFAT drives (hard link not supported)
- Copy progress bar display
- Settings persistence via `mkpfs_config.json`
- Compression level saved to config

### v1.04
- Added `--skip-executable-compression` option
- inode-bits 64 support

### v1.03
- Initial release
- Folder / `.exfat` / `.ffpkg` compression support
- `.ffpfs` / `.ffpfsc` unpack support
