const previousButton = document.querySelector("#previous-button");
const nextButton = document.querySelector("#next-button");
const shuffleButton = document.querySelector("#shuffle-button");
const trackList = document.querySelector("#tracks");
const playlistSearch = document.querySelector("#playlist-search");
const trackSearchStatus = document.querySelector("#track-search-status");
const playlistQueueSection = document.querySelector('[aria-labelledby="queue-heading"]');
const youtubeSearchButton = document.querySelector("#youtube-search-button");
const youtubeSearchSection = document.querySelector("#youtube-search-section");
const youtubeSearchForm = document.querySelector("#youtube-search-form");
const youtubeSearchQuery = document.querySelector("#youtube-search-query");
const youtubeSearchSubmit = document.querySelector("#youtube-search-submit");
const youtubeSearchStatus = document.querySelector("#youtube-search-status");
const youtubeSearchResults = document.querySelector("#youtube-search-results");
const status = document.querySelector("#status");
const playlistTitle = document.querySelector("#playlist-title");
const playlistList = document.querySelector("#playlist-list");
const addSongButton = document.querySelector("#add-song-button");
const addPlaylistButton = document.querySelector("#add-playlist-button");
const playlistEditor = document.querySelector("#playlist-editor");
const playlistEditorForm = document.querySelector("#playlist-editor-form");
const playlistEditorHeading = document.querySelector("#playlist-editor-heading");
const playlistNameInput = document.querySelector("#playlist-name");
const playlistVideoSearch = document.querySelector("#playlist-video-search");
const playlistVideoFields = document.querySelector("#playlist-video-fields");
const playlistEditorStatus = document.querySelector("#playlist-editor-status");
const cancelPlaylistButton = document.querySelector("#cancel-playlist-button");
const savePlaylistButton = document.querySelector("#save-playlist-button");
const deletePlaylistButton = document.querySelector("#delete-playlist-button");
const importPlaylistButton = document.querySelector("#import-playlist-button");
const playlistImportDialog = document.querySelector("#playlist-import-dialog");
const playlistImportForm = document.querySelector("#playlist-import-form");
const playlistImportUrl = document.querySelector("#playlist-import-url");
const submitPlaylistImport = document.querySelector("#submit-playlist-import");
const cancelPlaylistImport = document.querySelector("#cancel-playlist-import");
const videoAddDialog = document.querySelector("#video-add-dialog");
const videoAddHeading = document.querySelector("#video-add-heading");
const videoAddForm = document.querySelector("#video-add-form");
const videoAddUrl = document.querySelector("#video-add-url");
const videoAddLinkField = document.querySelector("#video-add-link-field");
const songPlaylistOptions = document.querySelector("#song-playlist-options");
const videoAddStatus = document.querySelector("#video-add-status");
const submitVideoAdd = document.querySelector("#submit-video-add");
const cancelVideoAdd = document.querySelector("#cancel-video-add");
const videoReplaceDialog = document.querySelector("#video-replace-dialog");
const videoReplaceSearchForm = document.querySelector("#video-replace-search-form");
const videoReplaceQuery = document.querySelector("#video-replace-query");
const videoReplaceSearchSubmit = document.querySelector("#video-replace-search-submit");
const videoReplaceResults = document.querySelector("#video-replace-results");
const videoReplaceLinkForm = document.querySelector("#video-replace-link-form");
const videoReplaceUrl = document.querySelector("#video-replace-url");
const videoReplaceLinkSubmit = document.querySelector("#video-replace-link-submit");
const videoReplaceStatus = document.querySelector("#video-replace-status");
let replacingRow = null;
let pendingReplacements = [];
let videoReplaceRequest = 0;
const player = document.querySelector("#player");
const castButton = document.querySelector("#cast-button");
const castIcon = castButton.querySelector(".material-symbols-outlined");
const playPauseButton = document.querySelector("#play-pause-button");
const playPauseIcon = playPauseButton.querySelector(".material-symbols-outlined");
const stopButton = document.querySelector("#stop-button");
const seekSlider = document.querySelector("#seek-slider");
const seekCurrentTime = document.querySelector("#seek-current-time");
const seekDuration = document.querySelector("#seek-duration");
const volumeSlider = document.querySelector("#volume-slider");
const volumeValue = document.querySelector("#volume-value");
const maxAudioLoadRetries = 2;
const audioLoadError = "The audio stream could not be loaded.";
const currentThumbnail = document.querySelector("#current-thumbnail");
const playerGlow = document.querySelector("#player-glow");
const logoutButton = document.querySelector("#logout-button");
const appShell = document.querySelector(".app-shell");
const sidebarToggle = document.querySelector("#sidebar-toggle");

function setSidebarHidden(hidden) {
  appShell.classList.toggle("sidebar-hidden", hidden);
  sidebarToggle.setAttribute("aria-expanded", String(!hidden));
  try {
    localStorage.setItem("sidebarHidden", String(hidden));
  } catch {}
}

sidebarToggle.addEventListener("click", () => {
  setSidebarHidden(!appShell.classList.contains("sidebar-hidden"));
});

try {
  setSidebarHidden(localStorage.getItem("sidebarHidden") === "true");
} catch {}
let tracks = [];
let currentIndex = -1;
let ambientHue = -1;
let playbackRequest = 0;
let cancelMetadataWait = null;
let currentPlaylistTitle = "";
let currentPlaylistId = null;
let playlists = [];
let selectedSearchSong = null;
let editingPlaylistId = null;
let castContext = null;
let castSession = null;
let remotePlayer = null;
let remotePlayerController = null;
let castMediaReady = false;
let castCompletionHandled = false;
let castMediaSession = null;
let castMediaUpdateListener = null;
let resolvedMedia = null;
let userVolume = player.volume;
const loudnessSettingKey = "audify.loudnessNormalization";

function loudnessNormalizationEnabled() {
  try {
    return localStorage.getItem(loudnessSettingKey) !== "off";
  } catch (error) {
    return true;
  }
}

function normalizationFactor() {
  if (castSession || !resolvedMedia || !loudnessNormalizationEnabled()) {
    return 1;
  }
  const gainDb = resolvedMedia.gainDb;
  return Number.isFinite(gainDb) && gainDb < 0 ? 10 ** (gainDb / 20) : 1;
}

function applyLocalVolume() {
  player.volume = Math.min(1, Math.max(0, userVolume * normalizationFactor()));
}

window.addEventListener("storage", (event) => {
  if (event.key === loudnessSettingKey) {
    applyLocalVolume();
  }
});
let isSeeking = false;
let youtubeSearchRequest = 0;

const visualizerSettingKey = "audify.visualizer";
const visualizerCanvas = document.querySelector("#visualizer");
const visualizerContext = visualizerCanvas.getContext("2d");
let audioContext = null;
let analyser = null;
let frequencyData = null;
let waveformData = null;
let visualizerFrame = 0;
let sourceHasCors = false;
let corsBlocked = false;
let mediaSourceNode = null;

function visualizerMode() {
  try {
    return localStorage.getItem(visualizerSettingKey) || "bars";
  } catch (error) {
    return "bars";
  }
}

// createMediaElementSource() silences cross-origin audio unless it was loaded with CORS,
// so the element only gets a CORS request when a visualizer is wanted.
function setPlayerSource(url) {
  const wantCors = !corsBlocked && (mediaSourceNode !== null || visualizerMode() !== "off");
  if (wantCors) {
    player.crossOrigin = "anonymous";
  } else {
    player.removeAttribute("crossorigin");
  }
  sourceHasCors = wantCors;
  player.src = wantCors
    ? `/api/audio-proxy?url=${encodeURIComponent(url)}`
    : url;
}

