#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import http.client
import logging
import sys

import shufflr.client
import shufflr.configuration
from shufflr.logging import gLogger
import shufflr.playlist
import shufflr.shuffling


def Main() -> None:
  configuration = shufflr.configuration.Configuration()
  configuration.ParseArguments(sys.argv)

  if configuration.verbose >= 0:
    gLogger.setLevel(logging.INFO)
  else:
    gLogger.setLevel(logging.WARNING)

  if configuration.verbose >= 1: http.client.HTTPConnection.debuglevel = 2

  with shufflr.client.Client(configuration.clientID, configuration.clientSecret, configuration.redirectURI) as client:
    tracks = shufflr.playlist.CollectInputTracks(
      client,
      configuration.inputPlaylistSpecifiers,
      configuration.inputPlaylistWeights,
    )
    tracks = shufflr.playlist.SelectInputTracks(tracks, configuration)
    shuffledTracks = shufflr.shuffling.ShuffleTracks(tracks, configuration)

    if configuration.outputPlaylistName is not None:
      shufflr.playlist.SavePlaylist(
        client,
        configuration.outputPlaylistName,
        [track.id for track in shuffledTracks],
        playlistDescription=configuration.outputPlaylistDescription,
        isPublic=configuration.outputPlaylistIsPublic,
        overwrite=configuration.overwriteOutputPlaylist,
      )
