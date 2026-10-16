// Opens the game socket for this page and hands every server message to `onMessage`.
// Shared by the TV and phone pages; knows nothing about screens.
export function openSocket(path, onMessage) {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${scheme}://${location.host}${path}`);
  ws.addEventListener("message", (event) => onMessage(JSON.parse(event.data)));
  return {
    send: (intent) => ws.send(JSON.stringify(intent)),
    ready: new Promise((resolve) => ws.addEventListener("open", resolve, { once: true })),
  };
}
