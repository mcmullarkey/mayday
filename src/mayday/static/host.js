// TV page: renders the views the server sends to /ws/host. No game rules here.
import { openSocket } from "/static/net.js";
import { flagIcon } from "/static/flags.js";
import { startCountdown, stopCountdown } from "/static/clock.js";

const $ = (id) => document.getElementById(id);
const screens = ["lobby", "question", "reveal"];
const ARC_LENGTH = 106.8;

function show(id) {
  for (const s of screens) $(s).hidden = s !== id;
  if (id !== "question") stopCountdown();
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

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
  show("lobby");
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

function renderQuestion(view) {
  show("question");
  $("q-number").textContent = view.number;
  $("q-total").textContent = view.total;
  $("q-category").textContent = view.category;
  $("q-prompt").textContent = view.prompt;
  $("q-answers").replaceChildren(
    ...view.choices.map((choice, i) => {
      const li = el("li", "answer");
      li.append(flagIcon(i), el("span", "", choice));
      return li;
    }),
  );
  startCountdown(view.remaining_ms, view.duration_ms, (seconds, fraction) => {
    $("q-seconds").textContent = seconds;
    $("q-arc").style.strokeDasharray = `${ARC_LENGTH * fraction} ${ARC_LENGTH}`;
  });
  $("q-crew").replaceChildren(
    ...view.players.map((p) => {
      const li = el("li", p.answered ? "mate in" : "mate");
      li.append(el("span", "pip"), el("span", "", p.name));
      return li;
    }),
  );
}

function renderReveal(view) {
  show("reveal");
  $("r-number").textContent = view.number;
  $("r-total").textContent = view.total;
  $("r-prompt").textContent = view.prompt;
  $("r-fact").textContent = view.fact;
  const gained = Object.fromEntries(view.scores.map((s) => [s.name, s.gained]));
  $("r-answers").replaceChildren(
    ...view.choices.map((choice, i) => {
      const li = el("li", i === view.answer ? "answer right" : "answer wrong");
      const who = el("span", "who");
      who.append(...view.picks[i].map((name) => el("span", "", gained[name] ? `${name} +${gained[name]}` : name)));
      li.append(flagIcon(i), el("span", "", choice), who);
      return li;
    }),
  );
}

const RENDER = { lobby: renderLobby, question: renderQuestion, reveal: renderReveal };

openSocket("/ws/host", (message) => {
  if (message.t === "view") RENDER[message.screen]?.(message);
});
