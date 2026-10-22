import json
import logging
import math
import os
import tempfile
import uuid
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlencode, urlsplit

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
    return get_youtube_video_id(value) is not None


def get_youtube_video_id(value: str) -> str | None:
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return None
    if not is_youtube_url(value):
        return None

    if parsed.hostname == "youtu.be":
        path_parts = parsed.path.strip("/").split("/")
        return path_parts[0] if len(path_parts) == 1 and path_parts[0] else None
    if parsed.path == "/watch":
        video_ids = parse_qs(parsed.query, keep_blank_values=True).get("v", [])
        return (
            video_ids[0].strip()
            if len(video_ids) == 1 and video_ids[0].strip()
            else None
        )
    path_parts = parsed.path.strip("/").split("/")
    if (
        len(path_parts) == 2
        and path_parts[0] in {"embed", "live", "shorts"}
        and path_parts[1]
    ):
        return path_parts[1]
    return None


def get_youtube_playlist_url(value: str) -> str | None:
    if not is_youtube_url(value):
        return None
    try:
        parsed = urlsplit(value.strip())
        playlist_ids = parse_qs(parsed.query, keep_blank_values=True).get("list", [])
    except ValueError:
        return None
    if (
        parsed.path not in {"/playlist", "/watch"}
        or len(playlist_ids) != 1
        or not playlist_ids[0].strip()
    ):
        return None
    return f"https://www.youtube.com/playlist?{urlencode({'list': playlist_ids[0].strip()})}"


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
        ids = []
        for playlist in user_playlists:
            if (
                isinstance(playlist, dict)
                and set(playlist) == {"title", "url"}
                and isinstance(playlist.get("title"), str)
                and isinstance(playlist.get("url"), str)
            ):
                continue
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
                user_playlists = libraries.get(session["username"], [])
                playlists = [
                    playlist for playlist in user_playlists if "id" in playlist
                ]
                legacy_count = len(user_playlists) - len(playlists)
        except PlaylistStorageError as error:
            app.logger.exception("Could not load the user's playlists")
            return jsonify(error=str(error)), 500
        return jsonify(playlists=playlists)

    @app.post("/api/youtube/search")
    def search_youtube():
        payload = request.get_json(silent=True)
        query = payload.get("query") if isinstance(payload, dict) else None
        if (
            not isinstance(query, str)
            or not query.strip()
            or len(query.strip()) > 200
        ):
            return jsonify(error="Enter a search query up to 200 characters."), 400

        options = {
            "extract_flat": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
        }
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(f"ytsearch30:{query.strip()}", download=False)
        except DownloadError:
            app.logger.exception("yt-dlp could not search YouTube")
            return jsonify(error="Could not search YouTube right now."), 422

        entries = info.get("entries") if isinstance(info, dict) else None
        results = []
        if isinstance(entries, (list, tuple)):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                video_id = entry.get("id")
                title = entry.get("title")
                if (
                    not isinstance(video_id, str)
                    or not video_id.strip()
                    or not isinstance(title, str)
                    or not title.strip()
                ):
                    continue
                link = (
                    "https://www.youtube.com/watch?"
                    f"{urlencode({'v': video_id.strip()})}"
                )
                if not is_youtube_video_url(link):
                    continue
                duration = entry.get("duration")
                if (
                    not isinstance(duration, (int, float))
                    or not math.isfinite(duration)
                    or duration < 0
                ):
                    duration = None
                results.append(
                    {
                        "name": title.strip()[:200],
                        "link": link,
                        "duration": duration,
                    }
                )
                if len(results) == 30:
                    break

        return jsonify(results=results)

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
                user_playlists = libraries.setdefault(session["username"], [])
                user_playlists[:] = [item for item in user_playlists if "id" in item]
                user_playlists.append(playlist)
                write_playlists(path, libraries)
        except PlaylistStorageError:
            app.logger.exception("Could not create playlist")
            return jsonify(error="Could not save the playlist."), 500
        return jsonify(playlist=playlist), 201

    @app.post("/api/playlists/import")
    def import_playlist():
        payload = request.get_json(silent=True)
        url = payload.get("url") if isinstance(payload, dict) else None
        playlist_url = get_youtube_playlist_url(url) if isinstance(url, str) else None
        if playlist_url is None:
            return jsonify(error="Enter a valid HTTPS YouTube playlist URL."), 400

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
                info = ydl.extract_info(playlist_url, download=False)
        except DownloadError:
            app.logger.exception("yt-dlp could not import the supplied playlist")
            return jsonify(error="Could not import that YouTube playlist."), 422

        entries = info.get("entries") if isinstance(info, dict) else None
        if not isinstance(entries, (list, tuple)):
            return jsonify(error="No videos were found in that YouTube playlist."), 422
        if len(entries) > 5000:
            return jsonify(
                error="That YouTube playlist has more than 5,000 videos and cannot be imported."
            ), 422

        videos = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            video_id = entry.get("id")
            title = entry.get("title")
            if not isinstance(video_id, str) or not video_id.strip():
                continue
            if not isinstance(title, str) or not title.strip():
                title = "Untitled video"
            video = {
                "name": title.strip()[:200],
                "link": f"https://www.youtube.com/watch?{urlencode({'v': video_id.strip()})}",
            }
            if validate_videos([video]) is not None:
                videos.append(video)

        if not videos:
            return jsonify(error="No videos were found in that YouTube playlist."), 422

        title = info.get("title") if isinstance(info, dict) else None
        if not isinstance(title, str) or not title.strip():
            title = "Imported YouTube playlist"
        playlist = {
            "id": uuid.uuid4().hex,
            "name": title.strip()[:200],
            "videos": videos,
        }
        try:
            with PLAYLISTS_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                libraries = read_playlists(path)
                user_playlists = libraries.setdefault(session["username"], [])
                user_playlists[:] = [item for item in user_playlists if "id" in item]
                user_playlists.append(playlist)
                write_playlists(path, libraries)
        except PlaylistStorageError:
            app.logger.exception("Could not save imported playlist")
            return jsonify(error="Could not save the imported playlist."), 500
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
                playlist = next(
                    (
                        item for item in playlists
                        if item.get("id") == playlist_id
                    ),
                    None,
                )
                if playlist is None:
                    return jsonify(error="Playlist was not found."), 404
                playlist["name"] = name.strip()
                playlist["videos"] = videos
                write_playlists(path, libraries)
        except PlaylistStorageError:
            app.logger.exception("Could not update playlist")
            return jsonify(error="Could not save the playlist."), 500
        return jsonify(playlist=playlist)

    @app.post("/api/playlists/add-song")
    def add_song_to_playlists():
        payload = request.get_json(silent=True)
        playlist_ids = payload.get("playlist_ids") if isinstance(payload, dict) else None
        submitted_video = payload.get("video") if isinstance(payload, dict) else None
        video = (
            {
                "name": submitted_video.get("name"),
                "link": submitted_video.get("link"),
            }
            if isinstance(submitted_video, dict)
            else None
        )
        videos = (
            validate_videos([video])
            if video is not None
            else None
        )
        if (
            not isinstance(playlist_ids, list)
            or not playlist_ids
            or len(playlist_ids) > 5000
            or any(
                not isinstance(playlist_id, str)
                or not playlist_id.strip()
                or len(playlist_id) > 200
                for playlist_id in playlist_ids
            )
            or len(playlist_ids) != len(set(playlist_ids))
        ):
            return jsonify(error="Select one or more valid playlists."), 400
        if videos is None:
            return jsonify(
                error=(
                    "The song details are invalid. Search again or provide a valid "
                    "YouTube video link."
                )
            ), 400

        try:
            with PLAYLISTS_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                libraries = read_playlists(path)
                playlists = libraries.get(session["username"], [])
                selected_playlists = [
                    playlist
                    for playlist in playlists
                    if playlist.get("id") in playlist_ids
                ]
                if len(selected_playlists) != len(playlist_ids):
                    return jsonify(error="One or more playlists were not found."), 404
                video_id = get_youtube_video_id(videos[0]["link"])
                duplicate_playlists = [
                    playlist["name"]
                    for playlist in selected_playlists
                    if any(
                        get_youtube_video_id(existing_video["link"]) == video_id
                        for existing_video in playlist["videos"]
                    )
                ]
                if duplicate_playlists:
                    names = ", ".join(duplicate_playlists)
                    return jsonify(
                        error=f"This song is already in: {names}.",
                        duplicate_playlists=duplicate_playlists,
                    ), 409
                if any(
                    len(playlist["videos"]) >= 5000
                    for playlist in selected_playlists
                ):
                    return jsonify(
                        error="A selected playlist has reached the 5,000-song limit."
                    ), 400
                for playlist in selected_playlists:
                    playlist["videos"].append(videos[0])
                write_playlists(path, libraries)
        except PlaylistStorageError:
            app.logger.exception("Could not add song to playlists")
            return jsonify(error="Could not save the song to those playlists."), 500
        return jsonify(playlists=selected_playlists)

    @app.delete("/api/playlists/<playlist_id>")
    def delete_playlist(playlist_id):
        try:
            with PLAYLISTS_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                libraries = read_playlists(path)
                playlists = libraries.get(session["username"], [])
                remaining = [
                    item for item in playlists if item.get("id") != playlist_id
                ]
                if len(remaining) == len(playlists):
                    return jsonify(error="Playlist was not found."), 404
                libraries[session["username"]] = remaining
                write_playlists(path, libraries)
        except PlaylistStorageError:
            app.logger.exception("Could not delete playlist")
            return jsonify(error="Could not remove the playlist."), 500
        return jsonify(playlists=remaining)

    @app.post("/api/videos/title")
    def video_title():
        payload = request.get_json(silent=True)
        url = payload.get("url") if isinstance(payload, dict) else None
        if not isinstance(url, str) or not is_youtube_video_url(url):
            return jsonify(error="Enter a valid HTTPS YouTube video URL."), 400

        options = {
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
        }
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url.strip(), download=False)
        except DownloadError:
            app.logger.exception("yt-dlp could not load video details")
            return jsonify(error="Could not get the title for that YouTube video."), 422

        title = info.get("title") if isinstance(info, dict) else None
        video_id = info.get("id") if isinstance(info, dict) else None
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(video_id, str)
            or not video_id.strip()
        ):
            return jsonify(error="Could not get the title for that YouTube video."), 422

        video = {
            "name": title.strip()[:200],
            "link": f"https://www.youtube.com/watch?{urlencode({'v': video_id.strip()})}",
        }
        return jsonify(video=video)

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
