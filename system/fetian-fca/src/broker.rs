//! One coordinator owns every SQLite transaction and every child handle.
use crate::{
    error::{Error, Result},
    model::*,
    paths::Paths,
    resources::ResourceAdapter,
    store::{Credential, Progress, Store},
    wire::{self, Request, Response},
};
use nix::{
    sys::signal::{killpg, Signal},
    unistd::Pid,
};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    fs::{self, OpenOptions},
    os::{
        fd::OwnedFd,
        unix::{
            fs::{OpenOptionsExt, PermissionsExt},
            net::{UnixListener, UnixStream},
        },
    },
    process::{Child, Command, Stdio},
    sync::mpsc::{self, SyncSender},
    thread,
    time::{Duration, Instant},
};
struct Active {
    child: Child,
    stream: UnixStream,
    lease: RuntimeLease,
    last_request: u64,
    barrier: bool,
}
struct Message {
    id: String,
    epoch: u64,
    request: Result<Request>,
}
pub struct Broker {
    store: Store,
    active: BTreeMap<String, Active>,
    resources: ResourceAdapter,
    sender: SyncSender<Message>,
    test_faults: bool,
    stopping: bool,
    crash_at: BTreeMap<String, String>,
    commit_times: Vec<u64>,
    recovery_us: u64,
}
fn ticks(pid: u32) -> Result<(char, u64)> {
    let text = fs::read_to_string(format!("/proc/{pid}/stat"))?;
    let fields: Vec<_> = text
        .rsplit_once(')')
        .ok_or_else(|| Error::new("PROCESS_IDENTITY", "Invalid proc stat"))?
        .1
        .split_whitespace()
        .collect();
    let state = fields
        .first()
        .and_then(|s| s.chars().next())
        .ok_or_else(|| Error::new("PROCESS_IDENTITY", "Missing process state"))?;
    let start = fields
        .get(19)
        .and_then(|s| s.parse().ok())
        .ok_or_else(|| Error::new("PROCESS_IDENTITY", "Missing process start time"))?;
    Ok((state, start))
}
fn prior_alive(authority: &ContinuationAuthority) -> bool {
    let lease = authority
        .current_executor
        .as_ref()
        .or_else(|| authority.previous_executors.last());
    let Some(lease) = lease else {
        return false;
    };
    match (lease.pid, lease.process_start_ticks) {
        (Some(pid), Some(start)) => match ticks(pid) {
            Ok((state, actual)) => actual == start && state != 'Z' && state != 'X',
            Err(_) => {
                !matches!(fs::metadata(format!("/proc/{pid}")),Err(error) if error.kind()==std::io::ErrorKind::NotFound)
            }
        },
        _ => false, // No worker was gated into execution before its PID was committed.
    }
}
fn stop_owned(active: &mut Active) -> Result<Option<i32>> {
    use std::os::unix::process::ExitStatusExt;
    let pid = Pid::from_raw(active.child.id() as i32);
    let already_exited = active.child.try_wait()?;
    if already_exited.is_none() {
        match killpg(pid, Signal::SIGKILL) {
            Ok(()) | Err(nix::errno::Errno::ESRCH) => (),
            Err(_) => {
                return Err(Error::new(
                    "STOP_UNPROVEN",
                    "Cannot stop owned executor group",
                ))
            }
        }
    }
    let status = match already_exited {
        Some(status) => status,
        None => active.child.wait()?,
    };
    let _ = active.stream.shutdown(std::net::Shutdown::Both);
    // Trusted v1 executors do not fork. Check the entire group before replacement.
    for entry in fs::read_dir("/proc")? {
        let entry = entry?;
        let Some(pid) = entry
            .file_name()
            .to_str()
            .and_then(|s| s.parse::<u32>().ok())
        else {
            continue;
        };
        if let Ok(text) = fs::read_to_string(format!("/proc/{pid}/stat")) {
            if let Some((_, tail)) = text.rsplit_once(')') {
                let fields: Vec<_> = tail.split_whitespace().collect();
                if fields.get(2).and_then(|v| v.parse::<u32>().ok()) == Some(active.child.id())
                    && fields.first().is_some_and(|s| *s != "Z" && *s != "X")
                {
                    return Err(Error::new(
                        "STOP_UNPROVEN",
                        "An executor descendant remains alive",
                    ));
                }
            }
        }
    }
    Ok(status.signal())
}
impl Broker {
    fn revoke(&mut self, id: &str, next: Lifecycle, reason: &str) -> Result<()> {
        self.store.begin_revoke(id, reason)?; // This FULL transaction MUST precede signals.
        if let Some(mut active) = self.active.remove(id) {
            match stop_owned(&mut active) {
                Err(error) => {
                    self.store.finish_revoke(id, Lifecycle::Orphaned)?;
                    return Err(error);
                }
                Ok(signal) => self.store.audit(
                    id,
                    "ExecutorTermination",
                    json!({"pid":active.child.id(),"signal":signal,"termination_confirmed":true}),
                )?,
            }
        } else if prior_alive(&self.store.get(id)?) {
            self.store.finish_revoke(id, Lifecycle::Orphaned)?;
            return Err(Error::new(
                "STOP_UNPROVEN",
                "Stored process identity is still alive; it was not signalled",
            ));
        }
        self.store.finish_revoke(id, next)
    }
    fn start(&mut self, id: &str, executor: ExecutorId, barrier: u64) -> Result<Value> {
        if self.active.len() >= 8 {
            return Err(Error::new(
                "EXECUTOR_LIMIT",
                "At most eight active executors",
            ));
        }
        if barrier > 0 && !self.test_faults {
            return Err(Error::new(
                "FAULTS_DISABLED",
                "Test barriers require --allow-test-faults",
            ));
        }
        let authority = self.store.get(id)?;
        if authority.lifecycle != Lifecycle::Ready {
            return Err(Error::new(
                "INVALID_STATE",
                "Resume or recover authority before running",
            ));
        }
        let resource = self
            .resources
            .prepare(&authority.id, &authority.contract.resource_budget)?;
        let bin = std::env::current_exe()?
            .parent()
            .ok_or_else(|| Error::new("EXECUTOR_MISSING", "No binary directory"))?
            .to_owned();
        let launcher = bin.join("fetian-fca-launcher");
        let mut command = Command::new(launcher);
        match executor {
            ExecutorId::Rust => {
                command.arg(bin.join("fetian-executor-rust"));
            }
            ExecutorId::Python => {
                command
                    .arg("/usr/bin/python3")
                    .arg("-I")
                    .arg(bin.join("fetian-executor-python.py"));
            }
        }
        let lease = self.store.issue_lease(id, executor)?;
        let (mut stream, worker) = UnixStream::pair()?;
        stream.set_read_timeout(Some(Duration::from_secs(3)))?;
        stream.set_write_timeout(Some(Duration::from_secs(3)))?;
        let stdin: OwnedFd = worker.try_clone()?.into();
        let stdout: OwnedFd = worker.into();
        let child = command
            .stdin(Stdio::from(stdin))
            .stdout(Stdio::from(stdout))
            .stderr(Stdio::null())
            .env_clear()
            .env("PATH", "/usr/bin:/bin")
            .env("LANG", "C.UTF-8")
            .current_dir("/")
            .spawn();
        let mut child = match child {
            Ok(child) => child,
            Err(error) => {
                self.store.begin_revoke(id, "spawn-failed")?;
                self.store.finish_revoke(id, Lifecycle::Failed)?;
                return Err(error.into());
            }
        };
        let setup = (|| -> Result<()> {
            let ready: Value = wire::read(&mut stream)?;
            if ready != json!({"version":1,"launcher_ready":true}) {
                return Err(Error::new(
                    "BOOTSTRAP_FAILED",
                    "Launcher did not establish process lifetime",
                ));
            }
            self.resources.attach(&authority.id, child.id())?;
            self.store.started(id, child.id(), ticks(child.id())?.1)?;
            self.store
                .audit(id, "ResourceEnforcement", resource.clone())?;
            wire::write(
                &mut stream,
                &json!({"version":1,"gate":"resources-attached"}),
            )?;
            wire::write(
                &mut stream,
                &json!({"version":1,"workload":"fetian.sum-i64/v1","credential":Credential{executor_id:executor,lease_id:lease.lease_id.clone(),epoch:lease.epoch},"checkpoint":authority.continuation,"barrier_after":barrier}),
            )?;
            Ok(())
        })();
        if let Err(error) = setup {
            let _ = killpg(Pid::from_raw(child.id() as i32), Signal::SIGKILL);
            let _ = child.kill();
            let _ = child.wait();
            self.store.begin_revoke(id, "bootstrap-failed")?;
            self.store.finish_revoke(id, Lifecycle::Failed)?;
            return Err(error);
        }
        let mut reader = stream.try_clone()?;
        reader.set_read_timeout(None)?;
        let sender = self.sender.clone();
        let identity = id.to_owned();
        let epoch = lease.epoch;
        thread::spawn(move || loop {
            let request = wire::read::<Request>(&mut reader);
            let failed = request.is_err();
            if sender
                .send(Message {
                    id: identity.clone(),
                    epoch,
                    request,
                })
                .is_err()
                || failed
            {
                break;
            }
        });
        let pid = child.id();
        self.active.insert(
            id.to_owned(),
            Active {
                child,
                stream,
                lease: RuntimeLease::new(lease),
                last_request: 0,
                barrier: false,
            },
        );
        Ok(
            json!({"authority_id":id,"pid":pid,"epoch":epoch,"executor":executor,"resources":resource}),
        )
    }
    fn worker_request(&mut self, id: &str, request: &Request) -> Result<Value> {
        if request.version != 1 {
            return Err(Error::new(
                "UNSUPPORTED_VERSION",
                "Protocol version must be 1",
            ));
        }
        let active = self
            .active
            .get_mut(id)
            .ok_or_else(|| Error::new("LEASE_REVOKED", "No active executor"))?;
        if request.request_id != active.last_request + 1
            || request.request_id > 4096
            || (request.request_id == 1) != (request.operation == "hello")
        {
            return Err(Error::new(
                "REQUEST_ORDER",
                "Begin with one hello; request IDs must increase by one and remain bounded",
            ));
        }
        active.last_request = request.request_id;
        let credential: Credential =
            serde_json::from_value(request.arguments["credential"].clone())?;
        active
            .lease
            .validate(credential.epoch, &credential.lease_id, Instant::now())?;
        if credential.executor_id != active.lease.record.executor_id {
            return Err(Error::new("LEASE_REVOKED", "Executor identity mismatch"));
        }
        active.lease.renew();
        let args = &request.arguments;
        match request.operation.as_str() {
            "hello" => {
                wire::fields(args, &["credential", "workload"])?;
                if args["workload"] != "fetian.sum-i64/v1" {
                    return Err(Error::new("INCOMPATIBLE_EXECUTOR", "Workload ABI mismatch"));
                }
                Ok(json!({"accepted":true}))
            }
            "read" => {
                wire::fields(args, &["credential", "position"])?;
                self.store.read_chunk(
                    id,
                    &credential,
                    args["position"]
                        .as_u64()
                        .ok_or_else(|| Error::new("INVALID_POSITION", "Missing cursor"))?
                        as usize,
                )
            }
            "commit" => {
                wire::fields(args, &["credential", "progress"])?;
                let progress: Progress = serde_json::from_value(args["progress"].clone())?;
                let fault = self.crash_at.remove(id);
                let began = Instant::now();
                let outcome =
                    self.store
                        .commit_with_hook(id, &credential, &progress, false, || {
                            if fault.as_deref() == Some("before-commit") {
                                std::process::exit(86);
                            }
                        })?;
                if fault.as_deref() == Some("after-commit") {
                    std::process::exit(87);
                }
                if self.commit_times.len() == 256 {
                    self.commit_times.remove(0);
                }
                self.commit_times.push(began.elapsed().as_micros() as u64);
                Ok(serde_json::to_value(outcome)?)
            }
            "inspect" => {
                wire::fields(args, &["credential"])?;
                Ok(serde_json::to_value(
                    self.store.inspect_executor(id, &credential)?,
                )?)
            }
            "complete" => {
                wire::fields(args, &["credential"])?;
                Ok(json!({"result":self.store.complete(id,&credential)?}))
            }
            "barrier" if self.test_faults => {
                wire::fields(args, &["credential"])?;
                self.store.audit(
                    id,
                    "TestBarrierReached",
                    json!({"chunk":self.store.get(id)?.continuation.last_committed_chunk}),
                )?;
                self.active.get_mut(id).expect("active checked").barrier = true;
                Ok(json!({"barrier":true}))
            }
            _ => Err(Error::new(
                "CAPABILITY_DENIED",
                "Unknown or ungranted executor operation",
            )),
        }
    }
    fn operator(&mut self, request: &Request) -> Result<Value> {
        if request.version != 1 || request.request_id != 1 {
            return Err(Error::new(
                "UNSUPPORTED_VERSION",
                "Operator request requires protocol 1 and request ID 1",
            ));
        }
        let args = &request.arguments;
        let allowed: &[&str] = match request.operation.as_str() {
            "status" | "list" | "stop" => &[],
            "import" => &["content"],
            "create" => &["contract"],
            "run" | "handoff" => &["id", "executor", "barrier_after"],
            "events" => &["id", "after"],
            "stale-probe" => &["id", "credential", "progress"],
            "fault-arm" => &["id", "phase"],
            "inspect" | "checkpoint" | "suspend" | "resume" | "cancel" | "verify"
            | "fault-kill" => &["id"],
            _ => {
                return Err(Error::new(
                    "UNKNOWN_OPERATION",
                    "Unknown operator operation",
                ))
            }
        };
        wire::fields(args, allowed)?;
        match request.operation.as_str() {
            "status" => Ok(
                json!({"running":true,"pid":std::process::id(),"protocol_version":1,"active_executors":self.active.len(),"test_faults":self.test_faults,"measurements":{"recent_effect_commit_us":self.commit_times,"startup_verification_recovery_us":self.recovery_us}}),
            ),
            "stop" => {
                self.stopping = true;
                Ok(json!({"stopping":true}))
            }
            "list" => Ok(json!(self.store.list()?.iter().map(|a|json!({"id":a.id,"lifecycle":a.lifecycle,"epoch":a.epoch,"continuation":a.continuation})).collect::<Vec<_>>())),
            "import" => {
                Ok(json!({"input_id":self.store.import(wire::string(args,"content")?.as_bytes())?}))
            }
            "create" => Ok(serde_json::to_value(self.store.create(
                AuthorityId::generate()?,
                serde_json::from_value(args["contract"].clone())?,
            )?)?),
            _ => {
                let id = wire::string(args, "id")?;
                AuthorityId::try_from(id.to_owned())?;
                match request.operation.as_str() {
                    "inspect" => {
                        let a = self.store.get(id)?;
                        let barrier = self.active.get(id).is_some_and(|a| a.barrier);
                        Ok(json!({"authority":a,"test_barrier_reached":barrier}))
                    }
                    "verify" => self.store.verify(id),
                    "events" => Ok(serde_json::to_value(self.store.events(
                        id,
                        args["after"].as_u64().unwrap_or(0),
                        64,
                    )?)?),
                    "checkpoint" => Ok(serde_json::to_value(self.store.checkpoint(id)?)?),
                    "run" => self.start(
                        id,
                        ExecutorId::parse(wire::string(args, "executor")?)?,
                        args["barrier_after"].as_u64().unwrap_or(0),
                    ),
                    "handoff" => {
                        let executor = ExecutorId::parse(wire::string(args, "executor")?)?;
                        self.revoke(id, Lifecycle::Ready, "operator-handoff")?;
                        self.start(id, executor, args["barrier_after"].as_u64().unwrap_or(0))
                    }
                    "suspend" | "cancel" => {
                        let next = if request.operation == "cancel" {
                            Lifecycle::Cancelled
                        } else {
                            Lifecycle::Suspended
                        };
                        if self.store.get(id)?.current_executor.is_some() {
                            self.revoke(id, next, "operator-lifecycle")?;
                        } else {
                            self.store.set_idle_state(id, next)?;
                        }
                        Ok(json!({"state":next}))
                    }
                    "resume" => {
                        let a = self.store.get(id)?;
                        if a.lifecycle == Lifecycle::Orphaned {
                            if prior_alive(&a) {
                                return Err(Error::new(
                                    "STOP_UNPROVEN",
                                    "Previous process identity remains alive",
                                ));
                            }
                            self.store.recover(id, false)?;
                        } else {
                            self.store.set_idle_state(id, Lifecycle::Ready)?;
                        }
                        Ok(json!({"state":"Ready"}))
                    }
                    "fault-kill" if self.test_faults => {
                        self.revoke(id, Lifecycle::Ready, "test-sigkill")?;
                        Ok(json!({"signal":"SIGKILL","state":"Ready"}))
                    }
                    "fault-arm" if self.test_faults => {
                        let phase = wire::string(args, "phase")?;
                        if !["before-commit", "after-commit"].contains(&phase) {
                            return Err(Error::new("INVALID_FAULT", "Unknown transaction fault"));
                        }
                        self.store.get(id)?;
                        self.crash_at.insert(id.into(), phase.into());
                        Ok(json!({"armed":phase}))
                    }
                    "stale-probe" if self.test_faults => {
                        let credential: Credential =
                            serde_json::from_value(args["credential"].clone())?;
                        let progress: Progress = serde_json::from_value(args["progress"].clone())?;
                        Ok(serde_json::to_value(self.store.commit(
                            id,
                            &credential,
                            &progress,
                            false,
                        )?)?)
                    }
                    _ => Err(Error::new(
                        "FAULTS_DISABLED",
                        "Fault operations require explicit test mode",
                    )),
                }
            }
        }
    }
    fn tick(&mut self) -> Result<()> {
        let mut exited = Vec::new();
        for (id, active) in &mut self.active {
            if active.child.try_wait()?.is_some() {
                exited.push((id.clone(), "executor-exited"));
            } else if active
                .lease
                .validate(
                    active.lease.record.epoch,
                    &active.lease.record.lease_id,
                    Instant::now(),
                )
                .is_err()
            {
                exited.push((id.clone(), "lease-expired"));
            }
        }
        for (id, reason) in exited {
            if self.store.get(&id)?.lifecycle.terminal() {
                if let Some(mut active) = self.active.remove(&id) {
                    stop_owned(&mut active)?;
                }
            } else {
                let next = if self.store.get(&id)?.contract.recovery.failure_behavior == "fail" {
                    Lifecycle::Failed
                } else {
                    Lifecycle::Ready
                };
                self.revoke(&id, next, reason)?;
            }
        }
        Ok(())
    }
}
pub fn serve(test_faults: bool) -> Result<()> {
    nix::sys::stat::umask(nix::sys::stat::Mode::from_bits_truncate(0o077));
    let paths = Paths::discover()?;
    let lock = OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(paths.runtime.join("broker.lock"))?;
    let _lock = nix::fcntl::Flock::lock(lock, nix::fcntl::FlockArg::LockExclusiveNonblock)
        .map_err(|_| Error::new("BROKER_EXISTS", "Another broker holds the runtime lock"))?;
    let state_lock = OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(paths.state.join("writer.lock"))?;
    let _state_lock =
        nix::fcntl::Flock::lock(state_lock, nix::fcntl::FlockArg::LockExclusiveNonblock).map_err(
            |_| {
                Error::new(
                    "BROKER_EXISTS",
                    "Another broker holds the state writer lock",
                )
            },
        )?;
    let recovery_start = Instant::now();
    let mut store = Store::open(&paths.state.join("authorities.sqlite3"))?;
    for authority in store.list()? {
        if !authority.lifecycle.terminal() {
            let orphaned = prior_alive(&authority);
            store.recover(authority.id.as_str(), orphaned)?;
        }
    }
    let socket = paths.socket();
    if fs::symlink_metadata(&socket).is_ok() {
        fs::remove_file(&socket)?;
    }
    let listener = UnixListener::bind(&socket)?;
    fs::set_permissions(&socket, fs::Permissions::from_mode(0o600))?;
    listener.set_nonblocking(true)?;
    let (sender, receiver) = mpsc::sync_channel(128);
    let mut broker = Broker {
        store,
        active: BTreeMap::new(),
        resources: ResourceAdapter::new(),
        sender,
        test_faults,
        stopping: false,
        crash_at: BTreeMap::new(),
        commit_times: Vec::new(),
        recovery_us: recovery_start.elapsed().as_micros() as u64,
    };
    while !broker.stopping {
        if let Ok((mut stream, _)) = listener.accept() {
            stream.set_read_timeout(Some(Duration::from_secs(2)))?;
            stream.set_write_timeout(Some(Duration::from_secs(2)))?;
            let peer =
                nix::sys::socket::getsockopt(&stream, nix::sys::socket::sockopt::PeerCredentials)
                    .map_err(|_| Error::new("PEER_UNVERIFIED", "Cannot verify socket peer"))?;
            if peer.uid() == nix::unistd::getuid().as_raw() {
                if let Ok(request) = wire::read::<Request>(&mut stream) {
                    let result = broker.operator(&request);
                    let _ = wire::write(&mut stream, &Response::new(request.request_id, result));
                }
            }
        }
        match receiver.recv_timeout(Duration::from_millis(5)) {
            Ok(message) => {
                if broker
                    .active
                    .get(&message.id)
                    .is_some_and(|active| active.lease.record.epoch == message.epoch)
                {
                    match message.request {
                        Ok(request) => {
                            let result = broker.worker_request(&message.id, &request);
                            let barrier = request.operation == "barrier" && result.is_ok();
                            if !barrier {
                                if let Some(active) = broker.active.get_mut(&message.id) {
                                    let _ = wire::write(
                                        &mut active.stream,
                                        &Response::new(request.request_id, result),
                                    );
                                }
                            }
                        }
                        Err(_) => {
                            let authority = broker.store.get(&message.id)?;
                            if !authority.lifecycle.terminal() {
                                let next = if authority.contract.recovery.failure_behavior == "fail"
                                {
                                    Lifecycle::Failed
                                } else {
                                    Lifecycle::Ready
                                };
                                broker.revoke(&message.id, next, "executor-channel-closed")?;
                            }
                        }
                    }
                }
            }
            Err(mpsc::RecvTimeoutError::Timeout) => (),
            Err(_) => break,
        }
        broker.tick()?;
    }
    let ids: Vec<_> = broker.active.keys().cloned().collect();
    for id in ids {
        if broker.store.get(&id)?.lifecycle.terminal() {
            if let Some(mut active) = broker.active.remove(&id) {
                stop_owned(&mut active)?;
            }
        } else {
            broker.revoke(&id, Lifecycle::Suspended, "broker-stop")?;
        }
    }
    fs::remove_file(socket)?;
    Ok(())
}
