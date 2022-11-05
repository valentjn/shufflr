#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import random
from typing import cast, List, Optional, Sequence, Set, TYPE_CHECKING


if TYPE_CHECKING:
  import shufflr.client
  import shufflr.configuration
  import shufflr.track


class Playlist(object):
  def __init__(self, playlistID: str, userID: str, name: str, trackIDs: Sequence[str]):
    self.playlistID = playlistID
    self.userID = userID
    self.name = name
    self.trackIDs = list(trackIDs)


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
      playlist = client.QueryPlaylistWithSpecifier(playlistSpecifier)
      trackIDsOfPlaylist = playlist.trackIDs

    trackIDsOfPlaylists.append(trackIDsOfPlaylist)

  if all(playlistWeight is None for playlistWeight in playlistWeights):
    trackIDs = [trackID for trackIDOfPlaylist in trackIDsOfPlaylists for trackID in trackIDOfPlaylist]
  else:
    songWeightRatios = [len(trackIDsOfPlaylist) / (0.0 if playlistWeight is None else playlistWeight)
                        for trackIDsOfPlaylist, playlistWeight in zip(trackIDsOfPlaylists, playlistWeights)]
    criticalPlaylistIndex = min(
      range(len(songWeightRatios)),
      key=lambda playlistIndex: songWeightRatios[playlistIndex],
    )
    totalWeight = sum(playlistWeight for playlistWeight in playlistWeights if playlistWeight is not None)
    totalNumberOfSongs = (len(trackIDsOfPlaylists[criticalPlaylistIndex]) /
                          (cast(float, playlistWeights[criticalPlaylistIndex]) / totalWeight))
    trackIDs = []

    for trackIDsOfPlaylist, playlistWeight in zip(trackIDsOfPlaylists, playlistWeights):
      if playlistWeight is None:
        trackIDs.extend(trackIDsOfPlaylist)
      else:
        random.shuffle(trackIDsOfPlaylist)
        numberOfSongs = round(totalNumberOfSongs * (playlistWeight / totalWeight))
        trackIDs.extend(trackIDsOfPlaylist[:numberOfSongs])

  return set(client.QueryTracks(trackIDs))


def SavePlaylist(
  client: "shufflr.client.Client",
  playlistName: str,
  trackIDs: Sequence[str],
  playlistDescription: str = "",
  isPublic: bool = False,
  overwrite: bool = False,
) -> None:
  playlistIDsAndNames = client.QueryPlaylistIDsAndNamesOfCurrentUser()
  playlistNames = [playlistName for _, playlistName in playlistIDsAndNames]

  try:
    playlistIndex = playlistNames.index(playlistName)
  except ValueError:
    playlistIndex = None

  if playlistIndex is None:
    playlistID = client.CreatePlaylist(playlistName, playlistDescription=playlistDescription, isPublic=isPublic)
  elif not overwrite:
    raise RuntimeError(
      f"Playlist '{playlistName}' already exists for current user and --overwriteOutputPlaylist not specified."
    )
  else:
    playlistID = playlistIDsAndNames[playlistIndex][0]
    client.ClearPlaylist(playlistID)

  client.AddTracksToPlaylist(playlistID, trackIDs)
