# Audify

A small local-network proof of concept for playing audio from a pasted YouTube
playlist or video URL. The app displays the playlist as a clickable track list,
with Previous and Next controls and automatic advancement. `yt-dlp` resolves
each audio format when its track is selected, and the browser's audio player
plays the resulting stream. The current track's YouTube thumbnail is shown
beside its title when available. Playback belongs to the page: it continues while
the browser is minimized and stops when the page is closed. Next stops at the
end of the playlist; Previous always selects the preceding track. Every track
starts at 0:00 whenever selected. Randomize shuffles the track list and
upcoming playback order while keeping the current track selected. Loaded
playlists can be saved to a JSON library on the host, reopened after restarting
the app, and removed from the library. Saving the same URL again updates its
saved title. The Save playlist button is enabled only after loading a playlist
through the URL field's Load button. The library is stored in
`instance/playlists.json` in the project folder. The lightweight responsive
interface places the saved library on the left and the player controls and
playlist queue on the right on wider screens; it stacks them on narrow screens.
If a track's audio stream fails to load, the player retries twice before
automatically moving to the next track.

This project does not download or store audio. Use it only for content you are
authorized to access this way. YouTube delivery methods can change, and
audio-only playback outside YouTube's supported player may not be supported by
YouTube's terms.

## Run on Windows

Use Python 3.10 or newer:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m audify
```

Open `http://localhost:8000` on the host computer. To use it from another
device on your home network, open `http://<host-computer-LAN-IP>:8000`.
The server listens on all network interfaces and has no authentication, so
only run it on a trusted network.

## Tests

```powershell
python -m pip install -e ".[test]"
python -m pytest
```
