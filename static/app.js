var API = typeof API_BASE_URL !== "undefined" ? API_BASE_URL : "";

let authToken = localStorage.getItem("rps_token") || "";
let authUser = localStorage.getItem("rps_user") || "";
let authUserId = parseInt(localStorage.getItem("rps_user_id") || "0", 10);

if (authToken) {
  document.getElementById("auth-forms").classList.add("hidden");
  document.getElementById("user-info").classList.remove("hidden");
  document.getElementById("display-username").textContent = authUser;
}

let currentRoom = null;
let roomPollInterval = null;

let chartMoves = null;
let chartResults = null;
let chartTimeline = null;

function showRoomLobby() {
  document.getElementById("mp-lobby").classList.remove("hidden");
  document.getElementById("room-view").classList.add("hidden");
}

function showRoomView() {
  document.getElementById("mp-lobby").classList.add("hidden");
  document.getElementById("room-view").classList.remove("hidden");
}

async function createRoom() {
  if (!authToken) return alert("You must be logged in to play multiplayer.");
  try {
    const data = await api("POST", "/rooms");
    currentRoom = data.room_code;
    document.getElementById("room-code-display").textContent = currentRoom;
    showRoomView();
    renderRoomState({ status: "waiting", player_a_username: authUser, player_b_id: null });
    startRoomPolling();
  } catch (err) {
    alert("Failed to create room: " + err.message);
  }
}

async function joinRoom() {
  if (!authToken) return alert("You must be logged in to play multiplayer.");
  const code = document.getElementById("room-code-input").value.trim().toUpperCase();
  if (!code) return alert("Enter a room code.");
  try {
    const data = await api("POST", "/rooms/" + code + "/join");
    currentRoom = data.room_code;
    document.getElementById("room-code-display").textContent = currentRoom;
    showRoomView();
    renderRoomState({ ...data, move_a_submitted: false, move_b_submitted: false });
    startRoomPolling();
  } catch (err) {
    alert("Failed to join room: " + err.message);
  }
}

async function playRoom(move) {
  if (!currentRoom) return;
  try {
    const data = await api("POST", "/rooms/" + currentRoom + "/play", { move });
    if (data.status === "complete") {
      stopRoomPolling();
    }
    await loadRoom();
  } catch (err) {
    alert("Failed to play: " + err.message);
  }
}

async function loadRoom() {
  if (!currentRoom) return;
  try {
    const data = await api("GET", "/rooms/" + currentRoom);
    renderRoomState(data);
    if (data.status === "complete") {
      stopRoomPolling();
    }
  } catch {
    leaveRoom();
  }
}

function renderRoomState(data) {
  document.getElementById("room-players").textContent =
    data.player_a_username +
    (data.player_b_username ? " vs " + data.player_b_username : " (waiting for opponent...)");

  const statusEl = document.getElementById("room-status-text");
  if (data.status === "waiting") statusEl.textContent = "Waiting for opponent...";
  else if (data.status === "playing") statusEl.textContent = "In progress";
  else statusEl.textContent = "Complete";

  const moveBtns = document.getElementById("room-move-buttons");
  const resultEl = document.getElementById("room-result");
  resultEl.classList.add("hidden");

  if (data.status === "playing") {
    const myId = data.player_a_username === authUser
      ? data.player_a_id : data.player_b_id;
    const iAmA = data.player_a_id === myId;
    const mySubmitted = iAmA ? data.move_a_submitted : data.move_b_submitted;

    if (mySubmitted) {
      moveBtns.classList.add("hidden");
      statusEl.textContent = "Waiting for opponent's move...";
    } else {
      moveBtns.classList.remove("hidden");
    }
  } else if (data.status === "complete") {
    moveBtns.classList.add("hidden");
    resultEl.classList.remove("hidden");
    const myId = data.player_a_username === authUser
      ? data.player_a_id : data.player_b_id;
    const iAmA = data.player_a_id === myId;
    const iWon = data.winner === "player_a" && iAmA || data.winner === "player_b" && !iAmA;
    const isDraw = data.winner === "draw";
    if (isDraw) resultEl.innerHTML = "<strong>It's a draw!</strong>";
    else if (iWon) resultEl.innerHTML = "<strong>You won!</strong>";
    else resultEl.innerHTML = "<strong>You lost!</strong>";
  } else {
    moveBtns.classList.add("hidden");
  }
}

function startRoomPolling() {
  stopRoomPolling();
  roomPollInterval = setInterval(loadRoom, 2000);
}

