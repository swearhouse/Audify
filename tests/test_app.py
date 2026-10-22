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
    assert b'id="add-song-button"' in response.data
    assert b">Add Song</button>" in response.data
    assert b'id="youtube-search-button"' in response.data
    assert b">Search YouTube</button>" in response.data
    assert b'id="youtube-search-section"' in response.data
    assert b'id="youtube-search-form"' in response.data
    assert b'id="youtube-search-query"' in response.data
    assert b'id="youtube-search-results"' in response.data
    assert b".youtube-search-thumbnail" not in response.data
    assert b'createElement("img")' not in response.data.split(
        b"function renderYoutubeSearchResults(results)", 1
    )[1].split(b"async function searchYoutube", 1)[0]
    assert b'id="youtube-search-section" class="queue-card"' in response.data
    assert b'fetch("/api/youtube/search"' in response.data
    assert b'ytsearch30:' not in response.data
    assert b"function showYoutubeSearch(showSearch)" in response.data
    assert b"function loadPlaylist(playlist) {\n        showYoutubeSearch(false);" in response.data
    assert b"function renderYoutubeSearchResults(results)" in response.data
    search_renderer = response.data.split(
        b"function renderYoutubeSearchResults(results)", 1
    )[1].split(b"async function searchYoutube", 1)[0]
    assert b'createElement("span")' in search_renderer
    assert b'createElement("a")' not in search_renderer
    assert b"title.href = result.link;" not in search_renderer
    assert b'addButton.textContent = "Add to playlist";' in response.data
    assert b".youtube-search-result-title" in response.data
    assert b"text-overflow: ellipsis;" in response.data
    assert b"width: 100px;" in response.data
    assert b"justify-self: end;" in response.data
    assert b"min-height: 28px;" in response.data
    assert b"padding: 0.2rem 0.4rem;" in response.data
    assert b"font-size: 11px;" in response.data
    assert b"item.addEventListener(\"click\", (event) => {" in response.data
    assert b"if (event.target.closest(\"button\")) {" in response.data
    assert b"selectTrack(0);" in response.data
    assert b"event.stopPropagation();" in response.data
    assert b"openAddSongDialog({ name: result.name, link: result.link });" in response.data
    assert b"videoAddUrl.required = !song;" in response.data
    assert b'id="playlist-editor-form"' in response.data
    assert b'id="delete-playlist-button"' in response.data
    assert b'id="import-playlist-button"' in response.data
    assert response.data.count(
        b'class="icon-button dialog-close-button" type="button" data-close-dialog'
    ) == 3
    assert response.data.count(b'aria-label="Close" title="Close"') == 3
    assert b'button.closest("dialog").close()' in response.data
    editor_dialog = response.data.split(b'<dialog id="playlist-editor"', 1)[1].split(
        b"</dialog>", 1
    )[0]
    assert b'<button id="delete-playlist-button" type="button" hidden>' in editor_dialog
    assert b'id="import-playlist-button"' in editor_dialog
    assert b'id="playlist-video-search"' in editor_dialog
    assert b'aria-label="Search videos in this playlist"' in editor_dialog
    assert b".playlist-video-row[hidden] {\n        display: none;" in response.data
    assert b'id="add-video-button"' not in editor_dialog
    assert response.data.index(b'id="add-song-button"') < response.data.index(
        b'id="add-playlist-button"'
    )
    assert b"deletePlaylistButton.hidden = !playlist;" in response.data
    assert b"deleteButton.addEventListener" not in response.data
    assert b'<button id="import-playlist-button"' not in response.data.split(
        b'<dialog id="playlist-editor"', 1
    )[0]
    assert b"Import YouTube playlist" in response.data
    assert b'id="video-add-dialog"' in response.data
    assert b'id="video-add-form"' in response.data
    assert b'<h2 id="video-add-heading">Add Song</h2>' in response.data
    assert b'id="song-playlist-choices"' in response.data
    assert b'id="song-playlist-options"' in response.data
    assert b'checkbox.name = "playlist";' in response.data
    assert b'fetch("/api/videos/title"' in response.data
    assert b'fetch("/api/playlists/add-song"' in response.data
    assert (
        b'throw new Error(result.error || "Could not add the song to those playlists.");'
        in response.data
    )
    assert b'const videoLink = document.createElement("a");' in response.data
    assert b"videoLink.href = video.link;" in response.data
    assert b"videoLink.textContent = video.name;" in response.data
    assert b"row.dataset.videoName = video.name;" in response.data
    assert b"row.dataset.videoLink = video.link;" in response.data
    assert b"filterPlaylistVideoRows();" in response.data
    assert (
        b"row.hidden = !row.dataset.videoName.toLocaleLowerCase().includes(query);"
        in response.data
    )
    assert b'playlistVideoFields.querySelectorAll(".playlist-video-row")' in response.data
    assert b"row.dataset.videoName, link: row.dataset.videoLink" in response.data
    assert b'playlistVideoSearch.addEventListener("input", filterPlaylistVideoRows);' in response.data
    assert b"async function persistPlaylist(closeEditor)" in response.data
    assert b"async function addSongToSelectedPlaylists(event)" in response.data
    assert b"Select at least one playlist." in response.data
    assert b'fetch("/api/playlists/import"' in response.data
    assert b'fetch("/api/playlists")' in response.data
    assert b"video.name" in response.data
    assert b"video.link" in response.data
    assert b'fetch("/api/playlist"' not in response.data
    assert b'fetch("/api/saved-playlists"' not in response.data
    assert b'fetch("/api/playlists"' in response.data
    assert b'id="tracks"' in response.data
    assert b'id="play-pause-button"' in response.data
    assert b'id="cast-button"' in response.data
    assert b'id="shuffle-button"' in response.data
    assert b'aria-label="Shuffle"' in response.data
    assert b'title="Shuffle"' in response.data
    assert b'aria-hidden="true">shuffle</span></button>' in response.data
    assert b"function shuffleTracks()" in response.data
    assert b"shuffleButton.addEventListener(\"click\", shuffleTracks);" in response.data
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
        ("post", "/api/youtube/search"),
        ("post", "/api/playlists"),
        ("post", "/api/playlists/import"),
        ("post", "/api/playlists/add-song"),
        ("post", "/api/videos/title"),
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


