# Bragi

A small local-network proof of concept for playing audio from a pasted YouTube
playlist or video URL. Loading a playlist only displays its tracks; playback
starts when you select a track. The app displays the playlist as a clickable track list,
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

Bragi requires a username and password to open the app or use its APIs. On the
first login attempt, it creates `users.json` beside `playlists.json` with the
initial accounts `admin` / `admin` and `quest` / `guest`. Edit that JSON file
to change passwords or add and remove accounts; account changes are checked
against active sessions on each request. The file contains plaintext passwords
and is never returned by the app's network endpoints. Change the initial
passwords before allowing other people to access Bragi, and restrict access to
the data directory. Plain HTTP does not encrypt credentials in transit; use
Bragi only on a trusted LAN or put it behind an HTTPS reverse proxy.

This project does not download or store audio. Use it only for content you are
authorized to access this way. YouTube delivery methods can change, and
audio-only playback outside YouTube's supported player may not be supported by
YouTube's terms.

## Run on Windows

Use Python 3.10 or newer:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m audify
```

Open `http://localhost:8000` on the host computer. To use it from another
device on your home network, open `http://<host-computer-LAN-IP>:8000`.
The server listens on all network interfaces, so only run it on a trusted
network. The first login attempt creates `instance\users.json`; edit it to
change the default credentials or manage accounts.

## Run as a Windows service

To start Bragi automatically at boot and keep it available when nobody is
signed in, install it as a Windows service using WinSW:

1. Set up Bragi from the project folder as described above. The virtual
   environment must be at `.venv` in this folder.
2. Download the current WinSW x64 executable from the
   [WinSW releases page](https://github.com/winsw/winsw/releases), place it in
   this folder, and name it `BragiService.exe`. Keep the included
   `BragiService.xml` beside it.
3. Open PowerShell as Administrator in this folder and run:

   ```powershell
   .\BragiService.exe install
   .\BragiService.exe start
   ```

   The service starts automatically at boot and restarts if Bragi exits.
   WinSW writes rolling logs to the `logs` folder.
4. In the same elevated PowerShell window, allow port 8000 on private
   networks only:

   ```powershell
   New-NetFirewallRule -DisplayName "Bragi (Private LAN)" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Private
   ```

5. On the host PC, open `http://localhost:8000`. Find its LAN IPv4 address
   with `ipconfig`; other devices on the same home network can open
   `http://<host-computer-LAN-IP>:8000`. Ensure the host network is marked
   **Private** in Windows network settings. A DHCP reservation in your router
   can keep the host's LAN address stable.

To stop or remove the service, run these commands from an elevated PowerShell
window in the project folder:

```powershell
.\BragiService.exe stop
.\BragiService.exe uninstall
```

Do not allow access from Public networks or forward port 8000 through your
router. Keep the service account's permissions to the project folder,
especially `instance\playlists.json` and `instance\users.json`, in mind.

## Run with Docker Compose

Install Docker Desktop for Windows and make sure its Linux container engine is
running. From the project folder, build and start Bragi:

```powershell
docker compose up -d --build
```

Open `http://localhost:8000` on the PC running Docker, or
`http://<host-computer-LAN-IP>:8000` from another device on the home network.
If port 8000 is already in use by a manually started Bragi instance or the
Windows service, stop that instance before starting the container.

View logs or stop the container with:

```powershell
docker compose logs -f
docker compose down
```

Compose restarts the container automatically unless it has been explicitly
stopped. To have Bragi return after a PC reboot, configure Docker Desktop to
start when you sign in. The `bragi-data` volume keeps `playlists.json` and
`users.json` across container removal or recreation. On CasaOS, you can
instead mount a host folder at `/var/lib/bragi` and edit its `users.json`
directly. Ensure the folder is writable by the container's `bragi` user.

Allow inbound TCP port 8000 through Windows Firewall on **Private** networks
only if other home devices cannot connect. Do not allow access from Public
networks or forward the port through your router.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest
```
