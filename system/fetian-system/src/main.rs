#![forbid(unsafe_code)]

use fetian_system::{collect, CpuTicks};
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::Path;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

fn atomic_write(path: &Path, data: &[u8]) -> io::Result<()> {
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let name = path
        .file_name()
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "output needs a filename"))?;
    let temporary = parent.join(format!(
        ".{}.{}.tmp",
        name.to_string_lossy(),
        std::process::id()
    ));
    // Never follow or overwrite an existing temporary file (including symlinks).
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)?;
    let result = (|| {
        file.write_all(data)?;
        file.sync_all()?;
        drop(file);
        fs::rename(&temporary, path)?;
        fs::File::open(parent)?.sync_all()
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let (json, output) = match args.as_slice() {
        [] => (false, None),
        [flag] if flag == "--text" => (false, None),
        [flag] if flag == "--json" => (true, None),
        [flag, path] if flag == "--output" => (true, Some(Path::new(path))),
        [flag] if flag == "--help" || flag == "-h" => {
            println!("Usage: fetian-health-rs [--text | --json | --output PATH]\nRead-only Linux health metrics; CPU is sampled over 200 ms.\n--output atomically replaces a JSON snapshot in an existing directory.");
            return Ok(());
        }
        _ => return Err("invalid arguments; use --help".into()),
    };
    if !cfg!(target_os = "linux") {
        return Err(
            "live metrics require Linux /proc and /sys; no simulated data is provided".into(),
        );
    }
    let cpu_path = Path::new("/proc/stat");
    let previous = CpuTicks::parse(&fs::read_to_string(cpu_path)?);
    std::thread::sleep(Duration::from_millis(200));
    let current = CpuTicks::parse(&fs::read_to_string(cpu_path)?);
    let mut snapshot = collect(Path::new("/proc"), Path::new("/sys"))?;
    snapshot.cpu_usage_percent = current
        .zip(previous)
        .and_then(|(now, before)| now.usage_since(&before));
    if snapshot.cpu_usage_percent.is_none() {
        snapshot.unavailable.push("cpu_usage_percent".into());
    }
    let timestamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    if let Some(path) = output {
        atomic_write(path, snapshot.json(timestamp).as_bytes())?;
    } else if json {
        print!("{}", snapshot.json(timestamp));
    } else {
        println!(
            "FetianOS health (Rust)\nSystem: {} {}\nKernel: {}\nUptime: {:.0} seconds",
            snapshot.vendor.as_deref().unwrap_or("Unavailable"),
            snapshot.model.as_deref().unwrap_or("Unavailable"),
            snapshot.kernel,
            snapshot.uptime_seconds
        );
        println!(
            "CPU: {}\nMemory: {} / {} MiB used",
            snapshot
                .cpu_usage_percent
                .map(|n| format!("{n:.1}%"))
                .unwrap_or_else(|| "Unavailable".into()),
            (snapshot.memory.total_bytes - snapshot.memory.available_bytes) / 1048576,
            snapshot.memory.total_bytes / 1048576
        );
        println!("Unavailable metrics: {}", snapshot.unavailable.join(", "));
    }
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("fetian-health-rs: {error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn output_replaces_complete_snapshot_and_preserves_previous_on_failure() {
        let directory = std::env::temp_dir().join(format!("fetian-atomic-{}", std::process::id()));
        fs::create_dir(&directory).unwrap();
        let path = directory.join("health.json");
        atomic_write(&path, b"old").unwrap();
        atomic_write(&path, b"new").unwrap();
        assert_eq!(fs::read(&path).unwrap(), b"new");
        let temporary = directory.join(format!(".health.json.{}.tmp", std::process::id()));
        fs::write(&temporary, b"occupied").unwrap();
        assert!(atomic_write(&path, b"bad").is_err());
        assert_eq!(fs::read(&path).unwrap(), b"new");
        fs::remove_file(temporary).unwrap();
        fs::remove_file(path).unwrap();
        fs::remove_dir(directory).unwrap();
    }
}