def test_old_playlist_format_does_not_block_new_playlist_operations(
    client, app, tmp_path
):
    library_path = tmp_path / "user_playlists.json"
    library_path.write_text(
        '{"admin":[{"title":"Old playlist","url":"https://youtube.com/playlist?list=id"}]}',
        encoding="utf-8",
    )
    app.config["PLAYLIST_LIBRARY_PATH"] = library_path

    response = client.get("/api/playlists")
    assert response.status_code == 200
    assert response.json == {"playlists": []}

    created = client.post(
        "/api/playlists",
        json={"name": "New playlist", "videos": []},
    )
    assert created.status_code == 201
    assert json.loads(library_path.read_text(encoding="utf-8")) == {
        "admin": [created.json["playlist"]]
    }


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


def test_song_can_be_added_to_multiple_playlists(client, app):
    first = client.post(
        "/api/playlists",
        json={
            "name": "First mix",
            "videos": [{"name": "Existing song", "link": "https://youtu.be/existing"}],
        },
    ).json["playlist"]
    second = client.post(
        "/api/playlists",
        json={"name": "Second mix", "videos": []},
    ).json["playlist"]
    new_song = {"name": "New song", "link": "https://youtu.be/new-song"}

    response = client.post(
        "/api/playlists/add-song",
        json={
            "playlist_ids": [first["id"], second["id"]],
            "video": new_song,
        },
    )

    assert response.status_code == 200
    assert response.json["playlists"] == [
        {
            **first,
            "videos": [first["videos"][0], new_song],
        },
        {
            **second,
            "videos": [new_song],
        },
    ]
    stored = json.loads(
        app.config["PLAYLIST_LIBRARY_PATH"].read_text(encoding="utf-8")
    )["admin"]
    assert stored[0]["videos"] == [first["videos"][0], new_song]
    assert stored[1]["videos"] == [new_song]


