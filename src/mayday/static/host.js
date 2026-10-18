// TV page: renders the views the server sends to /ws/host. No game rules here.
import { openSocket } from "/static/net.js";
import { flagIcon } from "/static/flags.js";
import { startCountdown, stopCountdown } from "/static/clock.js";

const $ = (id) => document.getElementById(id);
// Hosted mode (ADR-0008): the TV's address carries ?key=..., which the server checks.
const key = new URLSearchParams(location.search).get("key");
const screens = ["lobby", "rules", "question", "reveal", "standings", "final"];
const ARC_LENGTH = 106.8;

function show(id) {
  for (const s of screens) $(s).hidden = s !== id;
  if (id !== "question" && id !== "rules") stopCountdown();
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
  const qrSrc = `/qr.svg?code=${view.code}${key ? `&key=${encodeURIComponent(key)}` : ""}`;
  if ($("qr").getAttribute("src") !== qrSrc) $("qr").src = qrSrc;
  $("qr").hidden = false;
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

// Slide copy lives here; every number comes from the server's view so it can't drift.
const SLIDES = [
  (v) => ({
    title: "How to <em>play</em>",
    flags: true,
    points: [
      "Each question shows up here and on your phone.",
      "Tap a flag on your phone to lock in your answer. No take-backs.",
    ],
  }),
  (v) => ({
    title: `<em>${v.question_seconds}</em> seconds a question`,
    points: [
      "The clock runs here and on your phone.",
      "If everyone locks in early, we move straight on.",
    ],
  }),
  (v) => ({
    title: "Fast <em>and</em> right wins",
    points: [
      `Right answer: ${v.base_points} points, plus up to ${v.speed_points} more the faster you lock in.`,
      "Wrong or too slow: 0. Nobody ever loses points.",
      `Standings every ${v.standings_every} questions. ${v.total} questions in all.`,
    ],
  }),
];

function renderRules(view) {
  show("rules");
  $("ru-slide").textContent = view.slide;
  $("ru-slides").textContent = view.slides;
  const slide = SLIDES[view.slide - 1](view);
  const title = el("h1");
  title.innerHTML = slide.title; // static copy plus server integers, no player input
  const list = el("ul");
  list.append(...slide.points.map((text) => el("li", "", text)));
  const parts = [title];
  if (slide.flags) {
    const flags = el("div", "flags");
    flags.append(...[0, 1, 2, 3].map((i) => flagIcon(i)));
    parts.push(flags);
  }
  parts.push(list);
  $("ru-body").replaceChildren(...parts);
  startCountdown(view.remaining_ms, view.duration_ms, (_seconds, fraction) => {
    $("ru-bar").style.transform = `scaleX(${fraction})`;
  });
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

function standingRows(standings) {
  return standings.map((s) => {
    const li = el("li", s.rank === 1 ? "row leader" : "row");
    li.append(el("span", "place", s.rank), el("span", "", s.name), el("span", "pts", s.score.toLocaleString()));
    return li;
  });
}

function renderStandings(view) {
  show("standings");
  $("s-number").textContent = view.number;
  $("s-total").textContent = view.total;
  $("s-table").replaceChildren(...standingRows(view.standings));
}

function renderFinal(view) {
  show("final");
  $("f-winners").textContent = view.winners.join(" & ");
  $("f-winners").classList.toggle("shared", view.winners.length > 1);
  $("f-table").replaceChildren(...standingRows(view.standings));
}

const RENDER = { lobby: renderLobby, rules: renderRules, question: renderQuestion, reveal: renderReveal, standings: renderStandings, final: renderFinal };

const hostPath = key ? `/ws/host?key=${encodeURIComponent(key)}` : "/ws/host";

function renderNeedsKey() {
  show("lobby");
  $("qr").hidden = true;
  $("room-code").textContent = "····";
  $("join-url").textContent = key ? "That host key is wrong" : "This TV needs the host key";
  $("status").textContent = "Open this page as /host?key=YOUR-KEY";
}

openSocket(
  hostPath,
  (message) => {
    if (message.t === "refused" && message.reason === "host_key_required") renderNeedsKey();
    if (message.t === "view") RENDER[message.screen]?.(message);
  },
  {
    onClose: (code) => {
      if (code === 4401) renderNeedsKey();
    },
  },
);
