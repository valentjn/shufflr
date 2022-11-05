#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import http.server
import lzma
import pathlib
import re
import threading
import types
from typing import Any, cast, Dict, List, Optional, Sequence, Tuple, Type

import requests_cache
import spotipy

import shufflr.artist
from shufflr.logging import gLogger
import shufflr.playlist
import shufflr.track


class Client(object):
  def __init__(
    self,
    clientID: Optional[str] = None,
    clientSecret: Optional[str] = None,
    redirectURI: Optional[str] = None,
    useRequestCache: bool = True,
  ) -> None:
    self.clientID = clientID
    self.clientSecret = clientSecret
    self.redirectURI = redirectURI
    self.useRequestCache = useRequestCache
    self._apiClientCache: Dict[str, spotipy.Spotify] = {}
    self._artistCache: Dict[str, shufflr.artist.Artist] = {}
    self._authenticationHttpServer: Optional[http.server.HTTPServer] = None
    self._authenticationHttpServerIsRunning = False
    self._requestsCachePath = pathlib.Path(".shufflr-requests-cache.sqlite")
    self._compressedRequestsCachePath = self._requestsCachePath.parent / f"{self._requestsCachePath.name}.xz"
    self._trackCache: Dict[str, shufflr.track.Track] = {}
    self._userIDCache: Dict[str, str] = {}
    self.DecompressRequestsCache()
    self._CreateRequestsSession()

  def __enter__(self) -> "Client":
    return self

  def __exit__(
    self,
    exceptionType: Optional[Type[BaseException]],
    exceptionValue: Optional[BaseException],
    traceback: Optional[types.TracebackType]
  ) -> Optional[bool]:
    if not self.useRequestCache: return None

    if (exceptionType is None) or (exceptionType is KeyboardInterrupt):
      self.CompressRequestsCache()
    else:
      self._CloseRequestsCache()
      self._compressedRequestsCachePath.unlink(missing_ok=True)
      self._requestsCachePath.unlink(missing_ok=True)

    return None

  def _CloseRequestsCache(self) -> None:
    if not self.useRequestCache: return
    cast(requests_cache.backends.sqlite.SQLiteDict, self._requestsSessionCache.redirects).close()  # type: ignore
    self._requestsSessionCache.responses.close()  # type: ignore

  def CompressRequestsCache(self) -> None:
    if not self.useRequestCache: return
    self._CloseRequestsCache()

    if self._requestsCachePath.is_file():
      gLogger.info(f"Compressing requests cache {str(self._requestsCachePath)!r} to "
                   f"{str(self._compressedRequestsCachePath)!r}...")

      with lzma.open(self._compressedRequestsCachePath, "w") as file:
        file.write(self._requestsCachePath.read_bytes())

      self._requestsCachePath.unlink()

  def DecompressRequestsCache(self) -> None:
    if not self.useRequestCache: return

    if self._compressedRequestsCachePath.is_file():
      gLogger.info(f"Decompressing requests cache {str(self._compressedRequestsCachePath)!r} to "
                   f"{str(self._requestsCachePath)!r}...")

      with lzma.open(self._compressedRequestsCachePath, "r") as file:
        self._requestsCachePath.write_bytes(file.read())

      self._compressedRequestsCachePath.unlink()

  def _CreateRequestsSession(self) -> None:
    self._requestsSession: Optional[requests_cache.session.CachedSession]

    if self.useRequestCache:
      self._requestsSession = requests_cache.session.CachedSession(
        str(self._requestsCachePath),
        backend="sqlite",
        cache_control=True,
      )
      self._requestsSessionCache = cast(requests_cache.backends.sqlite.SQLiteCache, self._requestsSession.cache)
      self._requestsSession.remove_expired_responses()
    else:
      self._requestsSession = None

  def _GetAPIClient(self, loginUserID: str) -> spotipy.Spotify:
    if loginUserID in self._apiClientCache: return self._apiClientCache[loginUserID]

    if re.match(r"^[0-9A-Za-z_-]+", loginUserID) is None:
      raise ValueError(f"Invalid characters in login user ID {loginUserID}.")

    with http.server.HTTPServer(
      ("127.0.0.1", 11793),
      AuthenticationHTTPRequestHandler,
    ) as self._authenticationHttpServer:
      self._authenticationHttpServer.timeout = 0.1
      self._authenticationHttpServerIsRunning = True
      authenticationHttpServerThread = threading.Thread(target=self._ServeHTTPRequests, daemon=True)
      authenticationHttpServerThread.start()
      gLogger.info(
        "Creating API client... If you're asked to go to a URL, then open a new private browser window, "
        f"copy and paste the URL, enter the Spotify credentials for user '{loginUserID}', "
        "and copy and paste the URL you are redirected to."
      )

      authenticationCacheHandler = spotipy.oauth2.CacheFileHandler(
        cache_path=pathlib.Path(f".shufflr-authentication-cache-{loginUserID}.json"),
      )
      authenticationScopes = [
        "playlist-modify-private",
        "playlist-read-private",
        "playlist-read-collaborative",
        "user-library-read",
      ]
      authenticationManager = spotipy.oauth2.SpotifyOAuth(
        client_id=self.clientID,
        client_secret=self.clientSecret,
        redirect_uri=self.redirectURI,
        scope=authenticationScopes,
        cache_handler=authenticationCacheHandler,
        open_browser=False,
      )
      apiClient = spotipy.Spotify(auth_manager=authenticationManager, requests_session=self._requestsSession)

      result = apiClient.current_user()

      if result["id"] != loginUserID:
        raise RuntimeError(
          f"Authentication failed. Expected current user ID to be {loginUserID}', got '{result['id']}'."
        )

      self._authenticationHttpServerIsRunning = False

    self._apiClientCache[loginUserID] = apiClient
    return apiClient

  def _ServeHTTPRequests(self) -> None:
    assert self._authenticationHttpServer is not None

    while self._authenticationHttpServerIsRunning:
      self._authenticationHttpServer.handle_request()

  def QuerySavedTrackIDsOfCurrentUser(self, loginUserID: str) -> List[str]:
    pageSize = 50
    gLogger.info(f"Querying saved track IDs of user '{loginUserID}'...")
    result = self._GetAPIClient(loginUserID).current_user_saved_tracks(limit=pageSize)
    return [resultTrack["track"]["id"] for resultTrack in self._QueryAllItems(loginUserID, result)]

  def QueryArtist(self, loginUserID: str, artistID: str) -> shufflr.artist.Artist:
    return self.QueryArtists(loginUserID, [artistID])[0]

  def QueryArtists(self, loginUserID: str, artistIDs: Sequence[str]) -> List[shufflr.artist.Artist]:
    pageSize = 50
    newArtistIDs = sorted(set(artistIDs) - self._artistCache.keys())
    if len(newArtistIDs) > 0: gLogger.info("Querying {}...".format(Client._FormatNoun(len(newArtistIDs), "artist")))

    for offset in range(0, len(newArtistIDs), pageSize):
      pageArtistIDs = newArtistIDs[offset : offset + pageSize]
      result = self._GetAPIClient(loginUserID).artists(pageArtistIDs)

      for artistID, resultArtist in zip(pageArtistIDs, result["artists"]):
        self._artistCache[artistID] = shufflr.artist.Artist(
          resultArtist["id"],
          resultArtist["name"],
          resultArtist["genres"],
        )

    return [self._artistCache[artistID] for artistID in artistIDs]

  def QueryTracks(self, loginUserID: str, trackIDs: Sequence[str]) -> List[shufflr.track.Track]:
    pageSize = 50
    newTrackIDs = sorted(set(trackIDs) - self._trackCache.keys())
    if len(newTrackIDs) > 0: gLogger.info("Querying {}...".format(Client._FormatNoun(len(newTrackIDs), "track")))
    artistIDs = []
    unplayableTrackIDs = set()

    for offset in range(0, len(newTrackIDs), pageSize):
      pageTrackIDs = newTrackIDs[offset : offset + pageSize]
      resultTracks = self._GetAPIClient(loginUserID).tracks(pageTrackIDs, market="from_token")
      resultAudioFeatures = self._GetAPIClient(loginUserID).audio_features(pageTrackIDs)

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

    self.QueryArtists(loginUserID, artistIDs)
    return [self._trackCache[trackID] for trackID in trackIDs if trackID not in unplayableTrackIDs]

  def QueryPlaylistIDsAndNamesOfUser(self, loginUserID: str, userID: str) -> List[Tuple[str, str]]:
    pageSize = 50
    gLogger.info(f"Querying playlist IDs of user '{userID}'...")
    result = self._GetAPIClient(loginUserID).user_playlists(userID, limit=pageSize)
    return [(resultPlaylist["id"], resultPlaylist["name"])
            for resultPlaylist in self._QueryAllItems(loginUserID, result)]

  def QueryPlaylistWithName(
    self,
    loginUserID: str,
    playlistOwnerID: str,
    playlistName: str,
  ) -> shufflr.playlist.Playlist:
    gLogger.info(
      f"Querying playlist '{playlistName}' of user '{playlistOwnerID}'..."
    )
    playlistIDsAndNames = self.QueryPlaylistIDsAndNamesOfUser(loginUserID, playlistOwnerID)
    playlistNames = [playlistName for _, playlistName in playlistIDsAndNames]

    try:
      playlistIndex = playlistNames.index(playlistName)
    except ValueError:
      raise ValueError("Could not find playlist '{}' for user '{}'. Available playlists are: {}".format(
        playlistName,
        playlistOwnerID,
        ", ".join(f"'{playlistName}'" for playlistName in playlistNames),
      ))

    return self.QueryPlaylist(loginUserID, playlistIDsAndNames[playlistIndex][0])

  def QueryPlaylist(self, loginUserID: str, playlistID: str) -> shufflr.playlist.Playlist:
    gLogger.info(f"Querying playlist ID '{playlistID}'...")
    result = self._GetAPIClient(loginUserID).playlist(playlistID)
    trackIDs = [resultTrack["track"]["id"] for resultTrack in self._QueryAllItems(loginUserID, result["tracks"])]
    return shufflr.playlist.Playlist(playlistID, result["owner"]["id"], result["name"], trackIDs)

  def CreatePlaylist(
    self,
    loginUserID: str,
    playlistName: str,
    playlistDescription: str = "",
    isPublic: bool = False,
  ) -> str:
    gLogger.info(f"Creating playlist '{playlistName}'...")
    result = self._GetAPIClient(loginUserID).user_playlist_create(
      loginUserID,
      playlistName,
      public=isPublic,
      description=playlistDescription,
    )
    return cast(str, result["id"])

  def ClearPlaylist(self, loginUserID: str, playlistID: str) -> None:
    pageSize = 100
    gLogger.info(f"Clearing playlist ID '{playlistID}'...")
    playlist = self.QueryPlaylist(loginUserID, playlistID)

    for offset in range(0, len(playlist.trackIDs), pageSize):
      pageTrackIDs = playlist.trackIDs[offset : offset + pageSize]
      self._GetAPIClient(loginUserID).playlist_remove_all_occurrences_of_items(playlistID, pageTrackIDs)

  def AddTracksToPlaylist(self, loginUserID: str, playlistID: str, trackIDs: Sequence[str]) -> None:
    pageSize = 100
    gLogger.info("Adding {} to playlist ID '{}'...".format(Client._FormatNoun(len(trackIDs), "track"), playlistID))

    for offset in range(0, len(trackIDs), pageSize):
      pageTrackIDs = trackIDs[offset : offset + pageSize]
      self._GetAPIClient(loginUserID).playlist_add_items(playlistID, pageTrackIDs)

  def _QueryAllItems(self, loginUserID: str, resultItems: Any) -> List[Any]:
    items: List[Any] = []

    while True:
      items.extend(resultItems["items"])
      if resultItems["next"] is None: return items
      resultItems = self._GetAPIClient(loginUserID)._get(resultItems["next"])

  @staticmethod
  def _FormatNoun(number: int, noun: str) -> str:
    return f"1 {noun}" if number == 1 else f"{number} {noun}s"


class AuthenticationHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
  def do_GET(self) -> None:
    self.send_response(200)
    self.end_headers()

  def log_message(self, format: str, *arguments: Any) -> None:
    pass
