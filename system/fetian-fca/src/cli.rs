use crate::{
    client::{call, call_at},
    error::{Error, Result},
    model::*,
    paths::{private_dir, Paths},
};
use serde_json::{json, Value};
use std::{
    fs::{self, OpenOptions},
    io::{Read, Write},
    os::unix::fs::OpenOptionsExt,
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    thread,
    time::{Duration, Instant},
};
pub const HELP:&str="fetian-authority [--json] daemon start [--allow-test-faults] | daemon status | daemon stop\ninput import FILE | contract-template INPUT_ID | create --contract FILE\nlist | inspect ID | run ID --executor rust|python [--barrier-after N]\nhandoff ID --executor rust|python | checkpoint ID | suspend ID | resume ID | cancel ID\nevents ID [--after N] | verify ID | export ID --output FILE | demo-handoff";
fn file(path: &str, limit: usize) -> Result<Vec<u8>> {
    let mut file = OpenOptions::new()
        .read(true)
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(path)?;
    if !file.metadata()?.is_file() || file.metadata()?.len() > limit as u64 {
        return Err(Error::new("FILE_LIMIT", "Expected bounded regular file"));
    }
    let mut out = Vec::new();
    Read::by_ref(&mut file)
        .take(limit as u64 + 1)
        .read_to_end(&mut out)?;
    if out.len() > limit {
        return Err(Error::new("FILE_LIMIT", "File exceeds limit"));
    }
    Ok(out)
}
fn output(path: &str, value: &Value) -> Result<()> {
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(path)?;
    file.write_all(&serde_json::to_vec_pretty(value)?)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    Ok(())
}
fn option<'a>(args: &'a [String], name: &str) -> Result<&'a str> {
    args.iter()
        .position(|arg| arg == name)
        .and_then(|index| args.get(index + 1))
        .map(String::as_str)
        .ok_or_else(|| Error::new("USAGE", format!("Missing {name} value")))
}
fn arg(args: &[String], index: usize) -> Result<&str> {
    args.get(index)
        .map(String::as_str)
        .ok_or_else(|| Error::new("USAGE", HELP))
}
fn wait(socket: &Path, mut predicate: impl FnMut() -> Result<Option<Value>>) -> Result<Value> {
    let deadline = Instant::now() + Duration::from_secs(20);
    loop {
        match predicate() {
            Ok(Some(value)) => return Ok(value),
            Ok(None) => (),
            Err(error) => {
                if socket.exists() {
                    return Err(error);
                }
            }
        }
        if Instant::now() >= deadline {
            return Err(Error::new(
                "WAIT_TIMEOUT",
                "Observable state did not reach expected condition",
            ));
        }
        thread::sleep(Duration::from_millis(10)); // Polls state; elapsed time never authorizes progress.
    }
}
fn start_daemon(faults: bool) -> Result<Value> {
    let paths = Paths::discover()?;
    if call("status", json!({})).is_ok() {
        return Err(Error::new("BROKER_EXISTS", "Broker already running"));
    }
    let log = OpenOptions::new()
        .append(true)
        .create(true)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(paths.state.join("daemon.log"))?;
    let bin = std::env::current_exe()?.with_file_name("fetian-authorityd");
    let mut command = Command::new(bin);
    if faults {
        command.arg("--allow-test-faults");
    }
    let mut child = command
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(log)
        .spawn()?;
    let result = wait(&paths.socket(), || {
        if child.try_wait()?.is_some() {
            return Err(Error::new(
                "BROKER_START_FAILED",
                "Broker exited; inspect private daemon.log",
            ));
        }
        Ok(call("status", json!({})).ok())
    });
    if result.is_err() {
        let _ = child.kill();
        let _ = child.wait();
    }
    result
}
fn export(id: &str) -> Result<Value> {
    let inspection = call("inspect", json!({"id":id}))?;
    let verification = call("verify", json!({"id":id}))?;
    let mut events = Vec::new();
    let mut after = 0;
    loop {
        let page = call("events", json!({"id":id,"after":after}))?;
        let page = page
            .as_array()
            .ok_or_else(|| Error::new("INVALID_RESPONSE", "Expected event array"))?;
        if page.is_empty() {
            break;
        }
        after = page
            .last()
            .and_then(|v| v["event"]["sequence"].as_u64())
            .ok_or_else(|| Error::new("INVALID_RESPONSE", "Missing sequence"))?;
        events.extend(page.iter().cloned());
        if events.len() > 100000 {
            return Err(Error::new("EVENT_LIMIT", "Export limit"));
        }
    }
    if call("verify", json!({"id":id}))? != verification
        || call("inspect", json!({"id":id}))? != inspection
        || events.last().and_then(|v| v["event"]["sequence"].as_u64())
            != verification["events"].as_u64()
    {
        return Err(Error::new(
            "EXPORT_CHANGED",
            "Authority changed during export; suspend it and retry",
        ));
    }
    Ok(
        json!({"schema_version":1,"inspection":inspection,"verification":verification,"events":events,"signature":null}),
    )
}
struct Demo {
    root: PathBuf,
    child: Child,
}
impl Drop for Demo {
    fn drop(&mut self) {
        let socket = self.root.join("runtime/fetian-fca/authority.sock");
        let _ = call_at(&socket, "stop", json!({}));
        let deadline = Instant::now() + Duration::from_secs(3);
        while self.child.try_wait().ok().flatten().is_none() && Instant::now() < deadline {
            thread::sleep(Duration::from_millis(10));
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
        let _ = fs::remove_dir_all(&self.root);
    }
}
pub fn demo() -> Result<Value> {
    let root = std::env::temp_dir().join(new_id("fca-demo")?);
    private_dir(&root)?;
    private_dir(&root.join("state"))?;
    private_dir(&root.join("runtime"))?;
    let child = Command::new(std::env::current_exe()?.with_file_name("fetian-authorityd"))
        .arg("--allow-test-faults")
        .env("XDG_STATE_HOME", root.join("state"))
        .env("XDG_RUNTIME_DIR", root.join("runtime"))
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()?;
    let demo = Demo { root, child };
    let socket = demo.root.join("runtime/fetian-fca/authority.sock");
    wait(&socket, || Ok(call_at(&socket, "status", json!({})).ok()))?;
    let content = (1..=4096)
        .map(|v| format!("{}\n", v - 2048))
        .collect::<String>();
    let direct = Instant::now();
    let expected = parse_input(content.as_bytes())?
        .into_iter()
        .try_fold(0_i64, |sum, v| {
            sum.checked_add(v)
                .ok_or_else(|| Error::new("SUM_OVERFLOW", "Direct overflow"))
        })?;
    let direct_us = direct.elapsed().as_micros();
    let input = call_at(&socket, "import", json!({"content":content}))?;
    let creation = Instant::now();
    let authority = call_at(
        &socket,
        "create",
        json!({"contract":ExecutionContract::reference(input["input_id"].as_str().ok_or_else(||Error::new("INVALID_RESPONSE","Missing input ID"))?.into())}),
    )?;
    let creation_us = creation.elapsed().as_micros();
    let id = authority["id"]
        .as_str()
        .ok_or_else(|| Error::new("INVALID_RESPONSE", "Missing identity"))?;
    let elapsed = Instant::now();
    let first = call_at(
        &socket,
        "run",
        json!({"id":id,"executor":"rust","barrier_after":3}),
    )?;
    let paused = wait(&socket, || {
        let state = call_at(&socket, "inspect", json!({"id":id}))?;
        Ok((state["test_barrier_reached"] == true).then_some(state))
    })?;
    let checkpoint = paused["authority"]["continuation"].clone();
    let old_credential = json!({"executor_id":"rust-reference-v1","lease_id":paused["authority"]["current_executor"]["lease_id"],"epoch":first["epoch"]});
    let previous_events = call_at(&socket, "verify", json!({"id":id}))?["events"].clone();
    let kill_start = Instant::now();
    call_at(&socket, "fault-kill", json!({"id":id}))?;
    let kill_us = kill_start.elapsed().as_micros();
    let kill_events = call_at(&socket, "events", json!({"id":id,"after":previous_events}))?;
    let terminated = kill_events.as_array().is_some_and(|events| {
        events.iter().any(|record| {
            record["event"]["kind"] == "ExecutorTermination"
                && record["event"]["details"]["signal"] == 9
                && record["event"]["details"]["pid"] == first["pid"]
                && record["event"]["details"]["termination_confirmed"] == true
        })
    });
    if !terminated {
        return Err(Error::new(
            "DEMO_FAILED",
            "Rust SIGKILL termination was not confirmed",
        ));
    }
    let after_kill = call_at(&socket, "inspect", json!({"id":id}))?;
    if after_kill["authority"]["continuation"] != checkpoint {
        return Err(Error::new(
            "DEMO_FAILED",
            "Checkpoint changed during executor death",
        ));
    }
    let restart = Instant::now();
    let second = call_at(&socket, "run", json!({"id":id,"executor":"python"}))?;
    let handoff_us = restart.elapsed().as_micros();
    let completed = wait(&socket, || {
        let state = call_at(&socket, "inspect", json!({"id":id}))?;
        if state["authority"]["lifecycle"] == "Failed" {
            return Err(Error::new("DEMO_FAILED", "Python executor failed"));
        }
        Ok((state["authority"]["lifecycle"] == "Completed").then_some(state))
    })?;
    let stale=call_at(&socket,"stale-probe",json!({"id":id,"credential":old_credential,"progress":{"sequence":4,"input_position":192,"next_input_position":256,"accumulated_result":0,"idempotency_key":"chunk-4"}})).unwrap_err();
    let verification = call_at(&socket, "verify", json!({"id":id}))?;
    if completed["authority"]["continuation"]["accumulated_result"] != expected
        || stale.code != "STALE_EPOCH"
        || verification["effects"] != 64
        || second["epoch"].as_u64() <= first["epoch"].as_u64()
    {
        return Err(Error::new(
            "DEMO_FAILED",
            "Result, fencing or unique effects mismatch",
        ));
    }
    let journal_bytes = fs::metadata(demo.root.join("state/fetian-fca/authorities.sqlite3"))?.len();
    Ok(
        json!({"demo":"rust-sigkill-python-resume","passed":true,"rust_termination_confirmed":terminated,"authority_id":id,"rust_pid":first["pid"],"python_pid":second["pid"],"rust_epoch":first["epoch"],"python_epoch":second["epoch"],"checkpoint_at_kill":checkpoint,"expected_result":expected,"actual_result":completed["authority"]["continuation"]["accumulated_result"],"stale_request_error":stale.code,"verification":verification,"resources":second["resources"],"measurements":{"creation_us":creation_us,"kill_and_fence_us":kill_us,"replacement_launch_us":handoff_us,"managed_total_us":elapsed.elapsed().as_micros(),"direct_parse_sum_us":direct_us,"sqlite_main_bytes":journal_bytes},"scope":"managed transactional sum effects only; trusted reference executors; no hostile same-user sandbox"}),
    )
}
pub fn run(args: &[String]) -> Result<Value> {
    match arg(args, 0)? {
        "daemon" => match arg(args, 1)? {
            "start" => start_daemon(args.iter().any(|a| a == "--allow-test-faults")),
            "status" => call("status", json!({})),
            "stop" => call("stop", json!({})),
            _ => Err(Error::new("USAGE", HELP)),
        },
        "input" if arg(args, 1)? == "import" => {
            let bytes = file(arg(args, 2)?, MAX_INPUT_BYTES)?;
            parse_input(&bytes)?;
            call(
                "import",
                json!({"content":String::from_utf8(bytes).map_err(|_|Error::new("INVALID_INPUT","UTF-8 required"))?}),
            )
        }
        "contract-template" => Ok(serde_json::to_value(ExecutionContract::reference(
            arg(args, 1)?.into(),
        ))?),
        "create" => call(
            "create",
            json!({"contract":serde_json::from_slice::<ExecutionContract>(&file(option(args,"--contract")?,32768)?)?}),
        ),
        "list" => call("list", json!({})),
        "inspect" | "checkpoint" | "suspend" | "resume" | "cancel" | "verify" => {
            call(arg(args, 0)?, json!({"id":arg(args,1)?}))
        }
        "events" => call(
            "events",
            json!({"id":arg(args,1)?,"after":option(args,"--after").unwrap_or("0").parse::<u64>().map_err(|_|Error::new("USAGE","Invalid event cursor"))?}),
        ),
        "run" | "handoff" => call(
            arg(args, 0)?,
            json!({"id":arg(args,1)?,"executor":ExecutorId::parse(option(args,"--executor")?)?.name(),"barrier_after":option(args,"--barrier-after").unwrap_or("0").parse::<u64>().map_err(|_|Error::new("USAGE","Invalid barrier"))?}),
        ),
        "export" => {
            let result = export(arg(args, 1)?)?;
            output(option(args, "--output")?, &result)?;
            Ok(json!({"exported":true,"authority_id":arg(args,1)?}))
        }
        "demo-handoff" => demo(),
        _ => Err(Error::new("USAGE", HELP)),
    }
}
