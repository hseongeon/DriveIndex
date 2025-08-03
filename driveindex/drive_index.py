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

import json
import argparse
import logging


# --------------------------------------------------
def get_args():
    """Get command-line arguments"""

    parser = argparse.ArgumentParser(
        description=("Scan and index external drives to track folders and files."),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    return parser.parse_args()


# --------------------------------------------------
def main():
    """main"""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = get_args()


# --------------------------------------------------
if __name__ == "__main__":
    main()
