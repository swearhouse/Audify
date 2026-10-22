import json
from unittest.mock import patch

import pytest

from audify.app import create_app, is_youtube_url, is_youtube_video_url


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


def test_accepts_only_direct_youtube_video_links():
    assert is_youtube_video_url("https://www.youtube.com/watch?v=example")
    assert is_youtube_video_url("https://youtu.be/example")
    assert is_youtube_video_url("https://www.youtube.com/shorts/example")
    assert not is_youtube_video_url("https://www.youtube.com/playlist?list=example")
    assert not is_youtube_video_url("https://www.youtube.com/")


def test_homepage_renders_playlist_library_and_player(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"<title>Bragi</title>" in response.data
    assert b'<link rel="icon" type="image/png" href="/static/bragi.png">' in response.data
    assert b'<section class="saved-library" aria-label="Playlists">' in response.data
    assert b'id="playlist-list"' in response.data
    assert b'id="playlist-status" role="status" aria-live="polite"' in response.data
    assert b"Your playlists are private to your account." in response.data
    assert b'id="add-playlist-button"' in response.data
    assert b'id="playlist-editor-form"' in response.data
    assert b'fetch("/api/playlists")' in response.data
    assert b"video.name" in response.data
    assert b"video.link" in response.data
    assert b'fetch("/api/playlist"' not in response.data
    assert b'fetch("/api/saved-playlists"' not in response.data
    assert b'fetch("/api/playlists"' in response.data
    assert b'id="tracks"' in response.data
    assert b'id="play-pause-button"' in response.data
    assert b'id="cast-button"' in response.data
    assert b"function selectTrack(index)" in response.data
    assert b"function advanceTrack(index)" in response.data
    assert b"const maxAudioLoadRetries = 2;" in response.data
    assert b"remotePlayerController.seek();" in response.data


def test_homepage_requires_login(app):
    response = app.test_client().get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/playlists"),
        ("post", "/api/playlists"),
        ("put", "/api/playlists/example"),
        ("delete", "/api/playlists/example"),
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
    assert client.get("/api/playlists").status_code == 401


def test_removing_user_from_json_revokes_existing_session(client, tmp_path):
    (tmp_path / "users.json").write_text(
        '{"users":[{"username":"quest","password":"guest"}]}',
        encoding="utf-8",
    )

    response = client.get("/api/playlists")

    assert response.status_code == 401


def test_site_icon_is_served_as_png():
    response = create_app().test_client().get("/static/bragi.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_user_playlists_are_saved_in_given_order(client, app, tmp_path):
    playlists = [
        {
            "id": "evening-mix",
            "name": "Evening mix",
            "videos": [
                {
                    "name": "First song",
                    "link": "https://www.youtube.com/watch?v=video1",
                },
                {
                    "name": "Second song",
                    "link": "https://youtu.be/video2",
                },
            ],
        },
        {"id": "empty-list", "name": "Empty list", "videos": []},
    ]
    playlist_file = app.config["PLAYLIST_LIBRARY_PATH"]

    created = client.post("/api/playlists", json=playlists[0])
    assert created.status_code == 201
    second = client.post("/api/playlists", json=playlists[1])
    assert second.status_code == 201

    response = client.get("/api/playlists")
    assert response.status_code == 200
    assert response.json == {"playlists": [created.json["playlist"], second.json["playlist"]]}
    saved_document = json.loads(playlist_file.read_text(encoding="utf-8"))
    assert saved_document == {"admin": response.json["playlists"]}
    with patch("audify.app.YoutubeDL") as youtube_dl:
        client.get("/api/playlists")
    youtube_dl.assert_not_called()


def test_missing_playlist_library_returns_empty_list(client):
    response = client.get("/api/playlists")

    assert response.status_code == 200
    assert response.json == {"playlists": []}


@pytest.mark.parametrize(
    ("contents", "expected_error"),
    [
        ("{invalid json", "Could not read the playlist library."),
        ("[]", "The playlist library has an invalid format."),
    ],
)
def test_invalid_playlist_library_returns_error(
    client, app, tmp_path, contents, expected_error
):
    library_path = tmp_path / "user_playlists.json"
    library_path.write_text(contents, encoding="utf-8")
    app.config["PLAYLIST_LIBRARY_PATH"] = library_path

    response = client.get("/api/playlists")

    assert response.status_code == 500
    assert response.json == {"error": expected_error}


def test_old_playlist_format_returns_migration_error(client, app, tmp_path):
    library_path = tmp_path / "user_playlists.json"
    library_path.write_text(
        '{"admin":[{"title":"Old playlist","url":"https://youtube.com/playlist?list=id"}]}',
        encoding="utf-8",
    )
    app.config["PLAYLIST_LIBRARY_PATH"] = library_path

    response = client.get("/api/playlists")

    assert response.status_code == 500
    assert "old YouTube playlist format" in response.json["error"]
    assert "user_playlists.json" in response.json["error"]


def test_users_have_independent_playlists(app, client):
    admin_playlist = {
        "name": "Admin playlist",
        "videos": [{"name": "Admin song", "link": "https://youtu.be/admin-song"}],
    }
    created = client.post("/api/playlists", json=admin_playlist)
    assert created.status_code == 201

    guest_client = app.test_client()
    guest_client.post("/api/login", json={"username": "quest", "password": "guest"})
    assert guest_client.get("/api/playlists").json == {"playlists": []}
    guest_playlist = {
        "name": "Guest playlist",
        "videos": [{"name": "Guest song", "link": "https://youtu.be/guest-song"}],
    }
    guest_created = guest_client.post("/api/playlists", json=guest_playlist)
    assert guest_created.status_code == 201

    assert [item["id"] for item in client.get("/api/playlists").json["playlists"]] == [
        created.json["playlist"]["id"]
    ]
    assert [item["id"] for item in guest_client.get("/api/playlists").json["playlists"]] == [
        guest_created.json["playlist"]["id"]
    ]


def test_playlist_can_be_edited_and_deleted(client):
    created = client.post(
        "/api/playlists",
        json={
            "name": "Original",
            "videos": [{"name": "Song", "link": "https://www.youtube.com/watch?v=song"}],
        },
    )
    playlist_id = created.json["playlist"]["id"]

    updated = client.put(
        f"/api/playlists/{playlist_id}",
        json={
            "name": "Updated",
            "videos": [{"name": "New song", "link": "https://youtu.be/new-song"}],
        },
    )
    assert updated.status_code == 200
    assert updated.json["playlist"] == {
        "id": playlist_id,
        "name": "Updated",
        "videos": [{"name": "New song", "link": "https://youtu.be/new-song"}],
    }

    deleted = client.delete(f"/api/playlists/{playlist_id}")
    assert deleted.status_code == 200
    assert deleted.json == {"playlists": []}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "No videos"},
        {"name": "Bad video", "videos": [{"name": "Song", "link": "https://example.com"}]},
        {"name": "Blank name", "videos": [{"name": " ", "link": "https://youtu.be/video"}]},
        {"name": "", "videos": []},
    ],
)
def test_playlist_creation_rejects_invalid_data(client, payload):
    response = client.post("/api/playlists", json=payload)

    assert response.status_code == 400