player.addEventListener("error", () => {
  if (sourceHasCors && mediaSourceNode === null) {
    corsBlocked = true;
  }
});

function connectAnalyser() {
  if (analyser || !sourceHasCors || visualizerMode() === "off") {
    return Boolean(analyser);
  }
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    return false;
  }
  audioContext = new AudioContextClass();
  mediaSourceNode = audioContext.createMediaElementSource(player);
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 2048;
  analyser.smoothingTimeConstant = 0.8;
  mediaSourceNode.connect(analyser);
  analyser.connect(audioContext.destination);
  frequencyData = new Uint8Array(analyser.frequencyBinCount);
  waveformData = new Uint8Array(analyser.fftSize);
  return true;
}

function resizeVisualizer() {
  const ratio = window.devicePixelRatio || 1;
  const width = Math.round(visualizerCanvas.clientWidth * ratio);
  const height = Math.round(visualizerCanvas.clientHeight * ratio);
  if (visualizerCanvas.width !== width || visualizerCanvas.height !== height) {
    visualizerCanvas.width = width;
    visualizerCanvas.height = height;
  }
}

function clearVisualizer() {
  visualizerContext.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);
}

// Averages the lower ~75% of the spectrum into `count` log-spaced bands (0..1).
function spectrumBands(count) {
  const bands = new Array(count);
  const usable = Math.floor(frequencyData.length * 0.75);
  let start = 1;
  for (let i = 0; i < count; i += 1) {
    const end = Math.max(start + 1, Math.round(usable ** ((i + 1) / count)));
    let sum = 0;
    for (let bin = start; bin < end; bin += 1) {
      sum += frequencyData[bin];
    }
    bands[i] = sum / (end - start) / 255;
    start = end;
  }
  return bands;
}

