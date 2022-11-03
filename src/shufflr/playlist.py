#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import cast, List, Optional, Sequence, Set, TYPE_CHECKING


if TYPE_CHECKING:
  import shufflr.client
  import shufflr.configuration
  import shufflr.track


class Playlist(object):
  def __init__(self, playlistID: str, userID: str, name: str, tracks: Sequence["shufflr.track.Track"]):
    self.playlistID = playlistID
    self.userID = userID
    self.name = name
    self.tracks = list(tracks)


def CollectInputTracks(
  client: "shufflr.client.Client",
  playlistSpecifiers: List["shufflr.configuration.PlaylistSpecifier"],
  playlistWeights: Optional[List[Optional[float]]],
) -> Set["shufflr.track.Track"]:
  if playlistWeights is None: playlistWeights = cast(List[Optional[float]], len(playlistSpecifiers) * [None])
  trackIDsOfPlaylists = []

  for playlistSpecifier in playlistSpecifiers:
    if (playlistSpecifier.userID == "me") and (playlistSpecifier.playlistName in ["liked", "saved"]):
      trackIDsOfPlaylist = client.QuerySavedTrackIDsOfCurrentUser()
    else:
      playlist = client.QueryPlaylist(playlistSpecifier)
      trackIDsOfPlaylist = [track.id for track in playlist.tracks]

    trackIDsOfPlaylists.append(trackIDsOfPlaylist)

  trackIDs = [trackID for trackIDOfPlaylist in trackIDsOfPlaylists for trackID in trackIDOfPlaylist]
  return set(client.QueryTracks(trackIDs))
