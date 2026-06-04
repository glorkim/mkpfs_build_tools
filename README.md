# MkPFS Build Tool v1.16

**Created by: Xenogear**

A tool that compresses and unpacks PS5 game image files.  
Drag a folder or file to process it automatically.  
Compression reduces file size by approximately **40~60%**.

> Based on [MkPFS 0.0.5](https://github.com/PSBrew/MkPFS) by PSBrew.

---

## Table of Contents

1. [Using on PS5](#1-using-on-ps5)
2. [How to Use](#2-how-to-use)
3. [Supported Formats](#3-supported-formats)
4. [Folder Compression Details](#4-folder-compression-details)
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
  0:  Set output folder   :  D:\output
  1:  Temp work folder    :  D:\work_tmp
  3:  Unpack folder       :  (auto - file location)
  99: Reset temp folder

  Drag and drop a folder or file, then press Enter:
  =>
```

| Input | Function |
|-------|----------|
| `0`   | Change output folder |
| `1`   | Change temp work folder |
| `3`   | Change unpack folder |
| `99`  | Reset temp work folder setting |

Settings are saved automatically to `mkpfs_config.json`.

### Method 2 — Drag directly onto the exe

Drag your game folder or file onto the `mkpfs_builds.exe` icon.  
The window opens and conversion starts immediately.

---

## 3. Supported Formats

| Input | Output |
|-------|--------|
| Game folder (e.g. `PPSA04610-app\`) | `[Temp folder]` TITLEID-Title (Ver)**.pfs**<br>`[Output folder]` TITLEID-Title (Ver)**.ffpfsc** |
| `.pfs` (folder image) | `[Output folder]` same name**.ffpfsc** |
| `.exfat` | `[Output folder]` same name**.ffpfsc** |
| `.ffpkg` | `[Output folder]` same name**.ffpfsc** |
| `.ffpfs` | `[Unpack folder]` {name}-extracted\ |
| `.ffpfsc` | `[Unpack folder]` {name}-extracted\ |

---

## 4. Folder Compression Details

Dragging a folder triggers a two-step process.

### Step 1: Create uncompressed nested PFS image

```
Input:  PPSA04610-app\
Output: [Temp folder] PPSA04610-Elden Ring (01.10).pfs
```

The filename is generated automatically from `sce_sys\param.json`.

| param.json field | Example |
|---|---|
| `titleId` | `PPSA04610` |
| `en-US.titleName` | `Elden Ring` |
| `applicationVersion` | `01.10` |

> Falls back to the folder name if `param.json` is not found.

### Step 2: Pack into compressed PFS container

```
Input:  [Temp folder]   PPSA04610-Elden Ring (01.10).pfs
Output: [Output folder] PPSA04610-Elden Ring (01.10).ffpfsc
```

### Output name preview

After dragging a folder and pressing Enter, the output filename is shown before the compression level selection.

```
  Output name : PPSA04610-Elden Ring (01.10)
```

### Reusing the .pfs file

The `.pfs` file is kept in the temp work folder after completion.  
Drag it again to run **Step 2 only** and recreate the `.ffpfsc`.

```
Input:  PPSA04610-Elden Ring (01.10).pfs
Output: PPSA04610-Elden Ring (01.10).ffpfsc
```

### PFS file check on startup

If `.pfs` files exist in the temp work folder at startup, they are listed.

```
  PFS file(s) found in temp work folder.: D:\work_tmp

  PPSA04610-Elden Ring (01.10).pfs  (45.2 GB)

  Delete? [Enter: keep / y: delete]:
```

> When clearing leftover files, `.pfs` files are always preserved.

---

## 5. Conversion Examples

**Folder compression**
```
Input:  D:\PS5\PPSA04610-app\
Temp:   D:\work_tmp\PPSA04610-Elden Ring (01.10).pfs
Output: D:\output\PPSA04610-Elden Ring (01.10).ffpfsc
```

**File compression (.exfat / .ffpkg)**
```
Input:  D:\PS5\PPSA04610.exfat
Output: D:\output\PPSA04610.ffpfsc
```

**Re-compress .pfs**
```
Input:  D:\work_tmp\PPSA04610-Elden Ring (01.10).pfs
Output: D:\output\PPSA04610-Elden Ring (01.10).ffpfsc
```

**Unpack**
```
Input:  D:\output\PPSA04610-Elden Ring (01.10).ffpfsc
Output: D:\output\PPSA04610-Elden Ring (01.10)-extracted\
```

---

## 6. Temp Work Folder

The temp work folder is used for Step 1 `.pfs` creation and mkpfs internals.

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

**Q. I'm getting an error.**  
A. Try running the program as Administrator.

**Q. It says the temp work folder has insufficient space.**  
A. Enter `1` from the menu to switch the temp folder to a drive with more free space.  
Folder compression needs free space equal to the input folder size.

**Q. Can I delete the .pfs file after folder compression?**  
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

### v1.16 (current)
- Drive root selection blocked for all folder pickers (output / temp / unpack)
- Temp work folder cleanup default changed: `Enter`=keep, `y`=clear
- Temp work folder must be empty when selected (error shown if not empty)

### v1.15
- Two-step folder compression
  - Step 1: Create uncompressed nested PFS image (`.pfs`)
  - Step 2: Pack into compressed PFS container (`.ffpfsc`)
- Auto filename generation from `sce_sys\param.json` (`TITLEID-EnglishTitle (Version)`)
- `.pfs` file drag support (runs Step 2 only)
- Output filename preview before compression level selection
- Auto disk space check against temp work folder before compression
- Startup notification for existing `.pfs` files in temp work folder
- `.pfs` files preserved when clearing temp work folder
- `ESC` key support at all input prompts
- Added `--no-adjust-output-file-extension` for explicit file extensions

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
