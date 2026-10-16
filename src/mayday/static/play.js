// Phone page: sends intents to /ws/play and renders the views that come back.
// No game rules here: the server decides everything.
import { openSocket } from "/static/net.js";

const $ = (id) => document.getElementById(id);
const screens = ["join-screen", "lobby-screen"];

function show(id) {
  for (const s of screens) $(s).hidden = s !== id;
}

function renderLobby(view) {
  show("lobby-screen");
  $("you-name").textContent = view.you.name;
  $("you-captain").hidden = !view.you.captain;
  const others = view.crew_count - 1;
  const crew = others === 1 ? "1 other sailor" : `${others} other sailors`;
  $("lobby-note").textContent = view.you.captain
    ? `You're the Captain. ${crew} aboard so far. Look up at the TV.`
    : `${crew} aboard. Waiting for the Captain to cast off.`;
}

const socket = openSocket("/ws/play", (view) => {
  if (view.screen === "lobby") renderLobby(view);
});

const prefill = new URLSearchParams(location.search).get("code");
if (prefill) $("code").value = prefill.toUpperCase();

$("join-screen").addEventListener("submit", async (event) => {
  event.preventDefault();
  await socket.ready;
  socket.send({ t: "join", code: $("code").value.trim().toUpperCase(), name: $("name").value.trim() });
});
