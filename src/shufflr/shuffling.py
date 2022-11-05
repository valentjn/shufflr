#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import functools
import shutil
from typing import cast, List, Optional, Sequence, Set, TYPE_CHECKING

import numpy as np
import numpy.typing as npt
import ortools.constraint_solver.routing_enums_pb2 as routing_enums_pb2
import ortools.constraint_solver.pywrapcp as pywrapcp

from shufflr.logging import gLogger

if TYPE_CHECKING:
  import shufflr.track


def ShuffleTracks(
  tracks: Set["shufflr.track.Track"],
  maximumNumberOfTracks: Optional[int] = None,
  verbose: int = 0,
) -> List["shufflr.track.Track"]:
  trackList = list(tracks)
  distanceMatrix = ComputeDistanceMatrix(trackList)
  shuffledTrackIndices = SolveTravelingSalespersonProblem(distanceMatrix, verbose=verbose)
  shuffledTrackList = [trackList[trackIndex] for trackIndex in shuffledTrackIndices]
  if maximumNumberOfTracks is not None: shuffledTrackList = shuffledTrackList[:maximumNumberOfTracks]

  if verbose >= 0:
    distances = [
      distanceMatrix[previousTrackIndex, currentTrackIndex]
      for previousTrackIndex, currentTrackIndex in zip(shuffledTrackIndices[:-1], shuffledTrackIndices[1:])
    ]
    print(FormatTracks(shuffledTrackList, distances))

  return shuffledTrackList


def ComputeDistanceMatrix(tracks: Sequence["shufflr.track.Track"]) -> npt.NDArray[np.double]:
  gLogger.info("Computing distance matrix...")
  distanceMatrix = np.zeros((len(tracks), len(tracks)))

  for trackIndex1, track1 in enumerate(tracks):
    for trackIndex2, track2 in enumerate(tracks):
      distanceMatrix[trackIndex1, trackIndex2] = (track1.ComputeDistance(track2) if trackIndex1 <= trackIndex2 else
                                                  distanceMatrix[trackIndex2, trackIndex1])

  return distanceMatrix


def SolveTravelingSalespersonProblem(distanceMatrix: npt.NDArray[np.float_], verbose: int = 0) -> List[int]:
  integerDistanceScalingFactor = 1000
  timeLimitInSeconds = 10
  gLogger.info("Solving TSP...")

  numberOfLocations = distanceMatrix.shape[0]
  integerDistanceMatrix = (integerDistanceScalingFactor * distanceMatrix).astype(int)
  integerDistanceMatrix = np.hstack((
    np.vstack((integerDistanceMatrix, np.zeros((1, numberOfLocations), dtype=int))),
    np.zeros((numberOfLocations + 1, 1), dtype=int),
  ))

  routingIndexManager = pywrapcp.RoutingIndexManager(
    integerDistanceMatrix.shape[0],
    1,
    numberOfLocations,
  )
  routingModel = pywrapcp.RoutingModel(routingIndexManager)
  transitCallbackIndex = routingModel.RegisterTransitCallback(
    functools.partial(TravelingSalespersonDistanceCallback, integerDistanceMatrix, routingIndexManager)
  )
  routingModel.SetArcCostEvaluatorOfAllVehicles(transitCallbackIndex)
  searchParameters = pywrapcp.DefaultRoutingSearchParameters()
  searchParameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
  searchParameters.time_limit.seconds = timeLimitInSeconds
  searchParameters.log_search = verbose >= 1
  solution = routingModel.SolveWithParameters(searchParameters)

  indices = []
  index = solution.Value(routingModel.NextVar(routingModel.Start(0)))

  while not routingModel.IsEnd(index):
    indices.append(routingIndexManager.IndexToNode(index))
    index = solution.Value(routingModel.NextVar(index))

  return indices


def TravelingSalespersonDistanceCallback(
  integerDistanceMatrix: npt.NDArray[np.int_],
  routingIndexManager: pywrapcp.RoutingIndexManager,
  fromIndex: int,
  toIndex: int,
) -> int:
  return cast(
    int,
    integerDistanceMatrix[routingIndexManager.IndexToNode(fromIndex), routingIndexManager.IndexToNode(toIndex)],
  )


def FormatTracks(tracks: Sequence["shufflr.track.Track"], distances: Sequence[float]) -> str:
  lengthOfRemainingColumns = 50
  terminalWidth = shutil.get_terminal_size().columns
  artistAndTrackNameLength = terminalWidth - lengthOfRemainingColumns - 3
  artistNameLength = artistAndTrackNameLength // 2
  trackNameLength = artistAndTrackNameLength - artistNameLength
  formatString = (
    f"{{:{artistNameLength}}}  {{:{trackNameLength}}}  {{:>3}}  "
    f"{{:>3}}  {{:>3}}  {{:>3}}  {{:>3}}  {{:>3}}  {{:>3}}  {{:>3}}  {{:>3}}  {{:>3}}"
  )
  header = formatString.format("ARTIST", "TITLE", "DST", "ACS", "DNC", "ENR", "INS", "KEY", "LVN", "SPC", "TMP", "VLN")
  body = "\n".join(
    formatString.format(
      ", ".join(artist.name for artist in track.GetArtists())[:artistNameLength],
      track.name[:trackNameLength],
      (FormatFraction(min(distances[trackIndex - 1], 9.99)) if trackIndex > 0 else "-"),
      FormatFraction(track.acousticness),
      FormatFraction(track.danceability),
      FormatFraction(track.energy),
      FormatFraction(track.instrumentalness),
      str(track.key),
      FormatFraction(track.liveness),
      FormatFraction(track.speechiness),
      str(round(track.tempo)),
      FormatFraction(track.valence),
    ) for trackIndex, track in enumerate(tracks)
  )
  return f"{header}\n{body}"


def FormatFraction(fraction: float) -> str:
  return str(round(100 * fraction))
