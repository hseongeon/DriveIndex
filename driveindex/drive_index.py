#!/usr/bin/env python3
"""
Author : seong-eon Hwang (hseongeon@gmail.com)
Date   : 2025-08-03

Purpose:
    DriveIndex is a command-line tool that scans external drives to index directory
    and file information, helping users keep track of where their data is stored.
    It is designed for collections where data does not change frequently. Once indexed,
    users can search for directories and files by name and see which drive they
    belong to, even without connecting the drive, making large collections of data
    easier to manage.
"""

__version__ = "0.1.1"

from typing import TypedDict, List
from wcwidth import wcswidth  # type: ignore[import]
from ansi import colorize, BRIGHT_CYAN, BRIGHT_BLUE, GRAY_40
import json
import argparse
import logging
import os
import sys
import unicodedata


# --- type hint ---
class DirectoryMeta(TypedDict):
    name: str
    file_count: int


class FileMeta(TypedDict):
    name: str
    size: int


class DirectoryInfo(TypedDict):
    path: str
    directory: DirectoryMeta
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
        title="commands",
        dest="command",
        required=True,
        help="Available commands",
    )

    # ---- scan subcommand ----
    scan_parser = subparsers.add_parser(
        "scan", help="scan connected external drive and save index"
    )
    scan_parser.add_argument(
        "filename",
        metavar="OUTPUT_JSON",
        type=str,
        help="path to save the generated JSON index",
    )

    # ---- search subcommand ----
    search_parser = subparsers.add_parser(
        "search", help="search directories and files in an existing index"
    )
    search_parser.add_argument(
        "filename",
        metavar="INPUT_JSON",
        type=str,
        help="path to the existing JSON index file",
    )
    search_parser.add_argument(
        "-k",
        "--keyword",
        metavar="KW",
        type=str,
        required=True,
        help="keyword to search for (partial match supported)",
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
    elif len(volumes) == 1:
        drive_path = os.path.join(volumes_root, volumes[0])
        print(f"An external drive detected: {drive_path}")
    else:
        for i, volume in enumerate(volumes, start=1):
            print(f"{i}. {os.path.join(volumes_root, volume)}")
        while True:
            selected = input("Select the drive number to scan: ").strip()
            if not selected.isdigit():
                print("Please enter a valid number.")
                continue

            selected_int = int(selected)
            if 1 <= selected_int <= len(volumes):
                drive_path = os.path.join(volumes_root, volumes[selected_int - 1])
                break
            else:
                print(f"Please enter a number between 1 and {len(volumes)}.")

    results: List[DirectoryInfo] = []

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as fh:
                existing_data = json.load(fh)
                results.extend(existing_data)  # add existing data
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
            continue  # skip directories with no valid files

        directory_meta: DirectoryMeta = {
            "name": os.path.basename(dirpath),
            "file_count": len(valid_filenames),
        }

        directory_info: DirectoryInfo = {
            "path": os.path.abspath(dirpath),
            "directory": directory_meta,
            "files": [],
        }

        for filename in valid_filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                file_size = os.path.getsize(file_path)
            except OSError:
                continue  # ignore inaccessible files

            directory_info["files"].append({"name": filename, "size": file_size})

        results.append(directory_info)

    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=4, ensure_ascii=False)
        logging.info(f"Index saved to: {output_path}")
    except Exception as e:
        logging.error(f"Failed to save JSON file: {e}")
        sys.exit(1)


# --------------------------------------------------
def handle_search(index_path: str, keyword: str):
    """Search index JSON for directories or files containing the keyword"""

    try:
        with open(index_path, "r", encoding="utf-8") as fh:
            index: List[DirectoryInfo] = json.load(fh)
    except Exception as e:
        logging.error(f"Failed to load index JSON file: {e}")
        sys.exit(1)

    results: List[DirectoryInfo] = []

    for entry in index:
        directory_name = normalize(entry["directory"]["name"]).lower()
        files = entry["files"]

        if keyword in directory_name:
            results.append(entry)
            continue

        if matched := [
            f for f in files if keyword.lower() in normalize(f["name"]).lower()
        ]:
            matched.sort(key=lambda f: f["name"].lower())
            entry["files"] = matched
            results.append(entry)

    if not results:
        print(f"No results found for: '{keyword}'")
        return

    results.sort(key=lambda e: e["directory"]["name"].lower())

    for result in results:
        print(
            f"<Directory '{colorize(result['directory']['name'], BRIGHT_CYAN)}' "
            f"has {result['directory']['file_count']} file(s)> "
            f"{colorize(extract_volume_name(result['path']), BRIGHT_BLUE)}"
        )
        even_number_cell = False
        for file in result["files"]:
            cell_str = (
                "\t"
                + pad_to_width(file["name"], MAX_FILENAME_WIDTH)
                + human_readable_size(file["size"]).rjust(MAX_SIZE_WIDTH)
            )
            ## use light gray for even rows
            print(colorize(cell_str, GRAY_40) if even_number_cell else cell_str)
            even_number_cell = not even_number_cell


# --------------------------------------------------
def extract_volume_name(path: str) -> str:
    """
    Extract the volume name from a given file path, returning "(unknown)"
    if it cannot be determined.
    """

    parts = os.path.normpath(path).split(os.sep)
    if len(parts) >= 3 and parts[1] == "Volumes":
        return parts[2]
    return "(unknown)"


# --------------------------------------------------
def human_readable_size(size_bytes: int) -> str:
    """
    Convert a file size in bytes to a human-readable string
    using KB, MB, GB, TB, or PB units.
    """

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
    """Truncate or pad a string to fit a given display width."""

    text_width = wcswidth(text)
    if text_width <= width:
        # pad with spaces
        return text + " " * (width - text_width)

    # need to truncate
    ellipsis = "..."
    ellipsis_width = wcswidth(ellipsis)
    truncated = ""
    current_width = 0

    for ch in text:
        ch_w = wcswidth(ch)
        if current_width + ch_w + ellipsis_width > width:
            break
        truncated += ch
        current_width += ch_w

    return truncated + ellipsis + " " * (width - (current_width + ellipsis_width))


# --------------------------------------------------
def normalize(s: str) -> str:
    """
    Normalize a string to NFC (Canonical Composition) form for
    consistent Unicode representation.
    """

    return unicodedata.normalize("NFC", s)


# --------------------------------------------------
if __name__ == "__main__":
    main()
