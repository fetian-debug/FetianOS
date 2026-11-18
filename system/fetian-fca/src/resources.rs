//! Only a caller-owned delegated cgroup v2 subtree may enforce budgets.
use crate::{
    error::{Error, Result},
    model::{AuthorityId, ResourceBudget},
};
use serde_json::{json, Value};
use std::os::unix::fs::MetadataExt;
use std::{fs, path::PathBuf};
pub struct ResourceAdapter {
    root: Option<PathBuf>,
    reason: String,
}
impl Default for ResourceAdapter {
    fn default() -> Self {
        Self::new()
    }
}
impl ResourceAdapter {
    pub fn new() -> Self {
        match Self::delegated() {
            Ok(root) => Self {
                root: Some(root),
                reason: String::new(),
            },
            Err(error) => Self {
                root: None,
                reason: error.code,
            },
        }
    }
    fn delegated() -> Result<PathBuf> {
        let text = fs::read_to_string("/proc/self/cgroup")?;
        let relative = text
            .lines()
            .find_map(|line| line.strip_prefix("0::"))
            .ok_or_else(|| Error::new("CGROUP_UNAVAILABLE", "Unified cgroup v2 required"))?;
        if relative == "/" || relative.split('/').any(|part| part == "..") {
            return Err(Error::new(
                "DELEGATION_UNAVAILABLE",
                "Refusing machine root cgroup",
            ));
        }
        let root = PathBuf::from("/sys/fs/cgroup").join(relative.trim_start_matches('/'));
        let uid = nix::unistd::getuid().as_raw();
        if uid == 0
            || fs::symlink_metadata(&root)?.uid() != uid
            || fs::symlink_metadata(root.join("cgroup.procs"))?.uid() != uid
        {
            return Err(Error::new(
                "DELEGATION_UNAVAILABLE",
                "User-owned delegated cgroup required",
            ));
        }
        let controllers = fs::read_to_string(root.join("cgroup.controllers"))?;
        if ["cpu", "memory", "pids"]
            .iter()
            .any(|name| !controllers.split_whitespace().any(|item| item == *name))
        {
            return Err(Error::new(
                "CONTROLLERS_UNAVAILABLE",
                "cpu memory and pids delegation required",
            ));
        }
        let processes = fs::read_to_string(root.join("cgroup.procs"))?;
        if processes
            .lines()
            .any(|pid| pid != std::process::id().to_string())
        {
            return Err(Error::new("DELEGATION_SHARED", "Refusing shared cgroup"));
        }
        let manager = root.join("fca-manager");
        if !manager.exists() {
            fs::create_dir(&manager)?;
        }
        fs::write(manager.join("cgroup.procs"), std::process::id().to_string())?;
        fs::write(root.join("cgroup.subtree_control"), "+cpu +memory +pids")?;
        Ok(root)
    }
    pub fn prepare(&self, id: &AuthorityId, budget: &ResourceBudget) -> Result<Value> {
        let Some(root) = &self.root else {
            if budget.strict {
                return Err(Error::new(
                    "STRICT_RESOURCE_UNAVAILABLE",
                    "Kernel enforcement unavailable; executor was not started",
                ));
            }
            return Ok(
                json!({"mode":"advisory","kernel_enforced":false,"reason":self.reason,"cpu":"unavailable","memory":"unavailable","pids":"unavailable","budget":budget,"gpu":"unsupported"}),
            );
        };
        let group = root.join(id.as_str());
        if !group.exists() {
            fs::create_dir(&group)?;
        }
        for (name, value) in [
            (
                "cpu.max",
                format!("{} 100000", u64::from(budget.cpu_quota) * 100000),
            ),
            ("memory.max", budget.memory_bytes.to_string()),
            ("pids.max", budget.pids_max.to_string()),
        ] {
            fs::write(group.join(name), &value)?;
            if fs::read_to_string(group.join(name))?.trim() != value {
                return Err(Error::new(
                    "RESOURCE_READBACK",
                    "Kernel limit readback failed",
                ));
            }
        }
        Ok(json!({"mode":"enforced","kernel_enforced":true,"budget":budget,"gpu":"unsupported"}))
    }
    pub fn attach(&self, id: &AuthorityId, pid: u32) -> Result<()> {
        if let Some(root) = &self.root {
            fs::write(root.join(id.as_str()).join("cgroup.procs"), pid.to_string())?;
        }
        Ok(())
    }
}
