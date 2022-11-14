#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import functools
import math
import shutil
from typing import cast, List, Optional, Sequence, Set, TYPE_CHECKING

import numpy as np
import numpy.typing as npt
import ortools.constraint_solver.routing_enums_pb2 as routing_enums_pb2
import ortools.constraint_solver.pywrapcp as pywrapcp

from shufflr.logging import gLogger

if TYPE_CHECKING:
  import shufflr.configuration
  import shufflr.track


class RoutingMonitor(object):
  def __init__(
    self,
    routingModel: pywrapcp.RoutingModel,
    improvementSize: float,
    improvementTimeout: datetime.timedelta,
  ) -> None:
    self.routingModel = routingModel
    self.improvementSize = improvementSize
    self.improvementTimeout = improvementTimeout
    self._solutionTimes: List[datetime.datetime] = []
    self._currentObjectiveValues: List[float] = []
    self._bestObjectiveValues: List[float] = []
    self._didHitImprovementTimeout = False

  @property
  def didHitImprovementTimeout(self) -> bool:
    return self._didHitImprovementTimeout

  def __call__(self) -> None:
    solutionTime = datetime.datetime.now()
    currentObjectiveValue = self.routingModel.CostVar().Min()
    bestObjectiveValue = (min(currentObjectiveValue, self._bestObjectiveValues[-1])
                          if len(self._bestObjectiveValues) > 0 else currentObjectiveValue)
    self._solutionTimes.append(solutionTime)
    self._currentObjectiveValues.append(currentObjectiveValue)
    self._bestObjectiveValues.append(bestObjectiveValue)

    comparisonSolutionIndex = self.SearchSolutionTime(solutionTime - self.improvementTimeout)

    if (
      (comparisonSolutionIndex is not None) and
      (
        (self._bestObjectiveValues[comparisonSolutionIndex] - bestObjectiveValue) /
        (self._bestObjectiveValues[0] - bestObjectiveValue) < self.improvementSize
      )
    ):
      self._didHitImprovementTimeout = True
      self.routingModel.solver().FinishCurrentSearch()

  def SearchSolutionTime(self, queryTime: datetime.datetime) -> Optional[int]:
    return next(
      (
        len(self._solutionTimes) - reversedSolutionIndex - 1
        for reversedSolutionIndex, solutionTime in enumerate(reversed(self._solutionTimes))
        if solutionTime <= queryTime
      ),
      None,
    )

  def PlotObjectiveValue(self) -> None:
    import matplotlib.pyplot as plt

    figure = plt.figure()
    axes = figure.add_subplot()
    times = [(time - self._solutionTimes[0]).total_seconds() for time in self._solutionTimes]
    axes.plot(times, self._currentObjectiveValues, ".-")
    axes.plot(times, self._bestObjectiveValues, ".-")
    axes.set_title("Evolution of TSP Objective Value")
    axes.set_xlabel("Time [s]")
    axes.set_ylabel("Objective value")
    axes.legend(["Current solution", "Best known solution"])
    gLogger.info("Showing TSP plot. Close plot to continue...")
    plt.show()


def ShuffleTracks(
  loginUserID: str,
  tracks: Set["shufflr.track.Track"],
  configuration: "shufflr.configuration.Configuration",
) -> List["shufflr.track.Track"]:
  trackList = list(tracks)
  distanceMatrix = ComputeDistanceMatrix(loginUserID, trackList, configuration)
  shuffledTrackIndices = SolveTravelingSalespersonProblem(
    distanceMatrix,
    configuration.tspTimeout,
    configuration.tspImprovementSize,
    configuration.tspImprovementTimeout,
    plot=configuration.plotTSP,
    verbose=configuration.verbose,
  )
  shuffledTrackList = [trackList[trackIndex] for trackIndex in shuffledTrackIndices]

  if configuration.maximumNumberOfSongs is not None:
    shuffledTrackList = shuffledTrackList[:configuration.maximumNumberOfSongs]

  if configuration.verbose >= 0:
    distances = [
      distanceMatrix[previousTrackIndex, currentTrackIndex]
      for previousTrackIndex, currentTrackIndex in zip(shuffledTrackIndices[:-1], shuffledTrackIndices[1:])
    ]
    print(FormatTracks(loginUserID, shuffledTrackList, distances))

  return shuffledTrackList


def ComputeDistanceMatrix(
  loginUserID: str,
  tracks: Sequence["shufflr.track.Track"],
  configuration: "shufflr.configuration.Configuration",
) -> npt.NDArray[np.double]:
  gLogger.info("Computing distance matrix...")
  distanceMatrix = np.zeros((len(tracks), len(tracks)))

  for trackIndex1, track1 in enumerate(tracks):
    for trackIndex2, track2 in enumerate(tracks):
      distanceMatrix[trackIndex1, trackIndex2] = (
        track1.ComputeDistance(loginUserID, track2, configuration) if trackIndex1 <= trackIndex2 else
        distanceMatrix[trackIndex2, trackIndex1]
      )

  return distanceMatrix


def SolveTravelingSalespersonProblem(
  distanceMatrix: npt.NDArray[np.float_],
  timeout: datetime.timedelta,
  improvementSize: float,
  improvementTimeout: datetime.timedelta,
  plot: bool = False,
  verbose: int = 0,
) -> List[int]:
  integerDistanceScalingFactor = 1000
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
  routingMonitor = RoutingMonitor(routingModel, improvementSize, improvementTimeout)
  routingModel.AddAtSolutionCallback(routingMonitor)
  searchParameters = pywrapcp.DefaultRoutingSearchParameters()
  searchParameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
  searchParameters.time_limit.seconds = math.ceil(timeout.total_seconds())
  searchParameters.log_search = verbose >= 1
  solution = routingModel.SolveWithParameters(searchParameters)
  stoppingReason = "improvement timeout" if routingMonitor.didHitImprovementTimeout else "timeout"
  gLogger.info(
    f"Using solution of TSP with objective value {solution.ObjectiveValue()} (stopping reason: {stoppingReason})."
  )
  if plot: routingMonitor.PlotObjectiveValue()

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


def FormatTracks(loginUserID: str, tracks: Sequence["shufflr.track.Track"], distances: Sequence[float]) -> str:
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
      ", ".join(artist.name for artist in track.GetArtists(loginUserID))[:artistNameLength],
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
