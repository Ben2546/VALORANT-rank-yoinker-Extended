if True:
  """Protected HTTP server for embedded dashboard resources."""

  import json
  import threading
  from http.server import HTTPServer, SimpleHTTPRequestHandler
  import io
  import sys
  import os
  from pathlib import Path


def get_runtime_image_cache_dir():
  """Return persistent directory used for local dashboard image cache."""
  return Path(os.getenv("APPDATA") or ".") / "vry" / "image_cache"


# Embedded CSS - compiled into the executable
DASHBOARD_CSS = """:root {
  color-scheme: dark;
  --bg: #06080d;
  --panel: rgba(15, 22, 35, 0.92);
  --panel-2: rgba(24, 35, 56, 0.9);
  --border: rgba(255, 255, 255, 0.12);
  --text: #f5f7fb;
  --text-muted: #8f99af;
  --accent: #ff4655;
  --accent-2: #0f9d8f;
  --shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Inter", sans-serif;
  background: radial-gradient(circle at top, #131b29 0%, var(--bg) 50%, #04070c 100%);
  color: var(--text);
  min-height: 100vh;
}

img { max-width: 100%; display: block; }

.app-shell {
  width: min(1400px, calc(100% - 2rem));
  margin: 0 auto;
  padding: 2rem 0 3rem;
}

.hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  padding: 1.5rem;
  border: 1px solid var(--border);
  border-radius: 24px;
  background: var(--panel);
  box-shadow: var(--shadow);
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.25em;
  color: var(--accent-2);
  font-weight: 700;
  margin: 0 0 0.6rem;
}

h1 {
  margin: 0 0 0.6rem;
  font-size: clamp(1.7rem, 2.8vw, 2.8rem);
}

.subtitle {
  margin: 0;
  color: var(--text-muted);
  max-width: 720px;
}

.status-card {
  min-width: auto;
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: 0;
  display: flex;
  align-items: center;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: rgba(255, 70, 85, 0.16);
  color: #ff8a95;
  font-weight: 700;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  margin-bottom: 0.55rem;
}

.status-meta { color: var(--text-muted); font-size: 0.95rem; }

.status-pill,
.status-meta {
  display: none;
}

.refresh-feed-btn {
  margin-top: 0;
  width: auto;
  min-width: 140px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.08);
  color: var(--text);
  border-radius: 10px;
  padding: 0.55rem 0.75rem;
  font-weight: 700;
  cursor: pointer;
}

.refresh-feed-btn:hover {
  background: rgba(255, 255, 255, 0.14);
}

.player-match-section {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.6rem 0 0.4rem 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin-top: 0.4rem;
}

.player-match-dropdown {
  display: flex;
  width: 100%;
}

.match-select {
  flex: 1;
  padding: 0.35rem 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  font-family: "Inter", sans-serif;
  font-size: 0.75rem;
  transition: all 0.18s ease;
}

.match-select:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.25);
  color: var(--text);
}

.match-select:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.12);
  color: var(--text);
}

.match-select option {
  background: var(--panel-2);
  color: var(--text);
  padding: 0.5rem;
  font-size: 0.85rem;
}

.feed-section { margin-top: 1.4rem; }
.section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.section-head h2 { margin: 0; }
.section-head p { margin: 0; color: var(--text-muted); }

.players-grid {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.team-averages-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  align-items: stretch;
}

.team-average-card {
  padding: 0.85rem 0.95rem;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.08);
  background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.025));
  min-width: 0;
}

.team-average-ally {
  border-left: 3px solid rgba(69, 214, 141, 0.5);
}

.team-average-enemy {
  border-left: 3px solid rgba(238, 77, 77, 0.5);
}

.team-average-title {
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-bottom: 0.55rem;
}

.team-average-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) repeat(3, minmax(0, 0.75fr));
  gap: 0.65rem;
  align-items: center;
}

.team-average-rank,
.team-average-stat {
  min-width: 0;
}

.team-average-rank-label,
.team-average-stat span {
  display: block;
  color: var(--text-muted);
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 0.18rem;
}

.team-average-rank-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.team-average-rank-value strong,
.team-average-stat strong {
  font-size: 0.98rem;
  line-height: 1.15;
}

.team-average-rank-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
  flex-shrink: 0;
}

.team-section {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.9rem;
  border-radius: 18px;
  border: 1px solid var(--border);
  background: rgba(255,255,255,0.03);
  min-width: 0;
}

.team-ally { border-left: 3px solid rgba(69, 214, 141, 0.5); }
.team-enemy { border-left: 3px solid rgba(238, 77, 77, 0.5); }
.team-other { border-left: 3px solid rgba(255,255,255,0.16); }

.team-header {
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  font-size: 0.78rem;
}

.team-rows {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.player-row {
  display: grid;
  grid-template-columns: 112px minmax(180px, 1fr) minmax(102px, 0.62fr) minmax(300px, 1.45fr) minmax(255px, 1.2fr) 92px minmax(180px, 0.95fr);
  gap: 0.6rem;
  align-items: center;
  padding: 0.7rem;
  border-radius: 14px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
}

.row-cell { min-width: 0; }
.row-agent, .row-player, .row-kda, .row-rank, .row-stats, .row-meta, .row-skins { display: flex; align-items: center; }
.row-agent { gap: 0.55rem; }
.row-player { padding-left: 0.3rem; }
.hotstats-star { color: #ffd34d; font-size: 1.45rem; line-height: 1; font-weight: 800; display: inline-block; transform: translateY(-1px); text-shadow: 0 0 10px rgba(255, 211, 77, 0.7), 0 0 20px rgba(255, 211, 77, 0.4); }
.agent-mini { width: 48px; height: 48px; border-radius: 10px; object-fit: cover; flex-shrink: 0; }
.row-label { display: block; color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.12rem; }
.row-agent strong, .row-player strong, .row-kda strong, .row-rank strong, .row-stats strong, .row-meta strong, .row-skins strong { font-size: 0.94rem; line-height: 1.25; }
.player-name-block { display: flex; flex-direction: column; gap: 0.12rem; min-width: 0; }
.player-name-block strong { font-size: 1.08rem; line-height: 1.2; }
.player-name-block span { color: var(--text-muted); font-size: 0.82rem; }
.played-with-inline { color: #8bf2c0 !important; font-size: 0.7rem !important; letter-spacing: 0.02em; }
.row-kda { justify-content: flex-start; }
.kda-stack { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.08rem; min-width: 132px; margin-left: -4.15rem; padding: 0.28rem 0.6rem; border-radius: 10px; background: rgba(255,255,255,0.05); }
.kda-primary { font-size: 1rem; color: #e9eefc; white-space: nowrap; }
.kda-ratio { font-size: 0.78rem; color: var(--text-muted); }
.metric-footnote { color: #7f8aa3; font-size: 0.58rem; letter-spacing: 0.04em; text-transform: lowercase; }
.metric-footnote-inline { color: #7f8aa3; font-size: 0.58rem; letter-spacing: 0.04em; text-transform: lowercase; white-space: nowrap; }
.metric-footnote-last-game { margin-left: 0; }
.private-cell { background: rgba(255,255,255,0.03); border-radius: 10px; padding: 0.45rem 0.55rem; }
.private-note { color: var(--text-muted); font-size: 0.72rem; margin-top: 0.25rem; }
.row-rank { width: 100%; }
.rank-stack { width: 100%; display: flex; flex-wrap: nowrap; gap: 0.55rem; align-items: center; justify-content: flex-start; margin-left: -0.45rem; }
.rank-badge-row { flex: 1 1 11.25rem; min-width: 11.25rem; display: flex; align-items: center; gap: 0.6rem; min-height: 72px; padding: 0.5rem 0.85rem; border-radius: 12px; background: rgba(255,255,255,0.06); }
.peak-row { flex: 1 1 12.75rem; min-width: 12.75rem; background: rgba(255,255,255,0.035); }
.rank-badge { width: 38px; height: 38px; object-fit: contain; flex-shrink: 0; }
.rank-text-stack { display: flex; flex-direction: column; gap: 0.04rem; min-width: 0; }
.rank-primary { color: #ffffff; font-size: 1.12rem; display: inline-flex; align-items: baseline; gap: 0.35rem; white-space: nowrap; }
.rank-main { white-space: nowrap; }
.rank-current-rr { white-space: nowrap; font-size: 0.96em; }
.rank-secondary { color: var(--text-muted); font-size: 1rem; }
.rr-delta-pill { display: inline-flex; align-items: baseline; gap: 0.24rem; margin-top: 0.1rem; font-size: 0.88rem; font-weight: 700; white-space: nowrap; }
.row-stats { gap: 0.35rem; flex-wrap: wrap; margin-left: 3.5rem; }
.stat-primary-row { width: 100%; display: flex; gap: 0.35rem; }
.stat-primary-row .stat-line-large { flex: 1; min-width: 0; }
.stat-line { display: flex; justify-content: space-between; align-items: center; gap: 0.4rem; min-width: 70px; padding: 0.32rem 0.4rem; border-radius: 10px; background: rgba(255,255,255,0.05); }
.stat-line-large { min-width: 86px; padding: 0.42rem 0.5rem; }
.stat-line span { color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; }
.stat-line strong { font-size: 0.86rem; }
.stat-line-large strong { font-size: 1.04rem; }
.stat-value-stack { display: flex; flex-direction: column; align-items: flex-end; }
.stat-value-inline { display: flex; align-items: baseline; justify-content: flex-end; gap: 0.28rem; }
.stat-line .metric-footnote,
.stat-line .metric-footnote-inline { color: #7f8aa3; font-size: 0.58rem; letter-spacing: 0.04em; text-transform: lowercase; white-space: nowrap; }
.private-fill { background: rgba(8,12,20,0.8); border-radius: 10px; min-height: 100%; }
.private-stats { width: 100%; min-height: 52px; border-radius: 10px; background: linear-gradient(90px, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); }
.row-meta { flex-direction: column; gap: 0.35rem; align-items: flex-start; }
.pill { padding: 0.28rem 0.5rem; border-radius: 999px; background: rgba(255,255,255,0.08); color: var(--text-muted); font-size: 0.72rem; text-align: center; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pill-played-with { background: rgba(69, 214, 141, 0.16); color: #8bf2c0; }
.pill-history { background: rgba(78, 124, 255, 0.16); color: #b9d3ff; max-width: 230px; }
.pill-streak { max-width: 230px; }
.pill-streak-win { background: rgba(69, 214, 141, 0.16); color: #8bf2c0; }
.pill-streak-loss { background: rgba(238, 77, 77, 0.18); color: #ff9f9f; }
.metric-footnote-pill { display: block; margin-top: 0.12rem; font-size: 0.56rem; color: rgba(220, 228, 245, 0.72); }
.metric-footnote-pill-inline { color: rgba(220, 228, 245, 0.72); font-size: 0.56rem; }
.streak-win-count { color: #41f085; font-weight: 700; }
.streak-loss-count { color: #ff6b6b; font-weight: 700; }
.stat-history-pill {
  width: 100%;
  max-width: none;
  text-align: left;
  margin-top: 0.1rem;
}
.recent-outcomes-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.2rem;
  margin-top: 0.14rem;
  padding-left: 0.04rem;
  min-height: 10px;
}
.recent-outcome-square {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
  flex: 0 0 auto;
}
.recent-outcome-win { background: #41f085; box-shadow: 0 0 0 1px rgba(65, 240, 133, 0.2); }
.recent-outcome-loss { background: #ff6b6b; box-shadow: 0 0 0 1px rgba(255, 107, 107, 0.2); }
.skin-inline { display: flex; flex-direction: column; gap: 0.25rem; min-width: 0; }
.skin-chip { display: flex; align-items: center; gap: 0.45rem; font-size: 0.82rem; color: var(--text-muted); }
.skin-chip img {
  width: 120px;
  height: 50px;
  object-fit: contain;
  object-position: center;
  border-radius: 8px;
  padding: 0.2rem;
  background: rgba(255, 255, 255, 0.06);
}
.skin-empty { color: var(--text-muted); font-size: 0.72rem; }
.empty-state { padding: 2rem; border: 1px dashed var(--border); border-radius: 20px; text-align: center; color: var(--text-muted); }

.player-row { cursor: pointer; transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease; }
.player-row:hover, .player-row:focus-visible { transform: translateY(-1px); border-color: rgba(255,255,255,0.18); background: rgba(255,255,255,0.06); outline: none; }
.player-row-self { border-color: rgba(129, 246, 173, 0.65); background: rgba(72, 201, 120, 0.16); }
.player-row-played-before { border-color: rgba(255, 220, 112, 0.7); background: rgba(255, 213, 79, 0.16); }
.player-row-self.player-row-played-before { border-color: rgba(129, 246, 173, 0.65); background: rgba(72, 201, 120, 0.16); }
.player-row-hotstats { border-color: rgba(255, 220, 112, 0.7); background: rgba(255, 213, 79, 0.16); }

.player-modal {
  position: fixed;
  inset: 0;
  background: rgba(3, 6, 12, 0.82);
  backdrop-filter: blur(8px);
  display: none;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
  z-index: 1000;
}

.player-modal.visible { display: flex; }
body.modal-open { overflow: hidden; }

.modal-card {
  position: relative;
  width: min(75vw, 1600px);
  height: 75vh;
  max-height: 75vh;
  overflow: hidden;
  border-radius: 24px;
  background: var(--panel);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  padding: 1.4rem;
}

.modal-close {
  position: absolute;
  top: 0.8rem;
  right: 0.8rem;
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  color: var(--text);
  font-size: 1.35rem;
  cursor: pointer;
}

.modal-body { display: flex; flex-direction: column; gap: 1rem; height: 100%; max-height: calc(75vh - 3rem); overflow: hidden; }
.modal-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
.modal-eyebrow { margin: 0 0 0.25rem; color: var(--accent-2); text-transform: uppercase; letter-spacing: 0.18em; font-size: 0.72rem; font-weight: 700; }
.modal-header h3 { margin: 0; font-size: 1.45rem; }
.modal-tag { margin: 0.2rem 0 0; color: var(--text-muted); }
.modal-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); grid-template-rows: repeat(2, minmax(0, 1fr)); gap: 1rem; overflow: hidden; flex: 1; min-height: 0; }
.modal-panel { padding: 1rem; border-radius: 18px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); max-height: calc((75vh - 6rem) / 2); overflow: auto; }
.modal-panel-skins { grid-row: 1 / span 2; max-height: none; }
.modal-section-title { margin-bottom: 0.7rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-muted); font-size: 0.78rem; }
.modal-namecard-wrap { display: flex; justify-content: center; align-items: center; }
.modal-namecard { width: min(100%, 420px); border-radius: 16px; object-fit: contain; max-height: 320px; margin: 0 auto; }
.modal-asset-list { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.7rem; }
.modal-weapon-card { display: flex; flex-direction: column; gap: 0.55rem; padding: 0.75rem; border-radius: 16px; background: rgba(255,255,255,0.05); min-height: 100%; }
.modal-weapon-art { position: relative; display: flex; justify-content: center; align-items: center; min-height: 150px; padding: 0.6rem; border-radius: 12px; background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02)); overflow: hidden; }
.modal-weapon-image { width: 100%; max-width: 220px; height: 120px; object-fit: contain; }
.modal-buddy-badge { position: absolute; right: 0.45rem; bottom: 0.45rem; width: 40px; height: 40px; object-fit: cover; border-radius: 10px; border: 2px solid rgba(255,255,255,0.18); background: rgba(8,12,20,0.7); }
.modal-weapon-meta strong { display: block; font-size: 0.9rem; }
.modal-weapon-meta span { color: var(--text-muted); font-size: 0.8rem; }
.modal-empty { padding: 0.7rem 0.8rem; border-radius: 12px; background: rgba(255,255,255,0.04); color: var(--text-muted); font-size: 0.9rem; }

@media (max-width: 1200px) {
  .player-row { grid-template-columns: 96px minmax(140px, 1fr) minmax(110px, 0.75fr) minmax(240px, 1.3fr) minmax(190px, 0.95fr) 82px minmax(140px, 0.9fr); }
}

@media (max-width: 980px) {
  .player-row { grid-template-columns: 1fr; align-items: flex-start; }
  .row-agent, .row-player, .row-kda, .row-rank, .row-stats, .row-meta, .row-skins { width: 100%; }
  .row-stats, .row-meta { margin-left: 0; }
  .rank-stack { flex-wrap: wrap; }
  .rank-badge-row { flex: 1 1 100%; }
  .row-stats { flex-direction: column; align-items: stretch; }
  .stat-primary-row { flex-direction: column; }
  .private-stats { min-height: 34px; }
  .team-averages-strip { grid-template-columns: 1fr; }
  .team-average-grid { grid-template-columns: 1fr 1fr; }
  .team-average-rank { grid-column: 1 / -1; }
  .modal-header { flex-direction: column; }
  .modal-grid { grid-template-columns: 1fr; }
  .modal-panel-skins { grid-row: auto; max-height: calc((75vh - 6rem) / 2); }
}

.ui-component-cta {
  flex-direction: column;
  row-gap: var(--ui-gap-cta);
}

.ui-component-button {
  border: .0625rem solid var(--ui-color-brand);
  border-radius: var(--ui-radius-button);
  display: block;
  font-weight: 700;
  line-height: 1;
  text-align: center;
  text-decoration: none;
}

.ui-component-button-primary {
  background-color: var(--ui-color-brand);
  color: var(--ui-color-typography-button);
}

.ui-component-button-secondary {
  background-color: var(--ui-color-background-secondary);
  color: var(--ui-color-brand);
}

.ui-component-button-big,
.ui-component-button-normal { padding: .75rem 1rem .875rem; }

.ui-component-button-big { width: 100%; }

.ui-component-button-normal {
  width: -moz-fit-content;
  width: fit-content;
}

input[name="toggle"] { display: none; }

.ui-component-toggle {
  background-color: var(--ui-color-background-tertiary);
  border-radius: var(--ui-radius-button);
  color: var(--ui-color-typography-note);
  font-size: var(--ui-typography-s);
  font-weight: 700;
  line-height: 1;
  margin: var(--ui-gap-pricing) auto .5rem;
  padding: .25rem;
  width: max-content;
}

.ui-component-toggle--label {
  border-radius: var(--ui-radius-button);
  cursor: pointer;
  padding: .5rem .625rem;
}

#ui-component-toggle__monthly:checked ~
div label[for=ui-component-toggle__monthly],
#ui-component-toggle__yearly:checked ~
div label[for=ui-component-toggle__yearly] {
  background-color: var(--ui-color-background-primary);
  color: var(--ui-color-typography-body);
}

.ui-component-card {
  border: .0625rem solid var(--ui-color-border);
  border-radius: var(--ui-radius-card);
  overflow: hidden;
  width: 100%;
}

.ui-component-list {
  grid-template-columns: 1fr;
  row-gap: .75rem;
}

.ui-component-list--item {
  background-position: left center;
  background-repeat: no-repeat;
  background-size: 1.125rem;
  list-style: none;
  padding-left: 1.875rem;
}

.ui-component-list--item-check {
  background-image: url(https://res.cloudinary.com/uisual/image/upload/assets/icons/check.svg);
}

.ui-component-list--item-cross {
  background-image: url(https://res.cloudinary.com/uisual/image/upload/assets/icons/cross.svg);
}

.zoom {
  transition: transform .2s;
  margin: 0 auto;
}

.zoom:hover {
  transform: scale(1.25);
}

.white-box {
  background-color: white;
  border-radius: 15px;
  width: -moz-fit-content;
  width: fit-content;
  padding: 5px;
  box-sizing: border-box;
}

.ui-section-header {
  padding-bottom: 1.25rem;
  padding-top: 1.25rem;
}

.ui-section-header__layout {
  justify-content: space-between;
}

.ui-section-header--logo {
  z-index: 1;
}

#ui-section-header--menu-id { display: none; }

.ui-section-header--menu-icon {
  cursor: pointer;
  display: block;
  height: 1.125rem;
  padding-bottom: .25rem;
  padding-top: .25rem;
  position: relative;
  width: 1.125rem;
  z-index: 1;
}

.ui-section-header--menu-icon::before,
.ui-section-header--menu-icon::after {
  background: var(--ui-color-brand);
  content: "";
  height: .125rem;
  left: 0;
  position: absolute;
  transition: all 250ms cubic-bezier(.785, .135, .15, .86);
  width: 1.125rem;
}

.ui-section-header--menu-icon::before { top: .3125rem; }

.ui-section-header--menu-icon::after { top: .6875rem; }

#ui-section-header--menu-id:checked ~
.ui-section-header--menu-icon::before {
  transform: translateY(3px) rotate(135deg);
}

#ui-section-header--menu-id:checked ~
.ui-section-header--menu-icon::after {
  transform: translateY(-3px) rotate(45deg);
}

.ui-section-header--nav {
  background-color: var(--ui-color-background-primary);
  box-shadow: 0 .5rem 1rem rgba(0,0,0,.05);
  flex-direction: column;
  gap: var(--ui-gap-header);
  left: 0;
  opacity: 0;
  padding: 7.375rem var(--ui-layout-container) 5rem;
  position: absolute;
  right: 0;
  top: -1rem;
  transition: all 250ms cubic-bezier(.785, .135, .15, .86);
  visibility: hidden;
}

#ui-section-header--menu-id:checked ~
.ui-section-header--nav {
  opacity: 1;
  top: 0;
  visibility: visible;
}

.ui-section-header--nav-link {
  font-size: var(--ui-typography-h3);
  padding: .5rem;
  text-decoration: none;
}

.ui-section-hero {
  padding-bottom: 5rem;
  padding-top: 5rem;
  text-align: center;
}

.ui-section-hero__layout { row-gap: var(--ui-gap-hero); }

.ui-section-customer__layout {
  flex-direction: column;
  row-gap: var(--ui-gap-customer);
}

.ui-section-customer--logo {
  height: 1.5rem;
  width: auto;
}

.ui-section-customer--logo-str { height: 1.75rem; }

.ui-section-customer--logo-bhn { height: 1.375rem; }

.ui-section-feature {
  padding-bottom: 5rem;
  padding-top: 5rem;
}

.ui-section-feature__layout { row-gap: var(--ui-gap-feature); }

.ui-section-feature__layout:first-of-type div {
  grid-row-start: 1;
}

.ui-section-feature__layout:last-of-type { margin-top: 5rem; }

.ui-section-content {
  padding-bottom: 2em;
  padding-top: 2rem;
  text-align: center;
}

.ui-section-content--image {
  margin-bottom: var(--ui-gap-content);
  margin-top: var(--ui-gap-content);
}

.ui-section-content--feature { row-gap: var(--ui-gap-content); }

.ui-section-content--icon { margin-bottom: 1rem; }

.ui-section-testimonial {
  padding-bottom: 5rem;
  padding-top: 5rem;
  text-align: center;
}

.ui-section-testimonial__layout {
  row-gap: var(--ui-gap-testimonial);
}

.ui-section-testimonial--avatar {
  border-radius: var(--ui-radius-avatar);
  margin-top: 1px;
  height: 5rem;
  width: 5rem;
}

.ui-section-testimonial--quote {
  margin: 1rem;
}

.ui-section-testimonial--author { line-height: 1.25; }

.ui-section-close {
  background-color: var(--ui-color-background-secondary);
  padding-bottom: 5rem;
  padding-top: 5rem;
  text-align: center;
}

.ui-section-footer {
  padding-bottom: 1.25rem;
  padding-top: 1.25rem;
}

.ui-section-footer__layout {
  column-gap: var(--ui-layout-gutter);
}

.ui-section-footer--copyright {
  margin-bottom: 0;
  margin-right: auto;
}

@media screen and (min-width: 48rem) {
  :root {
    --ui-typography-h1: 2.1875rem;
    --ui-typography-h2: 1.75rem;
    --ui-typography-p : 1.125rem;
    --ui-typography-s : .875rem;
    --ui-typography-margin-body: 1.25rem;
    --ui-layout-container: 4.25rem;
    --ui-layout-gutter   : 1.5rem;
    --ui-gap-header: 1.5rem;
    --ui-gap-card  : 1.5rem;
  }

  .ui-image-half-left { padding-right: var(--ui-layout-gutter); }
  .ui-image-half-right { padding-left: var(--ui-layout-gutter); }
  .ui-image {
    border-radius: 8px;
    animation: up-down 2s ease-in-out infinite alternate-reverse both;
  }
  @keyframes up-down {
    0% { transform: translateY(15px); }
    100% { transform: translateY(-15px); }
  }

  .ui-layout-container, .ui-layout-column-center { margin-left: auto; margin-right: auto; }
  .ui-layout-grid-2, .ui-layout-grid-3 { column-gap: var(--ui-layout-gutter); grid-template-columns: repeat(2, 1fr); justify-items: center; }
  .ui-layout-grid-3 div:nth-of-type(3) { left: calc(50% + (var(--ui-layout-gutter) / 2)); position: relative; }
  .ui-layout-column-4 { width: calc((var(--ui-layout-grid) * 4) + (var(--ui-layout-gutter) * 3)); }
  .ui-component-list--item { background-size: 1.25rem; padding-left: 2rem; }
  .ui-section-header { padding-bottom: 0; padding-top: 2rem; }
  .ui-section-header--menu-icon { display: none; }
  .ui-section-header--nav { background-color: transparent; box-shadow: none; flex-direction: row; opacity: 1; padding: 0; position: static; visibility: visible; }
  .ui-section-header--nav-link { font-size: var(--ui-typography-p); padding: 0; }
  .ui-section-hero { text-align: left; }
  .ui-section-hero .ui-component-cta { align-items: start; }
  .ui-section-customer__layout { column-gap: var(--ui-gap-customer); flex-direction: row; }
  .ui-section-customer--logo { margin-left: 0; margin-right: 0; }
  .ui-section-feature__layout:first-of-type div { grid-row-start: initial; }
  .ui-component-card--pricing { padding: 2rem 2rem 2.25rem; }
  .ui-section-footer { padding-bottom: 2rem; padding-top: 2rem; }
}

@media screen and (min-width: 64rem) {
  :root {
    --ui-typography-h1: 2.75rem;
    --ui-typography-h2: 2rem;
    --ui-typography-p : 1.125rem;
    --ui-typography-s : .9rem;
    --ui-typography-margin-body: 1.5rem;
    --ui-layout-container: 3.5rem;
    --ui-layout-gutter   : 2rem;
    --ui-gap-cta: 1rem;
    --ui-gap-header: 2.5rem;
    --ui-gap-customer: 3rem;
    --ui-gap-card  : 2.5rem;
    --ui-gap-hero: 3rem;
    --ui-gap-feature: 2rem;
    --ui-gap-content: 2.5rem;
    --ui-gap-testimonial: 1.5rem;
    --ui-gap-pricing: 1.5rem;
  }

  .ui-layout-grid-2 { grid-template-columns: repeat(2, 1fr); }
  .ui-layout-grid-3 { grid-template-columns: repeat(3, 1fr); }
  .ui-layout-grid-3 div:nth-of-type(3) { left: auto; position: static; }
}
"""

