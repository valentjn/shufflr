#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import math
import pathlib
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple


def _NormalizeNumbers(numbers: Sequence[int]) -> List[float]:
  minimumNumber = min(numbers)
  maximumNumer = max(numbers)
  return [(value - minimumNumber) / (maximumNumer - minimumNumber) for value in numbers]


class GenreDistanceComputer(object):
  @staticmethod
  def _LoadData() -> Dict[str, Tuple[float, float, float, float, float]]:
    genresFilePath = pathlib.Path(__file__).parent / "genres.json"

    with open(genresFilePath, "r") as genresFile:
      data: Dict[str, Tuple[int, int, int, int, int]] = json.load(genresFile)

    genres = list(data.keys())
    xs = _NormalizeNumbers([genreData[0] for genreData in data.values()])
    ys = _NormalizeNumbers([genreData[1] for genreData in data.values()])
    rs = [genreData[2] for genreData in data.values()]
    gs = [genreData[3] for genreData in data.values()]
    bs = [genreData[4] for genreData in data.values()]
    colorFactor = 1.0 / (math.sqrt(3) * 255.0)
    return {
      genres[index]: (xs[index], ys[index], colorFactor * rs[index], colorFactor * gs[index], colorFactor * bs[index])
      for index in range(len(data))
    }

  _data = _LoadData()
  _cache: Dict[FrozenSet[str], Optional[float]] = {}

  @staticmethod
  def ComputeDistance(genre1: str, genre2: str) -> Optional[float]:
    cacheKey = frozenset((genre1, genre2))

    try:
      return GenreDistanceComputer._cache[cacheKey]
    except KeyError:
      pass

    try:
      genreData1 = GenreDistanceComputer._data[genre1]
      genreData2 = GenreDistanceComputer._data[genre2]
    except KeyError:
      GenreDistanceComputer._cache[cacheKey] = None
      return None

    distance = math.sqrt((
        (genreData1[0] - genreData2[0]) ** 2.0 +
        (genreData1[1] - genreData2[1]) ** 2.0 +
        (genreData1[2] - genreData2[2]) ** 2.0 +
        (genreData1[3] - genreData2[3]) ** 2.0 +
        (genreData1[4] - genreData2[4]) ** 2.0
      ) / 5.0
    )
    GenreDistanceComputer._cache[cacheKey] = distance
    return distance


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
    if self == other: return 0.0
    genreDistances = [
      GenreDistanceComputer.ComputeDistance(selfGenre, otherGenre)
      for selfGenre in self.genres for otherGenre in other.genres
    ]
    nonNoneGenreDistances = [genreDistance for genreDistance in genreDistances if genreDistance is not None]
    return min(nonNoneGenreDistances) if len(nonNoneGenreDistances) > 0 else 1.0
