//! Versioned, bounded frames. A partial frame is an error, never an empty request.
use crate::error::{Error, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::io::{Read, Write};
pub const MAX_FRAME: usize = 65536;
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub version: u32,
    pub request_id: u64,
    pub operation: String,
    pub arguments: Value,
}
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Response {
    pub version: u32,
    pub request_id: u64,
    pub result: Option<Value>,
    pub error: Option<Error>,
}
impl Response {
    pub fn new(id: u64, result: Result<Value>) -> Self {
        match result {
            Ok(value) => Self {
                version: 1,
                request_id: id,
                result: Some(value),
                error: None,
            },
            Err(error) => Self {
                version: 1,
                request_id: id,
                result: None,
                error: Some(error),
            },
        }
    }
    pub fn value(self, id: u64) -> Result<Value> {
        if self.version != 1
            || self.request_id != id
            || self.result.is_some() == self.error.is_some()
        {
            return Err(Error::new("INVALID_RESPONSE", "Invalid response envelope"));
        }
        self.result.ok_or_else(|| {
            self.error
                .unwrap_or_else(|| Error::new("INVALID_RESPONSE", "Missing result"))
        })
    }
}
pub fn read<T: serde::de::DeserializeOwned>(stream: &mut impl Read) -> Result<T> {
    let mut header = [0; 4];
    stream.read_exact(&mut header)?;
    let size = u32::from_be_bytes(header) as usize;
    if size == 0 || size > MAX_FRAME {
        return Err(Error::new(
            "FRAME_LIMIT",
            "Frame must contain 1–65536 bytes",
        ));
    }
    let mut bytes = vec![0; size];
    stream.read_exact(&mut bytes)?;
    Ok(serde_json::from_slice(&bytes)?)
}
pub fn write<T: Serialize>(stream: &mut impl Write, value: &T) -> Result<()> {
    let bytes = serde_json::to_vec(value)?;
    if bytes.is_empty() || bytes.len() > MAX_FRAME {
        return Err(Error::new("FRAME_LIMIT", "Response exceeds frame limit"));
    }
    stream.write_all(&(bytes.len() as u32).to_be_bytes())?;
    stream.write_all(&bytes)?;
    stream.flush()?;
    Ok(())
}
pub fn fields(value: &Value, allowed: &[&str]) -> Result<()> {
    let object = value
        .as_object()
        .ok_or_else(|| Error::new("INVALID_ARGUMENTS", "Expected an argument object"))?;
    if object.keys().any(|key| !allowed.contains(&key.as_str())) {
        return Err(Error::new("UNKNOWN_FIELD", "Unsupported argument"));
    }
    Ok(())
}
pub fn string<'a>(value: &'a Value, name: &str) -> Result<&'a str> {
    value[name]
        .as_str()
        .ok_or_else(|| Error::new("INVALID_ARGUMENTS", format!("Missing string: {name}")))
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn frames_reject_truncation_oversize_and_unknown_fields() {
        assert!(read::<Request>(&mut &b"\0\x01\0\x01"[..]).is_err());
        assert!(read::<Request>(&mut &b"\0\0\0\x02{"[..]).is_err());
        let mut out = Vec::new();
        write(&mut out,&serde_json::json!({"version":1,"request_id":1,"operation":"status","arguments":{},"extra":1})).unwrap();
        assert!(read::<Request>(&mut out.as_slice()).is_err());
    }
}
