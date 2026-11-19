use crate::{
    error::{Error, Result},
    model::*,
    store::{Credential, Progress},
    wire::{self, Request, Response},
};
use serde_json::{json, Value};
use std::io;
fn request(
    input: &mut impl io::Read,
    output: &mut impl io::Write,
    id: &mut u64,
    operation: &str,
    arguments: Value,
) -> Result<Value> {
    *id += 1;
    wire::write(
        output,
        &Request {
            version: 1,
            request_id: *id,
            operation: operation.into(),
            arguments,
        },
    )?;
    wire::read::<Response>(input)?.value(*id)
}
pub fn run() -> Result<()> {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    let start: Value = wire::read(&mut input)?;
    if start["version"] != 1 || start["workload"] != "fetian.sum-i64/v1" {
        return Err(Error::new("UNSUPPORTED_VERSION", "Executor ABI mismatch"));
    }
    let credential: Credential = serde_json::from_value(start["credential"].clone())?;
    let mut checkpoint: ContinuationState = serde_json::from_value(start["checkpoint"].clone())?;
    let mut seq = 0;
    request(
        &mut input,
        &mut output,
        &mut seq,
        "hello",
        json!({"workload":"fetian.sum-i64/v1","credential":credential}),
    )?;
    loop {
        let chunk = request(
            &mut input,
            &mut output,
            &mut seq,
            "read",
            json!({"credential":credential,"position":checkpoint.next_input_position}),
        )?;
        let values: Vec<i64> = serde_json::from_value(chunk["values"].clone())?;
        if values.is_empty() {
            request(
                &mut input,
                &mut output,
                &mut seq,
                "complete",
                json!({"credential":credential}),
            )?;
            return Ok(());
        }
        let mut sum = checkpoint.accumulated_result;
        for value in values {
            sum = sum
                .checked_add(value)
                .ok_or_else(|| Error::new("SUM_OVERFLOW", "Signed sum overflow"))?;
        }
        let progress = Progress {
            sequence: checkpoint.last_committed_chunk + 1,
            input_position: checkpoint.next_input_position,
            next_input_position: chunk["next_input_position"]
                .as_u64()
                .ok_or_else(|| Error::new("INVALID_CHUNK", "Missing cursor"))?
                as usize,
            accumulated_result: sum,
            idempotency_key: format!("chunk-{}", checkpoint.last_committed_chunk + 1),
        };
        let outcome = request(
            &mut input,
            &mut output,
            &mut seq,
            "commit",
            json!({"credential":credential,"progress":progress}),
        )?;
        checkpoint = serde_json::from_value(outcome["checkpoint"].clone())?;
        if start["barrier_after"].as_u64() == Some(checkpoint.last_committed_chunk) {
            let barrier = request(
                &mut input,
                &mut output,
                &mut seq,
                "barrier",
                json!({"credential":credential}),
            )?;
            if start["test_faults"] == true && barrier["research_probe"].is_object() {
                return crate::research::probe(&mut input, &mut output, &barrier["research_probe"]);
            }
        }
    }
}