const visualizers = {
  bars(ctx, w, h) {
    const count = 64;
    const bands = spectrumBands(count);
    const slot = w / count;
    for (let i = 0; i < count; i += 1) {
      const barHeight = Math.max(2, bands[i] * h * 0.85);
      ctx.fillRect(i * slot + slot * 0.15, h - barHeight, slot * 0.7, barHeight);
    }
  },
  mirror(ctx, w, h) {
    const count = 48;
    const bands = spectrumBands(count);
    const slot = w / (count * 2);
    for (let i = 0; i < count; i += 1) {
      const barHeight = Math.max(2, bands[i] * h * 0.8);
      const y = (h - barHeight) / 2;
      ctx.fillRect(w / 2 + i * slot + slot * 0.15, y, slot * 0.7, barHeight);
      ctx.fillRect(w / 2 - (i + 1) * slot + slot * 0.15, y, slot * 0.7, barHeight);
    }
  },
  wave(ctx, w, h) {
    analyser.getByteTimeDomainData(waveformData);
    ctx.lineWidth = Math.max(2, h / 90);
    ctx.lineJoin = "round";
    ctx.beginPath();
    const step = Math.max(1, Math.floor(waveformData.length / 512));
    for (let i = 0; i < waveformData.length; i += step) {
      const x = (i / (waveformData.length - 1)) * w;
      const y = (waveformData[i] / 255) * h * 0.8 + h * 0.1;
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
  },
  radial(ctx, w, h) {
    const count = 96;
    const bands = spectrumBands(count / 2);
    const cx = w / 2;
    const cy = h / 2;
    const base = Math.min(w, h) * 0.22;
    const reach = Math.min(w, h) * 0.3;
    ctx.lineWidth = Math.max(2, Math.min(w, h) / 120);
    ctx.lineCap = "round";
    ctx.beginPath();
    for (let i = 0; i < count; i += 1) {
      const mirrored = i < count / 2 ? i : count - 1 - i;
      const angle = (i / count) * Math.PI * 2 - Math.PI / 2;
      const length = base + bands[mirrored] * reach;
      ctx.moveTo(cx + Math.cos(angle) * base, cy + Math.sin(angle) * base);
      ctx.lineTo(cx + Math.cos(angle) * length, cy + Math.sin(angle) * length);
    }
    ctx.stroke();
  },
  area(ctx, w, h) {
    const count = 48;
    const bands = spectrumBands(count);
    ctx.beginPath();
    ctx.moveTo(0, h);
    for (let i = 0; i < count; i += 1) {
      const x = (i / (count - 1)) * w;
      const y = h - bands[i] * h * 0.85;
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fill();
  },
};

function drawVisualizer() {
  visualizerFrame = 0;
  const draw = visualizers[visualizerMode()];
  if (!draw || !analyser || player.paused) {
    clearVisualizer();
    return;
  }
  resizeVisualizer();
  analyser.getByteFrequencyData(frequencyData);
  const accent = getComputedStyle(document.body).getPropertyValue("--visualizer-color").trim();
  visualizerContext.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);
  visualizerContext.fillStyle = accent;
  visualizerContext.strokeStyle = accent;
  visualizerContext.globalAlpha = 0.28;
  draw(visualizerContext, visualizerCanvas.width, visualizerCanvas.height);
  visualizerFrame = requestAnimationFrame(drawVisualizer);
}

function updateVisualizer() {
  if (visualizerFrame) {
    cancelAnimationFrame(visualizerFrame);
    visualizerFrame = 0;
  }
  if (visualizerMode() === "off" || player.paused || document.hidden) {
    clearVisualizer();
    return;
  }
  try {
    if (!connectAnalyser()) {
      return;
    }
  } catch (error) {
    corsBlocked = true;
    return;
  }
  if (audioContext.state === "suspended") {
    audioContext.resume().catch(() => {});
  }
  visualizerFrame = requestAnimationFrame(drawVisualizer);
}

["play", "pause", "ended", "emptied"].forEach((eventType) => {
  player.addEventListener(eventType, updateVisualizer);
});
document.addEventListener("visibilitychange", updateVisualizer);
window.addEventListener("storage", (event) => {
  if (event.key === visualizerSettingKey) {
    updateVisualizer();
  }
});

document.querySelectorAll("[data-close-dialog]").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "0:00";
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function updateSeekProgress(value, duration) {
  const progress = Number.isFinite(duration) && duration > 0
    ? Math.min(100, Math.max(0, (value / duration) * 100))
    : 0;
  seekSlider.style.setProperty("--slider-progress", `${progress}%`);
}

function updateVolumeProgress(volume) {
  volumeSlider.style.setProperty("--slider-progress", `${volume * 100}%`);
}

function updatePlaybackControls() {
  const casting = Boolean(castSession);
  const hasRemoteMedia = casting && remotePlayer && remotePlayer.isMediaLoaded;
  const hasLocalMedia = !casting && Boolean(resolvedMedia);
  const hasMedia = hasRemoteMedia || hasLocalMedia;
  const duration = hasRemoteMedia
    ? remotePlayer.duration
    : hasLocalMedia
      ? player.duration
      : 0;
  const currentTime = hasRemoteMedia
    ? remotePlayer.currentTime
    : hasLocalMedia
      ? player.currentTime
      : 0;
  const canSeek = hasRemoteMedia
    ? remotePlayer.canSeek
    : hasLocalMedia && Number.isFinite(duration) && duration > 0;

  playPauseButton.disabled = !hasMedia;
  stopButton.disabled = !hasMedia;
  const shouldPlay = hasRemoteMedia
    ? remotePlayer.isPaused
    : hasLocalMedia && player.paused;
  playPauseIcon.textContent = shouldPlay ? "play_arrow" : "pause";
  playPauseButton.setAttribute("aria-label", shouldPlay ? "Play" : "Pause");
  playPauseButton.title = shouldPlay ? "Play" : "Pause";
  seekSlider.disabled = !canSeek;
  seekSlider.max = String(Number.isFinite(duration) ? duration : 0);
  seekDuration.textContent = formatTime(duration);
  updateSeekProgress(isSeeking ? Number(seekSlider.value) : currentTime, duration);
  if (!isSeeking) {
    seekSlider.value = String(Number.isFinite(currentTime) ? currentTime : 0);
    seekCurrentTime.value = formatTime(currentTime);
    seekCurrentTime.textContent = seekCurrentTime.value;
  }
}

function onCastMediaStatusChanged(mediaSession) {
  if (
    castSession
    && mediaSession
    && castMediaReady
    && !castCompletionHandled
    && mediaSession.playerState === chrome.cast.media.PlayerState.IDLE
    && mediaSession.idleReason === chrome.cast.media.IdleReason.FINISHED
  ) {
    castCompletionHandled = true;
    castMediaReady = false;
    if (currentIndex < tracks.length - 1) {
      advanceTrack(currentIndex + 1);
    } else if (currentIndex >= 0) {
      status.textContent = "Playlist finished.";
    }
  }
}

function watchCastMediaSession(event) {
  const mediaSession = event && event.mediaSession
    ? event.mediaSession
    : castSession
      ? castSession.getMediaSession()
      : null;
  if (!mediaSession || mediaSession === castMediaSession) {
    return;
  }
  if (castMediaSession && castMediaUpdateListener) {
    castMediaSession.removeUpdateListener(castMediaUpdateListener);
  }
  castMediaSession = mediaSession;
  castMediaUpdateListener = () => onCastMediaStatusChanged(mediaSession);
  mediaSession.addUpdateListener(castMediaUpdateListener);
  onCastMediaStatusChanged(mediaSession);
}

function onRemotePlayerChanged() {
  updatePlaybackControls();
  if (remotePlayer && remotePlayer.title) {
    status.textContent = remotePlayer.title;
  }
  onCastMediaStatusChanged(castSession ? castSession.getMediaSession() : null);
}

function updateVolumeControl(volume) {
  if (!Number.isFinite(volume)) {
    return;
  }
  const normalizedVolume = Math.min(1, Math.max(0, volume));
  volumeSlider.value = String(normalizedVolume);
  updateVolumeProgress(normalizedVolume);
  volumeValue.value = `${Math.round(normalizedVolume * 100)}%`;
  volumeValue.textContent = volumeValue.value;
}

function syncCastVolume() {
  if (castSession) {
    const volume = castSession.getVolume();
    if (Number.isFinite(volume)) {
      updateVolumeControl(volume);
    }
  }
}

function onCastVolumeChanged() {
  syncCastVolume();
}

function updateCastUi() {
  const castLabel = castSession ? "Disconnect from Chromecast" : "Cast to Chromecast";
  castButton.disabled = !castContext;
  castIcon.textContent = castSession ? "cast_connected" : "cast";
  castButton.title = castContext
    ? castLabel
    : (window.isSecureContext
      ? "Casting is unavailable in this browser."
      : "Casting requires HTTPS; localhost is allowed.");
  castButton.setAttribute("aria-label", castContext ? castLabel : "Cast unavailable");
  updatePlaybackControls();
}

function loadCastMedia(media) {
  if (!castSession) {
    return;
  }

  const mediaInfo = new chrome.cast.media.MediaInfo(
    media.audioUrl,
    media.contentType,
  );
  const metadata = new chrome.cast.media.GenericMediaMetadata();
  metadata.title = media.title;
  if (media.thumbnailUrl) {
    metadata.images = [new chrome.cast.Image(media.thumbnailUrl)];
  }
  mediaInfo.metadata = metadata;

  const loadRequest = new chrome.cast.media.LoadRequest(mediaInfo);
  loadRequest.autoplay = true;
  castMediaReady = false;
  status.textContent = `Sending ${media.title} to Chromecast…`;
  castSession.loadMedia(loadRequest).then(
    () => {
      if (resolvedMedia === media && castSession) {
        watchCastMediaSession();
        castMediaReady = true;
        castCompletionHandled = false;
        status.textContent = media.title;
      }
    },
    () => {
      if (resolvedMedia === media && castSession) {
        status.textContent = `Could not cast ${media.title}. The Chromecast may not support this audio stream.`;
        castContext.endCurrentSession(true);
      }
    },
  );
}

async function playLocally(media) {
  applyLocalVolume();
  const metadataLoaded = waitForMetadata();
  setPlayerSource(media.audioUrl);
  player.load();
  await metadataLoaded;
  player.currentTime = 0;
  await player.play();
  status.textContent = media.title;
}

function initializeCast() {
  if (!window.castApiAvailable || !window.cast || !window.cast.framework) {
    castButton.disabled = true;
    castButton.title = window.isSecureContext
      ? "Casting is unavailable in this browser."
      : "Casting requires HTTPS; localhost is allowed.";
    castButton.setAttribute("aria-label", "Cast unavailable");
    return;
  }

  castContext = cast.framework.CastContext.getInstance();
  remotePlayer = new cast.framework.RemotePlayer();
  remotePlayerController = new cast.framework.RemotePlayerController(remotePlayer);
  [
    cast.framework.RemotePlayerEventType.CURRENT_TIME_CHANGED,
    cast.framework.RemotePlayerEventType.DURATION_CHANGED,
    cast.framework.RemotePlayerEventType.IS_MEDIA_LOADED_CHANGED,
    cast.framework.RemotePlayerEventType.IS_PAUSED_CHANGED,
    cast.framework.RemotePlayerEventType.PLAYER_STATE_CHANGED,
    cast.framework.RemotePlayerEventType.CAN_SEEK_CHANGED,
  ].forEach((eventType) => {
    remotePlayerController.addEventListener(eventType, onRemotePlayerChanged);
  });
  castContext.setOptions({
    receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
    autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED,
  });
  castContext.addEventListener(
    cast.framework.CastContextEventType.SESSION_STATE_CHANGED,
    (event) => {
      if (
        event.sessionState === cast.framework.SessionState.SESSION_STARTED
        || event.sessionState === cast.framework.SessionState.SESSION_RESUMED
      ) {
        castSession = castContext.getCurrentSession();
        castSession.addEventListener(
          cast.framework.SessionEventType.VOLUME_CHANGED,
          onCastVolumeChanged,
        );
        castSession.addEventListener(
          cast.framework.SessionEventType.MEDIA_SESSION,
          watchCastMediaSession,
        );
        watchCastMediaSession();
        updateCastUi();
        syncCastVolume();
        updatePlaybackControls();
        if (resolvedMedia) {
          player.pause();
          loadCastMedia(resolvedMedia);
        } else {
          status.textContent = "Connected to Chromecast. Select a track to play.";
        }
      } else if (
        event.sessionState === cast.framework.SessionState.SESSION_ENDED
      ) {
        castSession = null;
        updateCastUi();
        updateVolumeControl(userVolume);
        if (resolvedMedia) {
          playLocally(resolvedMedia).catch((error) => {
            status.textContent = `Could not resume local playback: ${error.message}`;
          });
        }
      }
    },
  );
  castSession = castContext.getCurrentSession();
  if (castSession) {
    castSession.addEventListener(
      cast.framework.SessionEventType.VOLUME_CHANGED,
      onCastVolumeChanged,
    );
    castSession.addEventListener(
      cast.framework.SessionEventType.MEDIA_SESSION,
      watchCastMediaSession,
    );
    watchCastMediaSession();
    syncCastVolume();
  }
  updateCastUi();
}

window.addEventListener("cast-sdk-ready", initializeCast);
initializeCast();

castButton.addEventListener("click", async () => {
  try {
    if (castSession) {
      castContext.endCurrentSession(true);
    } else if (castContext) {
      await castContext.requestSession();
    }
  } catch (error) {
    status.textContent = `Could not connect to Chromecast: ${error.message}`;
  }
});

volumeSlider.addEventListener("input", () => {
  const volume = Number(volumeSlider.value);
  updateVolumeControl(volume);
  userVolume = volume;
  if (castSession) {
    castSession.setVolume(volume).catch(() => {
      status.textContent = "Could not change Chromecast volume.";
    });
  } else {
    applyLocalVolume();
  }
});

playPauseButton.addEventListener("click", async () => {
  try {
    if (castSession) {
      if (remotePlayer && remotePlayer.isMediaLoaded) {
        remotePlayerController.playOrPause();
      }
    } else if (player.paused) {
      await player.play();
    } else {
      player.pause();
    }
  } catch (error) {
    status.textContent = `Could not change playback: ${error.message}`;
  }
});
stopButton.addEventListener("click", () => {
  if (castSession) {
    if (remotePlayer && remotePlayer.isMediaLoaded) {
      remotePlayerController.stop();
    }
  } else if (resolvedMedia) {
    player.pause();
    player.currentTime = 0;
    status.textContent = "Stopped.";
  }
});
player.addEventListener("play", () => {
  if (resolvedMedia && !castSession && status.textContent === "Stopped.") {
    status.textContent = resolvedMedia.title;
  }
});
seekSlider.addEventListener("input", () => {
  isSeeking = true;
  const seekTime = Number(seekSlider.value);
  seekCurrentTime.value = formatTime(seekTime);
  seekCurrentTime.textContent = seekCurrentTime.value;
  updateSeekProgress(seekTime, Number(seekSlider.max));
});
seekSlider.addEventListener("change", () => {
  const seekTime = Number(seekSlider.value);
  isSeeking = false;
  if (castSession && remotePlayer && remotePlayer.isMediaLoaded) {
    remotePlayer.currentTime = seekTime;
    remotePlayerController.seek();
  } else if (resolvedMedia && Number.isFinite(player.duration)) {
    player.currentTime = seekTime;
    updatePlaybackControls();
  }
});
player.addEventListener("volumechange", () => {
  if (!castSession) {
    updateVolumeControl(userVolume);
  }
});
[
  "durationchange",
  "loadedmetadata",
  "pause",
  "play",
  "timeupdate",
].forEach((eventType) => {
  player.addEventListener(eventType, updatePlaybackControls);
});
updateVolumeControl(player.volume);
updatePlaybackControls();

logoutButton.addEventListener("click", async () => {
  try {
    const response = await fetch("/api/logout", { method: "POST" });
    if (!response.ok) {
      throw new Error("Could not sign out.");
    }
    window.location.assign("/login");
  } catch (error) {
    status.textContent = error.message;
  }
});

function applyAmbientColor(ambientColor) {
  document.body.style.setProperty("--ambient-color", ambientColor);
  const hueMatch = /^hsl\((\d+)/.exec(ambientColor);
  if (hueMatch) {
    const complement = (Number(hueMatch[1]) + 180) % 360;
    document.body.style.setProperty("--visualizer-color", `hsl(${complement} 75% 68%)`);
  }
  player.style.setProperty("--ambient-color", ambientColor);
  seekSlider.style.setProperty("--ambient-color", ambientColor);
  volumeSlider.style.setProperty("--ambient-color", ambientColor);
}

function shiftAmbientColor() {
  // Pick a hue noticeably different from the previous one; keep it dark and muted for readability.
  let hue;
  do {
    hue = Math.floor(Math.random() * 360);
  } while (ambientHue >= 0 && Math.min(Math.abs(hue - ambientHue), 360 - Math.abs(hue - ambientHue)) < 40);
  ambientHue = hue;
  const saturation = 25 + Math.floor(Math.random() * 16);
  const lightness = 14 + Math.floor(Math.random() * 6);
  applyAmbientColor(`hsl(${hue} ${saturation}% ${lightness}%)`);
}

const thumbnailAmbientColors = new Map();

function ambientColorFromPixels(data) {
  let weightSum = 0;
  let hueX = 0;
  let hueY = 0;
  let saturationSum = 0;
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i] / 255;
    const g = data[i + 1] / 255;
    const b = data[i + 2] / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const lightness = (max + min) / 2;
    const chroma = max - min;
    if (chroma === 0) {
      continue;
    }
    const saturation = chroma / (1 - Math.abs(2 * lightness - 1));
    let hue;
    if (max === r) {
      hue = ((g - b) / chroma + 6) % 6;
    } else if (max === g) {
      hue = (b - r) / chroma + 2;
    } else {
      hue = (r - g) / chroma + 4;
    }
    const radians = (hue * Math.PI) / 3;
    // Favor vivid, mid-brightness pixels so near-black/white areas don't decide the color.
    const weight = saturation * (1 - Math.abs(2 * lightness - 1));
    weightSum += weight;
    hueX += Math.cos(radians) * weight;
    hueY += Math.sin(radians) * weight;
    saturationSum += saturation * weight;
  }
  if (weightSum < 0.5) {
    return "hsl(210 8% 16%)";
  }
  const hue = Math.round(((Math.atan2(hueY, hueX) * 180) / Math.PI + 360) % 360);
  const saturation = Math.round(Math.min(45, Math.max(22, (saturationSum / weightSum) * 55)));
  return `hsl(${hue} ${saturation}% 16%)`;
}

