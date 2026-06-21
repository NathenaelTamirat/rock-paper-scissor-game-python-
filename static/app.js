const API = "";

let authToken = localStorage.getItem("rps_token") || "";
let authUser = localStorage.getItem("rps_user") || "";

if (authToken) {
  document.getElementById("auth-forms").classList.add("hidden");
  document.getElementById("user-info").classList.remove("hidden");
  document.getElementById("display-username").textContent = authUser;
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
    localStorage.setItem("rps_token", authToken);
    localStorage.setItem("rps_user", authUser);

    document.getElementById("auth-forms").classList.add("hidden");
    document.getElementById("user-info").classList.remove("hidden");
    document.getElementById("display-username").textContent = username;

    document.getElementById("login-username").value = "";
    document.getElementById("login-password").value = "";
  } catch (err) {
    alert("Login failed: " + err.message);
  }
}

function logout() {
  authToken = "";
  authUser = "";
  localStorage.removeItem("rps_token");
  localStorage.removeItem("rps_user");
  document.getElementById("auth-forms").classList.remove("hidden");
  document.getElementById("user-info").classList.add("hidden");
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

loadHistory();
loadStats();
loadLeaderboard();