# Embedded JavaScript - compiled into the executable
DASHBOARD_JS = """const playersGrid = document.getElementById("players-grid");
const statusPill = document.getElementById("status-pill");
const statusMeta = document.getElementById("status-meta");
const metaText = document.getElementById("meta-text");
const refreshFeedBtn = document.getElementById("refresh-feed-btn");
const playerModal = document.getElementById("player-modal");
const modalBody = document.getElementById("modal-body");
const modalCloseBtn = document.getElementById("modal-close");

let cosmeticsByPlayer = {};
let currentPlayers = new Map();
let currentUserPuuid = "";
let feedInteractionLockUntil = 0;
let pendingFeedPayload = null;
let feedInteractionUnlockTimer = null;

function isFeedInteractionLocked() {
  return Date.now() < feedInteractionLockUntil;
}

function flushPendingFeedPayload() {
  if (!pendingFeedPayload || isFeedInteractionLocked()) {
    return;
  }

  const payload = pendingFeedPayload;
  pendingFeedPayload = null;
  renderFeedPayload(payload);
}

function extendFeedInteractionLock(durationMs = 1500) {
  feedInteractionLockUntil = Math.max(feedInteractionLockUntil, Date.now() + durationMs);

  if (feedInteractionUnlockTimer) {
    clearTimeout(feedInteractionUnlockTimer);
  }

  feedInteractionUnlockTimer = setTimeout(() => {
    feedInteractionUnlockTimer = null;
    flushPendingFeedPayload();
  }, durationMs + 25);
}

function renderFeedPayload(payload) {
  const serverId = payload.server_id || payload.serverId || payload.server || "N/A";
  const matchId = payload.match_id || "N/A";
  metaText.textContent = `State: ${payload.state || "unknown"} • Mode: ${payload.mode || "unknown"} • Server: ${serverId} • Match: ${matchId}`;
  renderPlayers(payload);
}

function getWebSocketUrl() {
  const params = new URLSearchParams(window.location.search);
  const port = params.get("port");
  if (port) {
    return `ws://127.0.0.1:${port}`;
  }

  const candidates = [
    "ws://127.0.0.1:1100",
    "ws://localhost:1100",
    "ws://127.0.0.1:8080",
    "ws://localhost:8080"
  ];

  return candidates[0];
}

function formatValue(value, fallback = "—") {
  return value === undefined || value === null || value === "" ? fallback : value;
}

function stripAnsi(value) {
  return String(value ?? "").replace(/\u001b\\[[0-9;]*m/g, "");
}

function getRankNameFromValue(rankValue) {
  const numericValue = Number(rankValue);
  if (Number.isInteger(numericValue)) {
    const rankNames = [
      "Unranked", "Unranked", "Unranked",
      "Iron 1", "Iron 2", "Iron 3",
      "Bronze 1", "Bronze 2", "Bronze 3",
      "Silver 1", "Silver 2", "Silver 3",
      "Gold 1", "Gold 2", "Gold 3",
      "Platinum 1", "Platinum 2", "Platinum 3",
      "Diamond 1", "Diamond 2", "Diamond 3",
      "Ascendant 1", "Ascendant 2", "Ascendant 3",
      "Immortal 1", "Immortal 2", "Immortal 3",
      "Radiant"
    ];
    return rankNames[numericValue] || "Unranked";
  }

  return String(rankValue ?? "").trim();
}

function getRankIconPath(rankValue) {
  const rankText = getRankNameFromValue(rankValue);
  if (!rankText) {
    return "";
  }

  if (/unranked|^unr$/i.test(rankText)) {
    return "/assets/rank_png/Unranked.png";
  }

  const normalized = rankText
    .replace(/\\s+/g, "_")
    .replace(/[^a-zA-Z0-9_]/g, "")
    .replace(/_+$/, "");

  return `/assets/rank_png/${normalized}_Rank.png`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function interpolateColor(start, end, ratio) {
  const clamped = Math.max(0, Math.min(1, ratio));
  const mix = (a, b) => Math.round(a + (b - a) * clamped);
  return `rgb(${mix(start[0], end[0])}, ${mix(start[1], end[1])}, ${mix(start[2], end[2])})`;
}

function getMetricColor(value, mode = "hs") {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "#8f99af";
  }

  if (mode === "wr") {
    if (numeric <= 45) {
      return interpolateColor([64, 15, 10], [140, 119, 11], numeric / 45);
    }
    if (numeric <= 55) {
      return interpolateColor([140, 119, 11], [18, 204, 25], (numeric - 45) / 10);
    }
    return interpolateColor([18, 204, 25], [255, 255, 255], (numeric - 55) / 45);
  }

  if (numeric <= 25) {
    return interpolateColor([64, 15, 10], [140, 119, 11], numeric / 25);
  }
  if (numeric <= 50) {
    return interpolateColor([140, 119, 11], [18, 204, 25], (numeric - 25) / 25);
  }
  return interpolateColor([18, 204, 25], [255, 255, 255], (numeric - 50) / 50);
}

function getWrMatchesCount(player) {
  const directCandidates = [
    player.numberofgames,
    player.numberOfGames,
    player.games,
    player.gamesPlayedCompetitive,
    player.games_played_competitive,
    player.totalGames,
    player.total_games,
    player.wrMatches,
    player.wr_matches,
    player.winRateMatches,
    player.winrateMatches,
    player.winrate_matches,
    player.totalMatches,
    player.total_matches,
    player.matchesPlayed,
    player.matches_played,
  ];

  for (const candidate of directCandidates) {
    const numeric = Number(candidate);
    if (Number.isFinite(numeric) && numeric > 0) {
      return Math.trunc(numeric);
    }
  }

  const winPercentageText = String(player.winPercentage ?? player.win_percentage ?? "");
  const openParen = winPercentageText.lastIndexOf("(");
  const closeParen = winPercentageText.indexOf(")", openParen + 1);
  if (openParen > -1 && closeParen > openParen) {
    const insideParens = winPercentageText.slice(openParen + 1, closeParen);
    let digitsOnly = "";
    for (const ch of insideParens) {
      if (ch >= "0" && ch <= "9") {
        digitsOnly += ch;
      }
    }
    if (digitsOnly) {
      const parsed = Number(digitsOnly);
      if (Number.isFinite(parsed) && parsed > 0) {
        return Math.trunc(parsed);
      }
    }
  }

  const lower = winPercentageText.toLowerCase();
  const matchWordIndex = lower.indexOf("match");
  if (matchWordIndex > -1) {
    const beforeMatchWord = winPercentageText.slice(0, matchWordIndex);
    let spacedDigits = "";
    for (const ch of beforeMatchWord) {
      spacedDigits += ch >= "0" && ch <= "9" ? ch : " ";
    }
    const numberParts = spacedDigits.split(" ").filter(Boolean);
    if (numberParts.length > 0) {
      const parsed = Number(numberParts[numberParts.length - 1]);
      if (Number.isFinite(parsed) && parsed > 0) {
        return Math.trunc(parsed);
      }
    }
  }

  const wins = Number(
    player.wins ?? player.numberOfWins ?? player.number_of_wins ?? player.compWins ?? player.comp_wins
  );
  const losses = Number(
    player.losses ?? player.numberOfLosses ?? player.number_of_losses ?? player.compLosses ?? player.comp_losses
  );
  if (Number.isFinite(wins) && Number.isFinite(losses) && wins >= 0 && losses >= 0) {
    return Math.trunc(wins + losses);
  }

  return null;
}

function getKdaColor(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "#8f99af";
  }

  if (numeric <= 0.5) {
    return "rgb(90, 16, 16)";
  }
  if (numeric <= 0.8) {
    return interpolateColor([90, 16, 16], [205, 120, 28], (numeric - 0.5) / 0.3);
  }
  if (numeric <= 1.0) {
    return interpolateColor([205, 120, 28], [220, 190, 55], (numeric - 0.8) / 0.2);
  }
  if (numeric <= 1.2) {
    return interpolateColor([220, 190, 55], [120, 220, 120], (numeric - 1.0) / 0.2);
  }
  if (numeric <= 1.5) {
    return interpolateColor([120, 220, 120], [18, 204, 25], (numeric - 1.2) / 0.3);
  }
  if (numeric <= 2.0) {
    return interpolateColor([18, 204, 25], [0, 255, 255], (numeric - 1.5) / 0.5);
  }
  return "#00FFFF";
}

function getRankValueFromText(rankText) {
  const normalized = String(rankText ?? "").trim().toLowerCase().split("(")[0].trim();
  if (!normalized) {
    return null;
  }

  if (/^[0-9]+$/.test(normalized)) {
    const numeric = Number(normalized);
    return Number.isFinite(numeric) ? numeric : null;
  }

  const rankValueMap = {
    unranked: 0,
    "iron 1": 3,
    "iron 2": 4,
    "iron 3": 5,
    "bronze 1": 6,
    "bronze 2": 7,
    "bronze 3": 8,
    "silver 1": 9,
    "silver 2": 10,
    "silver 3": 11,
    "gold 1": 12,
    "gold 2": 13,
    "gold 3": 14,
    "platinum 1": 15,
    "platinum 2": 16,
    "platinum 3": 17,
    "diamond 1": 18,
    "diamond 2": 19,
    "diamond 3": 20,
    "ascendant 1": 21,
    "ascendant 2": 22,
    "ascendant 3": 23,
    "immortal 1": 24,
    "immortal 2": 25,
    "immortal 3": 26,
    radiant: 27,
  };

  return Object.prototype.hasOwnProperty.call(rankValueMap, normalized) ? rankValueMap[normalized] : null;
}

function getPlayerRankValue(player) {
  const candidates = [
    player.currentRank,
    player.rank,
    player.rankValue,
  ];

  for (const candidate of candidates) {
    const numeric = Number(candidate);
    if (Number.isFinite(numeric)) {
      return numeric;
    }
  }

  return getRankValueFromText(player.rankName ?? player.rank_name ?? "");
}

function getPlayerStatValue(player, keys, transform = (value) => value) {
  for (const key of keys) {
    const raw = player?.[key];
    const numeric = Number(transform(raw));
    if (Number.isFinite(numeric)) {
      return numeric;
    }
  }
  return null;
}

function getTeamAverageStats(players) {
  const totals = {
    rank: 0,
    rankCount: 0,
    kd: 0,
    kdCount: 0,
    wr: 0,
    wrCount: 0,
    hs: 0,
    hsCount: 0,
  };

  for (const player of players) {
    const rankValue = getPlayerRankValue(player);
    if (Number.isFinite(rankValue)) {
      totals.rank += rankValue;
      totals.rankCount += 1;
    }

    const kdValue = getPlayerStatValue(player, ["kda", "kd"], (value) => String(value ?? "").replace(/[^0-9.-]/g, ""));
    if (Number.isFinite(kdValue)) {
      totals.kd += kdValue;
      totals.kdCount += 1;
    }

    const wrValue = getPlayerStatValue(player, ["winPercentage", "win_percentage"], (value) => String(value ?? "").split(" ")[0]);
    if (Number.isFinite(wrValue)) {
      totals.wr += wrValue;
      totals.wrCount += 1;
    }

    const hsValue = getPlayerStatValue(player, ["headshotPercentage", "headshot_percentage"], (value) => String(value ?? "").replace(/%/g, ""));
    if (Number.isFinite(hsValue)) {
      totals.hs += hsValue;
      totals.hsCount += 1;
    }
  }

  const avg = (sum, count) => (count > 0 ? sum / count : null);
  const avgRank = totals.rankCount > 0 ? Math.round(avg(totals.rank, totals.rankCount)) : null;

  return {
    count: players.length,
    rankValue: avgRank,
    rankText: avgRank !== null ? getRankNameFromValue(avgRank) : "N/A",
    rankIconPath: avgRank !== null ? getRankIconPath(avgRank) : "",
    kd: avg(totals.kd, totals.kdCount),
    wr: avg(totals.wr, totals.wrCount),
    hs: avg(totals.hs, totals.hsCount),
  };
}

function createTeamAverageCard(label, teamClass, players) {
  const stats = getTeamAverageStats(players);
  const rankColor = stats.rankValue !== null ? getMetricColor(stats.rankValue, "wr") : "#8f99af";
  const kdColor = stats.kd !== null ? getKdaColor(stats.kd) : "#8f99af";
  const wrColor = stats.wr !== null ? getMetricColor(stats.wr, "wr") : "#8f99af";
  const hsColor = stats.hs !== null ? getMetricColor(stats.hs, "hs") : "#8f99af";

  return `
    <div class="team-average-card ${teamClass}">
      <div class="team-average-title">${escapeHtml(label)} Average</div>
      <div class="team-average-grid">
        <div class="team-average-rank">
          <span class="team-average-rank-label">Current Rank</span>
          <div class="team-average-rank-value">
            ${stats.rankIconPath ? `<img class="team-average-rank-icon" src="${escapeHtml(stats.rankIconPath)}" alt="${escapeHtml(stats.rankText)}" />` : ""}
            <strong style="color:${rankColor}">${escapeHtml(stats.rankText)}</strong>
          </div>
        </div>
        <div class="team-average-stat">
          <span>KD</span>
          <strong style="color:${kdColor}">${stats.kd !== null ? stats.kd.toFixed(2) : "N/A"}</strong>
        </div>
        <div class="team-average-stat">
          <span>WR</span>
          <strong style="color:${wrColor}">${stats.wr !== null ? `${Math.round(stats.wr)}%` : "N/A"}</strong>
        </div>
        <div class="team-average-stat">
          <span>HS</span>
          <strong style="color:${hsColor}">${stats.hs !== null ? `${Math.round(stats.hs)}%` : "N/A"}</strong>
        </div>
      </div>
    </div>
  `;
}

function formatPercent(value, fallback = "N/A") {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }
  return `${numeric}%`;
}

function getSkinTierColor(item) {
  const tierColor = item?.tierColor;
  if (Array.isArray(tierColor) && tierColor.length === 3) {
    return `rgb(${tierColor[0]}, ${tierColor[1]}, ${tierColor[2]})`;
  }

  const tierMap = {
    "0cebb8be-46d7-c12a-d306-e9907bfc5a25": "rgb(0, 149, 135)",
    "e046854e-406c-37f4-6607-19a9ba8426fc": "rgb(241, 184, 45)",
    "60bca009-4182-7998-dee7-b8a2558dc369": "rgb(209, 84, 141)",
    "12683d76-48d7-84a3-4e09-6985794f0445": "rgb(90, 159, 226)",
    "411e4a55-4e59-7757-41f0-86a53f101bb5": "rgb(239, 235, 101)"
  };

  return tierMap[item?.tierUuid] || "";
}

function getLevelColor(level) {
  const numeric = Number(level);
  if (!Number.isFinite(numeric)) {
    return "#8f99af";
  }
  if (numeric >= 400) return "#66d4d4";
  if (numeric >= 300) return "#cfcf4c";
  if (numeric >= 200) return "#4747cc";
  if (numeric >= 100) return "#f19036";
  return "#d3d3d3";
}

function getRrDeltaColor(value) {
  const numeric = Number(String(value ?? "").replace(/[^\\d.-]/g, ""));
  if (!Number.isFinite(numeric)) {
    return "#8f99af";
  }
  if (numeric > 0) return "#41f085";
  if (numeric < 0) return "#ff6b6b";
  return "#8f99af";
}

function getCurrentRrColor(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "#8f99af";
  }

  const clamped = Math.max(0, Math.min(100, numeric));
  return interpolateColor([241, 39, 39], [18, 204, 25], clamped / 100);
}

function parseCountStat(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    return Math.trunc(numeric);
  }
  return null;
}

function formatLastPlayed(secondsAgo) {
  const seconds = Number(secondsAgo);
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "recently";
  }

  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function parseBoolean(value) {
  if (typeof value === "string") {
    const lowered = value.trim().toLowerCase();
    return lowered === "true" || lowered === "1" || lowered === "yes";
  }
  return Boolean(value);
}

function getPlayerSubject(player) {
  return String(player?.puuid || player?.Subject || player?.subject || "").trim();
}

function normalizePlayerIdentity(player) {
  const rawName = String(player?.playerName || player?.name || "").trim();
  let displayName = rawName;
  let displayTag = String(player?.playerTag || "").trim();

  if (!displayTag && rawName.includes("#")) {
    const hashIndex = rawName.lastIndexOf("#");
    if (hashIndex > 0 && hashIndex < rawName.length - 1) {
      displayName = rawName.slice(0, hashIndex).trim();
      displayTag = rawName.slice(hashIndex + 1).trim();
    }
  }

  if (displayTag.startsWith("#")) {
    displayTag = displayTag.slice(1).trim();
  }

  return {
    name: displayName,
    tag: displayTag,
    rawName,
  };
}

function getPlayerName(player) {
  const identity = normalizePlayerIdentity(player);
  const isPrivateProfile = /private/i.test(identity.rawName);
  return isPrivateProfile ? "Name Set to Private" : formatValue(identity.name, "Unknown Player");
}

function getPlayerTag(player) {
  const identity = normalizePlayerIdentity(player);
  const isPrivateProfile = /private/i.test(identity.rawName);
  if (isPrivateProfile || !identity.tag) {
    return "";
  }
  return `#${escapeHtml(identity.tag)}`;
}

function closePlayerModal() {
  playerModal.classList.remove("visible");
  playerModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function openPlayerModal(player) {
  const subject = getPlayerSubject(player);
  const cosmetics = cosmeticsByPlayer[subject] || cosmeticsByPlayer[subject.toLowerCase()] || null;
  const playerName = getPlayerName(player);
  const playerTag = getPlayerTag(player);
  const namecardUrl = cosmetics?.PlayerCard || cosmetics?.playerCard || "";
  const weaponEntries = getPreferredSkinEntries(Object.entries(cosmetics?.Weapons || {}).map(([weaponId, weaponData]) => ({
    weaponId,
    weaponName: weaponData?.weapon || "Unknown weapon",
    skinName: weaponData?.skinDisplayName || "Unknown skin",
    skinIcon: weaponData?.skinDisplayIcon || "",
    buddyIcon: weaponData?.buddy_displayIcon || "",
    tierUuid: weaponData?.contentTierUuid || ""
  })), null);
  const sprayEntries = Object.values(cosmetics?.Sprays || {}).filter((item) => item && (item.displayName || item.displayIcon || item.fullTransparentIcon));

  const skinMarkup = weaponEntries.length
    ? weaponEntries.map((item) => `
        <div class="modal-weapon-card">
          <div class="modal-weapon-art">
            ${item.skinIcon ? `<img class="modal-weapon-image" src="${escapeHtml(item.skinIcon)}" alt="${escapeHtml(item.skinName)}" />` : ""}
            ${item.buddyIcon ? `<img class="modal-buddy-badge" src="${escapeHtml(item.buddyIcon)}" alt="Buddy" />` : ""}
          </div>
          <div class="modal-weapon-meta">
            <strong>${escapeHtml(item.skinName)}</strong>
            <span>${escapeHtml(item.weaponName)}</span>
          </div>
        </div>
      `).join("")
    : "<div class='modal-empty'>No skin data available.</div>";

  const sprayMarkup = sprayEntries.length
    ? sprayEntries.map((item) => `
        <div class="modal-asset-card">
          ${item.displayIcon ? `<img src="${escapeHtml(item.displayIcon)}" alt="${escapeHtml(item.displayName || "Spray")}" />` : ""}
          <div>
            <strong>${escapeHtml(item.displayName || "Spray")}</strong>
            <span>Spray</span>
          </div>
        </div>
      `).join("")
    : "<div class='modal-empty'>No sprays available.</div>";

  modalBody.innerHTML = `
    <div class="modal-header">
      <div>
        <p class="modal-eyebrow">Player details</p>
        <h3>${escapeHtml(playerName)}</h3>
        ${playerTag ? `<p class="modal-tag">${playerTag}</p>` : ""}
      </div>
    </div>
    <div class="modal-grid">
      <section class="modal-panel modal-panel-namecard">
        <div class="modal-section-title">Namecard</div>
        <div class="modal-namecard-wrap">
          ${namecardUrl ? `<img class="modal-namecard" src="${escapeHtml(namecardUrl)}" alt="${escapeHtml(playerName)} namecard" />` : "<div class='modal-empty'>No namecard available.</div>"}
        </div>
      </section>
      <section class="modal-panel modal-panel-skins">
        <div class="modal-section-title">Skins</div>
        <div class="modal-asset-list">${skinMarkup}</div>
      </section>
      <section class="modal-panel modal-panel-sprays">
        <div class="modal-section-title">Sprays</div>
        <div class="modal-asset-list">${sprayMarkup}</div>
      </section>
    </div>
  `;

  playerModal.classList.add("visible");
  playerModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

function getPreferredSkinEntries(skinSummary, limit = 4) {
  const priority = [
    "vandal",
    "phantom",
    "sheriff",
    "knife",
    "melee",
    "operator"
  ];

  const normalized = Array.isArray(skinSummary) ? skinSummary : [];
  const scored = normalized.map((item) => {
    const searchText = `${String(item?.weapon || item?.weaponName || item?.name || item?.skinName || "")} ${String(item?.skinName || item?.name || "")}`.toLowerCase();
    const priorityIndex = priority.findIndex((token) => searchText.includes(token));
    const label = String(item?.skinName || item?.name || "");
    const isDefaultSkin = /\\bstandard\\b|\\bdefault\\b|\\bmelee\\b/i.test(label);

    return {
      item,
      priorityIndex: priorityIndex === -1 ? priority.length : priorityIndex,
      isDefaultSkin,
      label
    };
  });

  const ordered = scored
    .sort((left, right) => {
      if (left.priorityIndex !== right.priorityIndex) {
        return left.priorityIndex - right.priorityIndex;
      }
      if (left.isDefaultSkin !== right.isDefaultSkin) {
        return left.isDefaultSkin ? 1 : -1;
      }
      return left.label.localeCompare(right.label);
    })
    .map((entry) => entry.item);

  return limit === null ? ordered : ordered.slice(0, limit);
}

function getPlayerMatchesDropdownHtml(player) {
  const matches = player.playerMatches || [];
  const playerId = getPlayerSubject(player);
  const dropdownId = `match-dropdown-${playerId}`.replace(/[^a-z0-9-]/gi, "");
  const safeMatches = Array.isArray(matches) ? matches : [];
  const hasMatches = safeMatches.length > 0;
  
  const matchOptions = safeMatches.slice(0, 5).map((match) => {
    const epoch = match.epoch || Date.now() / 1000;
    const date = new Date(epoch * 1000);
    const formattedDate = date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
    const url = match.tracker_url || `https://tracker.gg/valorant/match/${match.match_id}`;
    return `<option value="${escapeHtml(url)}" data-match-id="${escapeHtml(match.match_id)}">${escapeHtml(match.match_id)} - ${escapeHtml(formattedDate)}</option>`;
  }).join("");

  return `
    <div class="player-match-dropdown">
      <select id="${dropdownId}" class="match-select" data-player-id="${playerId}" ${hasMatches ? "" : "disabled"}>
        <option value="">${hasMatches ? `Matches (${safeMatches.length})` : "No tracked matches"}</option>
        ${matchOptions}
      </select>
    </div>
  `;
}

function createPlayerCard(player) {
  const card = document.createElement("article");
  card.className = "player-row";
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-label", `Open ${escapeHtml(getPlayerName(player))} details`);
  card.dataset.subject = getPlayerSubject(player);

  const skinSummary = getPreferredSkinEntries(Array.isArray(player.skinSummary) ? player.skinSummary : [], 4);
  const agentImg = formatValue(player.agentImgLink, "").trim();
  const hasAgentImg = agentImg.length > 0;
  const rankText = stripAnsi(player.rankName || player.currentRank || "Unranked");
  const peakText = stripAnsi(player.peakRankName || player.peakRank || "—");
  const rrValue = formatValue(player.rr, 0);
  const rrColor = getCurrentRrColor(player.rr);
  const rrDeltaRaw = stripAnsi(player.rrDelta ?? "N/A");
  const rrDeltaNumeric = Number(String(rrDeltaRaw).replace(/[^\\d.-]/g, ""));
  const rrDeltaText = Number.isFinite(rrDeltaNumeric) ? `${rrDeltaNumeric > 0 ? "+" : ""}${rrDeltaNumeric} RR` : "N/A";
  const rrDeltaColor = getRrDeltaColor(rrDeltaRaw);
  const rankIconPath = getRankIconPath(player.currentRank ?? rankText);
  const peakIconPath = getRankIconPath(player.peakRank ?? peakText);
  const hsValue = Number(String(player.headshotPercentage ?? "").replace(/%/g, ""));
  const winValue = Number(String(player.winPercentage ?? "").split(" ")[0]);
  const wrMatchesCount = getWrMatchesCount(player);
  const wrMatchesText = wrMatchesCount !== null
    ? `(${wrMatchesCount} ${wrMatchesCount === 1 ? "match" : "matches"})`
    : "";
  const kdValue = Number(String(player.kda ?? player.kd ?? "").replace(/[^\\d.-]/g, ""));
  const kdaColor = getKdaColor(kdValue);
  const hsColor = getMetricColor(hsValue, "hs");
  const winColor = getMetricColor(winValue, "wr");
  const levelColor = getLevelColor(player.accountLevel || player.level);
  const normalizedIdentity = normalizePlayerIdentity(player);
  const isPrivateProfile = /private/i.test(normalizedIdentity.rawName);
  const playerName = isPrivateProfile ? "Name Set to Private" : formatValue(normalizedIdentity.name, "Unknown Player");
  const playerTag = isPrivateProfile || !normalizedIdentity.tag ? "" : `#${escapeHtml(normalizedIdentity.tag)}`;
  const agentName = formatValue(player.agent, "Unknown");
  const killsValue = parseCountStat(player.kills);
  const deathsValue = parseCountStat(player.deaths);
  const assistsValue = parseCountStat(player.assists);
  const kdaRatioValue = formatValue(player.kda ?? player.kd, "N/A");
  const hasFullKdaCounts = killsValue !== null && deathsValue !== null && assistsValue !== null;
  const kdaLine = hasFullKdaCounts ? `${killsValue}/${deathsValue}/${assistsValue}` : "N/A";
  const playedWithCountRaw = player.playedWithCount ?? player.played_with_count ?? player.timesPlayedWith ?? 0;
  const playedWithCount = Number(playedWithCountRaw) || 0;
  const playedWithBeforeRaw = player.playedWithBefore ?? player.played_with_before;
  const playerSubject = String(getPlayerSubject(player) || "").trim().toLowerCase();
  const currentSubject = String(currentUserPuuid || "").trim().toLowerCase();
  const explicitSelfFlag = parseBoolean(player.isSelf ?? player.is_self);
  const isSelfPlayer = explicitSelfFlag || Boolean(playerSubject && currentSubject && playerSubject === currentSubject);
  const playedWithBefore = !isSelfPlayer && (parseBoolean(playedWithBeforeRaw) || playedWithCount > 0);
  const lastPlayedAgent = formatValue(player.lastPlayedAgent ?? player.last_played_agent, "").trim();
  const lastPlayedRaw = player.lastPlayedSecondsAgo ?? player.last_played_seconds_ago;
  const recentStreakType = String(player.recentStreakType ?? player.recent_streak_type ?? "none").toLowerCase();
  const recentStreakCount = Number(player.recentStreakCount ?? player.recent_streak_count ?? 0) || 0;
  const recentStreakWins = Number(player.recentStreakWins ?? player.recent_streak_wins ?? 0) || 0;
  const recentStreakLosses = Number(player.recentStreakLosses ?? player.recent_streak_losses ?? 0) || 0;
  const recentStreakWindow = Number(player.recentStreakWindow ?? player.recent_streak_window ?? 20) || 20;
  const recentOutcomesRaw = Array.isArray(player.recentStreakOutcomes ?? player.recent_streak_outcomes)
    ? (player.recentStreakOutcomes ?? player.recent_streak_outcomes)
    : [];
  const recentOutcomeSquares = recentOutcomesRaw
    .slice(0, 10)
    .map((outcome) => {
      const token = String(outcome ?? "").trim().toLowerCase();
      const isWin = token === "w" || token === "win" || token === "true" || token === "1";
      const isLoss = token === "l" || token === "loss" || token === "false" || token === "0";
      if (!isWin && !isLoss) {
        return "";
      }
      const cssClass = isWin ? "recent-outcome-win" : "recent-outcome-loss";
      const label = isWin ? "Win" : "Loss";
      return `<span class="recent-outcome-square ${cssClass}" title="${label}"></span>`;
    })
    .filter(Boolean)
    .join("");
  const hasRecentStreak = (recentStreakType === "win" || recentStreakType === "loss") && recentStreakCount > 0;
  const streakLabel = hasRecentStreak ? `${recentStreakType === "win" ? "Win" : "Loss"} streak ${recentStreakCount}` : "";
  const streakRecordHtml = hasRecentStreak
    ? `(<span class="streak-win-count">${escapeHtml(String(recentStreakWins))}W</span> <span class="streak-loss-count">${escapeHtml(String(recentStreakLosses))}L</span>)`
    : "";
  const historicalMatchesCount = Array.isArray(player.playerMatches) ? player.playerMatches.length : 0;
  const playedWithLabel = playedWithBefore
    ? `Played ${playedWithCount}x${lastPlayedAgent ? ` • Last ${lastPlayedAgent}` : ""} • ${formatLastPlayed(lastPlayedRaw)}`
    : "New teammate/opponent";
  const showMatchHistoryUi = !isSelfPlayer;
  const historyInfoLabel = showMatchHistoryUi
    ? (playedWithBefore
    ? playedWithLabel
    : (historicalMatchesCount > 0 ? `Tracked ${historicalMatchesCount} prior match${historicalMatchesCount === 1 ? "" : "es"}` : "No prior tracked matches"))
    : "";
  const isHighStatsHighlight = Number.isFinite(winValue) && Number.isFinite(hsValue) && Number.isFinite(kdValue) && winValue >= 60 && hsValue >= 25 && kdValue >= 1.25;

  if (isSelfPlayer) {
    card.classList.add("player-row-self");
  } else if (playedWithBefore) {
    card.classList.add("player-row-played-before");
  }

  card.addEventListener("click", () => openPlayerModal(player));
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openPlayerModal(player);
    }
  });

  card.innerHTML = `
    <div class="row-cell row-agent">
      ${isHighStatsHighlight ? '<span class="hotstats-star" aria-hidden="true">★</span>' : ""}
      ${hasAgentImg
        ? `<img class="agent-mini" src="${escapeHtml(agentImg)}" alt="${escapeHtml(agentName)}" />`
        : `<div><span class="row-label">Agent</span><strong>${escapeHtml(agentName)}</strong></div>`}
    </div>
    <div class="row-cell row-player ${isPrivateProfile ? "private-cell" : ""}">
      <div class="player-name-block">
        <strong>${escapeHtml(playerName)}</strong>
        ${playerTag ? `<span>${playerTag}</span>` : ""}
      </div>
      ${isPrivateProfile ? "<div class=\\"private-note\\">Private profile</div>" : ""}
    </div>
    <div class="row-cell row-kda ${isPrivateProfile ? "private-fill" : ""}">
      ${isPrivateProfile ? '<div class="private-stats"></div>' : `
        <div class="kda-stack">
          <span class="row-label">K / D / A</span>
          <strong class="kda-primary">${escapeHtml(kdaLine)}</strong>
          <span class="kda-ratio">KDA <span style="color:${kdaColor}; font-weight: 700;">${escapeHtml(String(kdaRatioValue))}</span> <span class="metric-footnote-inline">(last game)</span></span>
        </div>
      `}
    </div>
    <div class="row-cell row-rank">
      <div class="rank-stack">
        <div class="rank-badge-row">
          ${rankIconPath ? `<img class="rank-badge" src="${escapeHtml(rankIconPath)}" alt="${escapeHtml(rankText)}" />` : ""}
          <div class="rank-text-stack">
            <span class="row-label">Current</span>
            <strong class="rank-primary"><span class="rank-main">${escapeHtml(formatValue(rankText, "Unranked"))}</span>${rrValue !== undefined && rrValue !== null && rrValue !== "" ? `<span class="rank-current-rr" style="color:${rrColor}">${escapeHtml(String(rrValue))}RR</span>` : ""}</strong>
            <span class="rr-delta-pill" style="color:${rrDeltaColor}"><span>${escapeHtml(rrDeltaText)}</span><span class="metric-footnote-inline metric-footnote-last-game">(last game)</span></span>
          </div>
        </div>
        <div class="rank-badge-row peak-row">
          ${peakIconPath ? `<img class="rank-badge" src="${escapeHtml(peakIconPath)}" alt="${escapeHtml(peakText)}" />` : ""}
          <div class="rank-text-stack">
            <span class="row-label">Peak</span>
            <strong class="rank-secondary">${escapeHtml(formatValue(peakText, "—"))}</strong>
          </div>
        </div>
      </div>
    </div>
    <div class="row-cell row-stats ${isPrivateProfile ? "private-fill" : ""}">
      ${isPrivateProfile ? '<div class="private-stats"></div>' : `
        <div class="stat-primary-row">
          <div class="stat-line stat-line-large"><span>HS</span><div class="stat-value-inline"><strong style="color:${hsColor}">${escapeHtml(formatPercent(hsValue, "N/A"))}</strong><span class="metric-footnote-inline metric-footnote-last-game">(last game)</span></div></div>
          <div class="stat-line stat-line-large"><span>WR</span><div class="stat-value-stack"><strong style="color:${winColor}">${escapeHtml(formatPercent(winValue, "N/A"))}</strong>${wrMatchesText ? `<span class="metric-footnote-inline metric-footnote-last-game">${escapeHtml(wrMatchesText)}</span>` : ""}</div></div>
        </div>
        ${streakLabel ? `<div class="pill pill-streak ${recentStreakType === "win" ? "pill-streak-win" : "pill-streak-loss"} stat-history-pill"><span>${escapeHtml(streakLabel)} ${streakRecordHtml} <span class="metric-footnote-inline metric-footnote-pill-inline">(last ${escapeHtml(String(recentStreakWindow))} games)</span></span></div>` : ""}
        ${recentOutcomeSquares ? `<div class="recent-outcomes-row" aria-label="Last 10 results">${recentOutcomeSquares}</div>` : ""}
        ${historyInfoLabel ? `<div class="pill pill-history stat-history-pill">${escapeHtml(historyInfoLabel)}</div>` : ""}
      `}
    </div>
    <div class="row-cell row-meta">
      <span class="pill" style="color:${levelColor}">Lvl ${escapeHtml(formatValue(player.accountLevel || player.level, 0))}</span>
    </div>
    <div class="row-cell row-skins">
      <div class="skin-inline">${skinSummary.map((item) => `
        <div class="skin-chip">
          ${item.icon ? `<img src="${escapeHtml(item.icon)}" alt="${escapeHtml(item.name)}" />` : ""}
          <span style="${getSkinTierColor(item) ? `color:${getSkinTierColor(item)};` : ""}">${escapeHtml(item.name)}</span>
        </div>
      `).join("") || "<span class='skin-empty'>No skins</span>"}</div>
    </div>
    ${showMatchHistoryUi ? `
      <div class="player-match-section">
        ${getPlayerMatchesDropdownHtml(player)}
      </div>
    ` : ""}
  `;

  const matchSelect = card.querySelector(".match-select");
  if (matchSelect) {
    ["focus", "mousedown", "touchstart"].forEach((eventName) => {
      matchSelect.addEventListener(eventName, () => {
        extendFeedInteractionLock(1800);
      });
    });

    ["click", "mousedown", "mouseup", "touchstart", "touchend"].forEach((eventName) => {
      matchSelect.addEventListener(eventName, (event) => {
        event.stopPropagation();
      });
    });

    matchSelect.addEventListener("keydown", (event) => {
      extendFeedInteractionLock(1800);
      event.stopPropagation();
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
      }
    });

    matchSelect.addEventListener("change", () => {
      extendFeedInteractionLock(600);
    });

    matchSelect.addEventListener("blur", () => {
      extendFeedInteractionLock(200);
    });
  }

  return card;
}

function renderPlayers(payload) {
  const players = payload && payload.players ? payload.players : {};
  const entries = Object.values(players);
  currentUserPuuid = payload?.puuid || "";
  currentPlayers = new Map(entries.map((entry) => [getPlayerSubject(entry), entry]));

  playersGrid.innerHTML = "";
  if (!entries.length) {
    playersGrid.innerHTML = '<div class="empty-state">Waiting for a match payload…</div>';
    return;
  }

  const selfTeam = (() => {
    const selfPlayer = entries.find((player) => player.puuid === payload.puuid);
    const teamValue = selfPlayer && selfPlayer.team ? String(selfPlayer.team).toLowerCase() : "";
    return teamValue === "blue" || teamValue === "red" ? teamValue : "";
  })();

  const teams = { ally: [], enemy: [] };
  entries.forEach((player) => {
    const teamValue = typeof player.team === "string" ? player.team.toLowerCase() : "";
    if (selfTeam && teamValue === selfTeam) {
      teams.ally.push(player);
    } else if (teamValue === "blue" || teamValue === "red") {
      teams.enemy.push(player);
    } else {
      teams.enemy.push(player);
    }
  });

  const teamOrder = [
    { key: "ally", label: selfTeam ? "Your Team" : "Team A", className: "team-ally" },
    { key: "enemy", label: selfTeam ? "Enemy Team" : "Team B", className: "team-enemy" }
  ];

  const allyLabel = teamOrder[0].label;
  const enemyLabel = teamOrder[1].label;

  teamOrder.forEach(({ key, label, className }, index) => {
    const cards = teams[key] || [];
    if (!cards.length) return;

    const section = document.createElement("section");
    section.className = `team-section ${className}`;
    section.innerHTML = `<div class="team-header">${escapeHtml(label)}</div><div class="team-rows"></div>`;
    const teamRows = section.querySelector(".team-rows");
    cards.sort((a, b) => Number(b.rr || 0) - Number(a.rr || 0));
    cards.forEach((player) => teamRows.appendChild(createPlayerCard(player)));
    playersGrid.appendChild(section);

    if (index === 0 && teams.enemy && teams.enemy.length) {
      const averagesStrip = document.createElement("div");
      averagesStrip.className = "team-averages-strip";
      averagesStrip.innerHTML = [
        createTeamAverageCard(allyLabel, "team-average-ally", teams.ally),
        createTeamAverageCard(enemyLabel, "team-average-enemy", teams.enemy),
      ].join("");
      playersGrid.appendChild(averagesStrip);
    }
  });
}

function connectFeed() {
  const socketUrl = getWebSocketUrl();
  statusPill.textContent = "Connecting…";
  statusMeta.textContent = `Trying ${socketUrl}`;

  const socket = new WebSocket(socketUrl);

  socket.onopen = () => {
    statusPill.textContent = "Live";
    statusMeta.textContent = `Connected to ${socketUrl}`;
  };

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (!payload) {
        return;
      }

      if (payload.type === "matchLoadout") {
        cosmeticsByPlayer = payload.Players || payload.players || {};
        return;
      }

      if (payload.type !== "feed") {
        return;
      }

      if (isFeedInteractionLocked()) {
        pendingFeedPayload = payload;
        return;
      }

      renderFeedPayload(payload);
    } catch (error) {
      console.error("Unable to parse websocket payload", error);
    }
  };

  socket.onerror = () => {
    statusPill.textContent = "Offline";
    statusMeta.textContent = "Could not reach the local feed. Make sure vRY is running.";
  };

  socket.onclose = () => {
    statusPill.textContent = "Reconnecting…";
    statusMeta.textContent = "Connection closed. Trying again in a moment.";
    setTimeout(connectFeed, 2000);
  };
}

modalCloseBtn.addEventListener("click", closePlayerModal);
playerModal.addEventListener("click", (event) => {
  if (event.target === playerModal) {
    closePlayerModal();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closePlayerModal();
  }
});

if (refreshFeedBtn) {
  refreshFeedBtn.addEventListener("click", () => {
    window.location.reload();
  });
}

document.addEventListener("change", (e) => {
  if (e.target.classList.contains("match-select") && e.target.value) {
    window.open(e.target.value, "_blank");
    e.target.value = "";
  }
});

connectFeed();
"""


