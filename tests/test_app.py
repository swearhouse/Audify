import json
from unittest.mock import patch

import pytest

from audify.app import create_app, is_youtube_url


@pytest.fixture
def app(tmp_path):
    app = create_app()
    app.config["PLAYLIST_LIBRARY_PATH"] = tmp_path / "user_playlists.json"
    app.config["USER_FILE_PATH"] = tmp_path / "users.json"
    return app


@pytest.fixture
def client(app):
    client = app.test_client()
    response = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200
    return client


def test_accepts_youtube_video_urls():
    assert is_youtube_url("https://www.youtube.com/watch?v=example")
    assert is_youtube_url("https://youtu.be/example")


def test_rejects_non_youtube_urls_and_non_https():
    assert not is_youtube_url("http://www.youtube.com/watch?v=example")
    assert not is_youtube_url("https://example.com/video")
    assert not is_youtube_url("https://youtube.com.example.com/watch?v=example")


def test_homepage_renders_player(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"<title>Bragi</title>" in response.data
    assert b'<link rel="icon" type="image/png" href="/static/bragi.png">' in response.data
    assert b"<img" in response.data
    assert b'class="brand-mark"' in response.data
    assert b"https://raw.githubusercontent.com/swearhouse/Audify/main/src/audify/static/bragi.png" in response.data
    assert b'id="sidebar-toggle"' in response.data
    assert b'aria-expanded="true"' in response.data
    assert b'aria-controls="sidebar-content"' in response.data
    assert b'const sidebarContent = document.querySelector("#sidebar-content");' in response.data
    assert b'sidebarContent.hidden = expanded;' in response.data
    assert b"@property --ambient-color" in response.data
    assert b"inherits: false;" in response.data
    assert b"transition: --ambient-color 1.2s ease;" in response.data
    assert b"shiftAmbientColor();" in response.data
    assert b"function selectTrack(index)" in response.data
    assert b"button.addEventListener(\"click\", () => selectTrack(index));" in response.data
    assert b"nextButton.addEventListener(\"click\", () => selectTrack(currentIndex + 1));" in response.data
    assert b"function advanceTrack(index)" in response.data
    assert b"advanceTrack(currentIndex + 1);" in response.data
    assert b"advanceTrack(index + 1);" in response.data
    assert b'class="app-shell"' in response.data
    assert b'class="sidebar"' in response.data
    assert b'class="workspace"' in response.data
    assert b"align-content: start;" in response.data
    assert b"padding: 8px 0;" not in response.data
    assert b"<h1>Listen</h1>" not in response.data
    assert b"Play a YouTube playlist or video." not in response.data
    assert b"align-items: start;" in response.data
    assert b".saved-library {\n        flex: none;" in response.data
    assert b".queue-card {\n        display: flex;\n        flex: none;" in response.data
    assert b"min-height: 220px;" not in response.data
    assert b"max-height: 360px;" in response.data
    assert b"max-height: 52vh;" not in response.data
    assert b'player.style.setProperty("--ambient-color", ambientColor);' in response.data
    assert response.data.index(b'class="sidebar"') < response.data.index(b'class="workspace"')
    assert b'<section class="saved-library" aria-label="Saved playlists">' in response.data
    assert b'<h2 id="saved-heading">Saved playlists</h2>' not in response.data
    assert b'id="saved-status" role="status" aria-live="polite"' in response.data
    assert response.data.index(b'id="saved-playlists"') < response.data.index(b'class="sidebar-divider"')
    assert response.data.index(b'class="sidebar-divider"') < response.data.index(b'id="url-form"')
    assert response.data.index(b'id="url-form"') < response.data.index(b'class="workspace"')
    assert b"#url {\n        width: 100%;" in response.data
    assert b'class="player-card"' in response.data
    assert b'class="queue-card"' in response.data
    assert b"@media (max-width: 640px)" in response.data
    assert b"grid-template-columns: 1fr;\n          gap: 8px;" in response.data
    assert b".workspace {\n          gap: 8px;\n          padding: 0;" in response.data
    assert b'id="current-thumbnail"' in response.data
    assert b'<audio id="player" hidden></audio>' in response.data
    assert b'id="play-pause-button"' in response.data
    assert b'id="stop-button"' in response.data
    assert b'id="previous-button"' in response.data
    assert b'id="next-button"' in response.data
    assert b'id="cast-button"' in response.data
    assert b"Material+Symbols+Outlined" in response.data
    assert b">skip_previous</span>" in response.data
    assert b">play_arrow</span>" in response.data
    assert b">stop</span>" in response.data
    assert b">skip_next</span>" in response.data
    assert b">cast</span>" in response.data
    assert b">playlist_play</span>" in response.data
    assert b">bookmark_add</span>" in response.data
    assert b'<span>Save</span>' in response.data
    assert b"Randomize</span>" not in response.data
    assert b"shuffle" not in response.data
    assert b"randomize-button" not in response.data
    assert b"place-items: center;" in response.data
    assert b'removeButton.textContent = "delete";' in response.data
    assert b'id="logout-button"' in response.data
    assert b">logout</span>" in response.data
    assert b'id="seek-slider"' in response.data
    assert b'id="volume-slider"' in response.data
    assert b"remotePlayerController.playOrPause();" in response.data
    assert b"remotePlayerController.stop();" in response.data
    assert b"remotePlayerController.seek();" in response.data
    assert b"castSession.getMediaSession()" in response.data
    assert b"mediaSession.idleReason === chrome.cast.media.IdleReason.FINISHED" in response.data
    assert b"cast.framework.SessionEventType.MEDIA_SESSION" in response.data
    assert b"mediaSession.addUpdateListener(castMediaUpdateListener);" in response.data
    assert b"castMediaSession.removeUpdateListener(castMediaUpdateListener);" in response.data
    assert b"remotePlayer.idleReason" not in response.data
    assert b"&& castMediaReady" in response.data
    assert b"&& !castCompletionHandled" in response.data
    assert b"castCompletionHandled = true;" in response.data
    assert b'id="saved-playlists"' in response.data
    assert b'<dialog id="delete-playlist-dialog"' in response.data
    assert b'value="cancel">Cancel</button>' in response.data
    assert b'value="delete">Delete</button>' in response.data
    assert b"confirmDeleteSavedPlaylist(playlist.title)" in response.data
    assert b'id="save-button"' in response.data
    assert b'id="logout-button"' in response.data
    assert b"Signed in as <strong>admin</strong>" in response.data
    assert b'id="tracks"' in response.data
    assert b'id="playlist-search"' in response.data
    assert b'type="search"' in response.data
    assert b'aria-label="Search tracks in the current playlist"' in response.data
    assert b'id="track-search-status" role="status" aria-live="polite" hidden' in response.data
    assert b'playlistSearch.addEventListener("input", renderTracks);' in response.data
    assert b'.filter(({ track }) => track.title.toLocaleLowerCase().includes(query));' in response.data
    assert b"track-drag-handle" not in response.data
    assert b"function moveTrack(" not in response.data
    assert b"randomize" not in response.data
    assert b"shuffle" not in response.data
    assert b"function renameSavedPlaylist(playlist, item, originalButtons)" in response.data
    assert b"async function moveSavedPlaylist(fromIndex, toIndex)" in response.data
    assert b'classList.add("saved-playlist-drag-handle")' in response.data
    assert b'dragHandle.draggable = true;' in response.data
    assert b'event.key === "ArrowUp"' in response.data
    assert b'event.key === "ArrowDown"' in response.data
    assert b"Move Playlist 1 up" not in response.data
    assert b"Move Playlist 1 down" not in response.data
    assert b'body: JSON.stringify({\n              url: playlistOrder[0],\n              playlist_order: playlistOrder,\n            })' in response.data
    assert b".saved-playlist-rename .saved-playlist-action" in response.data
    assert b'window.prompt("Rename saved playlist:"' not in response.data
    assert b'method: "PUT"' in response.data
    assert b"(${tracks.length} songs)" in response.data
    assert b"const maxAudioLoadRetries = 2;" in response.data
    assert b"advanceTrack(index + 1);" in response.data
    assert b"await playTrack(0);" not in response.data
    playlist_loader = response.data.split(b"async function loadPlaylist(", 1)[1].split(
        b"async function refreshSavedPlaylists", 1
    )[0]
    assert b"clearPlayer();" not in playlist_loader
    assert b"if (!playbackContinues)" in playlist_loader
    assert b"currentIndex = -1;" in playlist_loader
    assert b"++playbackRequest;" in playlist_loader
    assert b'playlistTitle.textContent = "No playlist loaded";' not in playlist_loader


def test_homepage_requires_login(app):
    response = app.test_client().get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/saved-playlists"),
        ("post", "/api/saved-playlists"),
        ("put", "/api/saved-playlists"),
        ("delete", "/api/saved-playlists"),
        ("post", "/api/playlist"),
        ("post", "/api/resolve"),
    ],
)
def test_api_endpoints_require_login(app, method, path):
    response = getattr(app.test_client(), method)(path)

    assert response.status_code == 401
    assert response.json == {"error": "Authentication required."}


