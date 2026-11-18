//! Read-only Linux telemetry. No shell commands, network access, or unsafe code.
#![forbid(unsafe_code)]

use std::fmt::Write;
use std::fs;
use std::io;
use std::path::Path;

#[derive(Debug, PartialEq)]
pub struct Memory {
    pub total_bytes: u64,
    pub available_bytes: u64,
}

#[derive(Debug, PartialEq)]
pub struct CpuTicks {
    pub total: u64,
    pub idle: u64,
}

impl CpuTicks {
    /// Guest ticks are already included in user/nice and must not be counted twice.
    pub fn parse(text: &str) -> Option<Self> {
        let mut fields = text.lines().next()?.split_whitespace();
        if fields.next()? != "cpu" {
            return None;
        }
        let ticks: Vec<u64> = fields
            .take(8)
            .map(str::parse)
            .collect::<Result<_, _>>()
            .ok()?;
        if ticks.len() < 4 {
            return None;
        }
        Some(Self {
            total: ticks
                .iter()
                .try_fold(0u64, |sum, value| sum.checked_add(*value))?,
            idle: ticks[3].checked_add(*ticks.get(4).unwrap_or(&0))?,
        })
    }

    pub fn usage_since(&self, previous: &Self) -> Option<f64> {
        let total = self.total.checked_sub(previous.total)?;
        let idle = self.idle.checked_sub(previous.idle)?;
        if total == 0 || idle > total {
            return None;
        }
        Some((total - idle) as f64 * 100.0 / total as f64)
    }
}

impl Memory {
    pub fn parse(text: &str) -> Option<Self> {
        fn kib(text: &str, key: &str) -> Option<u64> {
            let mut fields = text
                .lines()
                .find(|line| line.starts_with(key))?
                .split_whitespace();
            fields.next()?;
            let value: u64 = fields.next()?.parse().ok()?;
            if fields.next()? != "kB" {
                return None;
            }
            value.checked_mul(1024)
        }
        let total_bytes = kib(text, "MemTotal:")?;
        let available_bytes = kib(text, "MemAvailable:")?;
        if total_bytes == 0 || available_bytes > total_bytes {
            return None;
        }
        Some(Self {
            total_bytes,
            available_bytes,
        })
    }
}

#[derive(Debug)]
pub struct Network {
    pub interface: String,
    pub received_bytes: u64,
    pub transmitted_bytes: u64,
}

pub fn parse_network(text: &str) -> Vec<Network> {
    text.lines()
        .filter_map(|line| {
            let (name, values) = line.rsplit_once(':')?;
            let fields: Vec<&str> = values.split_whitespace().collect();
            Some(Network {
                interface: name.trim().to_owned(),
                received_bytes: fields.first()?.parse().ok()?,
                transmitted_bytes: fields.get(8)?.parse().ok()?,
            })
        })
        .collect()
}

#[derive(Debug)]
pub struct Battery {
    pub name: String,
    pub capacity_percent: Option<u8>,
    pub status: Option<String>,
}

#[derive(Debug)]
pub struct Temperature {
    pub sensor: String,
    pub celsius: f64,
}

#[derive(Debug)]
pub struct Snapshot {
    pub vendor: Option<String>,
    pub model: Option<String>,
    pub kernel: String,
    pub uptime_seconds: f64,
    pub memory: Memory,
    pub cpu_usage_percent: Option<f64>,
    pub network: Option<Vec<Network>>,
    pub batteries: Option<Vec<Battery>>,
    pub temperatures: Option<Vec<Temperature>>,
    pub unavailable: Vec<String>,
}

fn optional_text(path: &Path) -> Option<String> {
    let text = fs::read_to_string(path).ok()?.trim().to_owned();
    if text.is_empty() {
        None
    } else {
        Some(text)
    }
}

fn invalid(name: &str) -> io::Error {
    io::Error::new(
        io::ErrorKind::InvalidData,
        format!("invalid Linux metric: {name}"),
    )
}

