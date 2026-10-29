import pytest

from audify.loudness import LoudnessYoutubeIE, gain_db_from_loudness, read_loudness_db
from yt_dlp.extractor.youtube import YoutubeIE


@pytest.mark.parametrize(
    ("loudness", "expected"),
    [
        (6.69, -6.69),
        (0.99, -0.99),
        (0, 0.0),
        (-3.2, 0.0),
        (None, None),
        ("6", None),
        (True, None),
        (float("nan"), None),
        (float("inf"), None),
    ],
)
def test_gain_db_from_loudness(loudness, expected):
    assert gain_db_from_loudness(loudness) == expected


def test_read_loudness_db_uses_first_response_with_a_value():
    responses = [
        {"playerConfig": {}},
        {"playerConfig": {"audioConfig": {"loudnessDb": 2.5}}},
        {"playerConfig": {"audioConfig": {"loudnessDb": 9.0}}},
    ]

    assert read_loudness_db(responses) == 2.5


@pytest.mark.parametrize(
    "responses",
    [[], [{}], [{"playerConfig": {"audioConfig": {"loudnessDb": "loud"}}}], None],
)
def test_read_loudness_db_ignores_missing_or_invalid_values(responses):
    assert read_loudness_db(responses) is None


def test_extractor_replaces_youtube_extractor_key():
    assert LoudnessYoutubeIE.ie_key() == YoutubeIE.ie_key()


def test_extractor_adds_loudness_to_info(monkeypatch):
    extractor = LoudnessYoutubeIE()
    responses = [{"playerConfig": {"audioConfig": {"loudnessDb": 4.5}}}]
    monkeypatch.setattr(
        YoutubeIE,
        "_extract_player_responses",
        lambda self, *args, **kwargs: (responses, "player-url"),
    )
    monkeypatch.setattr(
        YoutubeIE, "_real_extract", lambda self, url: {"id": "abc"}
    )

    extractor._extract_player_responses([], "abc")

    assert extractor._real_extract("https://www.youtube.com/watch?v=abc") == {
        "id": "abc",
        "loudness_db": 4.5,
    }


def test_extractor_leaves_info_unchanged_without_loudness(monkeypatch):
    extractor = LoudnessYoutubeIE()
    monkeypatch.setattr(
        YoutubeIE,
        "_extract_player_responses",
        lambda self, *args, **kwargs: ([{}], "player-url"),
    )
    monkeypatch.setattr(
        YoutubeIE, "_real_extract", lambda self, url: {"id": "abc"}
    )

    extractor._extract_player_responses([], "abc")

    assert extractor._real_extract("https://www.youtube.com/watch?v=abc") == {"id": "abc"}
