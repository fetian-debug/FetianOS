use fetian_fca::{
    error::{Error, Result},
    wire,
};
use std::os::fd::AsFd;
use std::{io, os::unix::process::CommandExt, process::Command};
fn run() -> Result<()> {
    let parent = nix::unistd::getppid();
    nix::unistd::setsid()
        .map_err(|_| Error::new("SESSION_FAILED", "Cannot isolate executor process group"))?;
    nix::sys::prctl::set_pdeathsig(nix::sys::signal::Signal::SIGKILL)
        .map_err(|_| Error::new("DEATH_SIGNAL_FAILED", "Cannot bind lifetime to broker"))?;
    if nix::unistd::getppid() != parent || parent.as_raw() == 1 {
        return Err(Error::new("PARENT_GONE", "Broker exited before bootstrap"));
    }
    wire::write(
        &mut io::stdout().lock(),
        &serde_json::json!({"version":1,"launcher_ready":true}),
    )?;
    // Stdin's buffered reader may prefetch the following worker descriptor.
    // exec would discard that buffer. Read only this frame from the raw FD.
    let mut gate_input = std::fs::File::from(io::stdin().as_fd().try_clone_to_owned()?);
    let gate: serde_json::Value = wire::read(&mut gate_input)?;
    if gate != serde_json::json!({"version":1,"gate":"resources-attached"}) {
        return Err(Error::new("GATE_REJECTED", "Executor gate was not opened"));
    }
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.is_empty() {
        return Err(Error::new("NO_EXECUTOR", "Bundled executor required"));
    }
    Err(Command::new(&args[0]).args(&args[1..]).exec().into())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
