// location.js — Geolocation API helper

window.LocationHelper = {
  coords: null,

  get(onSuccess, onError) {
    if (!navigator.geolocation) {
      onError('Geolocation is not supported by this browser.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        this.coords = { lat: pos.coords.latitude, lon: pos.coords.longitude, acc: pos.coords.accuracy };
        onSuccess(this.coords);
      },
      err => {
        const msgs = {
          1: 'Permission denied — please allow location access.',
          2: 'Position unavailable.',
          3: 'Timeout — try again.',
        };
        onError(msgs[err.code] || 'Unknown error.');
      },
      { enableHighAccuracy: true, timeout: 10000. }
    );
  },

  watch(onSuccess, onError) {
    if (!navigator.geolocation) { onError('Geolocation not supported.'); return; }
    return navigator.geolocation.watchPosition(
      pos => {
        this.coords = { lat: pos.coords.latitude, lon: pos.coords.longitude, acc: pos.coords.accuracy };
        onSuccess(this.coords);
      },
      err => onError(err.message),
      { enableHighAccuracy: true }
    );
  }
};
