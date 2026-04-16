// timer.js — Countdown timer with SVG ring

window.CountdownTimer = {
  interval: null,

  start(totalSeconds, onTick, onExpire) {
    clearInterval(this.interval);
    let remaining = totalSeconds;
    onTick(remaining, totalSeconds);
    this.interval = setInterval(() => {
      remaining--;
      onTick(remaining, totalSeconds);
      if (remaining <= 0) {
        clearInterval(this.interval);
        onExpire && onExpire();
      }
    }, 1000);
  },

  stop() { clearInterval(this.interval); },

  render(remaining, total, ringEl, textEl) {
    const r = 46;
    const circ = 2 * Math.PI * r;
    const pct = remaining / total;
    const offset = circ * (1 - pct);
    if (ringEl) {
      ringEl.style.strokeDasharray = circ;
      ringEl.style.strokeDashoffset = offset;
      // Color transition: green → yellow → red
      if (pct > 0.5) ringEl.style.stroke = 'var(--accent)';
      else if (pct > 0.25) ringEl.style.stroke = 'var(--warning)';
      else ringEl.style.stroke = 'var(--danger)';
    }
    if (textEl) {
      const m = Math.floor(remaining / 60);
      const s = remaining % 60;
      textEl.textContent = m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${remaining}s`;
    }
  }
};