def test_login_seeds_plaintext_users_file_and_does_not_return_it(app, tmp_path):
    client = app.test_client()

    response = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin"},
    )

    assert response.status_code == 200
    assert response.json == {"success": True}
    assert (tmp_path / "users.json").read_text(encoding="utf-8") == (
        '{\n'
        '  "users": [\n'
        '    {\n'
        '      "username": "admin",\n'
        '      "password": "admin"\n'
        '    },\n'
        '    {\n'
        '      "username": "quest",\n'
        '      "password": "guest"\n'
        '    }\n'
        '  ]\n'
        '}\n'
    )
    assert b'"password"' not in response.data


def test_login_rejects_invalid_credentials(app):
    response = app.test_client().post(
        "/api/login",
        json={"username": "admin", "password": "incorrect"},
    )

    assert response.status_code == 401
    assert response.json == {"error": "Incorrect username or password."}


def test_logout_clears_session(client):
    response = client.post("/api/logout")

    assert response.status_code == 200
    assert client.get("/api/saved-playlists").status_code == 401


def test_removing_user_from_json_revokes_existing_session(client, tmp_path):
    (tmp_path / "users.json").write_text(
        '{"users":[{"username":"quest","password":"guest"}]}',
        encoding="utf-8",
    )

    response = client.get("/api/saved-playlists")

    assert response.status_code == 401


