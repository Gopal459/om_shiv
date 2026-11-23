import { spawn, type ChildProcess } from 'node:child_process';
import * as path from 'node:path';
import * as fs from 'node:fs';

const isWin = process.platform === 'win32';
const rootDir = process.cwd();
const backendDir = path.join(rootDir, 'backend');
const frontendDir = path.join(rootDir, 'frontend');

// Detect Python executable in .venv or PATH
function findPython(): string {
  const venvWin = path.join(rootDir, '.venv', 'Scripts', 'python.exe');
  const venvUnix = path.join(rootDir, '.venv', 'bin', 'python');

  if (fs.existsSync(venvWin)) return venvWin;
  if (fs.existsSync(venvUnix)) return venvUnix;
  if (process.env.VIRTUAL_ENV) {
    const customWin = path.join(process.env.VIRTUAL_ENV, 'Scripts', 'python.exe');
    const customUnix = path.join(process.env.VIRTUAL_ENV, 'bin', 'python');
    if (fs.existsSync(customWin)) return customWin;
    if (fs.existsSync(customUnix)) return customUnix;
  }
  return isWin ? 'python' : 'python3';
}

const pythonPath = findPython();
const args = process.argv.slice(2);
const backendOnly = args.includes('--backend-only');
const frontendOnly = args.includes('--frontend-only');

console.log('\x1b[34m==============================================================\x1b[0m');
console.log('\x1b[1m\x1b[36m   OMSHIV BUILDVISION CRM — UNIFIED DEV ENVIRONMENT\x1b[0m');
console.log('\x1b[34m==============================================================\x1b[0m');
console.log(`\x1b[32m✔ Runtime:\x1b[0m      Bun ${Bun.version} (${process.platform})`);
console.log(`\x1b[32m✔ Python:\x1b[0m       ${pythonPath}`);
console.log(`\x1b[32m✔ Backend API:\x1b[0m  http://127.0.0.1:8000 (Swagger: /docs)`);
console.log(`\x1b[32m✔ Frontend UI:\x1b[0m  http://localhost:3000 (Proxies /v1 -> :8000)`);
console.log('\x1b[34m--------------------------------------------------------------\x1b[0m');
console.log('\x1b[33mPress Ctrl+C to stop both backend and frontend servers.\x1b[0m\n');

const runningProcesses: ChildProcess[] = [];

function pipeOutput(stream: NodeJS.ReadableStream | null, prefix: string, color: string) {
  if (!stream) return;
  stream.on('data', (data) => {
    const lines = data.toString().split(/\r?\n/);
    for (const line of lines) {
      if (line.trim().length > 0) {
        console.log(`${color}${prefix}\x1b[0m ${line}`);
      }
    }
  });
}

function startBackend(): ChildProcess {
  console.log('\x1b[36m[backend]\x1b[0m Starting FastAPI uvicorn server on port 8000...');
  const proc = spawn(
    pythonPath,
    ['-m', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', '8000'],
    {
      cwd: backendDir,
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONPATH: backendDir },
      shell: isWin,
    }
  );

  pipeOutput(proc.stdout, '[backend] ', '\x1b[36m');
  pipeOutput(proc.stderr, '[backend] ', '\x1b[36m');

  proc.on('close', (code) => {
    console.log(`\x1b[36m[backend]\x1b[0m Process exited with code ${code}`);
  });

  return proc;
}

function startFrontend(): ChildProcess {
  console.log('\x1b[35m[frontend]\x1b[0m Starting Vite development server on port 3000...');
  // Bun on Windows can run bun directly
  const proc = spawn('bun', ['run', 'dev'], {
    cwd: frontendDir,
    env: process.env,
    shell: isWin,
  });

  pipeOutput(proc.stdout, '[frontend]', '\x1b[35m');
  pipeOutput(proc.stderr, '[frontend]', '\x1b[35m');

  proc.on('close', (code) => {
    console.log(`\x1b[35m[frontend]\x1b[0m Process exited with code ${code}`);
  });

  return proc;
}

if (!frontendOnly) {
  runningProcesses.push(startBackend());
}

if (!backendOnly) {
  runningProcesses.push(startFrontend());
}

function cleanup() {
  console.log('\n\x1b[33mShutting down Omshiv CRM dev servers...\x1b[0m');
  for (const proc of runningProcesses) {
    if (proc.pid) {
      if (isWin) {
        try {
          spawn('taskkill', ['/pid', proc.pid.toString(), '/f', '/t'], { stdio: 'ignore' });
        } catch {
          // ignore error if already killed
        }
      }
      try {
        proc.kill('SIGINT');
      } catch {
        // ignore
      }
    }
  }
}

process.on('SIGINT', () => {
  cleanup();
  process.exit(0);
});

process.on('SIGTERM', () => {
  cleanup();
  process.exit(0);
});
