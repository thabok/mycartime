use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent, State};

/// Where a developer-run backend (run.sh) listens, used when there is no
/// compiled sidecar to spawn.
const DEFAULT_PORT: u16 = 1338;
const BACKEND_STARTUP_TIMEOUT: Duration = Duration::from_secs(90);

/// Populated once the sidecar (or dev backend) is confirmed reachable. Managed
/// synchronously in `setup` (unlike the port/child themselves) so `backend_port`
/// can be invoked - and answer "not ready yet" rather than error out entirely -
/// from the moment the window appears, instead of only once startup finishes.
struct Backend {
    port: u16,
    ready: Mutex<bool>,
    child: Mutex<Option<Child>>,
    /// Held open purely so the backend sees EOF when this process goes away,
    /// which is the only shutdown signal that survives a crash or force-quit.
    _stdin: Mutex<Option<ChildStdin>>,
}

/// The frontend asks for this at startup because the sidecar does not always
/// get the default port (see `pick_port`), and polls it until it returns
/// `Some` because startup (spawning the sidecar, waiting for it to bind its
/// port) happens on a background thread rather than blocking the window from
/// appearing.
#[tauri::command]
fn backend_port(backend: State<Backend>) -> Option<u16> {
    if *backend.ready.lock().unwrap() {
        Some(backend.port)
    } else {
        None
    }
}

fn pick_port() -> u16 {
    // Always take an OS-assigned port rather than probing the backend's default:
    // on macOS a probe of 127.0.0.1 succeeds even while another process holds
    // 0.0.0.0 on the same port, so "is 1338 free" cannot be answered reliably.
    // The frontend learns the real port through the `backend_port` command.
    TcpListener::bind(("127.0.0.1", 0))
        .and_then(|listener| listener.local_addr())
        .map(|addr| addr.port())
        .expect("no free TCP port available")
}

fn backend_executable(app: &tauri::AppHandle) -> Option<PathBuf> {
    let name = if cfg!(windows) {
        "mycartime-backend.exe"
    } else {
        "mycartime-backend"
    };

    // The bundler copies the contents of the Nuitka dist directory into
    // "backend", so the executable sits directly inside it.
    if let Ok(dir) = app.path().resource_dir() {
        let bundled = dir.join("backend").join(name);
        if bundled.exists() {
            return Some(bundled);
        }
    }

    // `tauri dev` does not stage bundle resources, so fall back to the Nuitka
    // output in the repo. If that is missing too, the developer is running the
    // backend themselves and we leave it alone.
    let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../backend/dist/app.dist")
        .join(name);
    dev.exists().then_some(dev)
}

fn wait_for_backend(port: u16) {
    let deadline = Instant::now() + BACKEND_STARTUP_TIMEOUT;
    while Instant::now() < deadline {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    eprintln!("backend did not become reachable on port {port}");
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .invoke_handler(tauri::generate_handler![backend_port])
        .setup(|app| {
            match backend_executable(app.handle()) {
                Some(executable) => {
                    // Spawning the sidecar and waiting for it to bind its port
                    // can take the better part of a minute for a cold Nuitka
                    // build (importing ortools/numpy from disk). Doing that
                    // here, synchronously, would block the window from ever
                    // appearing - `setup` runs before the event loop starts
                    // pumping, so the OS sees an unresponsive, unpainted
                    // window for the whole wait. Do it on a background thread
                    // instead and let the frontend poll `backend_port` and
                    // show its own loading state until it's ready.
                    let port = pick_port();
                    let data_dir = app.path().app_data_dir()?;
                    std::fs::create_dir_all(&data_dir)?;

                    app.manage(Backend {
                        port,
                        ready: Mutex::new(false),
                        child: Mutex::new(None),
                        _stdin: Mutex::new(None),
                    });

                    let app_handle = app.handle().clone();
                    std::thread::spawn(move || {
                        let mut child = match Command::new(executable)
                            .env("APP_DATA_DIR", &data_dir)
                            .env("BACKEND_PORT", port.to_string())
                            .env("BACKEND_HOST", "127.0.0.1")
                            .env("SUPERVISED", "1")
                            .stdin(Stdio::piped())
                            .spawn()
                        {
                            Ok(child) => child,
                            Err(err) => {
                                eprintln!("failed to spawn backend: {err}");
                                return;
                            }
                        };
                        let stdin = child.stdin.take();
                        wait_for_backend(port);

                        let backend = app_handle.state::<Backend>();
                        *backend.child.lock().unwrap() = Some(child);
                        *backend._stdin.lock().unwrap() = stdin;
                        *backend.ready.lock().unwrap() = true;
                    });
                }
                None => {
                    app.manage(Backend {
                        port: DEFAULT_PORT,
                        ready: Mutex::new(true),
                        child: Mutex::new(None),
                        _stdin: Mutex::new(None),
                    });
                }
            };

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build the application")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                if let Some(backend) = app.try_state::<Backend>() {
                    if let Some(mut child) = backend.child.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                }
            }
        });
}