function sampleThumbnailColor(url) {
  if (thumbnailAmbientColors.has(url)) {
    return Promise.resolve(thumbnailAmbientColors.get(url));
  }
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = 32;
        canvas.height = 24;
        const context = canvas.getContext("2d", { willReadFrequently: true });
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        const color = ambientColorFromPixels(
          context.getImageData(0, 0, canvas.width, canvas.height).data
        );
        thumbnailAmbientColors.set(url, color);
        resolve(color);
      } catch (error) {
        reject(error);
      }
    };
    image.onerror = () => reject(new Error("Thumbnail could not be sampled."));
    image.src = url;
  });
}

function updateAmbientColor(track) {
  if (!track.thumbnail_url) {
    shiftAmbientColor();
    return;
  }
  const url = track.thumbnail_url;
  sampleThumbnailColor(url).then(
    (color) => {
      if (tracks[currentIndex] === track) {
        applyAmbientColor(color);
      }
    },
    () => {
      if (tracks[currentIndex] === track) {
        shiftAmbientColor();
      }
    }
  );
}

const userScrollPauseMs = 5000;
let autoScrollTimer = null;

function autoScrollEnabled() {
  try {
    return localStorage.getItem("audify.autoScroll") !== "off";
  } catch (error) {
    return true;
  }
}

function centerCurrentTrack() {
  clearTimeout(autoScrollTimer);
  autoScrollTimer = null;
  if (!autoScrollEnabled()) {
    return;
  }
  const button = trackList.querySelector('button[aria-current="true"]');
  if (!button) {
    return;
  }
  const listRect = trackList.getBoundingClientRect();
  const buttonRect = button.getBoundingClientRect();
  const offset = buttonRect.top - listRect.top + trackList.scrollTop;
  const top = offset - (trackList.clientHeight - buttonRect.height) / 2;
  trackList.scrollTo({
    top: Math.max(0, top),
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "auto"
      : "smooth",
  });
}

