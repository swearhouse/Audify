const loudnessToggle = document.querySelector("#loudness-normalization");
const settingsStatus = document.querySelector("#settings-status");
const settingsKey = "audify.loudnessNormalization";

function readSetting() {
  try {
    return localStorage.getItem(settingsKey) !== "off";
  } catch (error) {
    return true;
  }
}

loudnessToggle.checked = readSetting();
loudnessToggle.addEventListener("change", () => {
  try {
    localStorage.setItem(settingsKey, loudnessToggle.checked ? "on" : "off");
    settingsStatus.textContent = loudnessToggle.checked
      ? "Loudness normalization is on."
      : "Loudness normalization is off.";
  } catch (error) {
    settingsStatus.textContent = "Could not save this setting in your browser.";
  }
});

const visualizerSelect = document.querySelector("#visualizer-select");
const autoShuffleToggle = document.querySelector("#auto-shuffle");
const autoShuffleKey = "audify.autoShuffle";
try {
  autoShuffleToggle.checked = localStorage.getItem(autoShuffleKey) === "on";
} catch (error) {
  autoShuffleToggle.checked = false;
}
autoShuffleToggle.addEventListener("change", () => {
  try {
    localStorage.setItem(autoShuffleKey, autoShuffleToggle.checked ? "on" : "off");
    settingsStatus.textContent = autoShuffleToggle.checked
      ? "Auto-shuffle is on."
      : "Auto-shuffle is off.";
  } catch (error) {
    settingsStatus.textContent = "Could not save this setting in your browser.";
  }
});
const autoScrollToggle = document.querySelector("#auto-scroll");
const autoScrollKey = "audify.autoScroll";
try {
  autoScrollToggle.checked = localStorage.getItem(autoScrollKey) !== "off";
} catch (error) {
  autoScrollToggle.checked = true;
}
autoScrollToggle.addEventListener("change", () => {
  try {
    localStorage.setItem(autoScrollKey, autoScrollToggle.checked ? "on" : "off");
    settingsStatus.textContent = autoScrollToggle.checked
      ? "Auto-scroll is on."
      : "Auto-scroll is off.";
  } catch (error) {
    settingsStatus.textContent = "Could not save this setting in your browser.";
  }
});
const visualizerKey = "audify.visualizer";
try {
  visualizerSelect.value = localStorage.getItem(visualizerKey) || "bars";
} catch (error) {
  visualizerSelect.value = "bars";
}
visualizerSelect.addEventListener("change", () => {
  try {
    localStorage.setItem(visualizerKey, visualizerSelect.value);
    settingsStatus.textContent = `Visualizer: ${visualizerSelect.selectedOptions[0].textContent}.`;
  } catch (error) {
    settingsStatus.textContent = "Could not save this setting in your browser.";
  }
});
