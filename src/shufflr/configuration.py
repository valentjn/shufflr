#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import datetime
import json
import pathlib
import re
from typing import Dict, List, Optional, Sequence


class Configuration(object):
  def __init__(self) -> None:
    self.acousticnessWeight = 1.0
    self.clientID = "c322a584f11a4bdcaaac83b0776bd021"
    self.clientSecret: Optional[str] = None
    self.danceabilityWeight = 1.0
    self.differentArtistWeight = 5.0
    self.disableRequestCache = False
    self.energyWeight = 1.0
    self.genreWeight = 3.0
    self.inputPlaylistSpecifiers: Optional[List[PlaylistSpecifier]] = None
    self.inputPlaylistWeights: Optional[List[Optional[float]]] = None
    self.instrumentalnessWeight = 1.0
    self.keyWeight = 3.0
    self.livenessWeight = 1.0
    self.maximumAcousticness: Optional[float] = None
    self.maximumDanceability: Optional[float] = None
    self.maximumEnergy: Optional[float] = None
    self.maximumInstrumentalness: Optional[float] = None
    self.maximumLiveness: Optional[float] = None
    self.maximumNumberOfSongs: Optional[int] = None
    self.maximumSpeechiness: Optional[float] = None
    self.maximumTempo: Optional[float] = None
    self.maximumValence: Optional[float] = None
    self.minimumAcousticness: Optional[float] = None
    self.minimumDanceability: Optional[float] = None
    self.minimumEnergy: Optional[float] = None
    self.minimumInstrumentalness: Optional[float] = None
    self.minimumLiveness: Optional[float] = None
    self.minimumSpeechiness: Optional[float] = None
    self.minimumTempo: Optional[float] = None
    self.minimumValence: Optional[float] = None
    self.outputPlaylistDescription = "Created by Shufflr"
    self.outputPlaylistIsPublic = False
    self.outputPlaylistSpecifier: Optional[PlaylistSpecifier] = None
    self.overwriteOutputPlaylist = False
    self.plotTSP = False
    self.redirectURI = "http://127.0.0.1:11793/"
    self.resetAuthenticationCache = False
    self.resetRequestCache = False
    self.speechinessWeight = 1.0
    self.tempoWeight = 2.0
    self.tspImprovementSize = 0.05
    self.tspImprovementTimeout = datetime.timedelta(seconds=3.0)
    self.tspTimeout = datetime.timedelta(seconds=15.0)
    self.userAliases = UserAliases()
    self.valenceWeight = 1.0
    self.verbose = 0

  def GetKeys(self) -> List[str]:
    return sorted(
      settingKey for settingKey in vars(self)
      if not settingKey.startswith("_") and (settingKey != "userAliases")
    )

  def ParseArguments(self, argv: Sequence[str]) -> None:
    argumentParser = Configuration.CreateArgumentParser()
    arguments = argumentParser.parse_args(argv[1:])

    specifiedArgumentParser = Configuration.CreateArgumentParser(useDefaults=False)
    specifiedArguments = specifiedArgumentParser.parse_args(argv[1:])

    for key in self.GetKeys():
      if key in specifiedArguments: setattr(self, key, getattr(arguments, key))

    if arguments.quiet: self.verbose = -1

  @staticmethod
  def CreateArgumentParser(useDefaults: bool = True) -> argparse.ArgumentParser:
    argumentParser = argparse.ArgumentParser(
      prog="shufflr",
      description="Shufflr - Shuffle Spotify playlists such that consecutive songs are similar.",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      argument_default=None if useDefaults else argparse.SUPPRESS,
      add_help=False,
    )
    defaultConfiguration = Configuration()

    outputArgumentGroup = argumentParser.add_argument_group("Output arguments")
    outputArgumentGroup.add_argument(
      "-h",
      "--help",
      action="help",
      default=argparse.SUPPRESS,
      help="Show a help message and exit.",
    )
    outputArgumentGroup.add_argument("-q", "--quiet", action="store_true", help="Only print warnings and errors.")
    outputArgumentGroup.add_argument(
      "-v",
      "--verbose",
      action="count",
      default=0 if useDefaults else argparse.SUPPRESS,
      help="Print log messages. Specify multiple times to increase log verbosity.",
    )

    inputPlaylistArgumentGroup = argumentParser.add_argument_group("Input playlist arguments")
    inputPlaylistArgumentGroup.add_argument(
      "-i",
      "--inputPlaylists",
      dest="inputPlaylistSpecifiers",
      metavar="PLAYLISTSPECIFIER",
      nargs="+",
      type=PlaylistSpecifier.ParseString,
      required=True,
      help="Playlist(s) to take the songs to be shuffled from. "
      "The format is `LOGIN_USER_ID/PLAYLIST_OWNER_ID/PLAYLIST_DISPLAY_NAME` or "
      "`PLAYLIST_OWNER_ID/PLAYLIST_DISPLAY_NAME`. "
      "If you use the first format, then the playlist must be visible to the specified login user. For example, the "
      "playlist is public, or it is private and the login user is a follower or collaborator of the playlist. "
      "If you use the second format, then the playlist owner is used as login user. "
      "To use the playlist of the user's liked songs, use `liked` or `saved` for `PLAYLIST_DISPLAY_NAME`. "
      "This is only possible if `LOGIN_USER_ID` equals `PLAYLIST_OWNER_ID` (e.g., if you use the second format), "
      "as it is not possible access other users' liked songs.",
    )
    inputPlaylistArgumentGroup.add_argument(
      "-w",
      "--inputPlaylistWeights",
      metavar="PLAYLISTWEIGHT",
      type=lambda argument: (None if argument == "*" else float(argument)),
      nargs="+",
      help="Weights for the shuffling of the input playlist. Specify one weight per input playlist. "
      "If you use 1 for all playlists, then the target playlist contains equally many songs from each "
      "input playlist. "
      "If you change the value for a playlist to 2, then twice as many songs are taken from that playlist "
      "compared to the other playlists. "
      "Use the special value `*` to include all songs of a playlist. "
      "This playlist is then discarded for the computation of the number of songs for the other playlists. "
      "The default is to use `*` for all input playlists.",
    )

    songSelectionArgumentGroup = argumentParser.add_argument_group("Song selection arguments")
    songSelectionArgumentGroup.add_argument(
      "--maximumNumberOfSongs",
      type=int,
      help="Maximum number of songs in the output playlist. If omitted, then all songs are taken."
    )

    featureNames = ["acousticness", "danceability", "differentArtist", "energy", "genre", "instrumentalness",
                    "key", "liveness", "speechiness", "tempo", "valence"]
    featureDescriptions = [
      "confidence whether the song is acoustic",
      "how suitable the song is for dancing based on a combination of musical elements including tempo, "
      "rhythm stability, beat strength, and overall regularity",
      "whether the artists of the song are different from the previous song",
      "perceptual measure of intensity and activity; typically, energetic tracks feel fast, loud, and noisy",
      "whether the genre of the song is similar to the previous song",
      "whether a track contains no vocals; 'ooh' and 'aah' sounds are treated as instrumental in this context",
      "whether the key of the song is harmonically compatible to the previous song",
      "confidence whether an audience is present in the recording",
      "presence of spoken words in the song; values above 66 are probably made entirely of spoken words",
      "tempo of the song in beats per minute",
      "musical positiveness conveyed by the song",
    ]

    for featureName, featureDescription in zip(featureNames, featureDescriptions):
      weightArgumentName = f"{featureName}Weight"
      songSelectionArgumentGroup.add_argument(
        f"--{weightArgumentName}",
        type=float,
        default=getattr(defaultConfiguration, weightArgumentName) if useDefaults else argparse.SUPPRESS,
        help=f"Weight of song feature `{featureName}` ({featureDescription}).",
      )

    for featureName, featureDescription in zip(featureNames, featureDescriptions):
      if featureName in ["differentArtist", "genre", "key"]: continue
      capitalFeatureName = featureName[0].upper() + featureName[1:]
      songSelectionArgumentGroup.add_argument(
        f"--minimum{capitalFeatureName}",
        type=float,
        help=f"Minimum permitted value of song feature `{featureName}` ({featureDescription}) between 0 and 100.",
      )

    for featureName, featureDescription in zip(featureNames, featureDescriptions):
      if featureName in ["differentArtist", "genre", "key"]: continue
      capitalFeatureName = featureName[0].upper() + featureName[1:]
      songSelectionArgumentGroup.add_argument(
        f"--maximum{capitalFeatureName}",
        type=float,
        help=f"Maximum permitted value of song feature `{featureName}` ({featureDescription}) between 0 and 100.",
      )

    tspArgumentGroup = argumentParser.add_argument_group("Traveling salesperson problem (TSP) arguments")
    tspArgumentGroup.add_argument(
      "--tspImprovementSize",
      type=float,
      default=defaultConfiguration.tspImprovementSize if useDefaults else argparse.SUPPRESS,
      help="If, while solving the TSP, the improvement of the objective value in the last `TSPIMPROVEMENTTIMEOUT` "
      "seconds (see `--tspImprovementTimeout`) falls below `TSPIMPROVEMENTSIZE` times the improvement since the "
      "initial solution, then the search is stopped and the best known solution is used. "
      "A lower value of `TSPIMPROVEMENTSIZE` and a higher value of `TSPIMPROVEMENTTIMEOUT` "
      "usually lead to better solutions.",
    )
    tspArgumentGroup.add_argument(
      "--tspImprovementTimeout",
      type=Configuration._ParseDuration,
      default=defaultConfiguration.tspImprovementTimeout if useDefaults else argparse.SUPPRESS,
      help="See `--tspImprovementSize`.",
    )
    tspArgumentGroup.add_argument(
      "--plotTSP",
      action="store_true",
      help="Plot the evolution of the objective value while solving the TSP (Matplotlib required).",
    )
    tspArgumentGroup.add_argument(
      "--tspTimeout",
      type=Configuration._ParseDuration,
      default=defaultConfiguration.tspTimeout if useDefaults else argparse.SUPPRESS,
      help="Maximum number of seconds for the TSP solution. "
      "For technical reasons, the duration is rounded up to the next integer. "
      "A higher value leads to better solutions.",
    )

    outputPlaylistArgumentGroup = argumentParser.add_argument_group("Output playlist arguments")
    outputPlaylistArgumentGroup.add_argument(
      "-o",
      "--outputPlaylist",
      type=PlaylistSpecifier.ParseString,
      dest="outputPlaylistSpecifier",
      metavar="PLAYLISTSPECIFIER",
      help="If specified, the list of shuffled songs is saved as a playlist with this name "
      "(`--overwriteOutputPlaylist` has to be specified if the playlist already exists). "
      "Use the format `PLAYLIST_OWNER_ID/PLAYLIST_DISPLAY_NAME`. "
      "Otherwise, the playlist is just printed (except if `--quiet` is given).",
    )
    outputPlaylistArgumentGroup.add_argument(
      "--outputPlaylistDescription",
      metavar="PLAYLISTDESCRIPTION",
      default=defaultConfiguration.outputPlaylistDescription if useDefaults else argparse.SUPPRESS,
      help="The description of the output playlist created by `--outputPlaylist`.",
    )
    outputPlaylistArgumentGroup.add_argument(
      "--outputPlaylistIsPublic",
      action="store_true",
      help="If specified, the output playlist created with `--outputPlaylist` is public. "
      "Otherwise, by default, it is private.",
    )
    outputPlaylistArgumentGroup.add_argument(
      "-f",
      "--overwriteOutputPlaylist",
      action="store_true",
      help="If the output playlist specified by `--outputPlaylist` already exists, overwrite it. "
      "Otherwise, an exception is thrown to prevent data loss.",
    )

    apiArgumentGroup = argumentParser.add_argument_group("API arguments")
    apiArgumentGroup.add_argument(
      "--clientID",
      default=defaultConfiguration.clientID if useDefaults else argparse.SUPPRESS,
      help="Client ID - unique identifier of the app.",
    )
    apiArgumentGroup.add_argument("--clientSecret", help="Client secret to authenticate the app.")
    apiArgumentGroup.add_argument(
      "--redirectURI",
      default=defaultConfiguration.redirectURI if useDefaults else argparse.SUPPRESS,
      help="URI opened by Spotify after successful logins.",
    )
    apiArgumentGroup.add_argument(
      "--resetAuthenticationCache",
      action="store_true",
      help="Delete cache file for API authentication tokens when starting.",
    )
    apiArgumentGroup.add_argument(
      "--disableRequestCache",
      action="store_true",
      help="Prevent storing API requests in a cache file and re-using responses.",
    )
    apiArgumentGroup.add_argument(
      "--resetRequestCache",
      action="store_true",
      help="Delete cache file for API requests and responses when starting.",
    )

    return argumentParser

  @staticmethod
  def _ParseDuration(string: str) -> datetime.timedelta:
    return datetime.timedelta(seconds=float(string))

  def ReadFile(self, path: pathlib.Path) -> None:
    fileConfiguration = json.loads(path.read_text())

    for key in self.GetKeys():
      if key in fileConfiguration: setattr(self, key, fileConfiguration[key])

    if fileConfiguration.get("quiet", False) == True: self.verbose = -1
    self.userAliases = UserAliases(fileConfiguration.get("userAliases", {}))

  def ApplyUserAliases(self) -> None:
    if self.inputPlaylistSpecifiers is not None:
      for playlistSpecifier in self.inputPlaylistSpecifiers:
        playlistSpecifier.ApplyUserAliases(self.userAliases)

    if self.outputPlaylistSpecifier is not None: self.outputPlaylistSpecifier.ApplyUserAliases(self.userAliases)


