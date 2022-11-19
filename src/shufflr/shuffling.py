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
from typing import cast, Iterable, List, Optional, Sequence, Set, TYPE_CHECKING

import numpy as np
import numpy.typing as npt
import ortools.constraint_solver.routing_enums_pb2 as routing_enums_pb2
import ortools.constraint_solver.pywrapcp as pywrapcp

from shufflr.logging import gLogger

if TYPE_CHECKING:
  import shufflr.configuration
  import shufflr.track


class Solution(object):
  def __init__(
    self,
    nodeIndices: Iterable[int],
    objectiveValue: float,
    time: Optional[datetime.datetime] = None,
  ) -> None:
    self._nodeIndices = list(nodeIndices)
    self._objectiveValue = objectiveValue
    self._time = time if time is not None else datetime.datetime.now()

  @property
  def nodeIndices(self) -> List[int]:
    return list(self._nodeIndices)

  @property
  def objectiveValue(self) -> float:
    return self._objectiveValue

  @property
  def time(self) -> datetime.datetime:
    return self._time


class RoutingMonitor(object):
  def __init__(
    self,
    routingModel: pywrapcp.RoutingModel,
    routingIndexManager: pywrapcp.RoutingIndexManager,
    distanceMatrix: npt.NDArray[np.float_],
    nodeNames: Iterable[str],
    improvementSize: float,
    improvementTimeout: datetime.timedelta,
  ) -> None:
    if TYPE_CHECKING:
      import matplotlib.animation

    self._routingModel = routingModel
    self._routingIndexManager = routingIndexManager
    self._distanceMatrix = distanceMatrix
    self._nodeNames = nodeNames
    self._improvementSize = improvementSize
    self._improvementTimeout = improvementTimeout

    self._solutions: List[Solution] = []
    self._bestSolutions: List[Solution] = []
    self._didHitImprovementTimeout = False
    self._nodeEmbedding: Optional[npt.NDArray[np.float_]] = None
    self._plotAnimations: List["matplotlib.animation.Animation"] = []

  @property
  def didHitImprovementTimeout(self) -> bool:
    return self._didHitImprovementTimeout

  @property
  def bestKnownSolution(self) -> Optional[Solution]:
    return self._bestSolutions[-1] if len(self._bestSolutions) > 0 else None

  def __call__(self) -> None:
    currentSolution = Solution(self._GetSolutionNodeIndices(), self._routingModel.CostVar().Min())
    bestSolution = (
      currentSolution
      if (len(self._bestSolutions) == 0) or (currentSolution.objectiveValue <= self._bestSolutions[-1].objectiveValue)
      else self._bestSolutions[-1]
    )
    self._solutions.append(currentSolution)
    self._bestSolutions.append(bestSolution)
    comparisonSolution = self._SearchBestSolutionByTime(currentSolution.time - self._improvementTimeout)

    if (
      (comparisonSolution is not None) and
      (
        (comparisonSolution.objectiveValue - bestSolution.objectiveValue) /
        (self._bestSolutions[0].objectiveValue - bestSolution.objectiveValue) < self._improvementSize
      )
    ):
      self._didHitImprovementTimeout = True
      self._routingModel.solver().FinishCurrentSearch()

  def _SearchBestSolutionByTime(self, queryTime: datetime.datetime) -> Optional[Solution]:
    return next(
      (
        bestSolution for solution, bestSolution in zip(reversed(self._solutions), reversed(self._bestSolutions))
        if solution.time <= queryTime
      ), None,
    )

  def _GetSolutionNodeIndices(self) -> List[int]:
    indices = []
    index = self._routingModel.NextVar(self._routingModel.Start(0)).Value()

    while not self._routingModel.IsEnd(index):
      indices.append(self._routingIndexManager.IndexToNode(index))
      index = self._routingModel.NextVar(index).Value()

    return indices

  def PlotObjectiveValue(self) -> None:
    import matplotlib.pyplot as plt

    times = [(solution.time - self._solutions[0].time).total_seconds() for solution in self._solutions]

    figure = plt.figure()
    axes = figure.add_subplot()
    axes.plot(times, [bestSolution.objectiveValue for bestSolution in self._bestSolutions], ".-")
    axes.plot(times, [solution.objectiveValue for solution in self._solutions], ".-")
    axes.set_title("Evolution of TSP Objective Value")
    axes.set_xlabel("Time [s]")
    axes.set_ylabel("Objective value")
    axes.legend(["Best known solution", "Current solution"])

  def PlotSolution(self, isAnimated: bool = False) -> None:
    import matplotlib.animation
    import matplotlib.patheffects
    import matplotlib.pyplot as plt

    if self._nodeEmbedding is None:
      self._nodeEmbedding = RoutingMonitor._ComputeEmbeddingOfNodes(self._distanceMatrix)

    solutionIndex = 0 if isAnimated else len(self._solutions) - 1
    nodeIndices = self._bestSolutions[solutionIndex].nodeIndices

    figure = plt.figure()
    axes = figure.add_subplot()
    bestSolutionLine, = axes.plot(self._nodeEmbedding[nodeIndices, 0], self._nodeEmbedding[nodeIndices, 1], "-")

    if isAnimated:
      currentSolutionLine, = axes.plot(self._nodeEmbedding[nodeIndices, 0], self._nodeEmbedding[nodeIndices, 1], "-")

      def UpdatePlot(frame: int) -> List[plt.Line2D]:
        assert self._nodeEmbedding is not None
        bestSolutionNodeIndices = self._bestSolutions[frame].nodeIndices
        bestSolutionLine.set_xdata(self._nodeEmbedding[bestSolutionNodeIndices, 0])
        bestSolutionLine.set_ydata(self._nodeEmbedding[bestSolutionNodeIndices, 1])
        currentSolutionNodeIndices = self._solutions[frame].nodeIndices
        currentSolutionLine.set_xdata(self._nodeEmbedding[currentSolutionNodeIndices, 0])
        currentSolutionLine.set_ydata(self._nodeEmbedding[currentSolutionNodeIndices, 1])
        axes.set_title(axisTitleFormat.format(frame + 1))
        return [currentSolutionLine, bestSolutionLine]

      self._plotAnimations.append(matplotlib.animation.FuncAnimation(
        figure,
        UpdatePlot,
        interval=50,
        frames=len(self._solutions),
      ))

    axes.plot(self._nodeEmbedding[:, 0], self._nodeEmbedding[:, 1], "k.")

    if not isAnimated:
      for node, nodeName in zip(self._nodeEmbedding, self._nodeNames):
        text = axes.text(node[0], node[1], f" {nodeName}", verticalalignment="center", fontsize=8)
        text.set_path_effects([matplotlib.patheffects.withStroke(linewidth=2, foreground="w", alpha=0.7)])

    axisTitleFormat = f"T-SNE Embedding and TSP Solution (Iteration {{}}/{len(self._solutions)})"
    axes.set_title(axisTitleFormat.format(solutionIndex + 1))
    axes.set_xlabel("$x_1$")
    axes.set_ylabel("$x_2$")
    axes.legend(["Best known solution"] + (["Current solution"] if isAnimated else []))

  @staticmethod
  def _ComputeEmbeddingOfNodes(distanceMatrix: npt.NDArray[np.float_]) -> npt.NDArray[np.float_]:
    import sklearn.manifold

    gLogger.info("Computing embedding of nodes...")
    fitter = sklearn.manifold.TSNE(n_components=2, learning_rate="auto", metric="precomputed", init="random", perplexity=10.0)
    return cast(npt.NDArray[np.float_], fitter.fit_transform(distanceMatrix))

  def ShowPlots(self) -> None:
    import matplotlib.pyplot as plt

    gLogger.info("Showing TSP plots. Close plots to continue...")
    plt.show()


