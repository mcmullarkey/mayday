// Phone page: sends intents to /ws/play and renders the views that come back.
// No game rules here: the server decides everything.
import { openSocket } from "/static/net.js";
import { flagIcon } from "/static/flags.js";
import { startCountdown, stopCountdown } from "/static/clock.js";

const $ = (id) => document.getElementById(id);
const screens = ["join-screen", "lobby-screen", "question-screen", "locked-screen", "reveal-screen"];

function show(id) {
  for (const s of screens) $(s).hidden = s !== id;
}

function choicePill(choices, index) {
  const pill = document.createElement("div");
  pill.className = `pill choice-${index}`;
  const label = document.createElement("span");
  label.textContent = choices[index];
  pill.append(flagIcon(index), label);
  return pill;
}

function runTimer(view, secsId, barId) {
  startCountdown(view.remaining_ms, view.duration_ms, (seconds, fraction) => {
    $(secsId).textContent = `${seconds}s`;
    $(barId).style.transform = `scaleX(${fraction})`;
  });
}

function renderLobby(view) {
  show("lobby-screen");
  $("you-name").textContent = view.you.name;
  $("you-captain").hidden = !view.you.captain;
  const others = view.crew_count - 1;
  const crew = others === 0 ? "Nobody else" : others === 1 ? "1 other sailor" : `${others} other sailors`;
  $("lobby-note").textContent = view.you.captain
    ? `You're the Captain. ${crew} aboard so far. Cast off when everyone's in.`
    : `${crew} aboard. Waiting for the Captain to cast off.`;
  $("cast-off").hidden = !view.you.captain;
  $("cast-off").disabled = false;
}

function renderQuestion(view) {
  if (view.your_choice !== null) return renderLocked(view);
  show("question-screen");
  runTimer(view, "q-secs", "q-bar");
  $("q-number").textContent = view.number;
  $("choices").replaceChildren(
    ...view.choices.map((choice, i) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `choice choice-${i}`;
      const label = document.createElement("span");
      label.textContent = choice;
      button.append(flagIcon(i), label);
      button.addEventListener("click", () => {
        for (const b of $("choices").children) b.disabled = true;
        socket.send({ t: "answer", choice: i });
      });
      return button;
    }),
  );
}

function renderLocked(view) {
  show("locked-screen");
  runTimer(view, "l-secs", "l-bar");
  $("l-number").textContent = view.number;
  $("l-choice").replaceChildren(choicePill(view.choices, view.your_choice));
}

function renderReveal(view) {
  show("reveal-screen");
  stopCountdown();
  $("r-number").textContent = view.number;
  $("r-total").textContent = view.total;
  const missed = view.your_choice === null;
  $("r-verdict").className = `center ${view.correct ? "verdict-right" : "verdict-wrong"}`;
  $("r-headline").textContent = view.correct ? "Right!" : missed ? "Too slow" : "Sunk";
  $("r-detail").textContent = view.correct ? "Nicely navigated." : "The answer was";
  $("r-answer").replaceChildren(...(view.correct ? [] : [choicePill(view.choices, view.answer)]));
}

const REFUSALS = {
  wrong_code: "That code doesn't match the TV. Check the letters and try again.",
  name_taken: "Someone aboard already has that name. Pick another.",
  bad_name: "Names need 1 to 12 characters.",
  room_full: "This ship is full: 8 crew already aboard.",
};

function renderRefusal(reason) {
  $("join-error").textContent = REFUSALS[reason] ?? "Couldn't join. Try again.";
  $("join-error").hidden = false;
  $("join").disabled = false;
}

const socket = openSocket("/ws/play", (message) => {
  if (message.t === "refused") renderRefusal(message.reason);
  if (message.t === "view" && message.screen === "lobby") renderLobby(message);
  if (message.t === "view" && message.screen === "question") renderQuestion(message);
  if (message.t === "view" && message.screen === "reveal") renderReveal(message);
});

$("cast-off").addEventListener("click", () => {
  $("cast-off").disabled = true;
  socket.send({ t: "start" });
});

const prefill = new URLSearchParams(location.search).get("code");
if (prefill) $("code").value = prefill.toUpperCase();

$("join-screen").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("join-error").hidden = true;
  $("join").disabled = true;
  await socket.ready;
  socket.send({ t: "join", code: $("code").value.trim().toUpperCase(), name: $("name").value.trim() });
});