class UserAliases(object):
  def __init__(self, aliases: Dict[str, str] = {}) -> None:
    self._aliases = aliases

  def GetUserID(self, name: str) -> str:
    return self._aliases.get(name, name)


class PlaylistSpecifier(object):
  def __init__(self, loginUserID: str, playlistOwnerID: str, playlistName: str) -> None:
    self.loginUserID = loginUserID
    self.playlistOwnerID = playlistOwnerID
    self.playlistName = playlistName

  def ApplyUserAliases(self, userAliases: UserAliases) -> None:
    self.loginUserID = userAliases.GetUserID(self.loginUserID)
    self.playlistOwnerID = userAliases.GetUserID(self.playlistOwnerID)

  @staticmethod
  def ParseString(string: str) -> "PlaylistSpecifier":
    regexMatch = re.match(
      r"^(?:(?P<loginUserID>[^/]+)/(?P<playlistOwnerID1>[^/]+)/(?P<playlistName1>.+)|"
      r"(?P<playlistOwnerID2>[^/]+)/(?P<playlistName2>.+))$",
      string,
    )

    if regexMatch is None:
      raise ValueError(f"Invalid playlist specifier '{string}'.")
    elif regexMatch.group("loginUserID") is not None:
      return PlaylistSpecifier(
        regexMatch.group("loginUserID"),
        regexMatch.group("playlistOwnerID1"),
        regexMatch.group("playlistName1"),
      )
    else:
      return PlaylistSpecifier(
        regexMatch.group("playlistOwnerID2"),
        regexMatch.group("playlistOwnerID2"),
        regexMatch.group("playlistName2"),
      )