function stopRoomPolling() {
  if (roomPollInterval) {
    clearInterval(roomPollInterval);
    roomPollInterval = null;
  }
}

let mmPollInterval = null;

async function findMatch() {
  if (!authToken) return alert("You must be logged in to play multiplayer.");
  try {
    await api("POST", "/matchmaking/join", { preferred_mode: "classic" });
    document.getElementById("mp-lobby").classList.add("hidden");
    document.getElementById("matchmaking-waiting").classList.remove("hidden");
    startMMPolling();
  } catch (err) {
    alert("Failed to join matchmaking: " + err.message);
  }
}

async function cancelMatchmaking() {
  stopMMPolling();
  try {
    await api("POST", "/matchmaking/leave");
  } catch {
    // ignore
  }
  document.getElementById("matchmaking-waiting").classList.add("hidden");
  document.getElementById("mp-lobby").classList.remove("hidden");
}

async function checkMatchingStatus() {
  if (!authUserId) return;
  try {
    const data = await api("GET", "/matchmaking/status/" + authUserId);
    if (data.status === "searching") {
      const posEl = document.getElementById("mm-position");
      posEl.textContent = "Position in queue: " + (data.position || "?");
    } else if (data.status === "matched") {
      stopMMPolling();
      document.getElementById("matchmaking-waiting").classList.add("hidden");
      document.getElementById("mp-lobby").classList.remove("hidden");
      // Auto-join the matched room
      currentRoom = data.room_code;
      document.getElementById("room-code-display").textContent = currentRoom;
      try {
        const roomData = await api("GET", "/rooms/" + currentRoom);
        showRoomView();
        renderRoomState(roomData);
        startRoomPolling();
      } catch {
        alert("Failed to load matched room.");
      }
    }
  } catch {
    // ignore polling errors
  }
}

function startMMPolling() {
  stopMMPolling();
  checkMatchingStatus();
  mmPollInterval = setInterval(checkMatchingStatus, 2000);
}

function stopMMPolling() {
  if (mmPollInterval) {
    clearInterval(mmPollInterval);
    mmPollInterval = null;
  }
}

function leaveRoom() {
  currentRoom = null;
  stopRoomPolling();
  showRoomLobby();
  document.getElementById("room-code-input").value = "";
  document.getElementById("room-result").classList.add("hidden");
  document.getElementById("room-move-buttons").classList.add("hidden");
}

