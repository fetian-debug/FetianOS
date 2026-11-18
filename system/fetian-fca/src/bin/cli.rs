fn main() {
    let mut args: Vec<_> = std::env::args().skip(1).collect();
    let compact = args.iter().any(|a| a == "--json");
    args.retain(|a| a != "--json");
    if args.is_empty() || args.iter().any(|a| a == "--help") {
        println!("{}", fetian_fca::cli::HELP);
        return;
    }
    match fetian_fca::cli::run(&args) {
        Ok(value) => println!(
            "{}",
            if compact {
                serde_json::to_string(&value)
            } else {
                serde_json::to_string_pretty(&value)
            }
            .expect("JSON value serializes")
        ),
        Err(error) => {
            eprintln!(
                "{}",
                serde_json::to_string(&error).expect("error serializes")
            );
            std::process::exit(1);
        }
    }
}
