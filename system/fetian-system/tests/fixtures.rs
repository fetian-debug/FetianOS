use fetian_system::collect;
use std::{fs, path::PathBuf};

struct Fixture(PathBuf);

impl Fixture {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!("fetian-fixture-{}", std::process::id()));
        fs::create_dir(&path).unwrap();
        Self(path)
    }

    fn write(&self, path: &str, data: &str) {
        let path = self.0.join(path);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, data).unwrap();
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn linux_metrics_and_missing_sensors_are_reported_honestly() {
    let fixture = Fixture::new();
    fixture.write("proc/meminfo", "MemTotal: 8192 kB\nMemAvailable: 4096 kB\n");
    fixture.write("proc/uptime", "123.45 200.0\n");
    fixture.write("proc/sys/kernel/osrelease", "fixture-kernel\n");
    fixture.write("sys/class/dmi/id/sys_vendor", "ACME \"Systems\"\n");
    let proc = fixture.0.join("proc");
    let sys = fixture.0.join("sys");
    let snapshot = collect(&proc, &sys).unwrap();
    assert_eq!(snapshot.uptime_seconds, 123.45);
    assert!(snapshot.network.is_none());
    assert!(snapshot.cpu_usage_percent.is_none());
    assert!(snapshot.unavailable.contains(&"temperatures".into()));
    assert!(snapshot
        .json(100)
        .contains("\"vendor\":\"ACME \\\"Systems\\\"\""));
    assert!(snapshot.json(100).contains("\"network\":null"));
    fixture.write("sys/class/power_supply/BAT0/type", "Battery");
    fixture.write("sys/class/power_supply/BAT0/capacity", "76");
    fixture.write("sys/class/power_supply/BAT0/status", "Discharging");
    fixture.write("sys/class/power_supply/AC/type", "Mains");
    fixture.write("sys/class/thermal/thermal_zone0/type", "cpu");
    fixture.write("sys/class/thermal/thermal_zone0/temp", "42500");
    let snapshot = collect(&proc, &sys).unwrap();
    let batteries = snapshot.batteries.unwrap();
    assert_eq!(batteries.len(), 1);
    assert_eq!(batteries[0].capacity_percent, Some(76));
    assert_eq!(snapshot.temperatures.unwrap()[0].celsius, 42.5);
    fixture.write("proc/uptime", "NaN");
    assert!(collect(&proc, &sys).is_err());
    fs::remove_file(proc.join("meminfo")).unwrap();
    assert!(collect(&proc, &sys).is_err());
}
