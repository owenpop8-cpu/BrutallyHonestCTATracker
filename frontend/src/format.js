export function formatClock(arrivalTime) {
  return arrivalTime?.split(" ")[1] ?? "";
}

export function formatSlack(slack) {
  if (slack >= 0) return `${slack} min to spare`;
  return `${Math.abs(slack)} min late`;
}