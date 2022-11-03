#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import difflib
from typing import Dict, FrozenSet, Iterable


class LongestCommonSubstringComputer(object):
  _cache: Dict[FrozenSet[str], int] = {}

  @staticmethod
  def ComputeLength(string1: str, string2: str) -> int:
    cacheKey = frozenset([string1, string2])

    if cacheKey in LongestCommonSubstringComputer._cache:
      length = LongestCommonSubstringComputer._cache[cacheKey]
    else:
      length = difflib.SequenceMatcher(None, string1, string2, autojunk=False).find_longest_match().size
      LongestCommonSubstringComputer._cache[cacheKey] = length

    return length


class Artist(object):
  def __init__(self, id_: str, name: str, genres: Iterable[str]) -> None:
    self.id = id_
    self.name = name
    self.genres = list(genres)

  def __eq__(self, other: object) -> bool:
    return isinstance(other, Artist) and (self.id == other.id)

  def __hash__(self) -> int:
    return hash(self.id)

  def ComputeDistance(self, other: "Artist") -> float:
    if self == other:
      return 0.0
    elif (len(self.genres) == 0) or (len(other.genres) == 0):
      return 1.0
    else:
      return min(1.0 - LongestCommonSubstringComputer.ComputeLength(selfGenre, otherGenre) /
                 min(len(selfGenre), len(otherGenre))
                 for selfGenre in self.genres for otherGenre in other.genres)
