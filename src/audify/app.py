import json
import logging
import os
import re
import tempfile
from pathlib import Path
from threading import Lock
from urllib.parse import urlencode, urlsplit

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?"
YOUTUBE_THUMBNAIL_HOSTS = {"i.ytimg.com", "img.youtube.com"}
YOUTUBE_HOSTS = {
    "youtu.be",
    "www.youtube.com",
    "youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
YOUTUBE_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
AUDIO_MIME_TYPES = {
    "aac": "audio/aac",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "opus": "audio/ogg",
    "wav": "audio/wav",
    "webm": "audio/webm",
}
LIBRARY_LOCK = Lock()
USER_LOCK = Lock()
DEFAULT_USERS = {
    "users": [
        {"username": "admin", "password": "admin"},
        {"username": "quest", "password": "guest"},
    ]
}


class LibraryStorageError(Exception):
    pass


class UserStorageError(Exception):
    pass


def read_users(path: Path) -> list[dict[str, str]]:
    temporary_path = None
    try:
        with USER_LOCK:
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=path.parent,
                    delete=False,
                ) as users_file:
                    temporary_path = Path(users_file.name)
                    json.dump(DEFAULT_USERS, users_file, ensure_ascii=False, indent=2)
                    users_file.write("\n")
                os.replace(temporary_path, path)
                temporary_path = None

            with path.open(encoding="utf-8") as users_file:
                document = json.load(users_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).exception(
                    "Could not clean up temporary user accounts file"
                )
        raise UserStorageError("Could not read the user accounts file.") from error

    users = document.get("users") if isinstance(document, dict) else None
    if not isinstance(users, list) or any(
        not isinstance(user, dict)
        or not isinstance(user.get("username"), str)
        or not user["username"]
        or not isinstance(user.get("password"), str)
        or not user["password"]
        for user in users
    ):
        raise UserStorageError("The user accounts file has an invalid format.")
    return users


def is_youtube_url(value: str) -> bool:
    try:
        parsed = urlsplit(value.strip())
        return (
            parsed.scheme == "https"
            and parsed.hostname in YOUTUBE_HOSTS
            and parsed.username is None
            and parsed.password is None
            and parsed.port is None
        )
    except ValueError:
        return False


def is_valid_track_order(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= 5000
        and all(
            isinstance(video_id, str)
            and YOUTUBE_VIDEO_ID_PATTERN.fullmatch(video_id)
            for video_id in value
        )
        and len(value) == len(set(value))
    )


def is_valid_playlist_order(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= 5000
        and all(isinstance(url, str) and is_youtube_url(url) for url in value)
        and len(value) == len(set(value))
    )


def get_thumbnail_url(entry: dict) -> str | None:
    thumbnails = entry.get("thumbnails")
    candidates = thumbnails if isinstance(thumbnails, list) else []
    if isinstance(entry.get("thumbnail"), str):
        candidates = [*candidates, {"url": entry["thumbnail"]}]

    valid_candidates = []
    for thumbnail in candidates:
        if not isinstance(thumbnail, dict) or not isinstance(thumbnail.get("url"), str):
            continue
        url = thumbnail["url"]
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        if (
            parsed.scheme != "https"
            or parsed.hostname not in YOUTUBE_THUMBNAIL_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port is not None
        ):
            continue
        width = thumbnail.get("width")
        height = thumbnail.get("height")
        area = width * height if isinstance(width, int) and isinstance(height, int) else 0
        valid_candidates.append((area, url))

    return max(valid_candidates, default=(0, None), key=lambda candidate: candidate[0])[1]


def read_library(path: Path) -> dict[str, list[dict[str, str]]]:
    try:
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as library_file:
            library = json.load(library_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LibraryStorageError("Could not read the saved playlist library.") from error

    if not isinstance(library, dict) or any(
        not isinstance(username, str)
        or not isinstance(playlists, list)
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("title"), str)
            or not isinstance(item.get("url"), str)
            or (
                "track_order" in item
                and not is_valid_track_order(item["track_order"])
            )
            for item in playlists
        )
        for username, playlists in library.items()
    ):
        raise LibraryStorageError("The saved playlist library has an invalid format.")
    return library


def write_library(path: Path, library: dict[str, list[dict[str, str]]]) -> None:
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as library_file:
            temporary_path = Path(library_file.name)
            json.dump(library, library_file, ensure_ascii=False, indent=2)
            library_file.write("\n")
        os.replace(temporary_path, path)
    except OSError as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).exception(
                    "Could not clean up temporary playlist library file"
                )
        raise LibraryStorageError("Could not save the playlist library.") from error


