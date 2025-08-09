#!/usr/bin/env python3
"""
Author : seong-eon Hwang (hseongeon@gmail.com)
Date   : 2025-08-03

Purpose:
DriveIndex is a command-line tool that scans external drives to index folder and file
information, helping users keep track of where their data is stored. It allows users
to search for folders by name and see which drive they belong to, making large
collections of files easier to manage.
"""

__version__ = "0.1.0"

from typing import TypedDict, List
from wcwidth import wcswidth
from ansi import colorize, BRIGHT_CYAN, BRIGHT_BLUE
import json
import argparse
import logging
import os
import sys
import unicodedata


# --- type hint ---
class FolderMeta(TypedDict):
    name: str
    file_count: int


class FileMeta(TypedDict):
    name: str
    size: int


class FolderInfo(TypedDict):
    path: str
    folder: FolderMeta
    files: List[FileMeta]


IGNORED_FILES = {
    ".DS_Store",
    ".com.apple.timemachine.donotpresent",
}

IGNORED_DIRS = {
    ".fseventsd",
}


MAX_FILENAME_WIDTH = 100
MAX_SIZE_WIDTH = 10


# --------------------------------------------------
def get_args():
    """Get command-line arguments"""

    parser = argparse.ArgumentParser(
        description="Index external drive contents or search from existing index"
    )

    subparsers = parser.add_subparsers(
        title="Commands",
        dest="command",
        required=True,
        help="Available commands",
    )

    # ---- scan subcommand ----
    scan_parser = subparsers.add_parser(
        "scan", help="Scan connected external drive and save index"
    )
    scan_parser.add_argument(
        "filename",
        metavar="OUTPUT_JSON",
        type=str,
        help="Path to save the generated JSON index (e.g. contents.json)",
    )

    # ---- search subcommand ----
    search_parser = subparsers.add_parser(
        "search", help="Search folders in an existing index"
    )
    search_parser.add_argument(
        "filename",
        metavar="INPUT_JSON",
        type=str,
        help="Path to the existing JSON index file",
    )
    search_parser.add_argument(
        "-k",
        "--keyword",
        metavar="KEYWORD",
        type=str,
        required=True,
        help="Keyword to search for (partial match supported)",
    )

    return parser.parse_args()


# --------------------------------------------------
def main():
    """main"""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = get_args()
    if args.command == "scan":
        handle_scan(args.filename)
    elif args.command == "search":
        handle_search(args.filename, args.keyword)


# --------------------------------------------------
def handle_scan(output_path: str):
    """Scan connected external drive and save index to JSON"""

    volumes_root = "/Volumes"
    excluded = {"Macintosh HD", "com.apple.TimeMachine.localsnapshots"}

    # 외장하드 후보 찾기
    try:
        volumes = [v for v in os.listdir(volumes_root) if v not in excluded]
    except FileNotFoundError:
        logging.warning(
            "The /Volumes directory does not exist. "
            "Are you sure you're running this on macOS?"
        )
        sys.exit(1)

    if not volumes:
        logging.info("No external drives detected.")
        sys.exit(1)
    elif len(volumes) > 1:
        logging.info(
            f"Multiple external drives detected: {volumes} "
            "Please connect only one external drive and try again."
        )
        sys.exit(1)

    drive_path = os.path.join(volumes_root, volumes[0])
    print(f"An external drive detected: {drive_path}")

    results: List[FolderInfo] = []

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as fh:
                existing_data = json.load(fh)
                results.extend(existing_data)  # 기존 데이터 추가
            logging.info(f"Existing index loaded from: {output_path}")
        except json.JSONDecodeError:
            logging.info(
                f"'{output_path}': invalid JSON format. Starting with a new index."
            )
        except Exception as e:
            logging.error(f"Failed to load index JSON file: {e}")
            sys.exit(1)

    for dirpath, dirnames, filenames in os.walk(drive_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        valid_filenames = [f for f in filenames if f not in IGNORED_FILES]
        if not valid_filenames:
            continue  # 유효한 파일이 하나도 없으면 폴더 자체 무시

        folder_meta: FolderMeta = {
            "name": os.path.basename(dirpath),
            "file_count": len(valid_filenames),
        }

        folder_info: FolderInfo = {
            "path": os.path.abspath(dirpath),
            "folder": folder_meta,
            "files": [],
        }

        for filename in valid_filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                file_size = os.path.getsize(file_path)
            except OSError:
                continue  # 접근 불가 파일 무시

            folder_info["files"].append({"name": filename, "size": file_size})

        results.append(folder_info)

    # JSON으로 저장
    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=4, ensure_ascii=False)
        logging.info(f"Index saved to: {output_path}")
    except Exception as e:
        logging.error(f"Failed to save JSON file: {e}")
        sys.exit(1)


# --------------------------------------------------
def handle_search(index_path: str, keyword: str):
    """Search index JSON for folders or files containing the keyword"""

    try:
        with open(index_path, "r", encoding="utf-8") as fh:
            index: List[FolderInfo] = json.load(fh)
    except Exception as e:
        logging.error(f"Failed to load index JSON file: {e}")
        sys.exit(1)

    results: List[FolderInfo] = []

    for entry in index:
        folder_name = normalize(entry["folder"]["name"]).lower()
        files = entry["files"]

        # 폴더 이름에 검색어가 포함되면 추가
        if keyword in folder_name:
            results.append(entry)
            continue

        # 파일 이름 중 하나라도 포함되면 추가
        if matched := [
            f for f in files if keyword.lower() in normalize(f["name"]).lower()
        ]:
            entry["files"] = matched
            results.append(entry)

    if not results:
        print(f"No results found for: '{keyword}'")
        return

    for result in results:
        print(
            f"<Directory '{colorize(result['folder']['name'], BRIGHT_CYAN)}' "
            f"has {result['folder']['file_count']} file(s)> ",
            end="",
        )
        print(f"{colorize(extract_volume_name(result['path']), BRIGHT_BLUE)}")

        for file in result["files"]:
            print(
                f"\t{pad_to_width(file['name'], MAX_FILENAME_WIDTH)}"
                f"{human_readable_size(file['size']):>{MAX_SIZE_WIDTH}}"
            )


# --------------------------------------------------
def extract_volume_name(path: str) -> str:
    parts = os.path.normpath(path).split(os.sep)
    if len(parts) >= 3 and parts[1] == "Volumes":
        return parts[2]
    return "(unknown)"


# --------------------------------------------------
def human_readable_size(size_bytes: int) -> str:
    """바이트 단위를 KB, MB, GB, TB 등으로 변환"""

    if size_bytes < 1024:
        return f"{size_bytes} B"
    size = float(size_bytes)
    for unit in ["KB", "MB", "GB", "TB", "PB"]:
        size /= 1024.0
        if size < 1024.0:
            return f"{size:.2f} {unit}"
    return f"{size:.2f} PB"


# --------------------------------------------------
def pad_to_width(text: str, width: int) -> str:
    text_width = wcswidth(text)
    return text + " " * (width - text_width)


# --------------------------------------------------
def normalize(s: str) -> str:
    return unicodedata.normalize("NFC", s)


# --------------------------------------------------
if __name__ == "__main__":
    main()
