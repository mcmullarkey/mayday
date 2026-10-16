// Phone page: sends intents to /ws/play and renders the views that come back.
// No game rules here: the server decides everything.
import { openSocket } from "/static/net.js";
import { flagIcon } from "/static/flags.js";

const $ = (id) => document.getElementById(id);
const screens = ["join-screen", "lobby-screen", "question-screen"];

function show(id) {
  for (const s of screens) $(s).hidden = s !== id;
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
  show("question-screen");
  $("q-number").textContent = view.number;
  $("q-total").textContent = view.total;
  $("choices").replaceChildren(
    ...view.choices.map((choice, i) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `choice choice-${i}`;
      const label = document.createElement("span");
      label.textContent = choice;
      button.append(flagIcon(i), label);
      return button;
    }),
  );
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
