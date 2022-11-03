#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import math
import statistics
from typing import List, Iterable, TYPE_CHECKING

if TYPE_CHECKING:
  import shufflr.artist as artist
  import shufflr.client as client


class Track(object):
  def __init__(
    self,
    id_: str,
    name: str,
    artistIDs: Iterable[str],
    client: "client.Client",
    acousticness: float,
    danceability: float,
    energy: float,
    instrumentalness: float,
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
    self.liveness = liveness
    self.speechiness = speechiness
    self.tempo = tempo
    self.valence = valence

  def __eq__(self, other: object) -> bool:
    return isinstance(other, Track) and (self.id == other.id)

  def __hash__(self) -> int:
    return hash(self.id)

  def GetArtists(self) -> List["artist.Artist"]:
    return self.client.QueryArtists(self.artistIDs)

  def ComputeDistance(self, other: "Track") -> float:
    acousticnessWeight = 1.0
    danceabilityWeight = 1.0
    energyWeight = 1.0
    genreWeight = 3.0
    instrumentalnessWeight = 1.0
    livenessWeight = 1.0
    speechinessWeight = 1.0
    tempoWeight = 2.0
    valenceWeight = 1.0
    maximumTempoDifference = 10.0

    if self == other: return 0.0
    genreDistance = statistics.mean(
      self.client.QueryArtist(selfArtistID).ComputeDistance(self.client.QueryArtist(otherArtistID))
      for selfArtistID in self.artistIDs for otherArtistID in other.artistIDs
    )
    tempoDistance = min(abs(self.tempo - other.tempo) / maximumTempoDifference, 1.0)
    distance = math.sqrt(
      acousticnessWeight * (self.acousticness - other.acousticness) ** 2.0 +
      danceabilityWeight * (self.danceability - other.danceability) ** 2.0 +
      energyWeight * (self.energy - other.energy) ** 2.0 +
      genreWeight * genreDistance ** 2.0 +
      instrumentalnessWeight * (self.instrumentalness - other.instrumentalness) ** 2.0 +
      livenessWeight * (self.liveness - other.liveness) ** 2.0 +
      speechinessWeight * (self.speechiness - other.speechiness) ** 2.0 +
      tempoWeight * tempoDistance ** 2.0 +
      valenceWeight * (self.valence - other.valence) ** 2.0
    )
    return distance
