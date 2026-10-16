// TV page: renders the views the server sends to /ws/host. No game rules here.
import { openSocket } from "/static/net.js";

const $ = (id) => document.getElementById(id);

function berth(number, player) {
  const li = document.createElement("li");
  li.className = "berth" + (player ? (player.captain ? " captain" : "") : " empty");
  const no = document.createElement("span");
  no.className = "no";
  no.textContent = String(number).padStart(2, "0");
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = player ? player.name : "open berth";
  li.append(no, name);
  if (player?.captain) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = "Captain";
    li.append(badge);
  }
  return li;
}

function renderLobby(view) {
  $("join-url").textContent = view.join_url.replace(/^https?:\/\//, "");
  $("room-code").textContent = view.code;
  $("berth-count").textContent = `${view.players.length} / ${view.max_players} berths`;
  const slots = Array.from({ length: view.max_players }, (_, i) => berth(i + 1, view.players[i]));
  $("berths").replaceChildren(...slots);
  const captain = view.players.find((p) => p.captain);
  $("status").textContent = captain
    ? `Waiting for ${captain.name} to cast off`
    : "Waiting for crew to climb aboard";
}

openSocket("/ws/host", (view) => {
  if (view.screen === "lobby") renderLobby(view);
});
