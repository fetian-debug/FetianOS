//! Test-only wire producer, reachable only through an explicit broker test barrier.
use crate::{
    error::{Error, Result},
    wire::{self, Response},
};
use serde_json::Value;
use std::io::{Read, Write};
pub fn probe(input: &mut impl Read, output: &mut impl Write, probe: &Value) -> Result<()> {
    match probe["mode"].as_str() {
        Some("request") => wire::write(output, &probe["request"])?,
        Some("oversize") => {
            output.write_all(&65537_u32.to_be_bytes())?;
            output.flush()?;
        }
        Some("truncated") => {
            output.write_all(&100_u32.to_be_bytes())?;
            output.write_all(b"{")?;
            output.flush()?;
            return Ok(());
        }
        Some("invalid-json") => {
            output.write_all(&1_u32.to_be_bytes())?;
            output.write_all(b"{")?;
            output.flush()?;
        }
        _ => return Err(Error::new("INVALID_PROBE", "Unknown research wire probe")),
    }
    // The result is independently recorded by the coordinator; a rejection is
    // expected in most experiments. Never turn it into fabricated worker progress.
    let _ = wire::read::<Response>(input);
    Ok(())
}
