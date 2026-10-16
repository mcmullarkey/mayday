// Countdown driven by the server's `remaining_ms` (ADR-0005). Counts down from the moment
// the view arrived; every new view restarts it, so screens never drift from the server.
let frame = null;

export function startCountdown(remainingMs, totalMs, onTick) {
  stopCountdown();
  const endsAt = performance.now() + remainingMs;
  const tick = () => {
    const left = Math.max(0, endsAt - performance.now());
    onTick(Math.ceil(left / 1000), left / totalMs);
    frame = left > 0 ? requestAnimationFrame(tick) : null;
  };
  tick();
}

export function stopCountdown() {
  if (frame !== null) cancelAnimationFrame(frame);
  frame = null;
}
