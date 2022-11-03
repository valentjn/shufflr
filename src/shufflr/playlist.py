#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import cast, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
  import shufflr.client
  import shufflr.track


def CollectInputTracks(
  client: "shufflr.client.Client",
  playlistSpecifiers: List[str],
  playlistWeights: Optional[List[Optional[float]]],
) -> Set["shufflr.track.Track"]:
  if playlistWeights is None: playlistWeights = cast(List[Optional[float]], len(playlistSpecifiers) * [None])
  trackIDsOfPlaylists = []

  for playlistSpecifier in playlistSpecifiers:
    if playlistSpecifier in ["liked", "saved"]:
      trackIDOfPlaylist = client.QuerySavedTrackIDsOfCurrentUser()
    else:
      pass

    trackIDsOfPlaylists.append(trackIDOfPlaylist)

  trackIDs = [trackID for trackIDOfPlaylist in trackIDsOfPlaylists for trackID in trackIDOfPlaylist]
  return set(client.QueryTracks(trackIDs))