def test_song_add_rejects_duplicate_video_across_selected_playlists_atomically(
    client,
    app,
):
    first = client.post(
        "/api/playlists",
        json={
            "name": "First mix",
            "videos": [{"name": "Existing song", "link": "https://youtu.be/song-id"}],
        },
    ).json["playlist"]
    second = client.post(
        "/api/playlists",
        json={"name": "Second mix", "videos": []},
    ).json["playlist"]

    response = client.post(
        "/api/playlists/add-song",
        json={
            "playlist_ids": [first["id"], second["id"]],
            "video": {
                "name": "Existing song",
                "link": "https://www.youtube.com/watch?v=song-id",
            },
        },
    )

    assert response.status_code == 409
    assert response.json == {
        "error": "This song is already in: First mix.",
        "duplicate_playlists": ["First mix"],
    }
    assert client.get("/api/playlists").json["playlists"] == [first, second]
    stored = json.loads(
        app.config["PLAYLIST_LIBRARY_PATH"].read_text(encoding="utf-8")
    )["admin"]
    assert stored == [first, second]


def test_add_song_to_playlists_rejects_invalid_or_unowned_playlist_ids(app, client):
    created = client.post(
        "/api/playlists",
        json={"name": "Private", "videos": []},
    ).json["playlist"]
    guest_client = app.test_client()
    guest_client.post("/api/login", json={"username": "quest", "password": "guest"})

    response = guest_client.post(
        "/api/playlists/add-song",
        json={
            "playlist_ids": [created["id"]],
            "video": {"name": "Song", "link": "https://youtu.be/song"},
        },
    )

    assert response.status_code == 404
    assert response.json == {"error": "One or more playlists were not found."}
    assert client.post(
        "/api/playlists/add-song",
        json={
            "playlist_ids": [created["id"], "missing"],
            "video": {"name": "Song", "link": "https://youtu.be/song"},
        },
    ).status_code == 404
    assert client.get("/api/playlists").json["playlists"] == [created]


def test_youtube_search_returns_up_to_thirty_results(client):
    entries = [
        {
            "id": f"video-{index}",
            "title": f"Song {index}",
            "duration": 90 + index,
            "thumbnail": f"https://i.ytimg.com/vi/video-{index}/mqdefault.jpg",
        }
        for index in range(32)
    ]
    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": entries
        }

        response = client.post("/api/youtube/search", json={"query": "jazz"})

    assert response.status_code == 200
    assert len(response.json["results"]) == 30
    assert response.json["results"][0] == {
        "name": "Song 0",
        "link": "https://www.youtube.com/watch?v=video-0",
        "duration": 90,
    }
    options = youtube_dl.call_args.args[0]
    assert options["extract_flat"] is True
    youtube_dl.return_value.__enter__.return_value.extract_info.assert_called_once_with(
        "ytsearch30:jazz",
        download=False,
    )


@pytest.mark.parametrize("query", ["", "  ", "x" * 201])
def test_youtube_search_rejects_invalid_queries(client, query):
    with patch("audify.app.YoutubeDL") as youtube_dl:
        response = client.post("/api/youtube/search", json={"query": query})

    assert response.status_code == 400
    youtube_dl.assert_not_called()


def test_youtube_search_reports_youtube_errors(client):
    from yt_dlp.utils import DownloadError

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.side_effect = (
            DownloadError("search failed")
        )

        response = client.post("/api/youtube/search", json={"query": "jazz"})

    assert response.status_code == 422
    assert response.json == {"error": "Could not search YouTube right now."}


def test_video_title_endpoint_returns_youtube_title_and_canonical_link(client):
    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
            "id": "video-id",
            "title": "  Video title  ",
        }
        response = client.post(
            "/api/videos/title",
            json={"url": "https://youtu.be/video-id"},
        )

    assert response.status_code == 200
    assert response.json == {
        "video": {
            "name": "Video title",
            "link": "https://www.youtube.com/watch?v=video-id",
        }
    }
    youtube_dl.assert_called_once()


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/video",
        "https://www.youtube.com/playlist?list=playlist-id",
        "http://www.youtube.com/watch?v=video-id",
    ],
)
def test_video_title_endpoint_rejects_invalid_links(client, url):
    with patch("audify.app.YoutubeDL") as youtube_dl:
        response = client.post("/api/videos/title", json={"url": url})

    assert response.status_code == 400
    assert response.json == {"error": "Enter a valid HTTPS YouTube video URL."}
    youtube_dl.assert_not_called()


