fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a != "--allow-test-faults") {
        eprintln!("usage: fetian-authorityd [--allow-test-faults]");
        std::process::exit(2);
    }
    if let Err(error) = fetian_fca::broker::serve(args.iter().any(|a| a == "--allow-test-faults")) {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
