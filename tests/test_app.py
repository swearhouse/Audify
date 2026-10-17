from unittest.mock import patch

from audify.app import create_app, is_youtube_url


def test_accepts_youtube_video_urls():
    assert is_youtube_url("https://www.youtube.com/watch?v=example")
    assert is_youtube_url("https://youtu.be/example")


def test_rejects_non_youtube_urls_and_non_https():
    assert not is_youtube_url("http://www.youtube.com/watch?v=example")
    assert not is_youtube_url("https://example.com/video")
    assert not is_youtube_url("https://youtube.com.example.com/watch?v=example")


def test_homepage_renders_player():
    response = create_app().test_client().get("/")

    assert response.status_code == 200
    assert b"<title>Bragi</title>" in response.data
    assert '<span class="brand-mark" aria-hidden="true">ᛉ</span>Bragi'.encode() in response.data
    assert b"@property --ambient-color" in response.data
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
    assert b"align-items: start;" in response.data
    assert b".saved-library {\n        flex: none;" in response.data
    assert b".queue-card {\n        display: flex;\n        flex: none;" in response.data
    assert b"min-height: 220px;" not in response.data
    assert b"max-height: 360px;" in response.data
    assert b"max-height: 52vh;" not in response.data
    assert response.data.index(b'class="sidebar"') < response.data.index(b'class="workspace"')
    assert response.data.index(b'id="saved-playlists"') < response.data.index(b'class="sidebar-divider"')
    assert response.data.index(b'class="sidebar-divider"') < response.data.index(b'id="url-form"')
    assert response.data.index(b'id="url-form"') < response.data.index(b'class="workspace"')
    assert b"#url {\n        width: 100%;" in response.data
    assert b'class="player-card"' in response.data
    assert b'class="queue-card"' in response.data
    assert b"@media (max-width: 640px)" in response.data
    assert b'id="current-thumbnail"' in response.data
    assert b'<audio id="player" controls></audio>' in response.data
    assert b'id="saved-playlists"' in response.data
    assert b'id="save-button"' in response.data
    assert b'id="previous-button"' in response.data
    assert b'id="next-button"' in response.data
    assert b'id="randomize-button"' in response.data
    assert b'id="tracks"' in response.data
    assert b"(${tracks.length} songs)" in response.data
    assert b"const maxAudioLoadRetries = 2;" in response.data
    assert b"advanceTrack(index + 1);" in response.data
    assert b"await playTrack(0);" not in response.data


def test_playlist_rejects_invalid_url():
    client = create_app().test_client()

    response = client.post("/api/playlist", json={"url": "https://example.com"})

    assert response.status_code == 400
    assert response.json == {"error": "Enter a valid HTTPS YouTube URL."}


def test_playlist_returns_ordered_video_tracks():
    client = create_app().test_client()
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


def test_playlist_ignores_thumbnail_urls_outside_youtube_image_hosts():
    client = create_app().test_client()
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


def test_playlist_skips_unavailable_entries():
    client = create_app().test_client()
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


def test_playlist_returns_error_when_no_tracks_are_available():
    client = create_app().test_client()

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


def test_resolve_rejects_invalid_url():
    client = create_app().test_client()

    response = client.post("/api/resolve", json={"url": "https://example.com"})

    assert response.status_code == 400
    assert response.json == {"error": "Enter a valid HTTPS YouTube video URL."}


def test_resolve_returns_audio_stream():
    client = create_app().test_client()
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
    }


def test_saved_playlists_persist_and_update_duplicate_urls(tmp_path):
    library_path = tmp_path / "playlists.json"
    app = create_app()
    app.config["PLAYLIST_LIBRARY_PATH"] = library_path
    client = app.test_client()

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
    listed = restarted_app.test_client().get("/api/saved-playlists")

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


def test_saved_playlist_can_be_removed(tmp_path):
    app = create_app()
    app.config["PLAYLIST_LIBRARY_PATH"] = tmp_path / "playlists.json"
    client = app.test_client()
    playlist_url = "https://www.youtube.com/playlist?list=example"
    client.post(
        "/api/saved-playlists",
        json={"title": "Example", "url": playlist_url},
    )

    response = client.delete("/api/saved-playlists", json={"url": playlist_url})

    assert response.status_code == 200
    assert response.json == {"playlists": []}


def test_saved_playlist_rejects_invalid_url(tmp_path):
    app = create_app()
    app.config["PLAYLIST_LIBRARY_PATH"] = tmp_path / "playlists.json"

    response = app.test_client().post(
        "/api/saved-playlists",
        json={"title": "Not YouTube", "url": "https://example.com"},
    )

    assert response.status_code == 400


def test_corrupt_saved_playlist_file_returns_error(tmp_path):
    library_path = tmp_path / "playlists.json"
    library_path.write_text("{invalid json", encoding="utf-8")
    app = create_app()
    app.config["PLAYLIST_LIBRARY_PATH"] = library_path

    response = app.test_client().get("/api/saved-playlists")

    assert response.status_code == 500
    assert response.json == {"error": "Could not load saved playlists."}