function pauseAutoScroll() {
  clearTimeout(autoScrollTimer);
  autoScrollTimer = setTimeout(centerCurrentTrack, userScrollPauseMs);
}

["wheel", "touchmove", "pointerdown", "keydown"].forEach((type) =>
  trackList.addEventListener(type, pauseAutoScroll, { passive: true })
);

function selectTrack(index) {
  playTrack(index);
}

function advanceTrack(index) {
  playTrack(index);
}

function renderTracks() {
  trackList.replaceChildren();
  const query = playlistSearch.value.trim().toLocaleLowerCase();
  const matchingTracks = tracks
    .map((track, index) => ({ track, index }))
    .filter(({ track }) => track.title.toLocaleLowerCase().includes(query));

  matchingTracks.forEach(({ track, index }) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.classList.add("track-select");
    button.textContent = track.title;
    button.setAttribute("data-track-number", String(index + 1));
    button.setAttribute("aria-current", String(index === currentIndex));
    button.addEventListener("click", () => {
      clearTimeout(autoScrollTimer);
      autoScrollTimer = null;
      selectTrack(index);
    });
    item.append(button);
    trackList.append(item);
  });
  trackSearchStatus.hidden = !query || matchingTracks.length > 0;
  trackSearchStatus.textContent = query
    ? `No tracks found for “${playlistSearch.value.trim()}”.`
    : "";
  previousButton.disabled = currentIndex <= 0;
  nextButton.disabled = currentIndex < 0 || currentIndex >= tracks.length - 1;
  shuffleButton.disabled = tracks.length < 2;
  playlistSearch.disabled = tracks.length === 0;
}

function autoShuffleEnabled() {
  try {
    return localStorage.getItem("audify.autoShuffle") === "on";
  } catch (error) {
    return false;
  }
}

function shuffleTracks() {
  const currentTrack = currentIndex >= 0 ? tracks[currentIndex] : null;
  for (let index = tracks.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [tracks[index], tracks[randomIndex]] = [tracks[randomIndex], tracks[index]];
  }
  if (currentTrack) {
    currentIndex = tracks.indexOf(currentTrack);
  }
  renderTracks();
}

function clearPlayer() {
  if (cancelMetadataWait) {
    cancelMetadataWait();
  }
  player.pause();
  player.removeAttribute("src");
  player.load();
}

function waitForMetadata() {
  return new Promise((resolve, reject) => {
    function cleanup() {
      player.removeEventListener("loadedmetadata", onLoadedMetadata);
      player.removeEventListener("error", onError);
      if (cancelMetadataWait === cancel) {
        cancelMetadataWait = null;
      }
    }

    function onLoadedMetadata() {
      cleanup();
      resolve();
    }

    function onError() {
      cleanup();
      reject(new Error("The audio stream could not be loaded."));
    }

    function cancel() {
      cleanup();
      reject(new Error("Playback was replaced."));
    }

    cancelMetadataWait = cancel;
    player.addEventListener("loadedmetadata", onLoadedMetadata);
    player.addEventListener("error", onError);
  });
}

const thumbnailFadeMs = 200;

// Fade the old thumbnail out, then swap in the new one once it has loaded and fade it in.
function showThumbnail(url) {
  currentThumbnail.hidden = true;
  playerGlow.classList.remove("is-visible");
  if (!url) {
    delete currentThumbnail.dataset.thumbnailUrl;
    return;
  }
  currentThumbnail.dataset.thumbnailUrl = url;
  const loaded = new Promise((resolve, reject) => {
    const loader = new Image();
    loader.onload = resolve;
    loader.onerror = reject;
    loader.src = url;
  });
  const faded = new Promise((resolve) => setTimeout(resolve, thumbnailFadeMs));
  Promise.all([loaded, faded]).then(
    () => {
      if (currentThumbnail.dataset.thumbnailUrl !== url) {
        return;
      }
      currentThumbnail.src = url;
      currentThumbnail.hidden = false;
      playerGlow.style.backgroundImage = `url("${url}")`;
      playerGlow.classList.add("is-visible");
    },
    () => {
      if (currentThumbnail.dataset.thumbnailUrl === url) {
        delete currentThumbnail.dataset.thumbnailUrl;
      }
    }
  );
}

async function playTrack(index, retryCount = 0) {
  if (index < 0 || index >= tracks.length) {
    return;
  }
  const track = tracks[index];
  const requestId = ++playbackRequest;
  const trackChanged = index !== currentIndex;
  currentIndex = index;
  if (trackChanged) {
    updateAmbientColor(track);
  }
  resolvedMedia = null;
  renderTracks();
  if (autoScrollTimer === null) {
    centerCurrentTrack();
  }
  clearPlayer();
  const thumbnailUrl = track.thumbnail_url || null;
  if ((currentThumbnail.dataset.thumbnailUrl || null) !== thumbnailUrl || !thumbnailUrl) {
    showThumbnail(thumbnailUrl);
  }
  status.textContent = `Resolving ${track.title}…`;

  try {
    const response = await fetch("/api/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: track.url,
        title: track.title,
        playlist: currentPlaylistId ? currentPlaylistTitle : null,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      const resolveError = new Error(result.error || "Could not resolve that track.");
      resolveError.unresolvable = response.status === 422;
      throw resolveError;
    }
    if (requestId !== playbackRequest) {
      return;
    }

    resolvedMedia = {
      audioUrl: result.audio_url,
      contentType: result.content_type || "audio/mpeg",
      title: result.title,
      thumbnailUrl: track.thumbnail_url,
      gainDb: result.gain_db,
    };
    if (castSession) {
      player.pause();
      loadCastMedia(resolvedMedia);
      return;
    }

    applyLocalVolume();
    const metadataLoaded = waitForMetadata();
    setPlayerSource(resolvedMedia.audioUrl);
    player.load();
    await metadataLoaded;
    if (requestId !== playbackRequest) {
      return;
    }
    player.currentTime = 0;
    await player.play();
    if (requestId === playbackRequest) {
      status.textContent = resolvedMedia.title;
      updatePlaybackControls();
    }
  } catch (error) {
    if (requestId === playbackRequest) {
      if (error.message === audioLoadError && retryCount < maxAudioLoadRetries) {
        status.textContent = `Retrying ${track.title} (${retryCount + 1}/${maxAudioLoadRetries})…`;
        await playTrack(index, retryCount + 1);
      } else if (
        (error.message === audioLoadError || error.unresolvable)
        && index < tracks.length - 1
      ) {
        advanceTrack(index + 1);
      } else {
        status.textContent = `${track.title}: ${error.message}`;
      }
    }
  }
}

function youtubeThumbnailUrl(link) {
  try {
    const url = new URL(link);
    const videoId = url.hostname === "youtu.be"
      ? url.pathname.slice(1)
      : url.searchParams.get("v");
    return videoId && /^[\w-]{6,}$/.test(videoId)
      ? `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`
      : null;
  } catch {
    return null;
  }
}

function loadPlaylist(playlist) {
  showYoutubeSearch(false);
  const playbackContinues = castSession
    ? Boolean(remotePlayer && remotePlayer.isMediaLoaded && !remotePlayer.isPaused)
    : Boolean(resolvedMedia && !player.paused && !player.ended);
  ++playbackRequest;
  tracks = playlist.videos.map((video) => ({
    title: video.name,
    url: video.link,
    thumbnail_url: youtubeThumbnailUrl(video.link),
  }));
  currentIndex = -1;
  playlistSearch.value = "";
  trackSearchStatus.hidden = true;
  trackSearchStatus.textContent = "";
  currentPlaylistTitle = playlist.name;
  currentPlaylistId = playlist.id;
  playlistTitle.textContent = `${currentPlaylistTitle} (${tracks.length} songs)`;
  if (autoShuffleEnabled()) {
    shuffleTracks();
  } else {
    renderTracks();
  }
  updatePlaybackControls();
  if (!playbackContinues) {
    status.textContent = `${currentPlaylistTitle} — ${tracks.length} tracks`;
  }
}

