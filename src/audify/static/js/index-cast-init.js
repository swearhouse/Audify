window.castApiAvailable = false;
window.__onGCastApiAvailable = (isAvailable) => {
  window.castApiAvailable = isAvailable;
  window.dispatchEvent(new Event("cast-sdk-ready"));
};
