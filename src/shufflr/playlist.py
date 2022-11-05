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
    if playlistSpecifier.playlistName in ["liked", "saved"]:
      trackIDsOfPlaylist = client.QuerySavedTrackIDsOfCurrentUser(playlistSpecifier.playlistOwnerID)
    else:
      playlist = client.QueryPlaylistWithName(
        playlistSpecifier.playlistOwnerID,
        playlistSpecifier.playlistOwnerID,
        playlistSpecifier.playlistName,
      )
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

  return set(client.QueryTracks(playlistSpecifiers[0].playlistOwnerID, trackIDs))


def SelectInputTracks(
  tracks: Set["shufflr.track.Track"],
  configuration: "shufflr.configuration.Configuration",
) -> Set["shufflr.track.Track"]:
  featureNames = ["acousticness", "danceability", "energy", "instrumentalness",
                  "liveness", "speechiness", "tempo", "valence"]
  subsetTracks = set(tracks)

  for featureName in featureNames:
    capitalFeatureName = featureName[0].upper() + featureName[1:]
    minimumValue = getattr(configuration, f"minimum{capitalFeatureName}")
    maximumValue = getattr(configuration, f"maximum{capitalFeatureName}")

    if minimumValue is not None:
      subsetTracks = {track for track in subsetTracks if getattr(track, featureName) >= minimumValue / 100.0}

    if maximumValue is not None:
      subsetTracks = {track for track in subsetTracks if getattr(track, featureName) <= maximumValue / 100.0}

  return subsetTracks


def SavePlaylist(
  client: "shufflr.client.Client",
  playlistSpecifier: "shufflr.configuration.PlaylistSpecifier",
  trackIDs: Sequence[str],
  playlistDescription: str = "",
  isPublic: bool = False,
  overwrite: bool = False,
) -> None:
  playlistIDsAndNames = client.QueryPlaylistIDsAndNamesOfUser(
    playlistSpecifier.playlistOwnerID,
    playlistSpecifier.playlistOwnerID,
  )
  playlistNames = [playlistName for _, playlistName in playlistIDsAndNames]

  try:
    playlistIndex = playlistNames.index(playlistSpecifier.playlistName)
  except ValueError:
    playlistIndex = None

  if playlistIndex is None:
    playlistID = client.CreatePlaylist(
      playlistSpecifier.playlistOwnerID,
      playlistSpecifier.playlistName,
      playlistDescription=playlistDescription,
      isPublic=isPublic,
    )
  elif not overwrite:
    raise RuntimeError(
      f"Playlist '{playlistSpecifier.playlistName}' already exists for user '{playlistSpecifier.playlistOwnerID}' and "
      "--overwriteOutputPlaylist not specified."
    )
  else:
    playlistID = playlistIDsAndNames[playlistIndex][0]
    client.ClearPlaylist(playlistSpecifier.playlistOwnerID, playlistID)

  client.AddTracksToPlaylist(playlistSpecifier.playlistOwnerID, playlistID, trackIDs)
