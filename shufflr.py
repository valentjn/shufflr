#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import difflib
import functools
import http.client
import logging
import lzma
import math
import pathlib
import statistics
import sys
import tempfile
import types
from typing import cast, Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Type

import numpy as np
import numpy.typing as npt
import ortools.constraint_solver.routing_enums_pb2 as routing_enums_pb2
import ortools.constraint_solver.pywrapcp as pywrapcp
import requests_cache
import spotipy


gLogger = logging.Logger("shufflr")


def SetUpLogger() -> None:
  handler = logging.StreamHandler()
  formatter = logging.Formatter("%(message)s")
  handler.setFormatter(formatter)
  gLogger.addHandler(handler)


class Configuration(object):
  def __init__(self) -> None:
    self.clientID: Optional[str] = "c322a584f11a4bdcaaac83b0776bd021"
    self.clientSecret: Optional[str] = None
    self.redirectURI: Optional[str] = "http://127.0.0.1:11793/"
    self.verbose: int = 0

  def GetKeys(self) -> List[str]:
    return sorted(settingKey for settingKey in vars(self) if not settingKey.startswith("_"))

  def ParseArguments(self, argv: Sequence[str]) -> None:
    argumentParser = argparse.ArgumentParser(
      description="Shufflr - Shuffle Spotify playlists such that consecutive songs are similar.",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    defaultConfiguration = Configuration()

    outputArgumentGroup = argumentParser.add_argument_group("output options")
    outputArgumentGroup.add_argument("-q", "--quiet", action="store_true", help="Only print warnings and errors.")
    outputArgumentGroup.add_argument("-v", "--verbose", action="count", default=0, help="Print log messages.")

    authentificationArgumentGroup = argumentParser.add_argument_group("authentification options")
    authentificationArgumentGroup.add_argument("--clientID", default=defaultConfiguration.clientID,
                                               help="Client ID - unique identifier of the app.")
    authentificationArgumentGroup.add_argument("--clientSecret", help="Client secret to authenticate the app.")
    authentificationArgumentGroup.add_argument("--redirectURI", default=defaultConfiguration.redirectURI,
                                               help="URI opened by Spotify after successful logins.")

    arguments = argumentParser.parse_args(argv[1:])

    for key in self.GetKeys():
      if hasattr(arguments, key): setattr(self, key, getattr(arguments, key))

    if arguments.quiet: self.verbose = -1


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


class Track(object):
  def __init__(
    self,
    id_: str,
    name: str,
    artistIDs: Iterable[str],
    client: "Client",
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

  def GetArtists(self) -> List[Artist]:
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


class Client(object):
  def __init__(self, clientID: Optional[str], clientSecret: Optional[str], redirectURI: Optional[str]) -> None:
    self.clientID = clientID
    self.clientSecret = clientSecret
    self.redirectURI = redirectURI
    self._artistCache: Dict[str, Artist] = {}
    self._requestsCachePath = pathlib.Path(tempfile.gettempdir()) / "shufflr-requests-cache.sqlite"
    self._compressedRequestsCachePath = self._requestsCachePath.parent / f"{self._requestsCachePath.name}.xz"
    self._trackCache: Dict[str, Track] = {}
    self.DecompressRequestsCache()
    self._CreateSpotify()

  def __enter__(self) -> "Client":
    return self

  def __exit__(
    self,
    exceptionType: Optional[Type[BaseException]],
    exceptionValue: Optional[BaseException],
    traceback: Optional[types.TracebackType]
  ) -> Optional[bool]:
    if (exceptionType is None) or (exceptionType is KeyboardInterrupt):
      self.CompressRequestsCache()
    else:
      self._CloseRequestsCache()
      self._compressedRequestsCachePath.unlink(missing_ok=True)
      self._requestsCachePath.unlink(missing_ok=True)

    return None

  def _CloseRequestsCache(self) -> None:
    cast(requests_cache.backends.sqlite.SQLiteDict, self._sessionCache.redirects).close()  # type: ignore
    self._sessionCache.responses.close()  # type: ignore

  def CompressRequestsCache(self) -> None:
    self._CloseRequestsCache()

    if self._requestsCachePath.is_file():
      gLogger.info(f"Compressing requests cache {str(self._requestsCachePath)!r} to "
                   f"{str(self._compressedRequestsCachePath)!r}...")

      with lzma.open(self._compressedRequestsCachePath, "w") as file:
        file.write(self._requestsCachePath.read_bytes())

      self._requestsCachePath.unlink()

  def DecompressRequestsCache(self) -> None:
    if self._compressedRequestsCachePath.is_file():
      gLogger.info(f"Decompressing requests cache {str(self._compressedRequestsCachePath)!r} to "
                   f"{str(self._requestsCachePath)!r}...")

      with lzma.open(self._compressedRequestsCachePath, "r") as file:
        self._requestsCachePath.write_bytes(file.read())

      self._compressedRequestsCachePath.unlink()

  def _CreateSpotify(self) -> None:
    cachedSession = requests_cache.session.CachedSession(
      str(self._requestsCachePath),
      backend="sqlite",
      cache_control=True,
    )
    self._sessionCache = cast(requests_cache.backends.sqlite.SQLiteCache, cachedSession.cache)
    cachedSession.remove_expired_responses()
    self._spotify = spotipy.Spotify(
      auth_manager=spotipy.oauth2.SpotifyOAuth(
        client_id=self.clientID,
        client_secret=self.clientSecret,
        redirect_uri=self.redirectURI,
        scope=[
          "playlist-read-private",
          "playlist-read-collaborative",
          "playlist-modify-private",
          "user-library-read",
        ],
      ),
      requests_session=cachedSession,
    )

  def QueryCurrentUserID(self) -> str:
    gLogger.info("Querying current user ID...")
    return cast(str, self._spotify.current_user()["id"])

  def QuerySavedTracksOfCurrentUser(self) -> List[Track]:
    pageSize = 50
    gLogger.info("Querying saved tracks of current user...")
    numberOfSavedTracks = self._spotify.current_user_saved_tracks(limit=1)["total"]
    trackIDs: List[str] = []

    for offset in range(0, numberOfSavedTracks, pageSize):
      result = self._spotify.current_user_saved_tracks(limit=pageSize, offset=offset)
      trackIDs.extend(resultTrack["track"]["id"] for resultTrack in result["items"])

    return self.QueryTracks(trackIDs)

  def QueryArtist(self, artistID: str) -> Artist:
    return self.QueryArtists([artistID])[0]

  def QueryArtists(self, artistIDs: Sequence[str]) -> List[Artist]:
    pageSize = 50
    newArtistIDs = sorted(set(artistIDs) - self._artistCache.keys())
    if len(newArtistIDs) > 0: gLogger.info("Querying {}...".format(FormatNoun(len(newArtistIDs), "artist")))

    for offset in range(0, len(newArtistIDs), pageSize):
      pageArtistIDs = newArtistIDs[offset : offset + pageSize]
      result = self._spotify.artists(pageArtistIDs)

      for artistID, resultArtist in zip(pageArtistIDs, result["artists"]):
        self._artistCache[artistID] = Artist(resultArtist["id"], resultArtist["name"], resultArtist["genres"])

    return [self._artistCache[artistID] for artistID in artistIDs]

  def QueryTracks(self, trackIDs: Sequence[str]) -> List[Track]:
    pageSize = 50
    newTrackIDs = sorted(set(trackIDs) - self._trackCache.keys())
    if len(newTrackIDs) > 0: gLogger.info("Querying {}...".format(FormatNoun(len(newTrackIDs), "track")))
    artistIDs = []
    unplayableTrackIDs = set()

    for offset in range(0, len(newTrackIDs), pageSize):
      pageTrackIDs = newTrackIDs[offset : offset + pageSize]
      resultTracks = self._spotify.tracks(pageTrackIDs, market="from_token")
      resultAudioFeatures = self._spotify.audio_features(pageTrackIDs)

      for trackID, resultTrack, resultAudioFeature in zip(
        pageTrackIDs,
        resultTracks["tracks"],
        resultAudioFeatures,
      ):
        if resultTrack["is_playable"]:
          track = Track(
            resultTrack["id"],
            resultTrack["name"],
            [resultArtist["id"] for resultArtist in resultTrack["artists"]],
            self,
            resultAudioFeature["acousticness"],
            resultAudioFeature["danceability"],
            resultAudioFeature["energy"],
            resultAudioFeature["instrumentalness"],
            resultAudioFeature["liveness"],
            resultAudioFeature["speechiness"],
            resultAudioFeature["tempo"],
            resultAudioFeature["valence"],
          )
          self._trackCache[trackID] = track
          artistIDs.extend(track.artistIDs)
        else:
          unplayableTrackIDs.add(trackID)

    self.QueryArtists(artistIDs)
    return [self._trackCache[trackID] for trackID in trackIDs if trackID not in unplayableTrackIDs]


def FormatNoun(number: int, noun: str) -> str:
  return f"1 {noun}" if number == 1 else f"{number} {noun}s"


def CollectTracks(client: Client) -> Set[Track]:
  return set(client.QuerySavedTracksOfCurrentUser())


def ShuffleTracks(tracks: Set[Track], verbose: int = 0) -> List[Track]:
  trackList = list(tracks)
  distanceMatrix = ComputeDistanceMatrix(trackList)
  shuffledTrackIndices = SolveTravelingSalespersonProblem(distanceMatrix, verbose=verbose)
  shuffledTrackList = [trackList[trackIndex] for trackIndex in shuffledTrackIndices]

  if verbose >= 0:
    previousTrackIndex = None

    for trackIndex in shuffledTrackIndices:
      if previousTrackIndex is not None:
        gLogger.info(f"    | distance = {distanceMatrix[previousTrackIndex, trackIndex]:.2f}")

      track = trackList[trackIndex]
      gLogger.info("{} - {}".format(", ".join(artist.name for artist in track.GetArtists()), track.name))
      previousTrackIndex = trackIndex

  return shuffledTrackList


def ComputeDistanceMatrix(tracks: Sequence[Track]) -> npt.NDArray[np.double]:
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


def Main() -> None:
  SetUpLogger()

  configuration = Configuration()
  configuration.ParseArguments(sys.argv)

  if configuration.verbose >= 0:
    gLogger.setLevel(logging.INFO)
  else:
    gLogger.setLevel(logging.WARNING)

  if configuration.verbose >= 1: http.client.HTTPConnection.debuglevel = 2

  with Client(configuration.clientID, configuration.clientSecret, configuration.redirectURI) as client:
    tracks = CollectTracks(client)
    shuffledTracks = ShuffleTracks(tracks, verbose=configuration.verbose)


if __name__ == "__main__": Main()
