"""mkpfs-worker CLI entry point.

Based on
    mkpfs (GPL-3.0)
    https://github.com/PSBrew/MkPFS
    Target version: 0.0.8 (run `mkpfs-worker -V` for the bundled version)

Commands
    [passthrough] pack / verify / inspect / tree / unpack
        Forwarded as-is to the stock mkpfs CLI.
    [extra] PFS-image operations the host needed that the stock mkpfs CLI lacks:
        probe-header <path>            detect whether a file is a PFS image (header only)
        read-member  <img> <rel>       read a member file's bytes/JSON from the image
        read-member-ffpfsc <img> <rel> read a member from a .ffpfsc (compressed PFS)
                                       via partial decode (read-only; decodes only
                                       the blocks the member touches). Add
                                       --with-member-name to also return the
                                       wrapped-image container name in the JSON.
        probe-ffpfsc-compression <img> report the inner image's PFSC compression
                                       ratio + zlib FLEVEL level bucket (read-only;
                                       exact 1-9 level is not recoverable)
        check-space <ffpfsc> <dest>    check dest free space vs the size the .ffpfsc
                                       unpacks to (+ --margin=<percent>, default 3)
        member-info  <img> <rel>       query a member's allocated size / compression
        patch-member <img> <rel> <f>   in-place patch a member within its allocated blocks
"""

from __future__ import annotations

import json
import math
import struct
import sys
import tempfile
from pathlib import Path

import mkpfs
from mkpfs import cli as mkpfs_cli

import mkpfs_worker

PASSTHROUGH_COMMANDS = {"pack", "verify", "inspect", "tree", "unpack"}


def _print_version() -> None:
    print(f"mkpfs-worker {mkpfs_worker.__version__}")
    print(f"  bundles mkpfs {mkpfs.__version__} (GPL-3.0)")
    print("  source: https://github.com/PSBrew/MkPFS")
    print("  this worker is GPL-3.0; see LICENSE and NOTICE")


def _apply_auto_overwrite() -> None:
    """Patch prompt_overwrite in both the cli and pfs modules to auto-confirm."""

    def _auto_overwrite(output_path) -> bool:
        try:
            p = Path(output_path)
            if p.exists():
                p.unlink()
            tmp = Path(str(output_path) + ".tmp")
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return True

    mkpfs_cli.prompt_overwrite = _auto_overwrite
    try:
        import mkpfs.pfs as mkpfs_pfs

        mkpfs_pfs.prompt_overwrite = _auto_overwrite
    except Exception:
        pass


def _apply_copy_fallback() -> None:
    """Patch single-file staging to fall back to a plain copy when hardlink/symlink fail."""
    import contextlib
    import os
    import shutil

    @contextlib.contextmanager
    def _stage_with_copy_fallback(*, source_file: Path, temp_folder=None):
        mkdtemp_kw = {"dir": str(temp_folder)} if temp_folder is not None else {}
        test_dir = tempfile.mkdtemp(**mkdtemp_kw)
        test_file = Path(test_dir) / source_file.name
        linked = False
        try:
            os.link(src=source_file, dst=test_file)
            linked = True
        except OSError:
            try:
                test_file.symlink_to(target=source_file)
                linked = True
            except OSError:
                pass

        if linked:
            try:
                yield Path(test_dir)
            finally:
                shutil.rmtree(test_dir, ignore_errors=True)
            return

        shutil.rmtree(test_dir, ignore_errors=True)
        copy_staging = tempfile.mkdtemp(**mkdtemp_kw)
        copy_file = Path(copy_staging) / source_file.name
        shutil.copy2(source_file, copy_file)
        try:
            yield Path(copy_staging)
        finally:
            shutil.rmtree(copy_staging, ignore_errors=True)

    mkpfs_cli._stage_single_file_source_root = _stage_with_copy_fallback


def _run_passthrough(argv: list[str]) -> int:
    forward: list[str] = []
    auto_yes = False
    stage_mode = None
    for a in argv:
        if a == "--yes":
            auto_yes = True
            continue
        if a.startswith("--stage-mode="):
            stage_mode = a.split("=", 1)[1]
            continue
        forward.append(a)

    if auto_yes:
        _apply_auto_overwrite()
    if stage_mode == "copy-fallback":
        _apply_copy_fallback()

    return mkpfs_cli.cli_mkpfs_main(forward)


