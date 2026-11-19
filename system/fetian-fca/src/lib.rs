//! Experimental user-space continuation authority; not a Linux kernel primitive.
#![forbid(unsafe_code)]

pub const PROTOCOL_VERSION: u32 = 1;
pub mod broker;
pub mod cli;
pub mod client;
pub mod error;
pub mod model;
pub mod paths;
pub mod research;
pub mod resources;
pub mod store;
pub mod wire;
pub mod worker;
