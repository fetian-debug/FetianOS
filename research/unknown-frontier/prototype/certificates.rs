//! Isolated H005 certificate experiment. Not an OS service or novel algorithm.
use std::io::{self, BufRead};
const A: [[i128; 2]; 6] = [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1]];
const CERTIFICATES: [[i128; 6]; 5] = [
    [1,1,0,0,0,0], [0,0,1,1,0,0], [0,0,0,0,1,1],
    [1,0,1,0,0,1], [0,1,0,1,1,0],
];
fn valid(y: &[i128; 6]) -> bool {
    y.iter().all(|v| *v >= 0) && y.iter().any(|v| *v > 0)
        && (0..2).all(|j| (0..6).map(|i| y[i] * A[i][j]).sum::<i128>() == 0)
}
fn feasible(b: &[i128]) -> bool {
    CERTIFICATES.iter().all(|y| y.iter().zip(b).map(|(a,c)| a*c).sum::<i128>() >= 0)
}
fn main() {
    assert!(CERTIFICATES.iter().all(valid));
    if std::env::args().nth(1).as_deref() == Some("--invalid-certificate") {
        assert!(!valid(&[1,-1,0,0,0,0]));
        println!("INVALID_CERTIFICATE");
        std::process::exit(2);
    }
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