/// Paths are injected for fixture tests; the executable always uses /proc and /sys.
pub fn collect(proc: &Path, sys: &Path) -> io::Result<Snapshot> {
    let memory = Memory::parse(&fs::read_to_string(proc.join("meminfo"))?)
        .ok_or_else(|| invalid("meminfo"))?;
    let uptime_seconds = fs::read_to_string(proc.join("uptime"))?
        .split_whitespace()
        .next()
        .and_then(|s| s.parse::<f64>().ok())
        .filter(|n| n.is_finite() && *n >= 0.0)
        .ok_or_else(|| invalid("uptime"))?;
    let kernel = optional_text(&proc.join("sys/kernel/osrelease"))
        .ok_or_else(|| invalid("kernel release"))?;
    let vendor = optional_text(&sys.join("class/dmi/id/sys_vendor"));
    let model = optional_text(&sys.join("class/dmi/id/product_name"));
    let network = fs::read_to_string(proc.join("net/dev"))
        .ok()
        .map(|s| parse_network(&s));
    let batteries = fs::read_dir(sys.join("class/power_supply"))
        .ok()
        .map(|entries| {
            let mut result = Vec::new();
            for entry in entries.flatten() {
                if optional_text(&entry.path().join("type")).as_deref() != Some("Battery") {
                    continue;
                }
                result.push(Battery {
                    name: entry.file_name().to_string_lossy().into_owned(),
                    capacity_percent: optional_text(&entry.path().join("capacity"))
                        .and_then(|s| s.parse::<u8>().ok())
                        .filter(|n| *n <= 100),
                    status: optional_text(&entry.path().join("status")),
                });
            }
            result.sort_by(|a, b| a.name.cmp(&b.name));
            result
        });
    let temperatures = fs::read_dir(sys.join("class/thermal")).ok().map(|entries| {
        let mut result = Vec::new();
        for entry in entries.flatten() {
            if !entry
                .file_name()
                .to_string_lossy()
                .starts_with("thermal_zone")
            {
                continue;
            }
            let value = optional_text(&entry.path().join("temp"))
                .and_then(|s| s.parse::<f64>().ok())
                .filter(|n| n.is_finite());
            if let Some(value) = value {
                result.push(Temperature {
                    sensor: optional_text(&entry.path().join("type"))
                        .unwrap_or_else(|| entry.file_name().to_string_lossy().into_owned()),
                    celsius: value / 1000.0,
                });
            }
        }
        result.sort_by(|a, b| a.sensor.cmp(&b.sensor));
        result
    });
    let mut unavailable = Vec::new();
    for (name, missing) in [
        ("vendor", vendor.is_none()),
        ("model", model.is_none()),
        ("network", network.is_none()),
        ("batteries", batteries.is_none()),
        (
            "temperatures",
            temperatures.as_ref().map_or(true, |v| v.is_empty()),
        ),
    ] {
        if missing {
            unavailable.push(name.to_owned());
        }
    }
    Ok(Snapshot {
        vendor,
        model,
        kernel,
        uptime_seconds,
        memory,
        cpu_usage_percent: None,
        network,
        batteries,
        temperatures,
        unavailable,
    })
}

