#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import html
import json
import pathlib
import re
import ssl
from typing import cast, Dict, Tuple
import urllib.request


def Main() -> None:
  genresFilePath = pathlib.Path(__file__).parent.parent / "src/shufflr/genres.json"
  everyNoiseAtOnceHTML = GetEveryNoiseAtOnceHTML()
  genresData = ExtractGenresDataFromHTML(everyNoiseAtOnceHTML)
  genresJSON = FormatGenresDataAsJSON(genresData)
  with open(genresFilePath, "w", newline="\n") as file: file.write(genresJSON)


def GetEveryNoiseAtOnceHTML() -> str:
  url = "https://everynoise.com/"
  context = ssl.create_default_context()
  context.check_hostname = False
  context.verify_mode = ssl.CERT_NONE

  with urllib.request.urlopen(url, context=context) as response:
    return cast(str, response.read().decode("utf-8"))


def ExtractGenresDataFromHTML(everyNoiseAtOnceHTML: str) -> Dict[str, Tuple[int, int, int, int, int]]:
  matches = re.findall(
    r"style=\"color: *#([0-9a-fA-F]{6}); *top: *(-?[0-9]+)px; *left: *(-?[0-9]+)px;[^>]*>([^<]+)<",
    everyNoiseAtOnceHTML,
  )
  genresData = {html.unescape(match[3]): (int(match[2]), int(match[1]), *ParseHexColor(match[0])) for match in matches}
  genresData = {genre: genresData[genre] for genre in sorted(genresData.keys())}
  return genresData


def ParseHexColor(hexColor: str) -> Tuple[int, int, int]:
  return int(hexColor[:2], base=16), int(hexColor[2:4], base=16), int(hexColor[4:6], base=16)


def FormatGenresDataAsJSON(genresData: Dict[str, Tuple[int, int, int, int, int]]) -> str:
  return "{{{}\n}}\n".format(",".join(
    "\n  {}: [{}]".format(json.dumps(genre), ", ".join(f"{item}" for item in genreData))
    for genre, genreData in genresData.items()
  ))


if __name__ == "__main__": Main()
