import datetime
import sys
from argparse import ArgumentParser, Namespace
from enum import Enum


class OutputFormats(Enum):
    MARDKOWN = "markdown"
    JEKYLL = "jekyll"


def _validate_output_format(args) -> OutputFormats:
    """Validates the format argument"""
    format: OutputFormats = OutputFormats.MARDKOWN

    if args == "jekyll":
        format = OutputFormats.JEKYLL

    return format


def _set_date(args) -> datetime.date:
    """Validates the date argument, parsing the date from the ISO format"""
    date: datetime.date
    try:
        date = datetime.date.fromisoformat(args)
    except ValueError:
        date = datetime.date.today()
    return date


def parse(args=sys.argv) -> Namespace:
    parser: ArgumentParser = ArgumentParser(
        prog="GDScript Docs Maker",
        description="Merges or converts json data dumped by Godot's "
        "GDScript language server to create a code reference.",
    )
    parser.add_argument(
        "files", type=str, nargs="+", default="", help="A list of paths to JSON files."
    )
    parser.add_argument(
        "-p", "--path", type=str, default="export", help="Path to the output directory."
    )
    parser.add_argument(
        "-f",
        "--format",
        type=_validate_output_format,
        default=OutputFormats.MARDKOWN,
        help=(
            "Output format for the markdown files."
            "markdown (default) or jekyll"
        )
    )

    parser.add_argument(
        "-i",
        "--make-index",
        action="store_true",
        default=False,
        help="If this flag is present, create an index.md page with a table of contents.",
    )

    parser.add_argument(
        "-s",
        "--skip",
        type=str,
        nargs="+",
        default="",
        help="use with --make-index, skip files on index",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Set the verbosity level. For example, -vv sets the verbosity level to 2."
        " Default: 0.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Run the script without actual rendering or creating files and"
            " folders. For debugging purposes"
        ),
    )

    namespace: Namespace = parser.parse_args(args)
    namespace.verbose = 99999 if namespace.dry_run else namespace.verbose
    return namespace
