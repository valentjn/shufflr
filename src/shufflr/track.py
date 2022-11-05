#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import enum
import math
import statistics
from typing import List, Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
  import shufflr.artist
  import shufflr.client
  import shufflr.configuration


class Key(enum.Enum):
  cMajor = 0
  cMinor = 1
  dFlatMajor = 2
  dFlatMinor = 3
  dMinor = 4
  dMajor = 5
  eFlatMajor = 6
  eFlatMinor = 7
  eMajor = 8
  eMinor = 9
  fMajor = 10
  fMinor = 11
  fSharpMajor = 12
  fSharpMinor = 13
  gMajor = 14
  gMinor = 15
  aFlatMajor = 16
  aFlatMinor = 17
  aMajor = 18
  aMinor = 19
  bFlatMajor = 20
  bFlatMinor = 21
  bMinor = 22
  bMajor = 23

  def __str__(self) -> str:
    letter = self.name[0].upper() if "Major" in self.name else self.name[0].lower()

    if "Flat" in self.name:
      suffix = "\u266d"
    elif "Sharp" in self.name:
      suffix = "\u266f"
    else:
      suffix = ""

    return letter + suffix

  @staticmethod
  def FromSpotifyNotation(spotifyKey: int, spotifyMode: int) -> Optional["Key"]:
    if spotifyKey == -1:
      return None
    elif spotifyMode == 1:
      return [Key.cMajor, Key.dFlatMajor, Key.dMajor, Key.eFlatMajor, Key.eMajor, Key.fMajor,
              Key.fSharpMajor, Key.gMajor, Key.aFlatMajor, Key.aMajor, Key.bFlatMajor, Key.bMajor][spotifyKey]
    else:
      return [Key.cMinor, Key.dFlatMinor, Key.dMinor, Key.eFlatMinor, Key.eMinor, Key.fMinor,
              Key.fSharpMinor, Key.gMinor, Key.aFlatMinor, Key.aMinor, Key.bFlatMinor, Key.bMinor][spotifyKey]

  def IsCompatible(self, other: "Key") -> bool:
    majorKeys = [
      Key.cMajor, Key.gMajor, Key.dMajor, Key.aMajor, Key.eMajor, Key.bMajor,
      Key.fSharpMajor, Key.dFlatMajor, Key.aFlatMajor, Key.eFlatMajor, Key.bFlatMajor, Key.fMajor,
    ]
    minorKeys = [
      Key.aMinor, Key.eMinor, Key.bMinor, Key.fSharpMinor, Key.dFlatMinor, Key.aFlatMinor,
      Key.eFlatMinor, Key.bFlatMinor, Key.fMinor, Key.cMinor, Key.gMinor, Key.dMinor,
    ]

    selfMajorIndex = Key._FindKey(self, majorKeys)
    selfMinorIndex = Key._FindKey(self, minorKeys)
    otherMajorIndex = Key._FindKey(other, majorKeys)
    otherMinorIndex = Key._FindKey(other, minorKeys)

    if (selfMajorIndex is not None) and (otherMajorIndex is not None):
      return (
        (selfMajorIndex == otherMajorIndex) or
        (selfMajorIndex == otherMajorIndex - 1) or
        (selfMajorIndex == otherMajorIndex + 1) or
        (selfMajorIndex == otherMajorIndex - 11) or
        (selfMajorIndex == otherMajorIndex + 11)
      )
    elif (selfMinorIndex is not None) and (otherMinorIndex is not None):
      return (
        (selfMinorIndex == otherMinorIndex) or
        (selfMinorIndex == otherMinorIndex - 1) or
        (selfMinorIndex == otherMinorIndex + 1) or
        (selfMinorIndex == otherMinorIndex - 11) or
        (selfMinorIndex == otherMinorIndex + 11)
      )
    elif (selfMajorIndex is not None) and (otherMinorIndex is not None):
      return selfMajorIndex == otherMinorIndex
    else:
      return selfMinorIndex == otherMajorIndex

  @staticmethod
  def _FindKey(key: "Key", keys: List["Key"]) -> Optional[int]:
    try:
      return keys.index(key)
    except ValueError:
      return None


class Track(object):
  def __init__(
    self,
    id_: str,
    name: str,
    artistIDs: Iterable[str],
    client: "shufflr.client.Client",
    acousticness: float,
    danceability: float,
    energy: float,
    instrumentalness: float,
    key: Optional[Key],
    liveness: float,
    speechiness: float,
    tempo: float,
    valence: float,
  ) -> None:
    self.id = id_
    self.name = name
    self.artistIDs = list(artistIDs)
    self.client = client
    self.acousticness = acousticness
    self.danceability = danceability
    self.energy = energy
    self.instrumentalness = instrumentalness
    self.key = key
    self.liveness = liveness
    self.speechiness = speechiness
    self.tempo = tempo
    self.valence = valence

  def __eq__(self, other: object) -> bool:
    return isinstance(other, Track) and (self.id == other.id)

  def __hash__(self) -> int:
    return hash(self.id)

  def GetArtists(self) -> List["shufflr.artist.Artist"]:
    return self.client.QueryArtists(self.artistIDs)

  def ComputeDistance(self, other: "Track", configuration: "shufflr.configuration.Configuration") -> float:
    maximumTempoDifference = 10.0
    if self == other: return 0.0
    differentArtistDistance = 1.0 if len(set(self.artistIDs) & set(other.artistIDs)) > 0 else 0.0
    genreDistance = statistics.mean(
      self.client.QueryArtist(selfArtistID).ComputeDistance(self.client.QueryArtist(otherArtistID))
      for selfArtistID in self.artistIDs for otherArtistID in other.artistIDs
    )
    keyDistance = (0.0 if (self.key is not None) and (other.key is not None) and self.key.IsCompatible(other.key) else
                   1.0)
    tempoDistance = min(abs(self.tempo - other.tempo) / maximumTempoDifference, 1.0)
    distance = math.sqrt(
      configuration.acousticnessWeight * (self.acousticness - other.acousticness) ** 2.0 +
      configuration.danceabilityWeight * (self.danceability - other.danceability) ** 2.0 +
      configuration.differentArtistWeight * differentArtistDistance ** 2.0 +
      configuration.energyWeight * (self.energy - other.energy) ** 2.0 +
      configuration.genreWeight * genreDistance ** 2.0 +
      configuration.instrumentalnessWeight * (self.instrumentalness - other.instrumentalness) ** 2.0 +
      configuration.keyWeight * keyDistance ** 2.0 +
      configuration.livenessWeight * (self.liveness - other.liveness) ** 2.0 +
      configuration.speechinessWeight * (self.speechiness - other.speechiness) ** 2.0 +
      configuration.tempoWeight * tempoDistance ** 2.0 +
      configuration.valenceWeight * (self.valence - other.valence) ** 2.0
    )
    return distance