def cmd_probe_header(argv: list[str]) -> int:
    if len(argv) != 1:
        print(json.dumps({"error": "usage: probe-header <path>"}))
        return 2
    from mkpfs.pfs import parse_image_header

    path = Path(argv[0])
    try:
        with path.open("rb") as fh:
            header = parse_image_header(fh)
        result = {"type": "pfs"} if header is not None else {"type": "unknown"}
    except Exception:
        result = {"type": "unknown"}
    print(json.dumps(result))
    return 0


def _read_member_payload_from_fh(fh, rel: str) -> bytes | None:
    """Read one member's logical bytes from an open PFS image file handle.

    ``fh`` only needs ``seek`` and ``read``; this is what lets the same routine
    serve both a real file and the lazy in-memory reader used for .ffpfsc.
    """
    from mkpfs.pfs import (
        build_tree_from_uroot,
        decode_inode_payload,
        parse_image_header,
        parse_image_inodes,
        parse_superroot_and_indexes,
        read_image_inode_payload,
    )

    header = parse_image_header(fh)
    if header is None:
        return None
    inodes = parse_image_inodes(fh, header)
    errors: list[str] = []
    uroot, _fpt, _coll, _special = parse_superroot_and_indexes(fh, header, inodes, errors)
    if uroot < 0:
        return None
    file_inodes, _dir_inodes, _dirents = build_tree_from_uroot(fh, header, inodes, uroot, errors)
    if rel not in file_inodes:
        return None
    inode = inodes[file_inodes[rel]]
    payload = read_image_inode_payload(fh, header, inode)
    if inode.is_compressed:
        payload = decode_inode_payload(payload=payload, inode=inode)
    return payload


def _read_member_payload(image_path: Path, rel: str) -> bytes | None:
    with image_path.open("rb") as fh:
        return _read_member_payload_from_fh(fh, rel)


class _PfscRandomReader:
    """Random-access, file-like view over a PFSC-compressed (or raw) inode payload.

    Decodes only the logical blocks that each ``read`` actually touches and keeps
    a small LRU of recently decoded blocks. This is what lets us pull
    sce_sys/param.json (1-2 blocks) and sce_sys/icon0.png (a few blocks) out of a
    .ffpfsc whose inner image is tens of GB, without decompressing the whole thing.

    Exposes only ``seek``/``tell``/``read`` because mkpfs' parsers (``_read_exact``)
    need nothing more.
    """

    def __init__(self, fh, header, inode, *, cache_blocks: int = 16):
        from mkpfs import consts
        from mkpfs.pfs import _parse_pfsc_header, read_image_bytes
        import struct
        from collections import OrderedDict

        self._fh = fh
        self._header = header
        self._read_image_bytes = read_image_bytes
        self._size = inode.logical_size
        self._pos = 0
        self._cache: "OrderedDict[int, bytes]" = OrderedDict()
        self._cache_blocks = cache_blocks
        self._base = inode.db[0] * header.block_size

        if not inode.is_compressed:
            # Raw payload stored contiguously from base — no PFSC table.
            self._lbs = None
            self._offsets = None
            return

        # Parse the PFSC header + block offset table (relative to payload start).
        head = read_image_bytes(fh, header, self._base, consts.PFSC_HEADER_SIZE)
        lbs, block_count, block_offsets_offset, data_offset, pfsc_logical_size = _parse_pfsc_header(head)
        offsets_size = (block_count + 1) * consts.PFSC_OFFSET_ENTRY_SIZE
        table = read_image_bytes(fh, header, self._base + block_offsets_offset, offsets_size)
        self._lbs = lbs
        self._offsets = list(struct.unpack_from(f"<{block_count + 1}Q", table, 0))
        self._block_count = block_count
        if self._size > pfsc_logical_size:
            self._size = pfsc_logical_size

    # -- file-like API (seek/tell/read only) --------------------------------
    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = self._size + offset
        return self._pos

    def tell(self) -> int:
        return self._pos

    def _logical_block(self, idx: int) -> bytes:
        from mkpfs.pfs import _decode_pfsc_block

        cached = self._cache.get(idx)
        if cached is not None:
            self._cache.move_to_end(idx)
            return cached
        start, end = self._offsets[idx], self._offsets[idx + 1]
        stored = self._read_image_bytes(self._fh, self._header, self._base + start, end - start)
        block = _decode_pfsc_block(stored, self._lbs, idx)
        self._cache[idx] = block
        if len(self._cache) > self._cache_blocks:
            self._cache.popitem(last=False)
        return block

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = self._size - self._pos
        end = min(self._pos + size, self._size)
        if end <= self._pos:
            return b""
        # Raw (uncompressed) payload: a single contiguous read suffices.
        if self._lbs is None:
            data = self._read_image_bytes(self._fh, self._header, self._base + self._pos, end - self._pos)
            self._pos = end
            return data
        out = bytearray()
        pos = self._pos
        while pos < end:
            idx = pos // self._lbs
            within = pos % self._lbs
            block = self._logical_block(idx)
            take = min(self._lbs - within, end - pos)
            out += block[within : within + take]
            pos += take
        self._pos = pos
        return bytes(out)