/// JSON string encoder covering all control characters, including hardware firmware strings.
pub fn json_string(value: &str) -> String {
    let mut result = String::from("\"");
    for ch in value.chars() {
        match ch {
            '"' => result.push_str("\\\""),
            '\\' => result.push_str("\\\\"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '\t' => result.push_str("\\t"),
            c if c <= '\u{001f}' => {
                write!(result, "\\u{:04x}", c as u32).unwrap();
            }
            c => result.push(c),
        }
    }
    result.push('"');
    result
}

fn text_json(value: &Option<String>) -> String {
    value
        .as_deref()
        .map(json_string)
        .unwrap_or_else(|| "null".into())
}

impl Snapshot {
    pub fn json(&self, timestamp: u64) -> String {
        let network = self
            .network
            .as_ref()
            .map(|entries| {
                format!("[{}]", entries.iter().map(|n| {
            format!("{{\"interface\":{},\"received_bytes\":{},\"transmitted_bytes\":{}}}",
                json_string(&n.interface), n.received_bytes, n.transmitted_bytes)
        }).collect::<Vec<_>>().join(","))
            })
            .unwrap_or_else(|| "null".into());
        let batteries = self
            .batteries
            .as_ref()
            .map(|entries| {
                format!(
                    "[{}]",
                    entries
                        .iter()
                        .map(|b| {
                            format!(
                                "{{\"name\":{},\"capacity_percent\":{},\"status\":{}}}",
                                json_string(&b.name),
                                b.capacity_percent
                                    .map(|v| v.to_string())
                                    .unwrap_or_else(|| "null".into()),
                                text_json(&b.status)
                            )
                        })
                        .collect::<Vec<_>>()
                        .join(",")
                )
            })
            .unwrap_or_else(|| "null".into());
        let temperatures = self
            .temperatures
            .as_ref()
            .map(|entries| {
                format!(
                    "[{}]",
                    entries
                        .iter()
                        .map(|t| {
                            format!(
                                "{{\"sensor\":{},\"celsius\":{:.3}}}",
                                json_string(&t.sensor),
                                t.celsius
                            )
                        })
                        .collect::<Vec<_>>()
                        .join(",")
                )
            })
            .unwrap_or_else(|| "null".into());
        format!(concat!("{{\"schema_version\":1,\"timestamp_unix_seconds\":{},",
            "\"vendor\":{},\"model\":{},\"kernel\":{},\"uptime_seconds\":{:.2},",
            "\"cpu_usage_percent\":{},\"memory\":{{\"total_bytes\":{},\"available_bytes\":{},\"used_bytes\":{}}},",
            "\"network\":{},\"batteries\":{},\"temperatures\":{},\"unavailable\":[{}]}}\n"),
            timestamp, text_json(&self.vendor), text_json(&self.model), json_string(&self.kernel),
            self.uptime_seconds, self.cpu_usage_percent.map(|n| format!("{n:.2}")).unwrap_or_else(|| "null".into()),
            self.memory.total_bytes, self.memory.available_bytes, self.memory.total_bytes - self.memory.available_bytes,
            network, batteries, temperatures, self.unavailable.iter().map(|s| json_string(s)).collect::<Vec<_>>().join(","))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cpu_excludes_guest_and_handles_counter_reset() {
        let before = CpuTicks::parse("cpu 100 0 50 800 50 0 0 0 30 0\n").unwrap();
        let after = CpuTicks::parse("cpu 150 0 50 850 50 0 0 0 50 0\n").unwrap();
        assert_eq!(before.total, 1000);
        assert_eq!(after.usage_since(&before), Some(50.0));
        assert_eq!(before.usage_since(&after), None);
        assert_eq!(before.usage_since(&before), None);
        assert!(CpuTicks::parse("cpu 1 2 broken 4").is_none());
        assert!(CpuTicks::parse("cpu 18446744073709551615 1 1 1").is_none());
    }

    #[test]
    fn memory_rejects_missing_inconsistent_and_overflowing_data() {
        assert_eq!(
            Memory::parse("MemTotal: 100 kB\nMemAvailable: 40 kB\n"),
            Some(Memory {
                total_bytes: 102400,
                available_bytes: 40960
            })
        );
        for text in [
            "MemTotal: 100 kB",
            "MemTotal: 1 kB\nMemAvailable: 2 kB",
            "MemTotal: 18446744073709551615 kB\nMemAvailable: 0 kB",
            "MemTotal: 0 kB\nMemAvailable: 0 kB",
            "MemTotal: 5 MB\nMemAvailable: 1 kB",
        ] {
            assert!(Memory::parse(text).is_none(), "{text}");
        }
    }

    #[test]
    fn network_uses_receive_and_transmit_columns() {
        let data = parse_network("Inter-| Receive | Transmit\n eth0: 123 1 2 3 4 5 6 7 456 9 10 11 12 13 14 15\n bad: x\n");
        assert_eq!(data.len(), 1);
        assert_eq!(data[0].interface, "eth0");
        assert_eq!(
            (data[0].received_bytes, data[0].transmitted_bytes),
            (123, 456)
        );
    }

    #[test]
    fn json_escapes_firmware_strings() {
        assert_eq!(
            json_string("ACME \"PC\"\\\n\t\r\0\u{001f} العربية"),
            "\"ACME \\\"PC\\\"\\\\\\n\\t\\r\\u0000\\u001f العربية\""
        );
    }
}
