const { app, BrowserWindow } = require("electron");
const { spawn, execSync } = require("child_process");
const path = require("path");
const http = require("http");

let mainWindow = null;
let pythonProcess = null;

const BACKEND_PORT = 8542;
const BACKEND_URL = "http://127.0.0.1:" + BACKEND_PORT;

function findPython() {
  const candidates = ["python3", "python"];
  for (const cmd of candidates) {
    try {
      execSync(cmd + " --version", { stdio: "ignore" });
      return cmd;
    } catch {
      continue;
    }
  }
  return "python3";
}

function startBackend() {
  const python = findPython();
  const projectRoot = path.join(__dirname, "..");
  const dbPath = path.join(app.getPath("userData"), "rps.db");
  const env = Object.assign({}, process.env, { RPS_DB_PATH: dbPath });

  const args = [
    "-m", "uvicorn", "app.main:app",
    "--host", "127.0.0.1",
    "--port", String(BACKEND_PORT),
    "--log-level", "warning",
  ];

  pythonProcess = spawn(python, args, {
    cwd: projectRoot,
    env: env,
    stdio: ["ignore", "pipe", "pipe"],
  });

  pythonProcess.stdout.on("data", function (data) {
    const text = data.toString().trim();
    if (text) console.log("[backend]", text);
  });

  pythonProcess.stderr.on("data", function (data) {
    const text = data.toString().trim();
    if (text) console.log("[backend]", text);
  });

  pythonProcess.on("exit", function (code) {
    console.log("[backend] exited with code", code);
    pythonProcess = null;
  });
}

function waitForBackend(retries, callback) {
  if (retries <= 0) {
    console.error("[electron] Backend failed to start");
    app.quit();
    return;
  }

  var req = http.get(BACKEND_URL + "/health", function (res) {
    if (res.statusCode === 200) {
      console.log("[electron] Backend is ready");
      callback();
    } else {
      setTimeout(function () { waitForBackend(retries - 1, callback); }, 500);
    }
  });

  req.on("error", function () {
    setTimeout(function () { waitForBackend(retries - 1, callback); }, 500);
  });

  req.setTimeout(2000, function () {
    req.destroy();
    setTimeout(function () { waitForBackend(retries - 1, callback); }, 500);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 860,
    height: 780,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  mainWindow.loadURL(BACKEND_URL);

  mainWindow.on("closed", function () {
    mainWindow = null;
  });
}

app.on("ready", function () {
  startBackend();
  setTimeout(function () { waitForBackend(30, createWindow); }, 1000);
});

app.on("window-all-closed", function () {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", function () {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on("before-quit", function () {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
});
