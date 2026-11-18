use crate::{
    error::Result,
    paths::Paths,
    wire::{self, Request, Response},
};
use serde_json::Value;
use std::{os::unix::net::UnixStream, path::Path, time::Duration};
pub fn call_at(socket: &Path, operation: &str, arguments: Value) -> Result<Value> {
    let mut stream = UnixStream::connect(socket)?;
    stream.set_read_timeout(Some(Duration::from_secs(10)))?;
    stream.set_write_timeout(Some(Duration::from_secs(3)))?;
    wire::write(
        &mut stream,
        &Request {
            version: 1,
            request_id: 1,
            operation: operation.into(),
            arguments,
        },
    )?;
    wire::read::<Response>(&mut stream)?.value(1)
}
pub fn call(operation: &str, arguments: Value) -> Result<Value> {
    call_at(&Paths::discover()?.socket(), operation, arguments)
}