def test_site_icon_is_served_as_png():
    response = create_app().test_client().get("/static/bragi.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_playlist_rejects_invalid_url(client):
    response = client.post("/api/playlist", json={"url": "https://example.com"})

    assert response.status_code == 400
    assert response.json == {"error": "Enter a valid HTTPS YouTube URL."}


def test_playlist_returns_ordered_video_tracks(client):
    playlist_info = {
        "title": "My playlist",
        "entries": [
            {
                "id": "first",
                "title": "First song",
                "thumbnails": [
                    {
                        "url": "https://i.ytimg.com/vi/first/hqdefault.jpg",
                        "width": 336,
                        "height": 188,
                    },
                    {
                        "url": "https://i.ytimg.com/vi/first/mqdefault.jpg",
                        "width": 196,
                        "height": 110,
                    },
                ],
            },
            {"id": "second", "title": "Second song"},
        ],
    }

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = playlist_info
        response = client.post(
            "/api/playlist",
            json={"url": "https://www.youtube.com/playlist?list=example"},
        )

    assert response.status_code == 200
    assert response.json == {
        "title": "My playlist",
        "tracks": [
            {
                "id": "first",
                "title": "First song",
                "url": "https://www.youtube.com/watch?v=first",
                "thumbnail_url": "https://i.ytimg.com/vi/first/hqdefault.jpg",
            },
            {
                "id": "second",
                "title": "Second song",
                "url": "https://www.youtube.com/watch?v=second",
                "thumbnail_url": None,
            },
        ],
    }


def test_playlist_ignores_thumbnail_urls_outside_youtube_image_hosts(client):
    playlist_info = {
        "title": "My playlist",
        "entries": [
            {
                "id": "first",
                "title": "First song",
                "thumbnails": [
                    {
                        "url": "https://example.com/image.jpg",
                        "width": 640,
                        "height": 360,
                    }
                ],
            }
        ],
    }

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = playlist_info
        response = client.post(
            "/api/playlist",
            json={"url": "https://www.youtube.com/playlist?list=example"},
        )

    assert response.status_code == 200
    assert response.json["tracks"][0]["thumbnail_url"] is None


def test_playlist_skips_unavailable_entries(client):
    playlist_info = {
        "title": "Partially available",
        "entries": [None, {"id": "available", "title": "Available song"}],
    }

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = playlist_info
        response = client.post(
            "/api/playlist",
            json={"url": "https://www.youtube.com/playlist?list=example"},
        )

    assert response.status_code == 200
    assert [track["id"] for track in response.json["tracks"]] == ["available"]


def test_playlist_returns_error_when_no_tracks_are_available(client):

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
            "title": "Empty",
            "entries": [None],
        }
        response = client.post(
            "/api/playlist",
            json={"url": "https://www.youtube.com/playlist?list=example"},
        )

    assert response.status_code == 422
    assert response.json == {
        "error": "No playable videos were found in that playlist."
    }


