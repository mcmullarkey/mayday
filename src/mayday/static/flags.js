// Signal-flag icons for answer choices A–D (index 0–3). Shared by TV and phone.
const NS = "http://www.w3.org/2000/svg";
export const FLAG_LETTERS = ["a", "b", "c", "d"];

export function flagIcon(index, className = "flag") {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", className);
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(NS, "use");
  use.setAttribute("href", `/static/flags.svg#flag-${FLAG_LETTERS[index]}`);
  svg.append(use);
  return svg;
}
