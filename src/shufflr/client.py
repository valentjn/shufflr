#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import lzma
import pathlib
import tempfile
import types
from typing import Any, cast, Dict, List, Optional, Sequence, Tuple, Type

import requests_cache
import spotipy

import shufflr.artist
import shufflr.configuration
from shufflr.logging import gLogger
import shufflr.playlist
import shufflr.track


class Client(object):
  def __init__(self, clientID: Optional[str], clientSecret: Optional[str], redirectURI: Optional[str]) -> None:
    self.clientID = clientID
    self.clientSecret = clientSecret
    self.redirectURI = redirectURI
    self._artistCache: Dict[str, shufflr.artist.Artist] = {}
    self._requestsCachePath = pathlib.Path(tempfile.gettempdir()) / "shufflr-requests-cache.sqlite"
    self._compressedRequestsCachePath = self._requestsCachePath.parent / f"{self._requestsCachePath.name}.xz"
    self._trackCache: Dict[str, shufflr.track.Track] = {}
    self._userIDCache: Dict[str, str] = {}
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

  def QuerySavedTrackIDsOfCurrentUser(self) -> List[str]:
    pageSize = 50
    gLogger.info("Querying saved track IDs of current user...")
    result = self._spotify.current_user_saved_tracks(limit=pageSize)
    return [resultTrack["track"]["id"] for resultTrack in self._QueryAllItems(result)]

  def QueryArtist(self, artistID: str) -> shufflr.artist.Artist:
    return self.QueryArtists([artistID])[0]

  def QueryArtists(self, artistIDs: Sequence[str]) -> List[shufflr.artist.Artist]:
    pageSize = 50
    newArtistIDs = sorted(set(artistIDs) - self._artistCache.keys())
    if len(newArtistIDs) > 0: gLogger.info("Querying {}...".format(Client._FormatNoun(len(newArtistIDs), "artist")))

    for offset in range(0, len(newArtistIDs), pageSize):
      pageArtistIDs = newArtistIDs[offset : offset + pageSize]
      result = self._spotify.artists(pageArtistIDs)

      for artistID, resultArtist in zip(pageArtistIDs, result["artists"]):
        self._artistCache[artistID] = shufflr.artist.Artist(
          resultArtist["id"],
          resultArtist["name"],
          resultArtist["genres"],
        )

    return [self._artistCache[artistID] for artistID in artistIDs]

  def QueryTracks(self, trackIDs: Sequence[str]) -> List[shufflr.track.Track]:
    pageSize = 50
    newTrackIDs = sorted(set(trackIDs) - self._trackCache.keys())
    if len(newTrackIDs) > 0: gLogger.info("Querying {}...".format(Client._FormatNoun(len(newTrackIDs), "track")))
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
          track = shufflr.track.Track(
            resultTrack["id"],
            resultTrack["name"],
            [resultArtist["id"] for resultArtist in resultTrack["artists"]],
            self,
            resultAudioFeature["acousticness"],
            resultAudioFeature["danceability"],
            resultAudioFeature["energy"],
            resultAudioFeature["instrumentalness"],
            shufflr.track.Key.FromSpotifyNotation(resultAudioFeature["key"], resultAudioFeature["mode"]),
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

  def QueryPlaylistIDsAndNamesOfCurrentUser(self) -> List[Tuple[str, str]]:
    return self.QueryPlaylistIDsAndNamesOfUser("me")

  def QueryPlaylistIDsAndNamesOfUser(self, userID: str) -> List[Tuple[str, str]]:
    pageSize = 50
    gLogger.info(f"Querying playlist IDs of user '{userID}'...")
    result = (self._spotify.current_user_playlists(limit=pageSize) if userID == "me" else
              self._spotify.user_playlists(userID, limit=pageSize))
    return [(resultPlaylist["id"], resultPlaylist["name"]) for resultPlaylist in self._QueryAllItems(result)]

  def QueryPlaylistWithSpecifier(
    self,
    playlistSpecifier: shufflr.configuration.PlaylistSpecifier,
  ) -> shufflr.playlist.Playlist:
    gLogger.info(
      f"Querying playlist '{playlistSpecifier.playlistName}' of user '{playlistSpecifier.userID}'..."
    )
    playlistIDsAndNames = self.QueryPlaylistIDsAndNamesOfUser(playlistSpecifier.userID)
    playlistNames = [playlistName for _, playlistName in playlistIDsAndNames]

    try:
      playlistIndex = playlistNames.index(playlistSpecifier.playlistName)
    except ValueError:
      raise ValueError("Could not find playlist '{}' for user '{}'. Available playlists are: {}".format(
        playlistSpecifier.playlistName,
        playlistSpecifier.userID,
        ", ".join(f"'{playlistName}'" for playlistName in playlistNames),
      ))

    return self.QueryPlaylist(playlistIDsAndNames[playlistIndex][0])

  def QueryPlaylist(self, playlistID: str) -> shufflr.playlist.Playlist:
    gLogger.info(f"Querying playlist ID '{playlistID}'...")
    result = self._spotify.playlist(playlistID)
    trackIDs = [resultTrack["track"]["id"] for resultTrack in self._QueryAllItems(result["tracks"])]
    return shufflr.playlist.Playlist(playlistID, result["owner"]["id"], result["name"], trackIDs)

  def _QueryAllItems(self, resultItems: Any) -> List[Any]:
    items: List[Any] = []

    while True:
      items.extend(resultItems["items"])
      if resultItems["next"] is None: return items
      resultItems = self._spotify._get(resultItems["next"])

  @staticmethod
  def _FormatNoun(number: int, noun: str) -> str:
    return f"1 {noun}" if number == 1 else f"{number} {noun}s"