def test_playlist_cannot_be_updated_or_deleted_by_another_user(app, client):
    created = client.post("/api/playlists", json={"name": "Private", "videos": []})
    playlist_id = created.json["playlist"]["id"]

    guest_client = app.test_client()
    guest_client.post("/api/login", json={"username": "quest", "password": "guest"})
    assert guest_client.put(
        f"/api/playlists/{playlist_id}",
        json={"name": "Changed", "videos": []},
    ).status_code == 404
    assert guest_client.delete(f"/api/playlists/{playlist_id}").status_code == 404


def test_resolve_rejects_invalid_url(client):
    response = client.post("/api/resolve", json={"url": "https://example.com"})

    assert response.status_code == 400
    assert response.json == {"error": "Enter a valid HTTPS YouTube video URL."}


def test_resolve_rejects_playlist_url(client):
    response = client.post(
        "/api/resolve",
        json={"url": "https://www.youtube.com/playlist?list=example"},
    )

    assert response.status_code == 400


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


def test_data_directory_can_be_configured_with_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIFY_DATA_DIR", str(tmp_path))

    app = create_app()

    assert app.config["PLAYLIST_LIBRARY_PATH"] == tmp_path / "user_playlists.json"
    assert app.config["USER_FILE_PATH"] == tmp_path / "users.json"