async function refreshPlaylists() {
  const response = await fetch("/api/playlists");
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "Could not load playlists.");
  }

  playlists = result.playlists;
  renderPlaylists();
}

function showYoutubeSearch(showSearch) {
  youtubeSearchButton.setAttribute("aria-pressed", String(showSearch));
  const searchLabel = showSearch ? "Back to Playlist" : "Search YouTube";
  youtubeSearchButton.setAttribute("aria-label", searchLabel);
  youtubeSearchButton.title = searchLabel;
  youtubeSearchButton.querySelector(".material-symbols-outlined").textContent =
    showSearch ? "queue_music" : "video_search";
  youtubeSearchButton.querySelector(".button-label").textContent =
    showSearch ? "Back to Playlist" : "Search YouTube";
  youtubeSearchSection.hidden = !showSearch;
  playlistQueueSection.hidden = showSearch;
  if (showSearch) {
    youtubeSearchQuery.focus();
  }
}

function renderYoutubeSearchResults(results) {
  youtubeSearchResults.replaceChildren();
  results.forEach((result) => {
    const item = document.createElement("li");
    item.classList.add("youtube-search-result");
    item.setAttribute("role", "group");
    const playResult = () => {
      tracks = [{
        title: result.name,
        url: result.link,
        thumbnail_url: youtubeThumbnailUrl(result.link),
      }];
      currentIndex = -1;
      currentPlaylistTitle = result.name;
      currentPlaylistId = null;
      playlistTitle.textContent = `${result.name} (search result)`;
      playlistSearch.value = "";
      renderTracks();
      selectTrack(0);
    };
    item.addEventListener("click", (event) => {
      if (event.target.closest("button")) {
        return;
      }
      playResult();
    });
    const info = document.createElement("div");
    info.classList.add("youtube-search-result-info");
    const title = document.createElement("span");
    title.classList.add("youtube-search-result-title");
    title.textContent = result.name;
    const duration = document.createElement("span");
    duration.classList.add("youtube-search-duration");
    duration.textContent = result.duration === null
      ? "Duration unavailable"
      : formatTime(result.duration);
    info.append(title, duration);

    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.textContent = "Add to playlist";
    addButton.addEventListener("click", (event) => {
      event.stopPropagation();
      openAddSongDialog({ name: result.name, link: result.link });
    });
    item.append(info, addButton);
    youtubeSearchResults.append(item);
  });
}

async function searchYoutube(event) {
  event.preventDefault();
  const query = youtubeSearchQuery.value.trim();
  if (!query) {
    youtubeSearchStatus.textContent = "Enter a search query.";
    return;
  }

  const requestId = ++youtubeSearchRequest;
  youtubeSearchSubmit.disabled = true;
  youtubeSearchStatus.textContent = "Searching YouTube…";
  youtubeSearchResults.replaceChildren();
  try {
    const response = await fetch("/api/youtube/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not search YouTube.");
    }
    if (requestId !== youtubeSearchRequest) {
      return;
    }
    renderYoutubeSearchResults(result.results);
    youtubeSearchStatus.textContent = result.results.length
      ? `${result.results.length} result(s).`
      : "No YouTube results found.";
  } catch (error) {
    if (requestId === youtubeSearchRequest) {
      youtubeSearchStatus.textContent = error.message;
    }
  } finally {
    if (requestId === youtubeSearchRequest) {
      youtubeSearchSubmit.disabled = false;
    }
  }
}

function renderPlaylists() {
  playlistList.replaceChildren();
  playlists.forEach((playlist) => {
    const item = document.createElement("li");
    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.classList.add("playlist-title");
    openButton.textContent = playlist.name;
    openButton.addEventListener("click", () => loadPlaylist(playlist));

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.textContent = "Edit";
    editButton.setAttribute("aria-label", `Edit ${playlist.name}`);
    editButton.addEventListener("click", () => openPlaylistEditor(playlist));

    item.append(openButton, editButton);
    playlistList.append(item);
  });
}

function addVideoEditorRow(video = { name: "", link: "" }) {
  const row = document.createElement("div");
  row.classList.add("playlist-video-row");
  row.dataset.videoName = video.name;
  row.dataset.videoLink = video.link;
  const videoLink = document.createElement("a");
  videoLink.classList.add("playlist-video-link");
  videoLink.href = video.link;
  videoLink.target = "_blank";
  videoLink.rel = "noopener noreferrer";
  videoLink.textContent = video.name;

  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.textContent = "Remove";
  removeButton.setAttribute("aria-label", "Remove video");
  removeButton.addEventListener("click", () => row.remove());
  const replaceButton = document.createElement("button");
  replaceButton.type = "button";
  replaceButton.textContent = "Replace";
  replaceButton.setAttribute("aria-label", "Replace video");
  replaceButton.addEventListener("click", () => openReplaceDialog(row));
  row.append(videoLink, replaceButton, removeButton);
  playlistVideoFields.append(row);
  filterPlaylistVideoRows();
  return row;
}

function applyReplacement(video) {
  const row = replacingRow;
  if (!row || !row.isConnected) {
    videoReplaceDialog.close();
    return;
  }
  if (row.dataset.videoLink !== video.link) {
    const pendingReplacement = pendingReplacements.find(
      (replacement) => replacement.row === row,
    );
    if (pendingReplacement) {
      pendingReplacement.to = video;
    } else {
      pendingReplacements.push({
        from: row.dataset.videoLink,
        to: video,
        row,
      });
    }
  }
  row.dataset.videoName = video.name;
  row.dataset.videoLink = video.link;
  const link = row.querySelector(".playlist-video-link");
  link.href = video.link;
  link.textContent = video.name;
  filterPlaylistVideoRows();
  videoReplaceDialog.close();
  playlistEditorStatus.textContent =
    `Replaced with "${video.name}". Save the playlist to keep the change.`;
}

const previewAudio = new Audio();
let previewButton = null;
let previewRequest = 0;

function setPreviewButtonState(button, playing) {
  if (!button) {
    return;
  }
  button.querySelector(".material-symbols-outlined").textContent =
    playing ? "pause" : "play_arrow";
  const label = playing ? "Pause preview" : "Play preview";
  button.setAttribute("aria-label", label);
  button.title = label;
}

function stopPreview() {
  previewRequest += 1;
  previewAudio.pause();
  previewAudio.removeAttribute("src");
  previewAudio.load();
  setPreviewButtonState(previewButton, false);
  previewButton = null;
}

async function togglePreview(button, link) {
  if (previewButton === button) {
    if (previewAudio.paused) {
      try {
        await previewAudio.play();
        setPreviewButtonState(button, true);
      } catch (error) {
        videoReplaceStatus.textContent = "Could not play that preview.";
      }
    } else {
      previewAudio.pause();
      setPreviewButtonState(button, false);
    }
    return;
  }

  stopPreview();
  const requestId = previewRequest;
  previewButton = button;
  button.disabled = true;
  videoReplaceStatus.textContent = "Loading preview…";
  try {
    const response = await fetch("/api/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: link }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not load that preview.");
    }
    if (requestId !== previewRequest) {
      return;
    }
    player.pause();
    previewAudio.src = result.audio_url;
    await previewAudio.play();
    if (requestId === previewRequest) {
      setPreviewButtonState(button, true);
      videoReplaceStatus.textContent = "";
    }
  } catch (error) {
    if (requestId === previewRequest) {
      previewButton = null;
      videoReplaceStatus.textContent = error.message || "Could not play that preview.";
    }
  } finally {
    button.disabled = false;
  }
}