# Embedded HTML - these are compiled into the executable
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>VALORANT Live Feed</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style id="embedded-style"></style>
</head>
<body>
  <main class="app-shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Live VALORANT feed</p>
        <h1>Ranks, stats, agents, and skins in one view.</h1>
        <p class="subtitle">This dashboard connects to your local vRY feed and updates as the app detects players in game.</p>
      </div>
      <div class="status-card" id="status-card">
        <div class="status-pill" id="status-pill">Connecting…</div>
        <div class="status-meta" id="status-meta">Waiting for the local feed.</div>
        <button id="refresh-feed-btn" class="refresh-feed-btn" type="button">Refresh</button>
      </div>
    </header>

    <section class="feed-section">
      <div class="section-head">
        <h2>Players</h2>
        <p id="meta-text">No live payload yet.</p>
      </div>
      <div id="players-grid" class="players-grid"></div>
    </section>
  </main>

  <div id="player-modal" class="player-modal" aria-hidden="true">
    <div class="modal-card" role="dialog" aria-modal="true">
      <button id="modal-close" class="modal-close" type="button" aria-label="Close player details">×</button>
      <div id="modal-body" class="modal-body"></div>
    </div>
  </div>

  <script id="embedded-script"></script>
</body>
</html>"""


# CSS is stored separately but will be injected
# For brevity in this example, we'll serve via the HTTP handler
# But normally you'd embed it here too


class DashboardHTTPHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves embedded dashboard resources."""

    # Store CSS and JS as class variables (will be set by init_dashboard_http)
    css_content = ""
    js_content = ""
    image_cache_dir: Path | None = None

    def do_GET(self):
        """Handle GET requests for dashboard resources."""
        from pathlib import Path

        # Remove query string
        path = self.path.split('?')[0]

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            # Inject CSS and JS into the HTML
            html = DASHBOARD_HTML.replace(
                '<style id="embedded-style"></style>',
                f"<style>{self.css_content}</style>"
            ).replace(
                '<script id="embedded-script"></script>',
                f"<script>{self.js_content}</script>"
            )
            self.wfile.write(html.encode("utf-8"))
        elif path.startswith("/assets/"):
          try:
            base_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
            asset_path = (base_dir / "assets" / path[8:]).resolve()
            assets_base = (base_dir / "assets").resolve()

            if not str(asset_path).startswith(str(assets_base)):
              self.send_response(403)
              self.send_header("Content-type", "text/plain")
              self.end_headers()
              self.wfile.write(b"Forbidden")
              return

            if asset_path.exists() and asset_path.is_file():
              content_type = "application/octet-stream"
              if path.endswith(".png"):
                content_type = "image/png"
              elif path.endswith(".jpg") or path.endswith(".jpeg"):
                content_type = "image/jpeg"
              elif path.endswith(".gif"):
                content_type = "image/gif"
              elif path.endswith(".svg"):
                content_type = "image/svg+xml"
              elif path.endswith(".ico"):
                content_type = "image/x-icon"

              self.send_response(200)
              self.send_header("Content-type", content_type)
              self.send_header("Cache-Control", "max-age=3600")
              self.end_headers()

              with open(asset_path, "rb") as file_handle:
                self.wfile.write(file_handle.read())
            else:
              self.send_response(404)
              self.send_header("Content-type", "text/plain")
              self.end_headers()
              self.wfile.write(b"Asset not found")
          except Exception as ex:
            self.send_response(500)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Server error: {ex}".encode("utf-8"))
        elif path.startswith("/cache/"):
            try:
                cache_root = self.image_cache_dir or get_runtime_image_cache_dir()
                cache_root = Path(cache_root).resolve()
                requested_rel = path[len("/cache/"):]
                cache_path = (cache_root / requested_rel).resolve()

                if not str(cache_path).startswith(str(cache_root)):
                    self.send_response(403)
                    self.send_header("Content-type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"Forbidden")
                    return

                if cache_path.exists() and cache_path.is_file():
                    content_type = "application/octet-stream"
                    lower_path = path.lower()
                    if lower_path.endswith(".png"):
                        content_type = "image/png"
                    elif lower_path.endswith(".jpg") or lower_path.endswith(".jpeg"):
                        content_type = "image/jpeg"
                    elif lower_path.endswith(".gif"):
                        content_type = "image/gif"
                    elif lower_path.endswith(".webp"):
                        content_type = "image/webp"
                    elif lower_path.endswith(".svg"):
                        content_type = "image/svg+xml"

                    self.send_response(200)
                    self.send_header("Content-type", content_type)
                    self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                    self.end_headers()

                    with open(cache_path, "rb") as file_handle:
                        self.wfile.write(file_handle.read())
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"Cache asset not found")
            except Exception as ex:
                self.send_response(500)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Server error: {ex}".encode("utf-8"))
        elif path.endswith(".css"):
            self.send_response(200)
            self.send_header("Content-type", "text/css; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(self.css_content.encode("utf-8"))
        elif path.endswith(".js"):
            self.send_response(200)
            self.send_header("Content-type", "application/javascript; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(self.js_content.encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def start_dashboard_http(port, css_content, js_content, log_func=None):
    """Start HTTP server for dashboard resources.
    
    Args:
        port: Port to serve on (e.g., 1101)
        css_content: CSS as a string
        js_content: JS as a string
        log_func: Optional logging function
    """
    # Set class variables
    DashboardHTTPHandler.css_content = css_content
    DashboardHTTPHandler.js_content = js_content
    DashboardHTTPHandler.image_cache_dir = get_runtime_image_cache_dir()

    try:
        server = HTTPServer(("127.0.0.1", port), DashboardHTTPHandler)
        if log_func:
            log_func(f"Dashboard HTTP server started on http://127.0.0.1:{port}")

        # Run in a thread so it doesn't block
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
    except Exception as ex:
        if log_func:
            log_func(f"Failed to start dashboard HTTP server on port {port}: {ex}")
        return None


def get_dashboard_url(port):
    """Get the URL for accessing the dashboard."""
    return f"http://127.0.0.1:{port}/index.html"
