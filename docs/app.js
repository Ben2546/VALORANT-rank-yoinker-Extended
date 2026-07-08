const playersGrid = document.getElementById("players-grid");
const statusPill = document.getElementById("status-pill");
const statusMeta = document.getElementById("status-meta");
const metaText = document.getElementById("meta-text");
const refreshFeedBtn = document.getElementById("refresh-feed-btn");
const playerModal = document.getElementById("player-modal");
const modalBody = document.getElementById("modal-body");
const modalCloseBtn = document.getElementById("modal-close");

const RANK_NAMES = [
  "Unranked",
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

const RANK_VALUE_MAP = {
  unranked: 0,
  "iron 1": 1,
  "iron 2": 2,
  "iron 3": 3,
  "bronze 1": 4,
  "bronze 2": 5,
  "bronze 3": 6,
  "silver 1": 7,
  "silver 2": 8,
  "silver 3": 9,
  "gold 1": 10,
  "gold 2": 11,
  "gold 3": 12,
  "platinum 1": 13,
  "platinum 2": 14,
  "platinum 3": 15,
  "diamond 1": 16,
  "diamond 2": 17,
  "diamond 3": 18,
  "ascendant 1": 19,
  "ascendant 2": 20,
  "ascendant 3": 21,
  "immortal 1": 22,
  "immortal 2": 23,
  "immortal 3": 24,
  radiant: 25,
};

function ensureProceedButton() {
  if (!refreshFeedBtn || !refreshFeedBtn.parentElement) {
    return null;
  }

  let button = document.getElementById("proceed-feed-btn");
  if (button) {
    return button;
  }

  button = document.createElement("button");
  button.id = "proceed-feed-btn";
  button.type = "button";
  button.className = "refresh-feed-btn";
  button.textContent = "Proceed";
  button.style.display = "none";
  button.style.marginLeft = "0.5rem";
  refreshFeedBtn.insertAdjacentElement("afterend", button);
  return button;
}

const proceedFeedBtn = ensureProceedButton();

let cosmeticsByPlayer = {};
let currentPlayers = new Map();
let currentUserPuuid = "";
let feedInteractionLockUntil = 0;
let pendingFeedPayload = null;
let feedInteractionUnlockTimer = null;
let feedHoverFlushTimer = null;
let previousFeedState = "";
let waitingForWebProceed = false;
let pendingPostMatchPayload = null;

function setProceedButtonVisible(isVisible) {
  if (!proceedFeedBtn) {
    return;
  }
  proceedFeedBtn.style.display = isVisible ? "inline-flex" : "none";
}

function isFeedHoverActive() {
  if (!playersGrid) {
    return false;
  }
  return playersGrid.matches(":hover");
}

function isFeedInteractionLocked() {
  return Date.now() < feedInteractionLockUntil;
}

function flushPendingFeedPayload() {
  if (!pendingFeedPayload || isFeedInteractionLocked() || isFeedHoverActive()) {
    return;
  }

  const payload = pendingFeedPayload;
  pendingFeedPayload = null;
  handleFeedPayload(payload);
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

function scheduleFeedHoverFlush(delayMs = 90) {
  if (feedHoverFlushTimer) {
    clearTimeout(feedHoverFlushTimer);
  }

  feedHoverFlushTimer = setTimeout(() => {
    feedHoverFlushTimer = null;
    flushPendingFeedPayload();
  }, delayMs);
}

function renderFeedPayload(payload) {
  const serverId = payload.server_id || payload.serverId || payload.server || "N/A";
  const matchId = payload.match_id || "N/A";
  metaText.textContent = `State: ${payload.state || "unknown"} • Mode: ${payload.mode || "unknown"} • Server: ${serverId} • Match: ${matchId}`;
  renderPlayers(payload);
}

function handleFeedPayload(payload) {
  const nextState = String(payload?.state || "").trim().toUpperCase();
  const previousState = String(previousFeedState || "").trim().toUpperCase();
  const isMatchEndTransition = previousState === "INGAME" && nextState === "MENUS";

  previousFeedState = nextState;

  if (isMatchEndTransition) {
    waitingForWebProceed = true;
    pendingPostMatchPayload = payload;
    setProceedButtonVisible(true);
    statusMeta.textContent = "Match ended. Click Proceed to switch to lobby.";
    return;
  }

  if (waitingForWebProceed) {
    const shouldAutoResume = nextState === "PREGAME" || nextState === "INGAME";
    if (shouldAutoResume) {
      waitingForWebProceed = false;
      pendingPostMatchPayload = null;
      setProceedButtonVisible(false);
      renderFeedPayload(payload);
      return;
    }

    pendingPostMatchPayload = payload;
    return;
  }

  renderFeedPayload(payload);
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
  return String(value ?? "").replace(/\u001b\[[0-9;]*m/g, "");
}

function getRankNameFromValue(rankValue) {
  const numericValue = Number(rankValue);
  if (Number.isInteger(numericValue)) {
    // If the backend sent a Riot ID (Iron 1 = 3), convert it to your index (1)
    // If it's already using your custom index from team averages, keep it
    let index = numericValue;
    if (index >= 3 && index <= 27) {
      index = index - 2; // Converts Riot's 3 back to your 1
    }

    return RANK_NAMES[index] || "Unranked";
  }

  return String(rankValue ?? "").trim();
}

function getRankIconPath(rankValue) {
  const rankText = getRankNameFromValue(rankValue);
  if (!rankText) {
    return "";
  }

  if (/unranked|^unr$/i.test(rankText)) {
    return "../assets/rank_png/Unranked.png";
  }

  const normalized = rankText
    .replace(/\s+/g, "_")
    .replace(/[^a-zA-Z0-9_]/g, "")
    .replace(/_+$/, "");

  return `../assets/rank_png/${normalized}_Rank.png`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
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

  if (/^\d+$/.test(normalized)) {
    const numeric = Number(normalized);
    return Number.isFinite(numeric) ? numeric : null;
  }

  return Object.prototype.hasOwnProperty.call(RANK_VALUE_MAP, normalized) ? RANK_VALUE_MAP[normalized] : null;
}

function getPlayerRankValue(player) {
  const candidates = [
    player.currentRank,
    player.rank,
    player.rankValue,
  ];

  for (const candidate of candidates) {
    const numeric = Number(candidate);
    if (Number.isFinite(numeric) && numeric > 0) {
      return numeric;
    }
  }

  const derivedRank = getRankValueFromText(player.rankName ?? player.rank_name ?? "");
  return Number.isFinite(derivedRank) && derivedRank > 0 ? derivedRank : null;
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

    const kdValue = getPlayerStatValue(player, ["kda", "kd"], (value) => String(value ?? "").replace(/[^\d.-]/g, ""));
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
  const numeric = Number(String(value ?? "").replace(/[^\d.-]/g, ""));
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

  // MENUS payloads can provide Riot ID as a single value (Name#Tag).
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
    const isDefaultSkin = /\bstandard\b|\bdefault\b|\bmelee\b/i.test(label);

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
  const rrDeltaNumeric = Number(String(rrDeltaRaw).replace(/[^\d.-]/g, ""));
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
  const killsValue = parseCountStat(player.kills);
  const deathsValue = parseCountStat(player.deaths);
  const assistsValue = parseCountStat(player.assists);
  const fallbackKd = Number(String(player.kd ?? "").replace(/[^\d.-]/g, ""));
  const kdValue = Number.isFinite(fallbackKd) ? fallbackKd : null;
  const kdRatioText = kdValue !== null ? kdValue.toFixed(2) : "N/A";
  const kdaColor = getKdaColor(kdValue);
  const hsColor = getMetricColor(hsValue, "hs");
  const winColor = getMetricColor(winValue, "wr");
  const levelColor = getLevelColor(player.accountLevel || player.level);
  const normalizedIdentity = normalizePlayerIdentity(player);
  const isPrivateProfile = /private/i.test(normalizedIdentity.rawName);
  const playerName = isPrivateProfile ? "Name Set to Private" : formatValue(normalizedIdentity.name, "Unknown Player");
  const playerTag = isPrivateProfile || !normalizedIdentity.tag ? "" : `#${escapeHtml(normalizedIdentity.tag)}`;
  const agentName = formatValue(player.agent, "Unknown");
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
  const lastPlayedTeamRaw = formatValue(player.lastPlayedTeam ?? player.last_played_team, "").trim().toLowerCase();
  const lastPlayedTeam = lastPlayedTeamRaw === "blue"
    ? "Red"
    : (lastPlayedTeamRaw === "red" ? "Green" : "");
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
    ? `Played ${playedWithCount}x${lastPlayedAgent ? ` • Last ${lastPlayedAgent}` : ""}${lastPlayedTeam ? ` (${lastPlayedTeam})` : ""} • ${formatLastPlayed(lastPlayedRaw)}`
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
      ${isPrivateProfile ? "<div class=\"private-note\">Private profile</div>" : ""}
    </div>
    <div class="row-cell row-kda ${isPrivateProfile ? "private-fill" : ""}">
      ${isPrivateProfile ? '<div class="private-stats"></div>' : `
        <div class="kda-stack">
          <span class="row-label">K / D / A</span>
          <strong class="kda-primary">${escapeHtml(kdaLine)}</strong>
          <span class="kda-ratio">KD <span style="color:${kdaColor}; font-weight: 700;">${escapeHtml(kdRatioText)}</span> <span class="metric-footnote-inline">(last game)</span></span>
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
          <div class="stat-line stat-line-large"><span>HS</span><div class="stat-value-stack"><strong style="color:${hsColor}">${escapeHtml(formatPercent(hsValue, "N/A"))}</strong><span class="metric-footnote-inline metric-footnote-last-game">(last game)</span></div></div>
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

  // Keep dropdown interactions from bubbling to the card click/keydown handlers.
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
  const stateText = String(payload?.state || "").toLowerCase();
  const modeText = String(payload?.mode || "").toLowerCase();
  const isLobby = stateText === "menus" || modeText.includes("lobby");
  const allowAverageStats = !isLobby;
  const isDeathmatch = entries.length === 12 || modeText.includes("deathmatch");
  currentUserPuuid = payload?.puuid || "";
  currentPlayers = new Map(entries.map((entry) => [getPlayerSubject(entry), entry]));

  playersGrid.innerHTML = "";
  if (!entries.length) {
    playersGrid.innerHTML = '<div class="empty-state">Waiting for a match payload…</div>';
    return;
  }

  if (isDeathmatch) {
    const dmSection = document.createElement("section");
    dmSection.className = "team-section team-other";
    dmSection.innerHTML = '<div class="team-header">Deathmatch Lobby</div><div class="team-rows"></div>';

    const dmRows = dmSection.querySelector(".team-rows");
    const sortedEntries = [...entries].sort((a, b) => Number(b.rr || 0) - Number(a.rr || 0));
    sortedEntries.forEach((player) => dmRows.appendChild(createPlayerCard(player)));
    playersGrid.appendChild(dmSection);

    if (allowAverageStats) {
      const averagesStrip = document.createElement("div");
      averagesStrip.className = "team-averages-strip";
      averagesStrip.innerHTML = createTeamAverageCard("Deathmatch", "team-average-ally", entries);
      playersGrid.appendChild(averagesStrip);
    }
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
  let averagesRendered = false;

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

    if (allowAverageStats && index === 0 && teams.enemy && teams.enemy.length) {
      const averagesStrip = document.createElement("div");
      averagesStrip.className = "team-averages-strip";
      averagesStrip.innerHTML = [
        createTeamAverageCard(allyLabel, "team-average-ally", teams.ally),
        createTeamAverageCard(enemyLabel, "team-average-enemy", teams.enemy),
      ].join("");
      playersGrid.appendChild(averagesStrip);
      averagesRendered = true;
    }
  });

  // Agent select and other partial payloads may only have one visible side.
  // Still show averages for the available side so the strip is not missing.
  if (allowAverageStats && !averagesRendered) {
    const averageCards = [];
    if (teams.ally && teams.ally.length) {
      averageCards.push(createTeamAverageCard(allyLabel, "team-average-ally", teams.ally));
    }
    if (teams.enemy && teams.enemy.length) {
      averageCards.push(createTeamAverageCard(enemyLabel, "team-average-enemy", teams.enemy));
    }

    if (averageCards.length) {
      const averagesStrip = document.createElement("div");
      averagesStrip.className = "team-averages-strip";
      averagesStrip.innerHTML = averageCards.join("");
      playersGrid.appendChild(averagesStrip);
    }
  }
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

      if (isFeedInteractionLocked() || isFeedHoverActive()) {
        pendingFeedPayload = payload;
        return;
      }

      handleFeedPayload(payload);
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

if (proceedFeedBtn) {
  proceedFeedBtn.addEventListener("click", () => {
    if (!waitingForWebProceed) {
      setProceedButtonVisible(false);
      return;
    }

    waitingForWebProceed = false;
    setProceedButtonVisible(false);

    const nextPayload = pendingPostMatchPayload;
    pendingPostMatchPayload = null;
    if (nextPayload) {
      renderFeedPayload(nextPayload);
    }
  });
}

if (playersGrid) {
  playersGrid.addEventListener("mouseleave", () => {
    scheduleFeedHoverFlush(90);
  });

  playersGrid.addEventListener("focusout", () => {
    scheduleFeedHoverFlush(120);
  });
}

// Event delegation for player match dropdowns
document.addEventListener("change", (e) => {
  if (e.target.classList.contains("match-select") && e.target.value) {
    window.open(e.target.value, "_blank");
    e.target.value = "";
  }
});

connectFeed();

