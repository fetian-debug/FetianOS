use crate::error::{Error, Result};
use std::os::unix::fs::{DirBuilderExt, MetadataExt};
use std::{
    env, fs,
    path::{Path, PathBuf},
};
pub struct Paths {
    pub state: PathBuf,
    pub runtime: PathBuf,
}
pub fn private_dir(path: &Path) -> Result<()> {
    if !path.is_absolute()
        || path
            .components()
            .any(|p| matches!(p, std::path::Component::ParentDir))
    {
        return Err(Error::new(
            "UNSAFE_PATH",
            "Absolute normalized directory required",
        ));
    }
    let mut current = PathBuf::from("/");
    for part in path.components().skip(1) {
        current.push(part);
        match fs::symlink_metadata(&current) {
            Ok(info) if info.is_dir() && !info.file_type().is_symlink() => (),
            Ok(_) => {
                return Err(Error::new(
                    "UNSAFE_PATH",
                    "Directory path contains a symlink or non-directory",
                ))
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                fs::DirBuilder::new().mode(0o700).create(&current)?;
            }
            Err(error) => return Err(error.into()),
        }
    }
    let info = fs::metadata(path)?;
    if info.uid() != nix::unistd::getuid().as_raw() || info.mode() & 0o077 != 0 {
        return Err(Error::new(
            "UNSAFE_PATH",
            "FCA directory must be owned by this user and mode 0700",
        ));
    }
    Ok(())
}
impl Paths {
    pub fn discover() -> Result<Self> {
        let home = env::var_os("HOME").ok_or_else(|| Error::new("NO_HOME", "HOME is required"))?;
        let state = env::var_os("XDG_STATE_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from(home).join(".local/state"))
            .join("fetian-fca");
        let runtime = PathBuf::from(
            env::var_os("XDG_RUNTIME_DIR")
                .ok_or_else(|| Error::new("NO_RUNTIME", "XDG_RUNTIME_DIR is required"))?,
        )
        .join("fetian-fca");
        private_dir(&state)?;
        private_dir(&runtime)?;
        if runtime.join("authority.sock").as_os_str().len() > 100 {
            return Err(Error::new("PATH_LIMIT", "Runtime socket path is too long"));
        }
        Ok(Self { state, runtime })
    }
    pub fn socket(&self) -> PathBuf {
        self.runtime.join("authority.sock")
    }
}
