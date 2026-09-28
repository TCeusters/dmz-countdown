// DMZ 2.0 countdown — iPhone widget for the Scriptable app.
// One square tile (Small widget), same look as the page: dark HUD, green digits,
// skull icon. Shows only "24d 14h". Also works as a Lock Screen widget.
//
// Install: App Store → "Scriptable" (free) → + → paste this file → name it "DMZ 2.0".
// Home screen: long-press → + → Scriptable → Small → tap the widget → Script: "DMZ 2.0".
// Lock screen (optional): customise lock screen → add widget → Scriptable → Script: "DMZ 2.0".

const T0 = Date.UTC(2026, 9, 22, 22, 0, 0); // 23 Oct 2026 00:00 Brussels (PS Store unlock)
const PAGE = "https://tceusters.github.io/dmz-countdown/";
const ICON = PAGE + "icons/icon-192.png";

const C = {
  bg: new Color("#070a08"),
  line: new Color("#2c3f31"),
  text: new Color("#d9ded7"),
  muted: new Color("#7f8c82"),
  accent: new Color("#9dff57"),
  amber: new Color("#ffb547"),
  digits: new Color("#f2fff0"),
};

// ---------- time left ----------
const now = Date.now();
const diff = Math.max(0, T0 - now);
const live = diff <= 0;
const totalH = Math.floor(diff / 3600000);
const d = Math.floor(totalH / 24);
const h = totalH - d * 24;
const m = Math.floor((diff % 3600000) / 60000);
const short = live ? "GO GO GO" : (d > 0 ? `${d}d ${h}h` : `${h}h ${m}m`);

const family = config.widgetFamily || "small";
const lock = family.startsWith("accessory");

function mono(stack, text, size, color, bold) {
  const t = stack.addText(text);
  t.font = bold ? Font.boldMonospacedSystemFont(size) : Font.regularMonospacedSystemFont(size);
  t.textColor = color;
  t.lineLimit = 1;
  t.minimumScaleFactor = 0.5;
  return t;
}

const w = new ListWidget();
w.url = PAGE;
w.refreshAfterDate = new Date(now + 15 * 60 * 1000);

// ---------- Lock Screen variants: text only ----------
if (lock) {
  if (family === "accessoryCircular") {
    w.addSpacer();
    mono(w, live ? "GO" : `${d}d`, 20, Color.white(), true).centerAlignText();
    mono(w, live ? "GO" : `${h}h`, 12, Color.white(), false).centerAlignText();
    w.addSpacer();
  } else if (family === "accessoryInline") {
    w.addText("DMZ 2.0 · " + short);
  } else {
    mono(w, "DMZ 2.0 // MW4", 11, Color.white(), false);
    mono(w, short, 22, Color.white(), true);
    mono(w, "23 OCT · 00:00", 11, Color.white(), false);
  }
  if (config.runsInWidget) Script.setWidget(w); else await w.presentAccessoryRectangular();
} else {

// ---------- Home Screen: square HUD tile ----------
const S = 158; // Small widget canvas (points); Medium/Large reuse the same art, left-aligned
const W = family === "small" ? S : (family === "medium" ? 338 : 338);
const H = family === "large" ? 354 : S;

const ctx = new DrawContext();
ctx.size = new Size(W, H);
ctx.opaque = true;
ctx.respectScreenScale = true;
ctx.setFillColor(C.bg);
ctx.fillRect(new Rect(0, 0, W, H));
// faint grid
ctx.setStrokeColor(new Color("#9dff57", 0.07));
ctx.setLineWidth(1);
for (let x = 12; x < W; x += 24) { const p = new Path(); p.move(new Point(x, 0)); p.addLine(new Point(x, H)); ctx.addPath(p); ctx.strokePath(); }
for (let y = 12; y < H; y += 24) { const p = new Path(); p.move(new Point(0, y)); p.addLine(new Point(W, y)); ctx.addPath(p); ctx.strokePath(); }
// radar rings, top right
ctx.setStrokeColor(new Color("#9dff57", 0.13));
for (let r = 26; r < 150; r += 30) { ctx.strokeEllipse(new Rect(W - 34 - r, -34 - r, 2 * r, 2 * r)); }
// HUD corner brackets
ctx.setStrokeColor(C.accent);
ctx.setLineWidth(2);
const mg = 8, L = 14;
for (const [x0, y0, x1, y1, x2, y2] of [
  [mg, mg + L, mg, mg, mg + L, mg],
  [W - mg - L, mg, W - mg, mg, W - mg, mg + L],
  [mg, H - mg - L, mg, H - mg, mg + L, H - mg],
  [W - mg - L, H - mg, W - mg, H - mg, W - mg, H - mg - L],
]) {
  const p = new Path(); p.move(new Point(x0, y0)); p.addLine(new Point(x1, y1)); p.addLine(new Point(x2, y2));
  ctx.addPath(p); ctx.strokePath();
}
w.backgroundImage = ctx.getImage();
w.setPadding(14, 16, 12, 16);

// header: skull icon (cached) + label
const head = w.addStack();
head.centerAlignContent();
let icon = null;
try {
  const fm = FileManager.local();
  const cache = fm.joinPath(fm.cacheDirectory(), "dmz-icon.png");
  if (fm.fileExists(cache)) icon = fm.readImage(cache);
  else { icon = await new Request(ICON).loadImage(); fm.writeImage(cache, icon); }
} catch (e) { icon = null; }
if (icon) {
  const im = head.addImage(icon);
  im.imageSize = new Size(20, 20);
  im.cornerRadius = 4;
  head.addSpacer(6);
} else {
  const dot = head.addText("●"); dot.font = Font.systemFont(7); dot.textColor = C.accent; head.addSpacer(5);
}
mono(head, "DMZ 2.0", 10, C.muted, false);
head.addSpacer();
mono(head, live ? "LIVE" : "T-0", 10, live ? C.accent : C.amber, false);

w.addSpacer();

// the number
const big = mono(w, short, live ? 26 : 36, live ? C.accent : C.digits, true);
big.shadowColor = new Color("#9dff57", 0.55);
big.shadowRadius = 8;
big.shadowOffset = new Point(0, 0);

w.addSpacer(4);
mono(w, live ? "EXFIL WINDOW OPEN" : "UNTIL EXFIL · 23 OCT", 9, C.accent, true);
w.addSpacer();

if (config.runsInWidget) Script.setWidget(w); else await w.presentSmall();
}
Script.complete();
