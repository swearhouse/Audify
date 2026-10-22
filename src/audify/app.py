import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlsplit

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


YOUTUBE_HOSTS = {
    "youtu.be",
    "www.youtube.com",
    "youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
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
PLAYLISTS_LOCK = Lock()
USER_LOCK = Lock()
DEFAULT_USERS = {
    "users": [
        {"username": "admin", "password": "admin"},
        {"username": "quest", "password": "guest"},
    ]
}


class UserStorageError(Exception):
    pass


class PlaylistStorageError(Exception):
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


def is_youtube_video_url(value: str) -> bool:
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return False
    if not is_youtube_url(value):
        return False

    if parsed.hostname == "youtu.be":
        path_parts = parsed.path.strip("/").split("/")
        return len(path_parts) == 1 and bool(path_parts[0])
    if parsed.path == "/watch":
        video_ids = parse_qs(parsed.query, keep_blank_values=True).get("v", [])
        return len(video_ids) == 1 and bool(video_ids[0].strip())
    path_parts = parsed.path.strip("/").split("/")
    return (
        len(path_parts) == 2
        and path_parts[0] in {"embed", "live", "shorts"}
        and bool(path_parts[1])
    )


def validate_videos(value: object) -> list[dict[str, str]] | None:
    if not isinstance(value, list) or len(value) > 5000:
        return None
    videos = []
    for video in value:
        if (
            not isinstance(video, dict)
            or set(video) != {"link", "name"}
            or not isinstance(video.get("link"), str)
            or not is_youtube_video_url(video["link"])
            or not isinstance(video.get("name"), str)
            or not video["name"].strip()
            or len(video["name"].strip()) > 200
        ):
            return None
        videos.append({"name": video["name"].strip(), "link": video["link"].strip()})
    return videos


def read_playlists(path: Path) -> dict[str, list[dict]]:
    try:
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as playlists_file:
            playlists = json.load(playlists_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PlaylistStorageError("Could not read the playlist library.") from error

    if not isinstance(playlists, dict):
        raise PlaylistStorageError("The playlist library has an invalid format.")
    for username, user_playlists in playlists.items():
        if not isinstance(username, str) or not isinstance(user_playlists, list):
            raise PlaylistStorageError("The playlist library has an invalid format.")
        if any(
            isinstance(playlist, dict) and set(playlist) == {"title", "url"}
            for playlist in user_playlists
        ):
            raise PlaylistStorageError(
                "Existing playlists use the old YouTube playlist format. "
                "Convert or remove them from user_playlists.json before using "
                "the playlist editor."
            )
        ids = []
        for playlist in user_playlists:
            if (
                not isinstance(playlist, dict)
                or set(playlist) != {"id", "name", "videos"}
                or not isinstance(playlist.get("id"), str)
                or not playlist["id"].strip()
                or len(playlist["id"]) > 200
                or not isinstance(playlist.get("name"), str)
                or not playlist["name"].strip()
                or len(playlist["name"]) > 200
                or validate_videos(playlist.get("videos")) is None
            ):
                raise PlaylistStorageError("The playlist library has an invalid format.")
            ids.append(playlist["id"])
        if len(ids) != len(set(ids)):
            raise PlaylistStorageError("The playlist library contains duplicate ids.")
    return playlists


def write_playlists(path: Path, playlists: dict[str, list[dict]]) -> None:
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as playlists_file:
            temporary_path = Path(playlists_file.name)
            json.dump(playlists, playlists_file, ensure_ascii=False, indent=2)
            playlists_file.write("\n")
        os.replace(temporary_path, path)
    except OSError as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).exception(
                    "Could not clean up temporary playlist file"
                )
        raise PlaylistStorageError("Could not save the playlist library.") from error


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

    @app.get("/api/playlists")
    def playlists_api():
        try:
            with PLAYLISTS_LOCK:
                libraries = read_playlists(Path(app.config["PLAYLIST_LIBRARY_PATH"]))
                playlists = libraries.get(session["username"], [])
        except PlaylistStorageError as error:
            app.logger.exception("Could not load the user's playlists")
            return jsonify(error=str(error)), 500
        return jsonify(playlists=playlists)

    @app.post("/api/playlists")
    def create_playlist():
        payload = request.get_json(silent=True)
        name = payload.get("name") if isinstance(payload, dict) else None
        videos = validate_videos(payload.get("videos")) if isinstance(payload, dict) else None
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name.strip()) > 200
            or videos is None
        ):
            return jsonify(error="Provide a playlist name and valid video list."), 400

        playlist = {"id": uuid.uuid4().hex, "name": name.strip(), "videos": videos}
        try:
            with PLAYLISTS_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                libraries = read_playlists(path)
                libraries.setdefault(session["username"], []).append(playlist)
                write_playlists(path, libraries)
        except PlaylistStorageError:
            app.logger.exception("Could not create playlist")
            return jsonify(error="Could not save the playlist."), 500
        return jsonify(playlist=playlist), 201

    @app.put("/api/playlists/<playlist_id>")
    def update_playlist(playlist_id):
        payload = request.get_json(silent=True)
        name = payload.get("name") if isinstance(payload, dict) else None
        videos = validate_videos(payload.get("videos")) if isinstance(payload, dict) else None
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name.strip()) > 200
            or videos is None
        ):
            return jsonify(error="Provide a playlist name and valid video list."), 400

        try:
            with PLAYLISTS_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                libraries = read_playlists(path)
                playlists = libraries.get(session["username"], [])
                playlist = next((item for item in playlists if item["id"] == playlist_id), None)
                if playlist is None:
                    return jsonify(error="Playlist was not found."), 404
                playlist["name"] = name.strip()
                playlist["videos"] = videos
                write_playlists(path, libraries)
        except PlaylistStorageError:
            app.logger.exception("Could not update playlist")
            return jsonify(error="Could not save the playlist."), 500
        return jsonify(playlist=playlist)

    @app.delete("/api/playlists/<playlist_id>")
    def delete_playlist(playlist_id):
        try:
            with PLAYLISTS_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                libraries = read_playlists(path)
                playlists = libraries.get(session["username"], [])
                remaining = [item for item in playlists if item["id"] != playlist_id]
                if len(remaining) == len(playlists):
                    return jsonify(error="Playlist was not found."), 404
                libraries[session["username"]] = remaining
                write_playlists(path, libraries)
        except PlaylistStorageError:
            app.logger.exception("Could not delete playlist")
            return jsonify(error="Could not remove the playlist."), 500
        return jsonify(playlists=remaining)

    @app.post("/api/resolve")
    def resolve():
        payload = request.get_json(silent=True)
        url = payload.get("url", "") if isinstance(payload, dict) else ""
        if not isinstance(url, str) or not is_youtube_video_url(url):
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
