"""Parses the JSON data from Godot as a dictionary and outputs markdown
documents

"""
import re
from argparse import Namespace
from typing import List

from .command_line import OutputFormats
from .config import LOGGER
from .gdscript_objects import (
    Element,
    GDScriptClass,
    GDScriptClasses,
    ProjectInfo,
)

from .make_markdown import (
    MarkdownDocument,
    MarkdownSection,
    make_bold,
    make_code_block,
    make_comment,
    make_heading,
    make_link,
    make_table_header,
    make_table_row,
    surround_with_html,
    wrap_in_newlines,
    jekyll,
    dark_mode_button
)


def convert_to_markdown(
    classes: GDScriptClasses, arguments: Namespace, info: ProjectInfo
) -> List[MarkdownDocument]:
    """Takes a list of dictionaries that each represent one GDScript class to
    convert to markdown and returns a list of markdown documents.

    """
    markdown: List[MarkdownDocument] = []
    if arguments.make_index:
        output_format: OutputFormats = arguments.format
        if output_format != OutputFormats.JEKYLL:
            markdown.append(_write_index_page(classes, info)) # don't work

    index_dict = {}
    for entry in classes:
        markdown.append(_as_markdown(classes, entry, arguments))
        _add_index_dict(index_dict, entry, arguments)

    for parent in index_dict:
        if parent in ["main", ""]:
            continue;

        content: List[str] = []

        jp: str = "/" + parent
        order: int = 2

        content += [jekyll([
                "title: {}".format(parent.title()),
                "permalink: {}".format(jp),
                "nav_order: {}".format(order),
                "has_children: true",
                "has_toc: true"
            ])
        ]

        markdown.append(MarkdownDocument(parent, content))

    return markdown

def _add_index_dict(index_dict: dict, gdscript: GDScriptClass, arguments):
    output_format: OutputFormats = arguments.format
    if output_format == OutputFormats.JEKYLL and arguments.make_index:
        paths = gdscript.jekyll_path.split("/")

        for p in paths:
            if p in ["", paths[-1]]:
                continue

            pair = {p:{}}

            if not (p in index_dict):
                pair[p].update({gdscript.name: gdscript.jekyll_path})
                index_dict.update(pair)

            else:
                index_dict[p].update({gdscript.name: gdscript.jekyll_path})

def _as_markdown(
    classes: GDScriptClasses, gdscript: GDScriptClass, arguments: Namespace
) -> MarkdownDocument:
    """Converts the data for a GDScript class to a markdown document, using the command line
    options."""

    content: List[str] = []
    output_format: OutputFormats = arguments.format

    if gdscript.name == "Main":
        gdscript.name = "Rakugo"

    name: str = gdscript.name
    if "abstract" in gdscript.metadata.tags:
        name += " " + surround_with_html("(abstract)", "small")
    
    paths = gdscript.jekyll_path.split("/")

    if output_format == OutputFormats.JEKYLL:

        if len(paths) >= 3:
            parent = paths[-2]

        else:
            parent = ""

        if parent == "gui":
            parent = "GUI"

        else:
            parent = parent.title()

        if gdscript.name == "Rakugo":
            content += [jekyll([
                "title: {}".format(gdscript.name),
                "permalink: {}".format("/rakugo"),
                "nav_order: 1",
            ])]

        else:
            content += [jekyll([
                "title: {}".format(gdscript.name),
                "permalink: {}".format(gdscript.jekyll_path),
                "parent: {}".format(parent),
            ])]

    if output_format == OutputFormats.MARDKOWN:
        content += [*make_heading(name, 1)]

    if gdscript.extends:
        extends_list: List[str] = gdscript.get_extends_tree(classes)
        extends_links = [make_link(entry, entry) for entry in extends_list]
        content += [make_bold("Extends:") + " " + " < ".join(extends_links)]

    description = _replace_references(classes, gdscript, gdscript.description)
    content += [*MarkdownSection("Description", 2, [description]).as_text()]

    for attribute, title in [("members", "Properties"), ("functions", "Functions")]:
        summary = _write_summary(gdscript, attribute)
        if not summary:
            continue
        content += MarkdownSection(title, 2, summary).as_text()

    if gdscript.signals:
        content += MarkdownSection(
            "Signals", 2, _write_signals(classes, gdscript, output_format)
        ).as_text()

    for attribute, title in [
        ("enums", "Enumerations"),
        ("members", "Property Descriptions"),
        ("functions", "Method Descriptions"),
    ]:
        if not getattr(gdscript, attribute):
            continue

        content += MarkdownSection(
            title, 2, _write(attribute, classes, gdscript, output_format)
        ).as_text()

    return MarkdownDocument(gdscript.name, content)


