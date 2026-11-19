//! Conventional interval projection, independently expressed from certificates.
use std::io::{self, BufRead};
fn feasible(b: &[i128]) -> bool {
    let (xlo,xhi,ylo,yhi,slo,shi) = (-b[1],b[0],-b[3],b[2],-b[5],b[4]);
    if xlo > xhi || ylo > yhi || slo > shi { return false; }
    let lowest = (xlo+ylo).max(slo);
    let highest = (xhi+yhi).min(shi);
    lowest <= highest
}
fn main() {
    for line in io::stdin().lock().lines() {
        let line = line.expect("input IO failure");
        let parsed: Result<Vec<i128>,_> = line.split_whitespace().map(str::parse).collect();
        let answer = match parsed {
            Ok(b) if line.len() <= 256 && b.len() == 6 && b.iter().all(|x| (-1_000_000..=1_000_000).contains(x)) => {
                if feasible(&b) { "FEASIBLE" } else { "INFEASIBLE" }
            }
            _ => "INVALID_INPUT",
        };
        println!("{answer}");
    }
}
