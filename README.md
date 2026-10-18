# Bragi

Bragi is a small, self-hosted web audio player for a trusted home network.
Paste a YouTube video or playlist URL to load its tracks, then select a track
to play it in your browser. Bragi supports previous/next playback, shuffle,
track thumbnails, and a saved-playlist library that is separate for each user.
It resolves streams when you play a track; it does not download or store audio.

Bragi requires a username and password to use the app and its APIs. It is
intended for a trusted local network, not direct public exposure. The app uses
HTTP by default, so login credentials are not encrypted in transit. Do not
forward its port to the internet; use an HTTPS reverse proxy if you need remote
access.

## User accounts

Bragi stores accounts as plaintext in `users.json`, in its data directory. On
the first login attempt, if the file does not already exist, Bragi creates it
with these initial accounts:

```json
{
  "users": [
    {
      "username": "admin",
      "password": "admin"
    },
    {
      "username": "quest",
      "password": "guest"
    }
  ]
}
```

Sign in with one of these accounts, then edit `users.json` directly on the
server to change passwords or add/remove accounts. Keep the same JSON shape:
each entry needs a non-empty `username` and `password`, and usernames should be
unique. For example, change a password by editing its value, or add another
account by adding an object to the `users` array. Save valid JSON. Changes are
checked against active sessions on each request; removing an account signs
that user out on their next request. Bragi does not provide an in-app user
editor.

Change both initial passwords before sharing access. Anyone who can read the
data directory can read every password in this file. Do not commit `users.json`
to source control or share its contents.

## Data files and persistence

Bragi uses a data directory for account and playlist JSON files:

- `users.json` is created on the first login attempt.
- `user_playlists.json` is created when a user first saves a playlist. It
  contains separate playlist lists keyed by username.
- The older shared `playlists.json`, if present, is left untouched and is not
  imported into per-user libraries.

Keep the data directory persistent and writable by the Bragi process or
container. Back it up if you want to preserve accounts and saved playlists.

## Run locally with Python

Use Python 3.10 or newer. From the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m audify
```

Open `http://localhost:8000`. The default data directory is `instance` in the
project folder, so the account file is `instance\users.json`. To use Bragi
from another device on the home network, open `http://<host-LAN-IP>:8000`.

## Run with Docker Compose

Install Docker with Compose support. From the project folder:

```bash
docker compose up -d --build
```

Open `http://<host-LAN-IP>:8000` from a device on the same network. Compose
stores Bragi data in the named `bragi-data` volume. To stop Bragi, run:

```bash
docker compose down
```

## Run on CasaOS

Build Bragi's image on the CasaOS machine from the project source. For example,
over SSH, from a suitable working directory:

```bash
sudo docker build -t bragi:latest https://github.com/swearhouse/Audify.git#main
sudo mkdir -p /DATA/AppData/bragi-data
```

Then in CasaOS **Manual App Install**, use:

- Docker image: `bragi`
- Tag: `latest`
- Web UI: HTTP, port `8000`, path `/`
- Port mapping: host `8000` to container `8000`, TCP
- Volume: `/DATA/AppData/bragi-data` to `/var/lib/bragi`
- Restart policy: `unless-stopped`, if available

After the first login attempt, edit
`/DATA/AppData/bragi-data/users.json` on the CasaOS host to manage accounts.
Saved playlists will be stored in
`/DATA/AppData/bragi-data/user_playlists.json` after a user first saves one.
The host directory must be writable by Bragi's container user.

## Tests

Install the test dependency and run the suite:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest
```
