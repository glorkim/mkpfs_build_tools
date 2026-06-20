"""Frozen-exe entry point for mkpfs-worker (used by PyInstaller)."""

import multiprocessing
import sys

from mkpfs_worker.cli import main

if __name__ == "__main__":
    # PyInstaller로 묶인 exe에서 mkpfs가 멀티프로세싱(PFSC 압축 등)으로
    # 자식 프로세스를 띄울 때 자기 자신을 `--multiprocessing-fork ...`로 재실행한다.
    # 이 호출이 그 재실행을 가로채 자식 워커로 동작시킨다. 반드시 인자 파싱 전에 호출.
    multiprocessing.freeze_support()
    sys.exit(main())
