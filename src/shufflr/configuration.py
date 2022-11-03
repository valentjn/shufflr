#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
from typing import List, Optional, Sequence


class Configuration(object):
  def __init__(self) -> None:
    self.clientID: Optional[str] = "c322a584f11a4bdcaaac83b0776bd021"
    self.clientSecret: Optional[str] = None
    self.inputPlaylistSpecifiers: List[PlaylistSpecifier] = [PlaylistSpecifier("me", "liked")]
    self.inputPlaylistWeights: Optional[List[Optional[float]]] = None
    self.redirectURI: Optional[str] = "http://127.0.0.1:11793/"
    self.verbose: int = 0

  def GetKeys(self) -> List[str]:
    return sorted(settingKey for settingKey in vars(self) if not settingKey.startswith("_"))

  def ParseArguments(self, argv: Sequence[str]) -> None:
    argumentParser = argparse.ArgumentParser(
      prog="shufflr",
      description="Shufflr - Shuffle Spotify playlists such that consecutive songs are similar.",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    defaultConfiguration = Configuration()

    outputArgumentGroup = argumentParser.add_argument_group("output options")
    outputArgumentGroup.add_argument("-q", "--quiet", action="store_true", help="Only print warnings and errors.")
    outputArgumentGroup.add_argument("-v", "--verbose", action="count", default=0, help="Print log messages.")

    playlistArgumentGroup = argumentParser.add_argument_group("playlist options")
    playlistArgumentGroup.add_argument(
      "--inputPlaylists",
      nargs="+",
      default=defaultConfiguration.inputPlaylistSpecifiers,
      type=PlaylistSpecifier.ParseString,
      dest="inputPlaylistSpecifiers",
      help="Playlist(s) to take the songs to be shuffled from. "
      "Use the format 'USER_ID/PLAYLIST_DISPLAY_NAME' for the playlist of another user or just "
      "'PLAYLIST_DISPLAY_NAME' for one of your playlists. "
      "The user ID can be retrieved by extracting it from the link of the user profile, "
      "which can be obtained via the Spotify app. "
      "To use the playlist of your liked songs, use 'liked' or 'saved' (this is the default). "
      "Note that Spotify currently does not provide a way to access the playlist of liked songs of other users.",
    )
    playlistArgumentGroup.add_argument(
      "--inputPlaylistWeights",
      type=lambda argument: (None if argument == "*" else float(argument)),
      nargs="+",
      help="Weights for the shuffling of the input playlist. Specify one weight per input playlist. "
      "If you use 1 for all playlists, then the target playlist will contain equally many songs from each "
      "input playlist. "
      "If you change the value for a playlist to 2, then twice as many songs will be taken from that playlist "
      "compared to the other playlists. "
      "Use the special value '*' to include all songs of a playlist. "
      "This playlist is then discarded for the computation of the number of songs for the other playlists. "
      "The default is to use '*' for all input playlists.",
    )

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


class PlaylistSpecifier(object):
  def __init__(self, userID: str, playlistName: str) -> None:
    self.userID = userID
    self.playlistName = playlistName

  @staticmethod
  def ParseString(string: str) -> "PlaylistSpecifier":
    if "/" in string:
      delimiterIndex = string.index("/")
      return PlaylistSpecifier(string[:delimiterIndex], string[delimiterIndex + 1:])
    else:
      return PlaylistSpecifier("me", string)
