//! H105 finite-channel decoder. Protected metadata is not total working space.
use std::io::{self, BufRead};
fn columns(n: u32) -> Option<&'static [u32]> {
    match n { 5 => Some(&[1,2,3,4,8]), 6 => Some(&[1,2,3,4,5,6]), _ => None }
}
fn syndrome(word: u32, cols: &[u32]) -> u32 {
    cols.iter().enumerate().filter(|(i,_)| (word >> i)&1 == 1).fold(0,|a,(_,v)| a^v)
}
fn line_answer(line: &str) -> Option<String> {
    let fields: Vec<_> = line.split_whitespace().collect();
    if line.len()>128 || fields.len()<3 { return None; }
    let n: u32=fields[1].parse().ok()?;
    let cols=columns(n)?;
    let word: u32=fields[2].parse().ok()?;
    if word >= 1<<n {return None;}
    match fields[0] {
        "E" if fields.len()==3 => Some(syndrome(word,cols).to_string()),
        "D" if fields.len()==4 => {
            let saved: u32=fields[3].parse().ok()?;
            if saved >= 1<<(if n==5 {4} else {3}) {return None;}
            let delta=syndrome(word,cols)^saved;
            if delta==0 {return Some(word.to_string());}
            if let Some(bit)=cols.iter().position(|v| *v==delta) {
                return Some((word^(1<<bit)).to_string());
            }
            let full=cols.iter().fold(0,|a,v|a^v);
            Some(if delta==full {(word^((1<<n)-1)).to_string()} else {"UNDECODABLE".into()})
        }
        _ => None,
    }
}
fn main() {
    for line in io::stdin().lock().lines() {
        let line=line.expect("stdin failure");
        println!("{}",line_answer(&line).unwrap_or_else(||"INVALID_INPUT".into()));
    }
}
