// location.js — Geolocation API helper (GPS-priority)

window.LocationHelper = {
  coords: null,
  _watchId: null,

  /**
   * Get the best available GPS position.
   * Uses watchPosition internally for up to 8 seconds to let GPS lock.
   * Returns the reading with the smallest accuracy (most precise).
   */
  get(onSuccess, onError) {
    if (!navigator.geolocation) {
      onError('Geolocation is not supported by this browser.');
      return;
    }

    let bestPosition = null;
    let settled = false;

    const finish = () => {
      if (settled) return;
      settled = true;
      navigator.geolocation.clearWatch(watchId);

      if (bestPosition) {
        this.coords = bestPosition;
        onSuccess(this.coords);
      } else {
        onError('Could not get location. Please allow GPS/location access and try again.');
      }
    };

    // Watch for position updates — GPS readings improve over time
    const watchId = navigator.geolocation.watchPosition(
      pos => {
        const reading = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          acc: pos.coords.accuracy,
        };

        // Keep the most accurate reading
        if (!bestPosition || reading.acc < bestPosition.acc) {
          bestPosition = reading;
        }

        // If accuracy is good enough (< 50m = real GPS), return immediately
        if (reading.acc <= 50) {
          finish();
        }
      },
      err => {
        const msgs = {
          1: 'Permission denied — please allow location access in your browser settings.',
          2: 'Position unavailable — make sure GPS/Location is turned ON.',
          3: 'Timeout — GPS could not lock. Move to an open area and try again.',
        };
        if (!bestPosition) {
          // No position at all — report error
          settled = true;
          navigator.geolocation.clearWatch(watchId);
          onError(msgs[err.code] || 'Unknown location error.');
        }
        // If we already have a position, ignore the error and use what we have
      },
      {
        enableHighAccuracy: true,  // Force GPS over Wi-Fi
        maximumAge: 0,             // No cached positions — always fresh
        timeout: 15000,            // 15s timeout for each attempt
      }
    );

    // Safety timeout: after 8 seconds, return the best we got
    setTimeout(() => {
      finish();
    }, 8000);
  },

  /**
   * Continuously watch position (for real-time tracking).
   */
  watch(onSuccess, onError) {
    if (!navigator.geolocation) { onError('Geolocation not supported.'); return null; }
    
    this._watchId = navigator.geolocation.watchPosition(
      pos => {
        this.coords = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          acc: pos.coords.accuracy,
        };
        onSuccess(this.coords);
      },
      err => onError(err.message),
      {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 15000,
      }
    );
    return this._watchId;
  },

  /**
   * Stop watching position.
   */
  stopWatch() {
    if (this._watchId !== null) {
      navigator.geolocation.clearWatch(this._watchId);
      this._watchId = null;
    }
  }
};
