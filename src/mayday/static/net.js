// Game socket that keeps itself connected (ADR-0009). Hands every server message to
// `onMessage`; calls `onOpen` after each (re)connect so the page can rejoin, and
// `onClose` with the close code. Code 4401 (host key refused) stops reconnecting.
// Shared by the TV and phone pages; knows nothing about screens.
export function openSocket(path, onMessage, { onOpen = () => {}, onClose = () => {} } = {}) {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const url = `${scheme}://${location.host}${path}`;
  let ws = null;
  let retries = 0;
  let timer = null;
  let stopped = false;

  function connect() {
    clearTimeout(timer);
    timer = null;
    ws = new WebSocket(url);
    ws.addEventListener("open", () => {
      retries = 0;
      onOpen();
    });
    ws.addEventListener("message", (event) => onMessage(JSON.parse(event.data)));
    ws.addEventListener("close", (event) => {
      onClose(event.code);
      if (event.code === 4401) {
        stopped = true;
        return;
      }
      timer = setTimeout(connect, Math.min(5000, 500 * 2 ** retries++));
    });
  }

  // Phones throttle timers while locked; reconnect the moment the screen comes back.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && !stopped && ws.readyState === WebSocket.CLOSED) connect();
  });

  connect();
  return {
    isOpen: () => ws.readyState === WebSocket.OPEN,
    send: (intent) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(intent));
    },
  };
}