def ShuffleTracks(
  loginUserID: str,
  tracks: Set["shufflr.track.Track"],
  configuration: "shufflr.configuration.Configuration",
) -> List["shufflr.track.Track"]:
  maximumArtistLength = 10
  maximumTitleLength = 20
  trackList = list(tracks)
  distanceMatrix = ComputeDistanceMatrix(loginUserID, trackList, configuration)
  nodeNames = [
    "{} - {}".format(
      TruncateString(", ".join(artist.name for artist in track.GetArtists(loginUserID)), maximumArtistLength),
      TruncateString(track.name, maximumTitleLength),
    ) for track in trackList
  ]
  shuffledTrackIndices = SolveTravelingSalespersonProblem(
    distanceMatrix,
    nodeNames,
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


def TruncateString(string: str, maximumLength: int) -> str:
  return string if len(string) <= maximumLength else f"{string[:maximumLength - 3]}..."


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
  nodeNames: Iterable[str],
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
  routingMonitor = RoutingMonitor(
    routingModel,
    routingIndexManager,
    distanceMatrix,
    nodeNames,
    improvementSize,
    improvementTimeout,
  )
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

  if plot:
    routingMonitor.PlotObjectiveValue()
    routingMonitor.PlotSolution(isAnimated=False)
    routingMonitor.PlotSolution(isAnimated=True)
    routingMonitor.ShowPlots()

  bestKnownSolution = routingMonitor.bestKnownSolution
  if bestKnownSolution is None: raise RuntimeError("Could not find a solution.")
  return bestKnownSolution.nodeIndices


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