def test_resolve_rejects_invalid_url(client):
    response = client.post("/api/resolve", json={"url": "https://example.com"})

    assert response.status_code == 400
    assert response.json == {"error": "Enter a valid HTTPS YouTube video URL."}


def test_resolve_returns_audio_stream(client):
    video_info = {"title": "Example", "url": "https://audio.example/stream"}

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = video_info
        response = client.post(
            "/api/resolve",
            json={"url": "https://www.youtube.com/watch?v=example"},
        )

    assert response.status_code == 200
    assert response.json == {
        "title": "Example",
        "audio_url": "https://audio.example/stream",
        "content_type": "audio/mpeg",
    }


def test_resolve_returns_audio_content_type_from_extension(client):
    video_info = {
        "title": "Example",
        "url": "https://audio.example/stream",
        "ext": "webm",
    }

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = video_info
        response = client.post(
            "/api/resolve",
            json={"url": "https://www.youtube.com/watch?v=example"},
        )

    assert response.status_code == 200
    assert response.json["content_type"] == "audio/webm"


def test_saved_playlists_persist_and_update_duplicate_urls(tmp_path, app, client):
    library_path = tmp_path / "user_playlists.json"
    app.config["PLAYLIST_LIBRARY_PATH"] = library_path

    first_response = client.post(
        "/api/saved-playlists",
        json={
            "title": "Old title",
            "url": "https://www.youtube.com/playlist?list=example",
        },
    )
    update_response = client.post(
        "/api/saved-playlists",
        json={
            "title": "Updated title",
            "url": "https://www.youtube.com/playlist?list=example",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json["updated"] is False
    assert update_response.status_code == 200
    assert update_response.json["updated"] is True

    restarted_app = create_app()
    restarted_app.config["PLAYLIST_LIBRARY_PATH"] = library_path
    restarted_app.config["USER_FILE_PATH"] = tmp_path / "users.json"
    restarted_client = restarted_app.test_client()
    restarted_client.post(
        "/api/login",
        json={"username": "admin", "password": "admin"},
    )
    listed = restarted_client.get("/api/saved-playlists")

    assert listed.status_code == 200
    assert listed.json == {
        "playlists": [
            {
                "title": "Updated title",
                "url": "https://www.youtube.com/playlist?list=example",
            }
        ]
    }
    assert library_path.exists()
    assert '"admin"' in library_path.read_text(encoding="utf-8")


def test_saved_playlist_stores_only_playlist_reference(tmp_path, app, client):
    library_path = tmp_path / "user_playlists.json"
    app.config["PLAYLIST_LIBRARY_PATH"] = library_path
    response = client.post(
        "/api/saved-playlists",
        json={
            "title": "Example",
            "url": "https://www.youtube.com/watch?v=video-secret-id&list=playlist-id&index=3",
            "tracks": [{"id": "video-secret-id", "title": "Song title"}],
        },
    )

    assert response.status_code == 200
    assert response.json["playlist"] == {
        "title": "Example",
        "url": "https://www.youtube.com/playlist?list=playlist-id",
    }
    stored_text = library_path.read_text(encoding="utf-8")
    assert "video-secret-id" not in stored_text
    assert "Song title" not in stored_text
    assert "tracks" not in stored_text
    assert "track_order" not in stored_text
    assert json.loads(stored_text) == {
        "admin": [
            {
                "title": "Example",
                "url": "https://www.youtube.com/playlist?list=playlist-id",
            }
        ]
    }


def test_saved_playlist_rejects_single_video_url(client):
    response = client.post(
        "/api/saved-playlists",
        json={
            "title": "Single video",
            "url": "https://www.youtube.com/watch?v=video-secret-id",
        },
    )

    assert response.status_code == 400


def test_saved_playlists_are_isolated_between_users(app, client):
    playlist_url = "https://www.youtube.com/playlist?list=admin-list"
    saved = client.post(
        "/api/saved-playlists",
        json={"title": "Admin playlist", "url": playlist_url},
    )
    assert saved.status_code == 200

    guest_client = app.test_client()
    login = guest_client.post(
        "/api/login",
        json={"username": "quest", "password": "guest"},
    )
    assert login.status_code == 200
    assert guest_client.get("/api/saved-playlists").json == {"playlists": []}

    guest_client.post(
        "/api/saved-playlists",
        json={
            "title": "Guest playlist",
            "url": "https://www.youtube.com/playlist?list=guest-list",
        },
    )
    assert guest_client.get("/api/saved-playlists").json == {
        "playlists": [
            {
                "title": "Guest playlist",
                "url": "https://www.youtube.com/playlist?list=guest-list",
            }
        ]
    }
    assert client.get("/api/saved-playlists").json == {
        "playlists": [
            {"title": "Admin playlist", "url": playlist_url}
        ]
    }

    denied_removal = guest_client.delete(
        "/api/saved-playlists",
        json={"url": playlist_url},
    )
    assert denied_removal.status_code == 404
    denied_update = guest_client.put(
        "/api/saved-playlists",
        json={"url": playlist_url, "title": "Guest rename"},
    )
    assert denied_update.status_code == 404


def test_existing_shared_playlist_file_is_untouched_and_not_migrated(
    tmp_path, app, client
):
    shared_library_path = tmp_path / "playlists.json"
    original_contents = (
        '[{"title":"Existing shared playlist",'
        '"url":"https://www.youtube.com/playlist?list=legacy"}]'
    )
    shared_library_path.write_text(original_contents, encoding="utf-8")

    response = client.get("/api/saved-playlists")

    assert response.status_code == 200
    assert response.json == {"playlists": []}
    assert shared_library_path.read_text(encoding="utf-8") == original_contents
    assert app.config["PLAYLIST_LIBRARY_PATH"] == tmp_path / "user_playlists.json"


def test_data_directory_can_be_configured_with_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIFY_DATA_DIR", str(tmp_path))

    app = create_app()

    assert app.config["PLAYLIST_LIBRARY_PATH"] == tmp_path / "user_playlists.json"
    assert app.config["USER_FILE_PATH"] == tmp_path / "users.json"


def test_saved_playlist_can_be_removed(tmp_path, app, client):
    app.config["PLAYLIST_LIBRARY_PATH"] = tmp_path / "user_playlists.json"
    playlist_url = "https://www.youtube.com/playlist?list=example"
    client.post(
        "/api/saved-playlists",
        json={"title": "Example", "url": playlist_url},
    )

    response = client.delete("/api/saved-playlists", json={"url": playlist_url})

    assert response.status_code == 200
    assert response.json == {"playlists": []}


def test_saved_playlist_can_be_renamed_without_song_order(client, tmp_path, app):
    app.config["PLAYLIST_LIBRARY_PATH"] = tmp_path / "user_playlists.json"
    playlist_url = "https://www.youtube.com/playlist?list=example"
    saved = client.post(
        "/api/saved-playlists",
        json={"title": "Original", "url": playlist_url},
    )
    assert saved.status_code == 200
    assert client.get("/api/saved-playlists").json == {
        "playlists": [{"title": "Original", "url": playlist_url}]
    }

    renamed = client.put(
        "/api/saved-playlists",
        json={"url": playlist_url, "title": "Renamed"},
    )

    assert renamed.status_code == 200
    assert renamed.json["playlist"]["title"] == "Renamed"
    assert client.get("/api/saved-playlists").json == {
        "playlists": [{"title": "Renamed", "url": playlist_url}]
    }
    assert "track_order" not in app.config["PLAYLIST_LIBRARY_PATH"].read_text(
        encoding="utf-8"
    )


def test_saved_playlist_update_validates_title_and_rejects_track_order(client):
    playlist_url = "https://www.youtube.com/playlist?list=example"
    client.post(
        "/api/saved-playlists",
        json={"title": "Original", "url": playlist_url},
    )

    invalid_title = client.put(
        "/api/saved-playlists",
        json={"url": playlist_url, "title": "  "},
    )
    unsupported_track_order = client.put(
        "/api/saved-playlists",
        json={"url": playlist_url, "track_order": ["video_2", "video_1"]},
    )
    missing_playlist = client.put(
        "/api/saved-playlists",
        json={
            "url": "https://www.youtube.com/playlist?list=missing",
            "title": "Missing",
        },
    )

    assert invalid_title.status_code == 400
    assert unsupported_track_order.status_code == 400
    assert missing_playlist.status_code == 404


def test_saved_playlists_can_be_reordered(client):
    urls = [
        f"https://www.youtube.com/playlist?list={playlist_id}"
        for playlist_id in ("first", "second", "third")
    ]
    for title, url in zip(("First", "Second", "Third"), urls):
        response = client.post(
            "/api/saved-playlists",
            json={"title": title, "url": url},
        )
        assert response.status_code == 200

    response = client.put(
        "/api/saved-playlists",
        json={
            "url": urls[2],
            "playlist_order": [urls[2], urls[0], urls[1]],
        },
    )

    assert response.status_code == 200
    assert [playlist["url"] for playlist in response.json["playlists"]] == [
        urls[2],
        urls[0],
        urls[1],
    ]
    assert [
        playlist["title"]
        for playlist in client.get("/api/saved-playlists").json["playlists"]
    ] == ["Third", "First", "Second"]


def test_saved_playlist_order_rejects_duplicates_and_unknown_urls(client):
    urls = [
        f"https://www.youtube.com/playlist?list={playlist_id}"
        for playlist_id in ("first", "second")
    ]
    for title, url in zip(("First", "Second"), urls):
        client.post("/api/saved-playlists", json={"title": title, "url": url})

    duplicate = client.put(
        "/api/saved-playlists",
        json={"url": urls[0], "playlist_order": [urls[0], urls[0]]},
    )
    unknown = client.put(
        "/api/saved-playlists",
        json={
            "url": urls[0],
            "playlist_order": ["https://www.youtube.com/playlist?list=unknown"],
        },
    )

    assert duplicate.status_code == 400
    assert unknown.status_code == 404


def test_saved_playlist_rejects_invalid_url(tmp_path, app, client):
    app.config["PLAYLIST_LIBRARY_PATH"] = tmp_path / "user_playlists.json"

    response = client.post(
        "/api/saved-playlists",
        json={"title": "Not YouTube", "url": "https://example.com"},
    )

    assert response.status_code == 400


def test_corrupt_saved_playlist_file_returns_error(tmp_path, app, client):
    library_path = tmp_path / "user_playlists.json"
    library_path.write_text("{invalid json", encoding="utf-8")
    app.config["PLAYLIST_LIBRARY_PATH"] = library_path

    response = client.get("/api/saved-playlists")

    assert response.status_code == 500
    assert response.json == {"error": "Could not load saved playlists."}