def test_video_title_endpoint_handles_unavailable_video(client):
    from yt_dlp.utils import DownloadError

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.side_effect = (
            DownloadError("video unavailable")
        )
        response = client.post(
            "/api/videos/title",
            json={"url": "https://www.youtube.com/watch?v=video-id"},
        )

    assert response.status_code == 422
    assert response.json == {
        "error": "Could not get the title for that YouTube video."
    }


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


def test_import_playlist_saves_youtube_videos_for_current_user(client, app, tmp_path):
    app.config["PLAYLIST_LIBRARY_PATH"] = tmp_path / "user_playlists.json"
    playlist_info = {
        "title": "Imported mix",
        "entries": [
            {"id": "first", "title": "First song"},
            None,
            {"id": "second", "title": "Second song"},
            {"title": "Unavailable video"},
        ],
    }

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = playlist_info
        response = client.post(
            "/api/playlists/import",
            json={"url": "https://www.youtube.com/playlist?list=example"},
        )

    assert response.status_code == 201
    assert response.json["playlist"]["name"] == "Imported mix"
    assert response.json["playlist"]["videos"] == [
        {
            "name": "First song",
            "link": "https://www.youtube.com/watch?v=first",
        },
        {
            "name": "Second song",
            "link": "https://www.youtube.com/watch?v=second",
        },
    ]
    assert json.loads(
        app.config["PLAYLIST_LIBRARY_PATH"].read_text(encoding="utf-8")
    ) == {"admin": [response.json["playlist"]]}
    options = youtube_dl.call_args.args[0]
    assert options["extract_flat"] == "in_playlist"
    assert options["ignoreerrors"] is True


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/playlist?list=example",
        "http://www.youtube.com/playlist?list=example",
        "https://www.youtube.com/playlist",
        "https://youtu.be/video",
        "https://www.youtube.com/channel/example?list=example",
    ],
)
def test_import_playlist_rejects_invalid_playlist_urls(client, url):
    with patch("audify.app.YoutubeDL") as youtube_dl:
        response = client.post("/api/playlists/import", json={"url": url})

    assert response.status_code == 400
    assert response.json == {"error": "Enter a valid HTTPS YouTube playlist URL."}
    youtube_dl.assert_not_called()


def test_import_playlist_returns_error_when_youtube_extraction_fails(client):
    from yt_dlp.utils import DownloadError

    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.side_effect = (
            DownloadError("playlist unavailable")
        )
        response = client.post(
            "/api/playlists/import",
            json={"url": "https://www.youtube.com/playlist?list=example"},
        )

    assert response.status_code == 422
    assert response.json == {"error": "Could not import that YouTube playlist."}


def test_import_playlist_returns_error_when_no_videos_are_available(client):
    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
            "title": "Empty playlist",
            "entries": [None, {"title": "Unavailable"}],
        }
        response = client.post(
            "/api/playlists/import",
            json={"url": "https://www.youtube.com/playlist?list=example"},
        )

    assert response.status_code == 422
    assert response.json == {
        "error": "No videos were found in that YouTube playlist."
    }


def test_import_playlist_rejects_oversized_playlist_without_truncating(client):
    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
            "title": "Very large playlist",
            "entries": [
                {"id": str(index), "title": f"Song {index}"}
                for index in range(5001)
            ],
        }
        response = client.post(
            "/api/playlists/import",
            json={"url": "https://www.youtube.com/playlist?list=example"},
        )

    assert response.status_code == 422
    assert response.json == {
        "error": "That YouTube playlist has more than 5,000 videos and cannot be imported."
    }


def test_imported_playlists_are_private_to_the_user(app, client, tmp_path):
    app.config["PLAYLIST_LIBRARY_PATH"] = tmp_path / "user_playlists.json"
    with patch("audify.app.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
            "title": "Admin import",
            "entries": [{"id": "video", "title": "Song"}],
        }
        response = client.post(
            "/api/playlists/import",
            json={"url": "https://www.youtube.com/playlist?list=admin"},
        )
    assert response.status_code == 201

    guest = app.test_client()
    guest.post("/api/login", json={"username": "quest", "password": "guest"})
    assert guest.get("/api/playlists").json == {"playlists": []}


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