async function api(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (authToken) {
    opts.headers["Authorization"] = "Bearer " + authToken;
  }
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(API + path, opts);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

async function play(move) {
  document.getElementById("loading").classList.remove("hidden");
  document.getElementById("result-section").classList.add("hidden");

  try {
    const persona = document.getElementById("persona-select").value;
    const data = await api("POST", "/play", { player_move: move, persona });

    document.getElementById("result-section").classList.remove("hidden");
    const emojis = { rock: "✊", paper: "✋", scissors: "✌️" };
    const resultMap = {
      player: "You win!",
      bot: "Bot wins!",
      draw: "It's a draw!",
    };
    document.getElementById("result-text").innerHTML =
      `${emojis[data.player_move]}  ${data.player_move} vs ` +
      `${data.bot_move} ${emojis[data.bot_move]}<br>` +
      `<strong>${resultMap[data.winner]}</strong>`;

    document.getElementById("score-section").classList.remove("hidden");
    document.getElementById("score-wins").textContent = data.score.wins;
    document.getElementById("score-losses").textContent = data.score.losses;
    document.getElementById("score-draws").textContent = data.score.draws;

    loadHistory();
    loadLeaderboard();
    loadAnalytics();
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    document.getElementById("loading").classList.add("hidden");
  }
}

async function loadStats() {
  try {
    const data = await api("GET", "/history");
    if (data.stats) {
      document.getElementById("score-section").classList.remove("hidden");
      document.getElementById("score-wins").textContent = data.stats.wins;
      document.getElementById("score-losses").textContent = data.stats.losses;
      document.getElementById("score-draws").textContent = data.stats.draws;
    }
  } catch {
    // silently ignore
  }
}

async function loadHistory() {
  try {
    const data = await api("GET", "/history");
    const list = document.getElementById("history-list");
    const rounds = data.latest_10 || [];
    if (rounds.length === 0) return;

    document.getElementById("history-section").classList.remove("hidden");
    list.innerHTML = rounds
      .map((r) => {
        const w = r.winner === "player" ? "Win" : r.winner === "bot" ? "Loss" : "Draw";
        return `<li>${r.player_move} vs ${r.bot_move} — <strong>${w}</strong></li>`;
      })
      .join("");
  } catch {
    // silently ignore
  }
}

async function loadLeaderboard() {
  try {
    const data = await api("GET", "/leaderboard?limit=10");
    const entries = data.leaderboard || [];
    if (entries.length === 0) return;

    document.getElementById("leaderboard-section").classList.remove("hidden");
    const tbody = document.getElementById("leaderboard-body");
    tbody.innerHTML = entries
      .map(
        (e, i) =>
          `<tr><td>${i + 1}</td><td>${e.username}</td><td>${e.wins}</td>` +
          `<td>${e.losses}</td><td>${(e.win_rate * 100).toFixed(1)}%</td>` +
          `<td>${e.streak}</td></tr>`
      )
      .join("");
  } catch {
    // silently ignore
  }
}

async function register() {
  const username = document.getElementById("reg-username").value.trim();
  const password = document.getElementById("reg-password").value;
  if (!username || !password) return alert("Fill in both fields.");

  try {
    await api("POST", "/register", { username, password });
    alert("Registered! You can now log in.");
    document.getElementById("reg-username").value = "";
    document.getElementById("reg-password").value = "";
  } catch (err) {
    alert("Registration failed: " + err.message);
  }
}

async function login() {
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  if (!username || !password) return alert("Fill in both fields.");

  try {
    const data = await api("POST", "/login", { username, password });
    authToken = data.token;
    authUser = username;
    authUserId = data.user_id;
    localStorage.setItem("rps_token", authToken);
    localStorage.setItem("rps_user", authUser);
    localStorage.setItem("rps_user_id", String(authUserId));

    document.getElementById("auth-forms").classList.add("hidden");
    document.getElementById("user-info").classList.remove("hidden");
    document.getElementById("display-username").textContent = username;

    document.getElementById("login-username").value = "";
    document.getElementById("login-password").value = "";
    loadAnalytics();
  } catch (err) {
    alert("Login failed: " + err.message);
  }
}

function logout() {
  authToken = "";
  authUser = "";
  authUserId = 0;
  localStorage.removeItem("rps_token");
  localStorage.removeItem("rps_user");
  localStorage.removeItem("rps_user_id");
  document.getElementById("auth-forms").classList.remove("hidden");
  document.getElementById("user-info").classList.add("hidden");
  loadAnalytics();
}

async function resetGame() {
  try {
    await api("POST", "/reset");
    document.getElementById("result-section").classList.add("hidden");
    document.getElementById("score-section").classList.add("hidden");
    document.getElementById("history-section").classList.add("hidden");
    document.getElementById("score-wins").textContent = "0";
    document.getElementById("score-losses").textContent = "0";
    document.getElementById("score-draws").textContent = "0";
    document.getElementById("history-list").innerHTML = "";
  } catch (err) {
    alert("Reset failed: " + err.message);
  }
}

let currentTournament = null;

function showTLobby() {
  document.getElementById("t-lobby").classList.remove("hidden");
  document.getElementById("t-view").classList.add("hidden");
}

function showTView() {
  document.getElementById("t-lobby").classList.add("hidden");
  document.getElementById("t-view").classList.remove("hidden");
}

async function createTournament() {
  if (!authToken) return alert("You must be logged in.");
  const name = document.getElementById("t-name-input").value.trim();
  if (!name) return alert("Enter a tournament name.");
  try {
    const data = await api("POST", "/tournaments", { name, max_players: 4 });
    currentTournament = data.code;
    document.getElementById("t-name-display").textContent = data.name;
    document.getElementById("t-code-display").textContent = data.code;
    showTView();
    renderTournament(data);
  } catch (err) {
    alert("Failed to create tournament: " + err.message);
  }
}

async function joinTournament() {
  if (!authToken) return alert("You must be logged in.");
  const code = document.getElementById("t-code-input").value.trim().toUpperCase();
  if (!code) return alert("Enter a tournament code.");
  try {
    const data = await api("POST", "/tournaments/" + code + "/join");
    currentTournament = data.code;
    document.getElementById("t-name-display").textContent = data.name;
    document.getElementById("t-code-display").textContent = data.code;
    showTView();
    renderTournament(data);
  } catch (err) {
    alert("Failed to join tournament: " + err.message);
  }
}

async function runTournament() {
  if (!currentTournament) return;
  try {
    const data = await api("POST", "/tournaments/" + currentTournament + "/run");
    renderTournament(data);
  } catch (err) {
    alert("Failed to run tournament: " + err.message);
  }
}

async function loadTournament() {
  if (!currentTournament) return;
  try {
    const data = await api("GET", "/tournaments/" + currentTournament);
    renderTournament(data);
  } catch {
    currentTournament = null;
    showTLobby();
  }
}

function renderTournament(data) {
  document.getElementById("t-players").textContent =
    data.players.map(function(p) { return p.username; }).join(", ") || "(none)";

  const sEl = document.getElementById("t-status-text");
  if (data.status === "waiting") sEl.textContent = "Waiting for players...";
  else if (data.status === "active") sEl.textContent = "In progress";
  else sEl.textContent = "Complete";

  document.getElementById("t-run-btn").classList.toggle("hidden", data.status !== "waiting");

  const bracketEl = document.getElementById("t-bracket");
  const matchesEl = document.getElementById("t-matches");
  const winnerEl = document.getElementById("t-winner");

  if (data.matches && data.matches.length > 0) {
    bracketEl.classList.remove("hidden");
    matchesEl.innerHTML = data.matches.map(function(m) {
      var pA = m.player_a_username || "TBD";
      var pB = m.player_b_username || "TBD";
      var score = m.status === "complete"
        ? "[" + m.score_a + " - " + m.score_b + "]"
        : "";
      var w = m.winner_username ? " Winner: " + m.winner_username : "";
      var r = m.round === 1 ? "Semifinal" : "Final";
      return "<div class='match-card'>" +
        "<strong>" + r + " " + (m.match_index + 1) + "</strong>: " +
        pA + " vs " + pB + " " + score + w +
        "</div>";
    }).join("");

    if (data.winner_username) {
      winnerEl.classList.remove("hidden");
      winnerEl.innerHTML = "<strong>Champion: " + data.winner_username + "</strong>";
    }
  }
}

var CHART_COLORS = ["#4e79a7", "#f28e2b", "#e15759"];

async function loadAnalytics() {
  try {
    const summary = await api("GET", "/analytics/summary");
    document.getElementById("an-win-rate").textContent =
      (summary.win_rate * 100).toFixed(1) + "%";
    document.getElementById("an-fav-move").textContent =
      summary.favorite_move || "-";
    document.getElementById("an-streak").textContent = summary.streak;
    document.getElementById("an-total").textContent = summary.total_rounds;

    document.getElementById("analytics-section").classList.remove("hidden");
  } catch {
    document.getElementById("analytics-section").classList.add("hidden");
    return;
  }

  try {
    const moves = await api("GET", "/analytics/moves");
    const dist = moves.distribution || [];
    if (chartMoves) chartMoves.destroy();
    chartMoves = new Chart(document.getElementById("chart-moves"), {
      type: "pie",
      data: {
        labels: dist.map(function(d) { return d.move; }),
        datasets: [{
          data: dist.map(function(d) { return d.count; }),
          backgroundColor: CHART_COLORS,
        }],
      },
      options: { responsive: false, plugins: { legend: { position: "bottom" } } },
    });
  } catch {}
  try {
    const timeline = await api("GET", "/analytics/timeline?days=7");
    const tl = timeline.timeline || [];
    if (chartResults) chartResults.destroy();
    chartResults = new Chart(document.getElementById("chart-results"), {
      type: "bar",
      data: {
        labels: ["Wins", "Losses", "Draws"],
        datasets: [{
          data: [
            tl.reduce(function(s, d) { return s + d.wins; }, 0),
            tl.reduce(function(s, d) { return s + d.losses; }, 0),
            tl.reduce(function(s, d) { return s + d.draws; }, 0),
          ],
          backgroundColor: CHART_COLORS,
        }],
      },
      options: {
        responsive: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
      },
    });
    if (tl.length > 0) {
      if (chartTimeline) chartTimeline.destroy();
      chartTimeline = new Chart(document.getElementById("chart-timeline"), {
        type: "line",
        data: {
          labels: tl.map(function(d) { return d.day; }),
          datasets: [{
            label: "Games",
            data: tl.map(function(d) { return d.games; }),
            borderColor: "#4e79a7",
            backgroundColor: "rgba(78, 121, 167, 0.1)",
            fill: true,
            tension: 0.3,
          }],
        },
        options: {
          responsive: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
        },
      });
    }
  } catch {}
}

loadHistory();
loadStats();
loadLeaderboard();
loadAnalytics();
