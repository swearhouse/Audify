import json
import logging
import os
import tempfile
from pathlib import Path
from threading import Lock
from urllib.parse import urlencode, urlsplit

from flask import Flask, jsonify, render_template, request
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
LIBRARY_LOCK = Lock()


class LibraryStorageError(Exception):
    pass


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


def read_library(path: Path) -> list[dict[str, str]]:
    try:
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as library_file:
            library = json.load(library_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LibraryStorageError("Could not read the saved playlist library.") from error

    if not isinstance(library, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("title"), str)
        or not isinstance(item.get("url"), str)
        for item in library
    ):
        raise LibraryStorageError("The saved playlist library has an invalid format.")
    return library


def write_library(path: Path, library: list[dict[str, str]]) -> None:
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
    app.config["PLAYLIST_LIBRARY_PATH"] = data_directory / "playlists.json"

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/saved-playlists")
    def saved_playlists():
        try:
            with LIBRARY_LOCK:
                playlists = read_library(Path(app.config["PLAYLIST_LIBRARY_PATH"]))
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
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(url, str)
            or not is_youtube_url(url)
        ):
            return jsonify(error="Provide a playlist title and valid HTTPS YouTube URL."), 400

        playlist = {"title": title.strip(), "url": url.strip()}
        try:
            with LIBRARY_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                playlists = read_library(path)
                existing = next(
                    (item for item in playlists if item["url"] == playlist["url"]),
                    None,
                )
                if existing:
                    existing["title"] = playlist["title"]
                else:
                    playlists.append(playlist)
                write_library(path, playlists)
        except LibraryStorageError:
            app.logger.exception("Could not save playlist")
            return jsonify(error="Could not save the playlist."), 500
        return jsonify(playlist=playlist, updated=existing is not None), 200

    @app.delete("/api/saved-playlists")
    def remove_saved_playlist():
        payload = request.get_json(silent=True)
        url = payload.get("url") if isinstance(payload, dict) else None
        if not isinstance(url, str) or not is_youtube_url(url):
            return jsonify(error="Provide a valid HTTPS YouTube URL."), 400

        try:
            with LIBRARY_LOCK:
                path = Path(app.config["PLAYLIST_LIBRARY_PATH"])
                playlists = read_library(path)
                remaining = [item for item in playlists if item["url"] != url.strip()]
                if len(remaining) == len(playlists):
                    return jsonify(error="Saved playlist was not found."), 404
                write_library(path, remaining)
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

        return jsonify(title=info.get("title") or "YouTube audio", audio_url=info["url"])

    return app
