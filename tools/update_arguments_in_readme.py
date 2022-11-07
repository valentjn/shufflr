#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import pathlib
import re

import shufflr.configuration


def FormatArgumentParserAsMarkdown(argumentParser: argparse.ArgumentParser) -> str:
  markdown = ""

  for argumentGroup in argumentParser._action_groups:
    if len(argumentGroup._group_actions) == 0: continue
    assert argumentGroup.title is not None
    markdown += "* **{}:** {}\n".format(
      ConvertToMarkdownLink(argumentGroup.title),
      ", ".join(
        ConvertToMarkdownLink(" / ".join(f"`{argument}`" for argument in action.option_strings))
        for action in argumentGroup._group_actions
      ),
    )

  markdown += "\n"
  isFirstArgumentGroup = True

  for argumentGroup in argumentParser._action_groups:
    if len(argumentGroup._group_actions) == 0: continue
    if not isFirstArgumentGroup: markdown += "\n"
    assert argumentGroup.title is not None
    argumentGroupTitle = " ".join(word[0].upper() + word[1:] for word in argumentGroup.title.split())
    markdown += f"### {argumentGroupTitle}\n\n"
    isFirstAction = True

    for action in argumentGroup._group_actions:
      if not isFirstAction: markdown += "\n"
      markdown += "#### {}\n\n".format(" / ".join(f"`{argument}`" for argument in action.option_strings))
      if action.required: markdown += "Required.\n\n"

      if isinstance(action, argparse._StoreAction):
        metavar = action.metavar if action.metavar is not None else action.option_strings[-1].upper().lstrip("-")

        if action.nargs is None:
          valuesString = metavar
        elif action.nargs == "+":
          valuesString = f"{metavar} [{metavar} ...]"
        else:
          raise ValueError(f"Unsupported nargs value {valuesString!r}.")

        markdown += "Format: {}\n\n".format(
          " / ".join(f"`{argument} {valuesString}`" for argument in action.option_strings)
        )

      markdown += f"{action.help}"

      if isinstance(action, argparse._StoreAction) and (action.default is not None):
        markdown += f" (default value: `{action.default}`)"

      markdown += "\n"
      isFirstAction = False

    isFirstArgumentGroup = False

  return markdown


def ConvertToMarkdownLink(sectionTitle: str) -> str:
  slug = re.sub(r"[^A-Za-z0-9- ]", "", sectionTitle).replace(" ", "-").lower()
  return f"[{sectionTitle}](#{slug})"


def Main() -> None:
  readmePath = pathlib.Path(__file__).parent.parent / "README.md"
  argumentsHeading = "## Arguments"

  argumentParser = shufflr.configuration.Configuration.CreateArgumentParser()
  argumentsMarkdown = FormatArgumentParserAsMarkdown(argumentParser)

  readmeMarkdown = readmePath.read_text()
  readmeMarkdown = re.sub(
    re.escape(argumentsHeading) + r".*",
    f"{argumentsHeading}\n\n{argumentsMarkdown}",
    readmeMarkdown,
    flags=re.DOTALL,
  )
  with open(readmePath, "w", newline="\n") as file: file.write(readmeMarkdown)


if __name__ == "__main__": Main()