def _write_summary(gdscript: GDScriptClass, key: str) -> List[str]:
    element_list = getattr(gdscript, key)

    if not element_list:
        return []

    markdown: List[str] = make_table_header(["Type", "Name"])
    return markdown + [make_table_row(item.summarize()) for item in element_list]


def _write(
    attribute: str,
    classes: GDScriptClasses,
    gdscript: GDScriptClass,
    output_format: OutputFormats,
) -> List[str]:
    assert hasattr(gdscript, attribute)

    markdown: List[str] = []
    for element in getattr(gdscript, attribute):
        # assert element is Element
        markdown.extend(make_heading(element.get_heading_as_string(), 3))
        markdown.extend([make_code_block(element.signature), ""])
        markdown.extend(element.get_unique_attributes_as_markdown())
        markdown.append("")
        description: str = _replace_references(
            classes, gdscript, element.description)
        markdown.append(description)

    return markdown


def _write_signals(
    classes: GDScriptClasses, gdscript: GDScriptClass, output_format: OutputFormats
) -> List[str]:
    return wrap_in_newlines(
        [
            "- {}: {}".format(
                s.signature, _replace_references(
                    classes, gdscript, s.description)
            )
            for s in gdscript.signals
        ]
    )


def _write_index_page(classes: GDScriptClasses, info: ProjectInfo) -> MarkdownDocument:
    title: str = "{} ({})".format(
        info.name, surround_with_html(info.version, "small"))
    content: List[str] = [
        *MarkdownSection(title, 1, info.description).as_text(),
        *MarkdownSection("Contents", 2,
                        _write_table_of_contents(classes)).as_text(),
    ]
    return MarkdownDocument("index", content)


def _write_table_of_contents(classes: GDScriptClasses) -> List[str]:
    toc: List[str] = []

    by_category = classes.get_grouped_by_category()

    for group in by_category:
        indent: str = ""
        first_class: GDScriptClass = group[0]
        category: str = first_class.category
        if category:
            toc.append("- {}".format(make_bold(category)))
            indent = "  "

        for gdscript_class in group:
            link: str = indent + "- " + make_link(
                gdscript_class.name, gdscript_class.name
            )
            toc.append(link)

    return toc


def _replace_references(
    classes: GDScriptClasses, gdscript: GDScriptClass, description: str
) -> str:
    """Finds and replaces references to other classes or methods in the
`description`."""
    ERROR_MESSAGES = {
        "class": "Class {} not found in the class index.",
        "member": "Symbol {} not found in {}. The name might be incorrect.",
    }
    ERROR_TAIL = "The name might be incorrect."

    references: re.Match = re.findall(r"\[.+\]", description)
    for reference in references:
        # Matches [ClassName], [symbol], and [ClassName.symbol]
        match: re.Match = re.match(
            r"\[([A-Z][a-zA-Z0-9]*)?\.?([a-z0-9_]+)?\]", reference
        )
        if not match:
            continue

        class_name, member = match[1], match[2]

        if class_name and class_name not in classes.class_index:
            LOGGER.warning(ERROR_MESSAGES["class"].format(
                class_name) + ERROR_TAIL)
            continue

        if member and class_name:
            if member not in classes.class_index[class_name]:
                LOGGER.warning(
                    ERROR_MESSAGES["member"].format(
                        member, class_name) + ERROR_TAIL
                )
                continue

        elif member and member not in classes.class_index[gdscript.name]:
            LOGGER.warning(
                ERROR_MESSAGES["member"].format(
                    member, gdscript.name) + ERROR_TAIL
            )
            continue

        display_text, path = "", ""
        if class_name:
            display_text, path = class_name, class_name

        if class_name and member:
            display_text += "."
            path += "/"

        if member:
            display_text += member
            path += "#" + member.replace("_", "-")

        link: str = make_link(display_text, path)
        description = description.replace(reference, link, 1)

    return description
