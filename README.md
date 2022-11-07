<!--
   - Copyright (C) 2022 Julian Valentin
   -
   - This Source Code Form is subject to the terms of the Mozilla Public
   - License, v. 2.0. If a copy of the MPL was not distributed with this
   - file, You can obtain one at https://mozilla.org/MPL/2.0/.
   -->

# Shufflr

![Shufflr](resources/card.svg)

Shuffle Spotify playlists such that consecutive songs are similar.

## Installation

```bash
pip install .
```

## Usage

```bash
python3 -m shufflr --clientSecret CLIENT_SECRET --inputPlaylists PLAYLIST1 PLAYLIST2
```

## Arguments

* **[Output arguments](#output-arguments):** [`-h` / `--help`](#-h----help), [`-q` / `--quiet`](#-q----quiet), [`-v` / `--verbose`](#-v----verbose)
* **[Input playlist arguments](#input-playlist-arguments):** [`-i` / `--inputPlaylists`](#-i----inputplaylists), [`-w` / `--inputPlaylistWeights`](#-w----inputplaylistweights)
* **[Song selection arguments](#song-selection-arguments):** [`--maximumNumberOfSongs`](#--maximumnumberofsongs), [`--tspSolutionDuration`](#--tspsolutionduration), [`--acousticnessWeight`](#--acousticnessweight), [`--minimumAcousticness`](#--minimumacousticness), [`--maximumAcousticness`](#--maximumacousticness), [`--danceabilityWeight`](#--danceabilityweight), [`--minimumDanceability`](#--minimumdanceability), [`--maximumDanceability`](#--maximumdanceability), [`--differentArtistWeight`](#--differentartistweight), [`--energyWeight`](#--energyweight), [`--minimumEnergy`](#--minimumenergy), [`--maximumEnergy`](#--maximumenergy), [`--genreWeight`](#--genreweight), [`--instrumentalnessWeight`](#--instrumentalnessweight), [`--minimumInstrumentalness`](#--minimuminstrumentalness), [`--maximumInstrumentalness`](#--maximuminstrumentalness), [`--keyWeight`](#--keyweight), [`--livenessWeight`](#--livenessweight), [`--minimumLiveness`](#--minimumliveness), [`--maximumLiveness`](#--maximumliveness), [`--speechinessWeight`](#--speechinessweight), [`--minimumSpeechiness`](#--minimumspeechiness), [`--maximumSpeechiness`](#--maximumspeechiness), [`--tempoWeight`](#--tempoweight), [`--minimumTempo`](#--minimumtempo), [`--maximumTempo`](#--maximumtempo), [`--valenceWeight`](#--valenceweight), [`--minimumValence`](#--minimumvalence), [`--maximumValence`](#--maximumvalence)
* **[Output playlist arguments](#output-playlist-arguments):** [`-o` / `--outputPlaylist`](#-o----outputplaylist), [`--outputPlaylistDescription`](#--outputplaylistdescription), [`--outputPlaylistIsPublic`](#--outputplaylistispublic), [`-f` / `--overwriteOutputPlaylist`](#-f----overwriteoutputplaylist)
* **[API arguments](#api-arguments):** [`--clientID`](#--clientid), [`--clientSecret`](#--clientsecret), [`--redirectURI`](#--redirecturi), [`--resetAuthenticationCache`](#--resetauthenticationcache), [`--disableRequestCache`](#--disablerequestcache), [`--resetRequestCache`](#--resetrequestcache)

### Output Arguments

#### `-h` / `--help`

Show a help message and exit.

#### `-q` / `--quiet`

Only print warnings and errors.

#### `-v` / `--verbose`

Print log messages. Specify multiple times to increase log verbosity.

### Input Playlist Arguments

#### `-i` / `--inputPlaylists`

Required.

Format: `-i PLAYLISTSPECIFIER [PLAYLISTSPECIFIER ...]` / `--inputPlaylists PLAYLISTSPECIFIER [PLAYLISTSPECIFIER ...]`

Playlist(s) to take the songs to be shuffled from. The format is `LOGIN_USER_ID/PLAYLIST_OWNER_ID/PLAYLIST_DISPLAY_NAME` or `PLAYLIST_OWNER_ID/PLAYLIST_DISPLAY_NAME`. If you use the first format, then the playlist must be visible to the specified login user. For example, the playlist is public, or it is private and the login user is a follower or collaborator of the playlist. If you use the second format, then the playlist owner is used as login user. To use the playlist of the user's liked songs, use `liked` or `saved` for `PLAYLIST_DISPLAY_NAME`. This is only possible if `LOGIN_USER_ID` equals `PLAYLIST_OWNER_ID` (e.g., if you use the second format), as it is not possible access other users' liked songs.

#### `-w` / `--inputPlaylistWeights`

Format: `-w PLAYLISTWEIGHT [PLAYLISTWEIGHT ...]` / `--inputPlaylistWeights PLAYLISTWEIGHT [PLAYLISTWEIGHT ...]`

Weights for the shuffling of the input playlist. Specify one weight per input playlist. If you use 1 for all playlists, then the target playlist contains equally many songs from each input playlist. If you change the value for a playlist to 2, then twice as many songs are taken from that playlist compared to the other playlists. Use the special value `*` to include all songs of a playlist. This playlist is then discarded for the computation of the number of songs for the other playlists. The default is to use `*` for all input playlists.

### Song Selection Arguments

#### `--maximumNumberOfSongs`

Format: `--maximumNumberOfSongs MAXIMUMNUMBEROFSONGS`

Maximum number of songs in the output playlist. If omitted, then all songs are taken.

#### `--tspSolutionDuration`

Format: `--tspSolutionDuration TSPSOLUTIONDURATION`

Number of seconds taken to solve the traveling salesperson problem heuristically. For technical reasons, the duration is rounded up to the next integer. (default value: `10.0`)

#### `--acousticnessWeight`

Format: `--acousticnessWeight ACOUSTICNESSWEIGHT`

Weight of song feature `acousticness` (confidence whether the song is acoustic). (default value: `1.0`)

#### `--minimumAcousticness`

Format: `--minimumAcousticness MINIMUMACOUSTICNESS`

Minimum permitted value of song feature `acousticness` (confidence whether the song is acoustic) between 0 and 100.

#### `--maximumAcousticness`

Format: `--maximumAcousticness MAXIMUMACOUSTICNESS`

Maximum permitted value of song feature `acousticness` (confidence whether the song is acoustic) between 0 and 100.

#### `--danceabilityWeight`

Format: `--danceabilityWeight DANCEABILITYWEIGHT`

Weight of song feature `danceability` (how suitable the song is for dancing based on a combination of musical elements including tempo, rhythm stability, beat strength, and overall regularity). (default value: `1.0`)

#### `--minimumDanceability`

Format: `--minimumDanceability MINIMUMDANCEABILITY`

Minimum permitted value of song feature `danceability` (how suitable the song is for dancing based on a combination of musical elements including tempo, rhythm stability, beat strength, and overall regularity) between 0 and 100.

#### `--maximumDanceability`

Format: `--maximumDanceability MAXIMUMDANCEABILITY`

Maximum permitted value of song feature `danceability` (how suitable the song is for dancing based on a combination of musical elements including tempo, rhythm stability, beat strength, and overall regularity) between 0 and 100.

#### `--differentArtistWeight`

Format: `--differentArtistWeight DIFFERENTARTISTWEIGHT`

Weight of song feature `differentArtist` (whether the artists of the song are different from the previous song). (default value: `5.0`)

#### `--energyWeight`

Format: `--energyWeight ENERGYWEIGHT`

Weight of song feature `energy` (perceptual measure of intensity and activity; typically, energetic tracks feel fast, loud, and noisy). (default value: `1.0`)

#### `--minimumEnergy`

Format: `--minimumEnergy MINIMUMENERGY`

Minimum permitted value of song feature `energy` (perceptual measure of intensity and activity; typically, energetic tracks feel fast, loud, and noisy) between 0 and 100.

#### `--maximumEnergy`

Format: `--maximumEnergy MAXIMUMENERGY`

Maximum permitted value of song feature `energy` (perceptual measure of intensity and activity; typically, energetic tracks feel fast, loud, and noisy) between 0 and 100.

#### `--genreWeight`

Format: `--genreWeight GENREWEIGHT`

Weight of song feature `genre` (whether the genre of the song is similar to the previous song). (default value: `3.0`)

#### `--instrumentalnessWeight`

Format: `--instrumentalnessWeight INSTRUMENTALNESSWEIGHT`

Weight of song feature `instrumentalness` (whether a track contains no vocals; 'ooh' and 'aah' sounds are treated as instrumental in this context). (default value: `1.0`)

#### `--minimumInstrumentalness`

Format: `--minimumInstrumentalness MINIMUMINSTRUMENTALNESS`

Minimum permitted value of song feature `instrumentalness` (whether a track contains no vocals; 'ooh' and 'aah' sounds are treated as instrumental in this context) between 0 and 100.

#### `--maximumInstrumentalness`

Format: `--maximumInstrumentalness MAXIMUMINSTRUMENTALNESS`

Maximum permitted value of song feature `instrumentalness` (whether a track contains no vocals; 'ooh' and 'aah' sounds are treated as instrumental in this context) between 0 and 100.

#### `--keyWeight`

Format: `--keyWeight KEYWEIGHT`

Weight of song feature `key` (whether the key of the song is harmonically compatible to the previous song). (default value: `3.0`)

#### `--livenessWeight`

Format: `--livenessWeight LIVENESSWEIGHT`

Weight of song feature `liveness` (confidence whether an audience is present in the recording). (default value: `1.0`)

#### `--minimumLiveness`

Format: `--minimumLiveness MINIMUMLIVENESS`

Minimum permitted value of song feature `liveness` (confidence whether an audience is present in the recording) between 0 and 100.

#### `--maximumLiveness`

Format: `--maximumLiveness MAXIMUMLIVENESS`

Maximum permitted value of song feature `liveness` (confidence whether an audience is present in the recording) between 0 and 100.

#### `--speechinessWeight`

Format: `--speechinessWeight SPEECHINESSWEIGHT`

Weight of song feature `speechiness` (presence of spoken words in the song; values above 66 are probably made entirely of spoken words). (default value: `1.0`)

#### `--minimumSpeechiness`

Format: `--minimumSpeechiness MINIMUMSPEECHINESS`

Minimum permitted value of song feature `speechiness` (presence of spoken words in the song; values above 66 are probably made entirely of spoken words) between 0 and 100.

#### `--maximumSpeechiness`

Format: `--maximumSpeechiness MAXIMUMSPEECHINESS`

Maximum permitted value of song feature `speechiness` (presence of spoken words in the song; values above 66 are probably made entirely of spoken words) between 0 and 100.

#### `--tempoWeight`

Format: `--tempoWeight TEMPOWEIGHT`

Weight of song feature `tempo` (tempo of the song in beats per minute). (default value: `2.0`)

#### `--minimumTempo`

Format: `--minimumTempo MINIMUMTEMPO`

Minimum permitted value of song feature `tempo` (tempo of the song in beats per minute) between 0 and 100.

#### `--maximumTempo`

Format: `--maximumTempo MAXIMUMTEMPO`

Maximum permitted value of song feature `tempo` (tempo of the song in beats per minute) between 0 and 100.

#### `--valenceWeight`

Format: `--valenceWeight VALENCEWEIGHT`

Weight of song feature `valence` (musical positiveness conveyed by the song). (default value: `1.0`)

#### `--minimumValence`

Format: `--minimumValence MINIMUMVALENCE`

Minimum permitted value of song feature `valence` (musical positiveness conveyed by the song) between 0 and 100.

#### `--maximumValence`

Format: `--maximumValence MAXIMUMVALENCE`

Maximum permitted value of song feature `valence` (musical positiveness conveyed by the song) between 0 and 100.

### Output Playlist Arguments

#### `-o` / `--outputPlaylist`

Format: `-o PLAYLISTSPECIFIER` / `--outputPlaylist PLAYLISTSPECIFIER`

If specified, the list of shuffled songs is saved as a playlist with this name (`--overwriteOutputPlaylist` has to be specified if the playlist already exists). Use the format `PLAYLIST_OWNER_ID/PLAYLIST_DISPLAY_NAME`. Otherwise, the playlist is just printed (except if `--quiet` is given).

#### `--outputPlaylistDescription`

Format: `--outputPlaylistDescription PLAYLISTDESCRIPTION`

The description of the output playlist created by `--outputPlaylist`. (default value: `Created by Shufflr`)

#### `--outputPlaylistIsPublic`

If specified, the output playlist created with `--outputPlaylist` is public. Otherwise, by default, it is private.

#### `-f` / `--overwriteOutputPlaylist`

If the output playlist specified by `--outputPlaylist` already exists, overwrite it. Otherwise, an exception is thrown to prevent data loss.

### API Arguments

#### `--clientID`

Format: `--clientID CLIENTID`

Client ID - unique identifier of the app. (default value: `c322a584f11a4bdcaaac83b0776bd021`)

#### `--clientSecret`

Format: `--clientSecret CLIENTSECRET`

Client secret to authenticate the app.

#### `--redirectURI`

Format: `--redirectURI REDIRECTURI`

URI opened by Spotify after successful logins. (default value: `http://127.0.0.1:11793/`)

#### `--resetAuthenticationCache`

Delete cache file for API authentication tokens when starting.

#### `--disableRequestCache`

Prevent storing API requests in a cache file and re-using responses.

#### `--resetRequestCache`

Delete cache file for API requests and responses when starting.
