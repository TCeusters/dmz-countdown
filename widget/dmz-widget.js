// DMZ 2.0 countdown — iPhone home-screen widget for the Scriptable app.
// Clock only (no price watch), same look as the web page: dark HUD, green digits.
//
// Install: App Store → "Scriptable" (free) → + → paste this file → name it "DMZ 2.0".
// Home screen: long-press → + → Scriptable → pick Small or Medium → tap the widget
// → Script: "DMZ 2.0". It refreshes itself every few minutes (iOS decides exactly when).

const T0 = Date.UTC(2026, 9, 22, 22, 0, 0); // 23 Oct 2026 00:00 Brussels (PS Store unlock)

const C = {
  bg: new Color("#070a08"),
  panel: new Color("#0d1510"),
  line: new Color("#2c3f31"),
  text: new Color("#d9ded7"),
  muted: new Color("#7f8c82"),
  accent: new Color("#9dff57"),
  amber: new Color("#ffb547"),
  digits: new Color("#f2fff0"),
};

const family = config.widgetFamily || "medium";
const small = family === "small";
const W = small ? 158 : 338;
const H = 158;

// ---------- background: grid + HUD corner brackets ----------
const ctx = new DrawContext();
ctx.size = new Size(W, H);
ctx.opaque = true;
ctx.respectScreenScale = true;
ctx.setFillColor(C.bg);
ctx.fillRect(new Rect(0, 0, W, H));
ctx.setStrokeColor(new Color("#9dff57", 0.07));
ctx.setLineWidth(1);
for (let x = 12; x < W; x += 24) { const p = new Path(); p.move(new Point(x, 0)); p.addLine(new Point(x, H)); ctx.addPath(p); ctx.strokePath(); }
for (let y = 12; y < H; y += 24) { const p = new Path(); p.move(new Point(0, y)); p.addLine(new Point(W, y)); ctx.addPath(p); ctx.strokePath(); }
// radar rings, top right
ctx.setStrokeColor(new Color("#9dff57", 0.12));
for (let r = 30; r < 170; r += 34) { ctx.strokeEllipse(new Rect(W - 40 - r, -40 - r, 2 * r, 2 * r)); }
// corner brackets
ctx.setStrokeColor(C.accent);
ctx.setLineWidth(2);
const m = 8, L = 16;
const corners = [
  [[m, m + L], [m, m], [m + L, m]],
  [[W - m - L, m], [W - m, m], [W - m, m + L]],
  [[m, H - m - L], [m, H - m], [m + L, H - m]],
  [[W - m - L, H - m], [W - m, H - m], [W - m, H - m - L]],
];
for (const pts of corners) {
  const p = new Path();
  p.move(new Point(pts[0][0], pts[0][1]));
  p.addLine(new Point(pts[1][0], pts[1][1]));
  p.addLine(new Point(pts[2][0], pts[2][1]));
  ctx.addPath(p);
  ctx.strokePath();
}

// ---------- widget ----------
const w = new ListWidget();
w.backgroundImage = ctx.getImage();
w.setPadding(16, 18, 14, 18);
w.url = "https://tceusters.github.io/dmz-countdown/";
w.refreshAfterDate = new Date(Date.now() + 10 * 60 * 1000);

const now = Date.now();
let diff = Math.max(0, T0 - now);
const live = diff <= 0;
let s = Math.floor(diff / 1000);
const d = Math.floor(s / 86400); s -= d * 86400;
const h = Math.floor(s / 3600); s -= h * 3600;
const mi = Math.floor(s / 60);
const pad = (n) => (n < 10 ? "0" : "") + n;

function mono(stack, text, size, color, bold) {
  const t = stack.addText(text);
  t.font = bold ? Font.boldMonospacedSystemFont(size) : Font.regularMonospacedSystemFont(size);
  t.textColor = color;
  t.lineLimit = 1;
  t.minimumScaleFactor = 0.6;
  return t;
}

// header
const head = w.addStack();
head.centerAlignContent();
const dot = head.addText("●");
dot.font = Font.systemFont(7);
dot.textColor = C.accent;
head.addSpacer(5);
mono(head, small ? "DMZ 2.0" : "DMZ 2.0 // MW4", 10, C.muted, false);
head.addSpacer();
mono(head, live ? "DEPLOYED" : "T-0 23 OCT", 10, live ? C.accent : C.amber, false);

w.addSpacer(small ? 6 : 8);
mono(w, live ? "EXFIL WINDOW IS OPEN" : "EXFIL WINDOW OPENS IN", small ? 8 : 9, C.accent, true);
w.addSpacer(small ? 4 : 6);

if (live) {
  mono(w, "GO GO GO", small ? 30 : 44, C.accent, true);
} else if (small) {
  const row = w.addStack();
  row.bottomAlignContent();
  mono(row, String(d), 44, C.digits, true);
  row.addSpacer(6);
  const col = row.addStack();
  col.layoutVertically();
  mono(col, "DAYS", 9, C.muted, false);
  mono(col, pad(h) + ":" + pad(mi), 16, C.digits, true);
  col.addSpacer(4);
} else {
  const row = w.addStack();
  row.centerAlignContent();
  const unit = (val, cap) => {
    const c = row.addStack();
    c.layoutVertically();
    c.centerAlignContent();
    mono(c, val, 40, C.digits, true);
    mono(c, cap, 8, C.muted, false);
  };
  const colon = () => { row.addSpacer(8); const t = mono(row, ":", 30, C.line, true); row.addSpacer(8); };
  unit(d < 100 ? pad(d) : String(d), " DAYS");
  colon();
  unit(pad(h), "HOURS");
  colon();
  unit(pad(mi), " MIN ");
  row.addSpacer();
}

w.addSpacer();
mono(w, small ? "23 OCT · 00:00" : "FRI 23 OCT 2026 · 00:00 BRUSSELS · DMZ DAY ONE", small ? 8 : 9, C.muted, false);

if (config.runsInWidget) {
  Script.setWidget(w);
} else {
  await (small ? w.presentSmall() : w.presentMedium());
}
Script.complete();