def create_app() -> Flask:
    app = Flask(__name__)
    data_directory = Path(
        os.environ.get(
            "AUDIFY_DATA_DIR",
            Path(__file__).resolve().parents[2] / "instance",
        )
    )
    app.config["PLAYLIST_LIBRARY_PATH"] = data_directory / "user_playlists.json"
    app.config["USER_FILE_PATH"] = data_directory / "users.json"
    app.secret_key = os.urandom(32)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    @app.before_request
    def require_login():
        if request.endpoint in {"login", "login_api", "static"}:
            return None

        username = session.get("username")
        if not isinstance(username, str):
            if request.endpoint == "index":
                return redirect(url_for("login"))
            return jsonify(error="Authentication required."), 401

        try:
            users = read_users(Path(app.config["USER_FILE_PATH"]))
        except UserStorageError:
            app.logger.exception("Could not validate the signed-in user")
            return jsonify(error="Could not load user accounts."), 500

        if not any(user["username"] == username for user in users):
            session.clear()
            if request.endpoint == "index":
                return redirect(url_for("login"))
            return jsonify(error="Authentication required."), 401
        return None

    @app.get("/login")
    def login():
        return render_template("login.html")

    @app.post("/api/login")
    def login_api():
        payload = request.get_json(silent=True)
        username = payload.get("username") if isinstance(payload, dict) else None
        password = payload.get("password") if isinstance(payload, dict) else None
        if not isinstance(username, str) or not isinstance(password, str):
            return jsonify(error="Enter a username and password."), 400

        try:
            users = read_users(Path(app.config["USER_FILE_PATH"]))
        except UserStorageError:
            app.logger.exception("Could not load user accounts for login")
            return jsonify(error="Could not load user accounts."), 500

        if not any(
            user["username"] == username and user["password"] == password
            for user in users
        ):
            return jsonify(error="Incorrect username or password."), 401

        session.clear()
        session["username"] = username
        return jsonify(success=True)

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(success=True)

    @app.get("/")
    def index():
        return render_template("index.html", username=session["username"])

    @app.get("/api/saved-playlists")
    def saved_playlists():
        try:
            with LIBRARY_LOCK:
                libraries = read_library(Path(app.config["PLAYLIST_LIBRARY_PATH"]))
                playlists = libraries.get(session["username"], [])
        except LibraryStorageError:
            app.logger.exception("Could not load saved playlists")
            return jsonify(error="Could not load saved playlists."), 500
        return jsonify(playlists=playlists)

    @app.post("/api/saved-playlists")
    def save_playlist():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Provide a playlist title and YouTube URL."), 400
        title = payload.get("title")
        url = payload.get("url")
        track_order = payload.get("track_order")
        if (
            not isinstance(title, str)
            or not title.strip()
            or len(title.strip()) > 200
            or not isinstance(url, str)
            or not is_youtube_url(url)
            or (
                "track_order" in payload
                and not is_valid_track_order(track_order)
            )
        ):
            return jsonify(error="Provide a playlist title and valid HTTPS YouTube URL."), 400

        playlist = {"title": title.strip(), "url": url.strip()}
        if "track_order" in payload:
            playlist["track_order"] = track_order
        try:
            with LIBRARY_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                libraries = read_library(path)
                playlists = libraries.get(session["username"], [])
                existing = next(
                    (item for item in playlists if item["url"] == playlist["url"]),
                    None,
                )
                if existing:
                    existing["title"] = playlist["title"]
                    if "track_order" in playlist:
                        existing["track_order"] = playlist["track_order"]
                else:
                    playlists.append(playlist)
                libraries[session["username"]] = playlists
                write_library(path, libraries)
        except LibraryStorageError:
            app.logger.exception("Could not save playlist")
            return jsonify(error="Could not save the playlist."), 500
        return jsonify(playlist=playlist, updated=existing is not None), 200

    @app.put("/api/saved-playlists")
    def update_saved_playlist():
        payload = request.get_json(silent=True)
        url = payload.get("url") if isinstance(payload, dict) else None
        title = payload.get("title") if isinstance(payload, dict) else None
        track_order = payload.get("track_order") if isinstance(payload, dict) else None
        playlist_order = payload.get("playlist_order") if isinstance(payload, dict) else None
        if not isinstance(url, str) or not is_youtube_url(url):
            return jsonify(error="Provide a valid HTTPS YouTube URL."), 400
        if (
            not isinstance(payload, dict)
            or not any(
                key in payload
                for key in ("title", "track_order", "playlist_order")
            )
            or (
                "title" in payload
                and (
                    not isinstance(title, str)
                    or not title.strip()
                    or len(title.strip()) > 200
                )
            )
            or (
                "track_order" in payload
                and not is_valid_track_order(track_order)
            )
            or (
                "playlist_order" in payload
                and not is_valid_playlist_order(playlist_order)
            )
        ):
            return jsonify(error="Provide a valid playlist title or track order."), 400

        try:
            with LIBRARY_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                libraries = read_library(path)
                playlists = libraries.get(session["username"], [])
                existing = next(
                    (item for item in playlists if item["url"] == url.strip()),
                    None,
                )
                if existing is None:
                    return jsonify(error="Saved playlist was not found."), 404
                if "playlist_order" in payload:
                    playlist_urls = {item["url"] for item in playlists}
                    if not set(playlist_order).issubset(playlist_urls):
                        return jsonify(error="Playlist order contains an unknown playlist."), 404
                    ordered_urls = set(playlist_order)
                    playlist_by_url = {item["url"]: item for item in playlists}
                    playlists[:] = [
                        *(playlist_by_url[url] for url in playlist_order),
                        *(item for item in playlists if item["url"] not in ordered_urls),
                    ]
                if "title" in payload:
                    existing["title"] = title.strip()
                if "track_order" in payload:
                    existing["track_order"] = track_order
                write_library(path, libraries)
        except LibraryStorageError:
            app.logger.exception("Could not update saved playlist")
            return jsonify(error="Could not update the saved playlist."), 500
        return jsonify(playlist=existing, playlists=playlists)

    @app.delete("/api/saved-playlists")
    def remove_saved_playlist():
        payload = request.get_json(silent=True)
        url = payload.get("url") if isinstance(payload, dict) else None
        if not isinstance(url, str) or not is_youtube_url(url):
            return jsonify(error="Provide a valid HTTPS YouTube URL."), 400

        try:
            with LIBRARY_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                libraries = read_library(path)
                playlists = libraries.get(session["username"], [])
                remaining = [item for item in playlists if item["url"] != url.strip()]
                if len(remaining) == len(playlists):
                    return jsonify(error="Saved playlist was not found."), 404
                libraries[session["username"]] = remaining
                write_library(path, libraries)
        except LibraryStorageError:
            app.logger.exception("Could not remove saved playlist")
            return jsonify(error="Could not remove the saved playlist."), 500
        return jsonify(playlists=remaining)

    @app.post("/api/playlist")
    def playlist():
        payload = request.get_json(silent=True)
        url = payload.get("url", "") if isinstance(payload, dict) else ""
        if not isinstance(url, str) or not is_youtube_url(url):
            return jsonify(error="Enter a valid HTTPS YouTube URL."), 400

        options = {
            "extract_flat": "in_playlist",
            "ignoreerrors": True,
            "noplaylist": False,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
        }
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url.strip(), download=False)
        except DownloadError:
            app.logger.exception("yt-dlp could not load the supplied playlist")
            return jsonify(error="Could not load that YouTube playlist."), 422

        entries = info.get("entries") if info else None
        if entries is None and info and info.get("id"):
            entries = [info]

        tracks = []
        for entry in entries or []:
            if not entry or not entry.get("id"):
                continue
            video_id = str(entry["id"])
            tracks.append(
                {
                    "id": video_id,
                    "title": entry.get("title") or "Untitled video",
                    "url": f"{YOUTUBE_VIDEO_URL}{urlencode({'v': video_id})}",
                    "thumbnail_url": get_thumbnail_url(entry),
                }
            )

        if not tracks:
            return jsonify(error="No playable videos were found in that playlist."), 422

        return jsonify(title=info.get("title") or "YouTube playlist", tracks=tracks)

    @app.post("/api/resolve")
    def resolve():
        payload = request.get_json(silent=True)
        url = payload.get("url", "") if isinstance(payload, dict) else ""
        if not isinstance(url, str) or not is_youtube_url(url):
            return jsonify(error="Enter a valid HTTPS YouTube video URL."), 400

        options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
        }
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url.strip(), download=False)
        except DownloadError:
            app.logger.exception("yt-dlp could not resolve the supplied URL")
            return jsonify(error="Could not resolve audio for that URL."), 422

        if not info or not info.get("url"):
            return jsonify(error="No playable audio stream was found."), 422

        content_type = info.get("mime_type")
        if not isinstance(content_type, str) or not content_type.startswith("audio/"):
            extension = info.get("ext")
            content_type = (
                AUDIO_MIME_TYPES.get(extension)
                if isinstance(extension, str)
                else None
            ) or "audio/mpeg"

        return jsonify(
            title=info.get("title") or "YouTube audio",
            audio_url=info["url"],
            content_type=content_type,
        )

    return app
