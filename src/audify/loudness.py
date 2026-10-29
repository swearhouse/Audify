import math

from yt_dlp.extractor.youtube import YoutubeIE
from yt_dlp.utils import traverse_obj


def read_loudness_db(player_responses: object) -> float | None:
    """Return YouTube's loudnessDb from the first player response that has it."""
    values = traverse_obj(
        player_responses, (..., "playerConfig", "audioConfig", "loudnessDb")
    )
    for value in values or []:
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        ):
            return float(value)
    return None


class LoudnessYoutubeIE(YoutubeIE):
    """YouTube extractor that also exposes YouTube's loudnessDb as ``loudness_db``."""

    @classmethod
    def ie_key(cls) -> str:
        return YoutubeIE.ie_key()

    def _extract_player_responses(self, clients, video_id, *args, **kwargs):
        result = super()._extract_player_responses(clients, video_id, *args, **kwargs)
        loudness = read_loudness_db(result[0])
        if loudness is not None:
            self._loudness_by_video_id = {
                **getattr(self, "_loudness_by_video_id", {}),
                video_id: loudness,
            }
        return result

    def _real_extract(self, url):
        info = super()._real_extract(url)
        if isinstance(info, dict):
            loudness = getattr(self, "_loudness_by_video_id", {}).pop(
                info.get("id"), None
            )
            if loudness is not None:
                info["loudness_db"] = loudness
        return info


def gain_db_from_loudness(loudness_db: object) -> float | None:
    """Attenuation (<= 0 dB) that brings a track to YouTube's reference level.

    Like YouTube's own player, quiet tracks are not boosted.
    """
    if (
        not isinstance(loudness_db, (int, float))
        or isinstance(loudness_db, bool)
        or not math.isfinite(loudness_db)
    ):
        return None
    return round(min(0.0, -float(loudness_db)), 2)