def _exfat_read_member_fh(fh, rel: str) -> bytes | None:
    """Read one member from an exFAT image exposed through a seek/read file-like.

    Generic exFAT directory walk (no mkpfs, no encryption); used when the image
    wrapped inside an .ffpfsc is exFAT rather than a nested PFS. ``fh`` only needs
    ``seek`` and ``read``, so the lazy PFSC reader works here unchanged.
    """
    import struct

    fh.seek(0)
    boot = fh.read(512)
    if len(boot) < 512 or boot[3:11] != b"EXFAT   ":
        return None
    fat_off = struct.unpack_from("<I", boot, 80)[0]
    cho = struct.unpack_from("<I", boot, 88)[0]
    root = struct.unpack_from("<I", boot, 96)[0]
    bps = 1 << boot[108]
    bpc = bps << boot[109]
    heap = cho * bps
    END = 0xFFFFFFF7

    def _co(c):
        return heap + (c - 2) * bpc

    def _nc(c):
        fh.seek(fat_off * bps + c * 4)
        return struct.unpack("<I", fh.read(4))[0]

    def _clusters(first, no_fat, dlen):
        if first < 2:
            return
        if no_fat:
            n = max(1, (dlen + bpc - 1) // bpc) if dlen else 1
            for k in range(n):
                yield first + k
        else:
            c = first
            while 2 <= c < END:
                yield c
                c = _nc(c)

    def _rdir(first, no_fat, dlen):
        b = bytearray()
        for c in _clusters(first, no_fat, dlen):
            fh.seek(_co(c))
            b += fh.read(bpc)
            if no_fat and dlen and len(b) >= dlen:
                break
        return bytes(b)

    def _find(first, no_fat, dlen, target):
        db = _rdir(first, no_fat, dlen)
        i = 0
        n = len(db)
        while i + 32 <= n:
            et = db[i]
            if et == 0x00:
                return None
            if et == 0x85:
                sec = db[i + 1]
                attrs = struct.unpack_from("<H", db, i + 4)[0]
                is_dir = bool(attrs & 0x10)
                stream = None
                pts = []
                for s in range(sec):
                    si = i + 32 * (s + 1)
                    if si + 32 > n:
                        break
                    if db[si] == 0xC0:
                        stream = db[si : si + 32]
                    elif db[si] == 0xC1:
                        pts.append(db[si + 2 : si + 32])
                if stream and pts:
                    no2 = bool(stream[1] & 0x02)
                    nl = stream[3]
                    fc = struct.unpack_from("<I", stream, 20)[0]
                    dl = struct.unpack_from("<Q", stream, 24)[0]
                    nm = b"".join(pts)[: nl * 2].decode("utf-16-le", errors="ignore")
                    if nm.lower() == target.lower():
                        return {"fc": fc, "dl": dl, "is_dir": is_dir, "no_fat": no2}
                i += 32 * (1 + sec)
            else:
                i += 32
        return None

    cur = {"fc": root, "no_fat": False, "dl": 0, "is_dir": True}
    for part in rel.split("/"):
        r = _find(cur["fc"], cur["no_fat"], cur["dl"], part)
        if not r:
            return None
        cur = r
    if cur["is_dir"]:
        return None
    rem = int(cur["dl"])
    out = bytearray()
    for c in _clusters(cur["fc"], cur["no_fat"], cur["dl"]):
        if rem <= 0:
            break
        fh.seek(_co(c))
        ch = fh.read(min(bpc, rem))
        if not ch:
            break
        out += ch
        rem -= len(ch)
    return bytes(out)


_UFS2_S_IFMT, _UFS2_S_IFDIR, _UFS2_S_IFREG = 0xF000, 0x4000, 0x8000


def _ufs2_read_member_fh(fh, rel: str) -> bytes | None:
    """Read one member from a UFS2 image exposed through a seek/read file-like.

    Pure on-disk UFS2 parse (no mkpfs, no UFS2Tool, read-only); used when the
    image wrapped inside an .ffpkg/.ffpfsc is UFS2. ``fh`` only needs ``seek`` and
    ``read``, so the lazy PFSC reader works here unchanged. Returns None on any
    structural mismatch or missing member.
    """
    import struct

    fh.seek(65536)
    sb = fh.read(8192)
    if len(sb) < 1376 or struct.unpack_from("<i", sb, 1372)[0] != 0x19540119:
        return None

    def i32(off):
        return struct.unpack_from("<i", sb, off)[0]

    fs_iblkno = i32(16); fs_bsize = i32(48); fs_fsize = i32(52); fs_frag = i32(56)
    fs_nindir = i32(116); fs_inopb = i32(120); fs_ipg = i32(184); fs_fpg = i32(188)
    if not (0 < fs_fsize <= fs_bsize and fs_frag > 0 and fs_inopb > 0
            and fs_ipg > 0 and fs_fpg > 0 and fs_nindir > 0):
        return None
    DINODE = 256

    def read_inode(ino):
        cg = ino // fs_ipg
        cgimin = fs_fpg * cg + fs_iblkno
        inblock = (ino % fs_ipg) // fs_inopb
        fsba = cgimin + inblock * fs_frag
        fsbo = ino % fs_inopb
        fh.seek(fsba * fs_fsize + fsbo * DINODE)
        return fh.read(DINODE)

    def fields(d):
        return (struct.unpack_from("<H", d, 0)[0],
                struct.unpack_from("<Q", d, 16)[0],
                struct.unpack_from("<q", d, 40)[0],
                list(struct.unpack_from("<12q", d, 112)),
                list(struct.unpack_from("<3q", d, 208)))

    def block_addr(db, ib, bi):
        if bi < 12:
            return db[bi]
        bj = bi - 12
        if bj < fs_nindir:
            if ib[0] == 0:
                return 0
            fh.seek(ib[0] * fs_fsize + bj * 8)
            return struct.unpack("<q", fh.read(8))[0]
        bj -= fs_nindir
        if bj < fs_nindir * fs_nindir:
            if ib[1] == 0:
                return 0
            fh.seek(ib[1] * fs_fsize + (bj // fs_nindir) * 8)
            a2 = struct.unpack("<q", fh.read(8))[0]
            if a2 == 0:
                return 0
            fh.seek(a2 * fs_fsize + (bj % fs_nindir) * 8)
            return struct.unpack("<q", fh.read(8))[0]
        return 0

    def read_data(size, db, ib):
        if size <= 0:
            return b""
        out = bytearray()
        remaining = size
        nblocks = (size + fs_bsize - 1) // fs_bsize
        for bi in range(nblocks):
            take = min(fs_bsize, remaining)
            addr = block_addr(db, ib, bi)
            if addr == 0:
                out += b"\x00" * take
            else:
                fh.seek(addr * fs_fsize)
                out += fh.read(take)
            remaining -= take
            if remaining <= 0:
                break
        return bytes(out)

    def dir_entries(data):
        i, n = 0, len(data)
        while i + 8 <= n:
            d_ino, d_reclen, _d_type, d_namlen = struct.unpack_from("<IHBB", data, i)
            if d_reclen < 8:
                break
            if d_ino != 0 and 0 < d_namlen <= 255 and i + 8 + d_namlen <= n:
                name = data[i + 8:i + 8 + d_namlen].decode("utf-8", "replace")
                if name not in (".", ".."):
                    yield name, d_ino
            i += d_reclen

    # Root inode is 2; verify it parses as a directory (offset sanity check).
    if (struct.unpack_from("<H", read_inode(2), 0)[0] & _UFS2_S_IFMT) != _UFS2_S_IFDIR:
        return None

    ino = 2
    for part in [p for p in rel.replace("\\", "/").split("/") if p]:
        mode, size, _mt, db, ib = fields(read_inode(ino))
        if (mode & _UFS2_S_IFMT) != _UFS2_S_IFDIR:
            return None
        nxt = None
        for name, c_ino in dir_entries(read_data(size, db, ib)):
            if name == part:
                nxt = c_ino
                break
        if nxt is None:
            return None
        ino = nxt
    mode, size, _mt, db, ib = fields(read_inode(ino))
    if (mode & _UFS2_S_IFMT) != _UFS2_S_IFREG:
        return None
    return read_data(size, db, ib)


def _select_ffpfsc_inner_member(file_inodes: dict) -> str | None:
    """Pick the wrapped-image member inside an .ffpfsc by file extension.

    The outer PFS wraps exactly one image, named by how it was packed:
    ``pfs_image.dat`` (nested PFS), ``*.exfat`` (exFAT), or ``*.ffpkg``.
    """
    for name in file_inodes:
        low = name.lower()
        if low == "pfs_image.dat" or low.endswith((".dat", ".exfat", ".ffpkg")):
            return name
    return None



def _read_member_from_ffpfsc(image_path: Path, rel: str) -> tuple[str | None, bytes | None]:
    """Read one member from a 2-level .ffpfsc (compressed PFS) via partial decode.

    Layout: outer PFS (PFSC-compressed) -> wrapped image member -> ``rel``. The
    inner filesystem is dispatched by the member's extension: ``pfs_image.dat``
    (.dat) is a nested PFS, ``*.exfat`` is exFAT, ``*.ffpkg`` is sniffed by its
    on-disk signature. Only the PFSC blocks covering the inner header/inodes/
    dirents and the target member are decompressed; the rest is never touched.

    Returns ``(member_name, payload)``:
      - ``(None, None)``   the file is not a usable .ffpfsc (or signed/
                           non-contiguous outer payload — not the .ffpfsc case)
      - ``(member, None)`` the wrapped image was found but ``rel`` was not
      - ``(member, bytes)`` success
    so the caller can report the container member name even on a miss.
    """
    from mkpfs.pfs import (
        build_tree_from_uroot,
        parse_image_header,
        parse_image_inodes,
        parse_superroot_and_indexes,
    )

    with image_path.open("rb") as fh:
        header = parse_image_header(fh)
        if header is None:
            return None, None
        inodes = parse_image_inodes(fh, header)
        errors: list[str] = []
        uroot, _fpt, _coll, _special = parse_superroot_and_indexes(fh, header, inodes, errors)
        if uroot < 0:
            return None, None
        file_inodes, _dir_inodes, _dirents = build_tree_from_uroot(fh, header, inodes, uroot, errors)
        member = _select_ffpfsc_inner_member(file_inodes)
        if member is None:
            return None, None
        outer = inodes[file_inodes[member]]
        # Partial decode only supports the unsigned, contiguous payload an .ffpfsc uses.
        if outer.db_sig or outer.ib_sig or outer.blocks <= 0 or not outer.db or outer.db[0] <= 0:
            return None, None
        inner_fh = _PfscRandomReader(fh, header, outer)

        # Inner-FS parsing can raise on an unexpected layout (e.g. a UFS2 image
        # mis-read as PFS); treat any structural failure as "member not found"
        # rather than letting the exception escape as a crash.
        low = member.lower()
        try:
            if low.endswith(".exfat"):
                return member, _exfat_read_member_fh(inner_fh, rel)
            if low.endswith(".ffpkg"):
                # .ffpkg wraps exFAT / UFS2 / PFS — sniff the inner signature.
                inner_fh.seek(0)
                sig = inner_fh.read(512)
                if len(sig) >= 11 and sig[3:11] == b"EXFAT   ":
                    return member, _exfat_read_member_fh(inner_fh, rel)
                ufs2 = _ufs2_read_member_fh(inner_fh, rel)
                if ufs2 is not None:
                    return member, ufs2
                inner_fh.seek(0)
                return member, _read_member_payload_from_fh(inner_fh, rel)
            # pfs_image.dat (or any .dat) — nested PFS.
            return member, _read_member_payload_from_fh(inner_fh, rel)
        except Exception:
            return member, None


def cmd_read_member(argv: list[str]) -> int:
    as_json = "--as-json" in argv
    positional = [a for a in argv if a != "--as-json"]
    if len(positional) != 2:
        print(json.dumps({"error": "usage: read-member <image> <rel_path> [--as-json]"}), file=sys.stderr)
        return 2
    image_path, rel = Path(positional[0]), positional[1]
    payload = _read_member_payload(image_path, rel)
    if payload is None:
        print(json.dumps({"error": "NOT_FOUND"}), file=sys.stderr)
        return 1
    if as_json:
        try:
            print(json.dumps({"json": json.loads(payload.decode("utf-8"))}))
        except Exception:
            import base64

            print(json.dumps({"data_base64": base64.b64encode(payload).decode("ascii")}))
    else:
        sys.stdout.buffer.write(payload)
    return 0


def cmd_read_member_ffpfsc(argv: list[str]) -> int:
    """Read a member from a .ffpfsc (compressed PFS) via partial decode (read-only).

    ``--with-member-name`` always emits a JSON object that also carries the
    wrapped-image container name (``member``), so a GUI can fetch the payload and
    the container's filename.ext in a single call:
      - JSON member:    {"member": "pfs_image.dat", "json": {...}}
      - binary member:  {"member": "pfs_image.dat", "data_base64": "..."}
    """
    flags = {"--as-json", "--with-member-name"}
    as_json = "--as-json" in argv
    with_member = "--with-member-name" in argv
    positional = [a for a in argv if a not in flags]
    if len(positional) != 2:
        print(
            json.dumps({"error": "usage: read-member-ffpfsc <image> <rel_path> [--as-json] [--with-member-name]"}),
            file=sys.stderr,
        )
        return 2
    image_path, rel = Path(positional[0]), positional[1]
    member, payload = _read_member_from_ffpfsc(image_path, rel)
    if payload is None:
        err = {"error": "NOT_FOUND"}
        if with_member and member is not None:
            err["member"] = member
        print(json.dumps(err), file=sys.stderr)
        return 1
    if with_member:
        # Always JSON when the container name is requested, so the binary case
        # (icon) is base64-wrapped rather than corrupting stdout.
        out: dict = {"member": member}
        try:
            out["json"] = json.loads(payload.decode("utf-8"))
        except Exception:
            import base64

            out["data_base64"] = base64.b64encode(payload).decode("ascii")
        print(json.dumps(out))
    elif as_json:
        try:
            print(json.dumps({"json": json.loads(payload.decode("utf-8"))}))
        except Exception:
            import base64

            print(json.dumps({"data_base64": base64.b64encode(payload).decode("ascii")}))
    else:
        sys.stdout.buffer.write(payload)
    return 0


def _probe_ffpfsc_compression(image_path: Path, sample: int = 4096) -> dict | None:
    """Report the inner image's PFSC compression ratio + zlib FLEVEL distribution.

    The overall ratio is exact (from the PFSC block-offset table; no block is
    decoded). The per-block zlib level *bucket* is sampled: up to ``sample``
    evenly spaced blocks are inspected, reading only each block's 2-byte zlib
    header (FLG). zlib stores compression level only as a 2-bit FLEVEL hint, so
    the exact 1-9 value is not recoverable; the buckets are::

        FLEVEL 0 -> level 0-1
        FLEVEL 1 -> level 2-5
        FLEVEL 2 -> level 6   (the only 1:1 bucket)
        FLEVEL 3 -> level 7-9 (mkpfs default is 7)

    Returns None when the file is not a usable .ffpfsc.
    """
    from mkpfs.pfs import (
        build_tree_from_uroot,
        parse_image_header,
        parse_image_inodes,
        parse_superroot_and_indexes,
    )

    with image_path.open("rb") as fh:
        header = parse_image_header(fh)
        if header is None:
            return None
        inodes = parse_image_inodes(fh, header)
        errors: list[str] = []
        uroot, _fpt, _coll, _special = parse_superroot_and_indexes(fh, header, inodes, errors)
        if uroot < 0:
            return None
        file_inodes, _dir_inodes, _dirents = build_tree_from_uroot(fh, header, inodes, uroot, errors)
        member = _select_ffpfsc_inner_member(file_inodes)
        if member is None:
            return None
        outer = inodes[file_inodes[member]]
        if outer.db_sig or outer.ib_sig or outer.blocks <= 0 or not outer.db or outer.db[0] <= 0:
            return None

        reader = _PfscRandomReader(fh, header, outer)
        if reader._lbs is None:
            # Raw, uncompressed inner payload (no PFSC blocks).
            return {
                "member": member,
                "compressed": False,
                "logical_size": reader._size,
                "stored_size": reader._size,
                "ratio": 1.0,
            }

        lbs = reader._lbs
        offsets = reader._offsets
        block_count = reader._block_count
        logical_size = block_count * lbs
        stored_size = offsets[block_count] - offsets[0]

        # Sample FLEVEL across the payload (read only the 2-byte zlib header).
        step = max(1, block_count // sample) if sample > 0 else 1
        flevel_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        raw_blocks = 0
        sampled = 0
        for idx in range(0, block_count, step):
            start, end = offsets[idx], offsets[idx + 1]
            stored_len = end - start
            sampled += 1
            if stored_len >= lbs:
                raw_blocks += 1  # block stored uncompressed (no zlib stream)
                continue
            head2 = reader._read_image_bytes(fh, header, reader._base + start, 2)
            if len(head2) < 2:
                continue
            flevel_counts[(head2[1] >> 6) & 0x3] += 1

        compressed_sampled = sum(flevel_counts.values())
        dominant = max(flevel_counts, key=flevel_counts.get) if compressed_sampled else None
        bucket_levels = {0: "0-1", 1: "2-5", 2: "6", 3: "7-9"}
        return {
            "member": member,
            "compressed": True,
            "logical_size": logical_size,
            "stored_size": stored_size,
            "ratio": round(stored_size / logical_size, 6) if logical_size else None,
            "block_size": lbs,
            "block_count": block_count,
            "sampled_blocks": sampled,
            "raw_blocks_sampled": raw_blocks,
            "flevel_counts": {str(k): v for k, v in flevel_counts.items()},
            "dominant_flevel": dominant,
            "level_bucket": bucket_levels.get(dominant) if dominant is not None else None,
        }


def cmd_probe_ffpfsc_compression(argv: list[str]) -> int:
    """Report a .ffpfsc inner image's compression ratio + zlib FLEVEL bucket (read-only)."""
    positional = [a for a in argv if not a.startswith("--")]
    sample = 4096
    for a in argv:
        if a.startswith("--sample="):
            try:
                sample = int(a.split("=", 1)[1])
            except ValueError:
                print(json.dumps({"error": "invalid --sample value"}), file=sys.stderr)
                return 2
    if len(positional) != 1:
        print(
            json.dumps({"error": "usage: probe-ffpfsc-compression <image> [--sample=N]"}),
            file=sys.stderr,
        )
        return 2
    info = _probe_ffpfsc_compression(Path(positional[0]), sample=sample)
    if info is None:
        print(json.dumps({"error": "NOT_FOUND"}), file=sys.stderr)
        return 1
    print(json.dumps(info))
    return 0


def _ffpfsc_unpacked_size(image_path: Path) -> int | None:
    """Return the size of the single image an .ffpfsc unpacks to (its inner
    wrapped member's logical/decompressed size), or None if not a usable .ffpfsc.

    Reads only the outer PFS metadata + the inner PFSC header (no block decode).
    """
    from mkpfs.pfs import (
        build_tree_from_uroot,
        parse_image_header,
        parse_image_inodes,
        parse_superroot_and_indexes,
    )

    with image_path.open("rb") as fh:
        header = parse_image_header(fh)
        if header is None:
            return None
        inodes = parse_image_inodes(fh, header)
        errors: list[str] = []
        uroot, _fpt, _coll, _special = parse_superroot_and_indexes(fh, header, inodes, errors)
        if uroot < 0:
            return None
        file_inodes, _dir_inodes, _dirents = build_tree_from_uroot(fh, header, inodes, uroot, errors)
        member = _select_ffpfsc_inner_member(file_inodes)
        if member is None:
            return None
        outer = inodes[file_inodes[member]]
        if outer.db_sig or outer.ib_sig or outer.blocks <= 0 or not outer.db or outer.db[0] <= 0:
            return None
        # _PfscRandomReader caps _size to the PFSC logical size, i.e. the exact
        # number of bytes the inner image expands to when unpacked.
        return _PfscRandomReader(fh, header, outer)._size


def cmd_check_space(argv: list[str]) -> int:
    """Check whether <dest> has room to unpack a .ffpfsc (ffpfsc only; read-only).

    An .ffpfsc unpacks to a single image file, so the requirement is its inner
    logical size plus a safety margin (default 3%). Other container types
    (exfat / pfs_image.dat / ffpkg) are out of scope and rejected.
    """
    import shutil

    margin = 3.0
    positional = []
    for a in argv:
        if a.startswith("--margin="):
            try:
                margin = float(a.split("=", 1)[1])
            except ValueError:
                print(json.dumps({"error": "invalid --margin value"}), file=sys.stderr)
                return 2
        elif a.startswith("--"):
            print(json.dumps({"error": f"unknown option {a}"}), file=sys.stderr)
            return 2
        else:
            positional.append(a)
    if len(positional) != 2:
        print(json.dumps({"error": "usage: check-space <ffpfsc> <dest> [--margin=<percent>]"}), file=sys.stderr)
        return 2

    image_path, dest = Path(positional[0]), positional[1]
    if image_path.suffix.lower() != ".ffpfsc":
        print(json.dumps({"error": "NOT_FFPFSC"}), file=sys.stderr)
        return 2
    need = _ffpfsc_unpacked_size(image_path)
    if need is None:
        print(json.dumps({"error": "NOT_FOUND"}), file=sys.stderr)
        return 1
    try:
        free = shutil.disk_usage(dest).free
    except OSError as exc:
        print(json.dumps({"error": "BAD_DEST", "detail": str(exc)}), file=sys.stderr)
        return 2

    need_with_margin = int(need * (1 + margin / 100.0))
    ok = free >= need_with_margin
    print(
        json.dumps(
            {
                "ok": ok,
                "need": need,
                "need_with_margin": need_with_margin,
                "free": free,
                "margin_percent": margin,
                "shortfall": max(0, need_with_margin - free),
            }
        )
    )
    return 0 if ok else 1


def cmd_member_info(argv: list[str]) -> int:
    from mkpfs.pfs import inspect_pfs_image

    if len(argv) != 2:
        print(json.dumps({"error": "usage: member-info <image> <rel_path>"}), file=sys.stderr)
        return 2
    image_path, rel = Path(argv[0]), argv[1]
    inspection = inspect_pfs_image(image=image_path)
    if inspection.header is None or rel not in inspection.file_inodes:
        print(json.dumps({"exists": False}))
        return 0
    inode = inspection.inodes[inspection.file_inodes[rel]]
    if inode.is_compressed or not inode.db or inode.db[0] <= 0:
        print(json.dumps({"exists": True, "alloc_bytes": None, "compressed": inode.is_compressed}))
        return 0
    block_size = inspection.header.block_size
    alloc_blocks = sum(1 for b in inode.db if b and b > 0) or 1
    print(json.dumps({"exists": True, "alloc_bytes": alloc_blocks * block_size, "compressed": False}))
    return 0


def cmd_patch_member(argv: list[str]) -> int:
    from mkpfs.consts import INODE_D32_SIZE, PFS_MODE_SIGNED
    from mkpfs.pfs import inspect_pfs_image

    if len(argv) != 3:
        print(json.dumps({"error": "usage: patch-member <image> <rel_path> <new_data_file>"}), file=sys.stderr)
        return 2
    image_path, rel, data_path = Path(argv[0]), argv[1], Path(argv[2])
    new_bytes = data_path.read_bytes()

    inspection = inspect_pfs_image(image=image_path)
    if inspection.header is None:
        print(json.dumps({"error": "NOT_FOUND"}), file=sys.stderr)
        return 1
    header = inspection.header
    if header.mode & PFS_MODE_SIGNED:
        print(json.dumps({"error": "SIGNED"}), file=sys.stderr)
        return 1
    if rel not in inspection.file_inodes:
        print(json.dumps({"error": "NOT_FOUND"}), file=sys.stderr)
        return 1
    inode_num = inspection.file_inodes[rel]
    inode = inspection.inodes[inode_num]
    if inode.is_compressed:
        print(json.dumps({"error": "COMPRESSED"}), file=sys.stderr)
        return 1
    if not inode.db or inode.db[0] <= 0:
        print(json.dumps({"error": "NO_BLOCK_POINTER"}), file=sys.stderr)
        return 1

    block_size = header.block_size
    alloc_blocks = sum(1 for b in inode.db if b and b > 0) or 1
    need_blocks = max(1, math.ceil(len(new_bytes) / block_size))
    if need_blocks > alloc_blocks:
        print(json.dumps({"error": "TOO_LARGE"}), file=sys.stderr)
        return 1

    pad = block_size - (len(new_bytes) % block_size) if len(new_bytes) % block_size else 0
    padded = new_bytes + b"\x00" * pad
    data_offset = inode.db[0] * block_size

    inode_size = INODE_D32_SIZE
    inodes_per_block = block_size // inode_size
    inode_file_offset = (
        block_size + (inode_num // inodes_per_block) * block_size + (inode_num % inodes_per_block) * inode_size
    )
    with image_path.open("r+b") as f:
        f.seek(data_offset)
        f.write(padded)
        f.seek(inode_file_offset + 0x08)
        f.write(struct.pack("<q", len(new_bytes)))
        f.write(struct.pack("<q", len(new_bytes)))

    print(json.dumps({"ok": True}))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-V", "--version"):
        _print_version()
        return 0

    cmd, rest = argv[0], argv[1:]
    if cmd in PASSTHROUGH_COMMANDS:
        return _run_passthrough(argv)
    if cmd == "probe-header":
        return cmd_probe_header(rest)
    if cmd == "read-member":
        return cmd_read_member(rest)
    if cmd == "read-member-ffpfsc":
        return cmd_read_member_ffpfsc(rest)
    if cmd == "probe-ffpfsc-compression":
        return cmd_probe_ffpfsc_compression(rest)
    if cmd == "check-space":
        return cmd_check_space(rest)
    if cmd == "member-info":
        return cmd_member_info(rest)
    if cmd == "patch-member":
        return cmd_patch_member(rest)

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
