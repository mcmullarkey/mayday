// Opens the game socket for this page and hands every view to `onView`.
// Shared by the TV and phone pages; knows nothing about screens.
export function openSocket(path, onView) {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${scheme}://${location.host}${path}`);
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.t === "view") onView(message);
  });
  return {
    send: (intent) => ws.send(JSON.stringify(intent)),
    ready: new Promise((resolve) => ws.addEventListener("open", resolve, { once: true })),
  };
}