previewAudio.addEventListener("ended", () => {
  setPreviewButtonState(previewButton, false);
  previewButton = null;
});
videoReplaceDialog.addEventListener("close", stopPreview);

function renderReplaceResults(results) {
  stopPreview();
  videoReplaceResults.replaceChildren();
  results.slice(0, 10).forEach((result) => {
    const item = document.createElement("li");
    item.classList.add("youtube-search-result");
    const info = document.createElement("div");
    info.classList.add("youtube-search-result-info");
    const title = document.createElement("span");
    title.classList.add("youtube-search-result-title");
    title.textContent = result.name;
    title.title = result.name;
    const duration = document.createElement("span");
    duration.classList.add("youtube-search-duration");
    duration.textContent = result.duration === null
      ? "Duration unavailable"
      : formatTime(result.duration);
    info.append(title, duration);
    const playButton = document.createElement("button");
    playButton.type = "button";
    playButton.classList.add("icon-button");
    playButton.innerHTML =
      '<span class="material-symbols-outlined" aria-hidden="true">play_arrow</span>';
    setPreviewButtonState(playButton, false);
    playButton.addEventListener("click", () => togglePreview(playButton, result.link));
    const selectButton = document.createElement("button");
    selectButton.type = "button";
    selectButton.classList.add("video-replace-select-button");
    selectButton.textContent = "Select";
    selectButton.addEventListener("click", () => {
      applyReplacement({ name: result.name, link: result.link });
    });
    const actions = document.createElement("div");
    actions.classList.add("video-replace-result-actions");
    actions.append(playButton, selectButton);
    item.append(info, actions);
    videoReplaceResults.append(item);
  });
}

async function searchReplacements(event) {
  if (event) {
    event.preventDefault();
  }
  const query = videoReplaceQuery.value.trim();
  if (!query) {
    return;
  }
  const requestId = ++videoReplaceRequest;
  stopPreview();
  videoReplaceSearchSubmit.disabled = true;
  videoReplaceStatus.textContent = "Searching YouTube…";
  videoReplaceResults.replaceChildren();
  try {
    const response = await fetch("/api/youtube/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not search YouTube.");
    }
    if (requestId !== videoReplaceRequest) {
      return;
    }
    renderReplaceResults(result.results);
    videoReplaceStatus.textContent = result.results.length
      ? ""
      : "No YouTube results found.";
  } catch (error) {
    if (requestId === videoReplaceRequest) {
      videoReplaceStatus.textContent = error.message;
    }
  } finally {
    if (requestId === videoReplaceRequest) {
      videoReplaceSearchSubmit.disabled = false;
    }
  }
}

async function replaceWithLink(event) {
  event.preventDefault();
  videoReplaceLinkSubmit.disabled = true;
  videoReplaceStatus.textContent = "Looking up song…";
  try {
    const response = await fetch("/api/videos/title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: videoReplaceUrl.value.trim() }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not get the song title.");
    }
    applyReplacement(result.video);
  } catch (error) {
    videoReplaceStatus.textContent = error.message;
  } finally {
    videoReplaceLinkSubmit.disabled = false;
  }
}

function openReplaceDialog(row) {
  replacingRow = row;
  videoReplaceRequest += 1;
  videoReplaceSearchSubmit.disabled = false;
  videoReplaceUrl.value = "";
  videoReplaceStatus.textContent = "";
  videoReplaceResults.replaceChildren();
  videoReplaceQuery.value = row.dataset.videoName;
  videoReplaceDialog.showModal();
  searchReplacements();
}

function filterPlaylistVideoRows() {
  const query = playlistVideoSearch.value.trim().toLocaleLowerCase();
  playlistVideoFields.querySelectorAll(".playlist-video-row").forEach((row) => {
    row.hidden = !row.dataset.videoName.toLocaleLowerCase().includes(query);
  });
}

function openPlaylistEditor(playlist = null) {
  editingPlaylistId = playlist ? playlist.id : null;
  playlistEditorHeading.textContent = playlist ? "Edit playlist" : "Add playlist";
  deletePlaylistButton.hidden = !playlist;
  playlistNameInput.value = playlist ? playlist.name : "";
  playlistVideoSearch.value = "";
  playlistEditorStatus.textContent = "";
  pendingReplacements = [];
  playlistVideoFields.replaceChildren();
  (playlist ? playlist.videos : [])
    .forEach(addVideoEditorRow);
  playlistEditor.showModal();
  playlistNameInput.focus();
}

function renderSongPlaylistChoices() {
  songPlaylistOptions.replaceChildren();
  if (!playlists.length) {
    const emptyMessage = document.createElement("p");
    emptyMessage.classList.add("song-playlist-empty");
    emptyMessage.textContent = "Create a playlist before adding a song.";
    songPlaylistOptions.append(emptyMessage);
    return;
  }

  playlists.forEach((playlist) => {
    const label = document.createElement("label");
    label.classList.add("song-playlist-option");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "playlist";
    checkbox.value = playlist.id;
    const name = document.createElement("span");
    name.textContent = playlist.name;
    label.append(checkbox, name);
    songPlaylistOptions.append(label);
  });
}

async function openAddSongDialog(song = null) {
  videoAddForm.reset();
  videoAddStatus.textContent = "";
  selectedSearchSong = song;
  videoAddHeading.textContent = song ? "Add to playlists" : "Add Song";
  videoAddLinkField.hidden = Boolean(song);
  videoAddUrl.required = !song;
  songPlaylistOptions.replaceChildren();
  const loadingMessage = document.createElement("p");
  loadingMessage.classList.add("song-playlist-empty");
  loadingMessage.textContent = "Loading playlists…";
  songPlaylistOptions.append(loadingMessage);
  videoAddDialog.showModal();
  if (!song) {
    videoAddUrl.focus();
  }
  try {
    await refreshPlaylists();
    renderSongPlaylistChoices();
  } catch (error) {
    videoAddStatus.textContent = error.message;
    songPlaylistOptions.replaceChildren();
  }
}

async function addSongToSelectedPlaylists(event) {
  event.preventDefault();
  submitVideoAdd.disabled = true;
  const playlistIds = Array.from(
    songPlaylistOptions.querySelectorAll('input[name="playlist"]:checked'),
    (checkbox) => checkbox.value,
  );
  if (!playlistIds.length) {
    videoAddStatus.textContent = "Select at least one playlist.";
    submitVideoAdd.disabled = false;
    return;
  }
  videoAddStatus.textContent = selectedSearchSong
    ? "Saving song to playlists…"
    : "Looking up song and saving to playlists…";
  try {
    let song = selectedSearchSong;
    if (!song) {
      const titleResponse = await fetch("/api/videos/title", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: videoAddUrl.value.trim() }),
      });
      const titleResult = await titleResponse.json();
      if (!titleResponse.ok) {
        throw new Error(titleResult.error || "Could not get the song title.");
      }
      song = titleResult.video;
    }
    const response = await fetch("/api/playlists/add-song", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ playlist_ids: playlistIds, video: song }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not add the song to those playlists.");
    }
    videoAddDialog.close();
    videoAddForm.reset();
    try {
      await refreshPlaylists();
    } catch {}
  } catch (error) {
    videoAddStatus.textContent = error.message;
  } finally {
    submitVideoAdd.disabled = false;
  }
}

async function persistPlaylist(closeEditor) {
  savePlaylistButton.disabled = true;
  const videos = Array.from(
    playlistVideoFields.querySelectorAll(".playlist-video-row"),
    (row) => ({ name: row.dataset.videoName, link: row.dataset.videoLink }),
  );
  const replacements = editingPlaylistId
    ? pendingReplacements
      .filter(({ row }) => row.isConnected)
      .map(({ from, to }) => ({ from, to }))
    : [];
  const method = editingPlaylistId ? "PUT" : "POST";
  const endpoint = editingPlaylistId
    ? `/api/playlists/${encodeURIComponent(editingPlaylistId)}`
    : "/api/playlists";
  try {
    const response = await fetch(endpoint, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: playlistNameInput.value.trim(),
        videos,
        replacements,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not save the playlist.");
    }
    editingPlaylistId = result.playlist.id;
    playlistEditorHeading.textContent = "Edit playlist";
    deletePlaylistButton.hidden = false;
    if (currentPlaylistId === result.playlist.id) {
      currentPlaylistTitle = result.playlist.name;
      replacements.forEach(({ from, to }) => {
        tracks.forEach((track) => {
          if (track.url !== from) {
            return;
          }
          track.title = to.name;
          track.url = to.link;
        });
      });
      renderTracks();
      playlistTitle.textContent = `${currentPlaylistTitle} (${tracks.length} songs)`;
    }
    pendingReplacements = [];
    try {
      await refreshPlaylists();
    } catch {}
    if (closeEditor) {
      playlistEditor.close();
    }
    return result.playlist;
  } finally {
    savePlaylistButton.disabled = false;
  }
}

async function savePlaylist(event) {
  event.preventDefault();
  try {
    await persistPlaylist(true);
  } catch (error) {
    playlistEditorStatus.textContent = error.message;
  }
}

async function deletePlaylist(playlist) {
  if (!window.confirm(`Delete "${playlist.name}"?`)) {
    return;
  }
  try {
    const response = await fetch(
      `/api/playlists/${encodeURIComponent(playlist.id)}`,
      { method: "DELETE" },
    );
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not delete the playlist.");
    }
    await refreshPlaylists();
    playlistEditor.close();
  } catch (error) {
    playlistEditorStatus.textContent = error.message;
  }
}

async function importPlaylist(event) {
  event.preventDefault();
  submitPlaylistImport.disabled = true;
  try {
    const response = await fetch("/api/playlists/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: playlistImportUrl.value.trim() }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not import the playlist.");
    }
    playlistImportDialog.close();
    playlistImportForm.reset();
    await refreshPlaylists();
  } catch (error) {
    window.alert(error.message);
  } finally {
    submitPlaylistImport.disabled = false;
  }
}

addSongButton.addEventListener("click", () => openAddSongDialog());
addPlaylistButton.addEventListener("click", () => openPlaylistEditor());
youtubeSearchButton.addEventListener("click", () => {
  showYoutubeSearch(youtubeSearchSection.hidden);
});
youtubeSearchForm.addEventListener("submit", searchYoutube);
cancelVideoAdd.addEventListener("click", () => videoAddDialog.close());
videoAddForm.addEventListener("submit", addSongToSelectedPlaylists);
cancelPlaylistButton.addEventListener("click", () => playlistEditor.close());
playlistEditorForm.addEventListener("submit", savePlaylist);
deletePlaylistButton.addEventListener("click", () => {
  if (editingPlaylistId) {
    deletePlaylist({ id: editingPlaylistId, name: playlistNameInput.value.trim() });
  }
});
importPlaylistButton.addEventListener("click", () => {
  playlistImportDialog.showModal();
  playlistImportUrl.focus();
});
cancelPlaylistImport.addEventListener("click", () => playlistImportDialog.close());
playlistImportForm.addEventListener("submit", importPlaylist);
videoReplaceSearchForm.addEventListener("submit", searchReplacements);
videoReplaceLinkForm.addEventListener("submit", replaceWithLink);

previousButton.addEventListener("click", () => selectTrack(currentIndex - 1));
nextButton.addEventListener("click", () => selectTrack(currentIndex + 1));
shuffleButton.addEventListener("click", shuffleTracks);
playlistSearch.addEventListener("input", renderTracks);
playlistVideoSearch.addEventListener("input", filterPlaylistVideoRows);
player.addEventListener("ended", () => {
  if (currentIndex < tracks.length - 1) {
    advanceTrack(currentIndex + 1);
  } else if (currentIndex >= 0) {
    status.textContent = "Playlist finished.";
  }
});

if ("mediaSession" in navigator) {
  const mediaSession = navigator.mediaSession;
  const setActionHandler = (action, handler) => {
    try {
      mediaSession.setActionHandler(action, handler);
    } catch (error) {
      // This browser does not support the action.
    }
  };

  const updateMediaSessionMetadata = () => {
    if (!resolvedMedia) {
      mediaSession.metadata = null;
      return;
    }
    mediaSession.metadata = new MediaMetadata({
      title: resolvedMedia.title || "Bragi",
      artist: "Bragi",
      album: currentPlaylistTitle,
      artwork: resolvedMedia.thumbnailUrl
        ? [{ src: resolvedMedia.thumbnailUrl }]
        : [],
    });
  };

  const updateMediaSessionPosition = () => {
    if (
      castSession
      || !Number.isFinite(player.duration)
      || player.duration <= 0
      || typeof mediaSession.setPositionState !== "function"
    ) {
      return;
    }
    try {
      mediaSession.setPositionState({
        duration: player.duration,
        playbackRate: player.playbackRate || 1,
        position: Math.min(player.currentTime, player.duration),
      });
    } catch (error) {
      // Ignore invalid position state.
    }
  };

  const updateMediaSessionState = () => {
    mediaSession.playbackState = !resolvedMedia
      ? "none"
      : player.paused ? "paused" : "playing";
    updateMediaSessionPosition();
  };

  setActionHandler("play", async () => {
    if (castSession) {
      return;
    }
    try {
      await player.play();
    } catch (error) {
      status.textContent = `Could not change playback: ${error.message}`;
    }
    updateMediaSessionState();
  });
  setActionHandler("pause", () => {
    if (castSession) {
      return;
    }
    player.pause();
    updateMediaSessionState();
  });
  setActionHandler("stop", () => stopButton.click());
  setActionHandler("previoustrack", () => {
    if (currentIndex > 0) {
      selectTrack(currentIndex - 1);
    }
  });
  setActionHandler("nexttrack", () => {
    if (currentIndex >= 0 && currentIndex < tracks.length - 1) {
      selectTrack(currentIndex + 1);
    }
  });
  setActionHandler("seekto", (details) => {
    if (
      !castSession
      && resolvedMedia
      && Number.isFinite(player.duration)
      && Number.isFinite(details.seekTime)
    ) {
      player.currentTime = Math.min(details.seekTime, player.duration);
      updateMediaSessionPosition();
    }
  });
  setActionHandler("seekbackward", (details) => {
    player.currentTime = Math.max(0, player.currentTime - (details.seekOffset || 10));
  });
  setActionHandler("seekforward", (details) => {
    if (Number.isFinite(player.duration)) {
      player.currentTime = Math.min(
        player.duration,
        player.currentTime + (details.seekOffset || 10),
      );
    }
  });

  ["play", "pause", "ended", "emptied", "durationchange", "seeked"].forEach(
    (eventType) => player.addEventListener(eventType, updateMediaSessionState),
  );
  player.addEventListener("loadedmetadata", () => {
    updateMediaSessionMetadata();
    updateMediaSessionState();
  });
}

refreshPlaylists().catch((error) => {
  status.textContent = error.message;
});
