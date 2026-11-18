fn main() {
    if let Err(error) = fetian_fca::worker::run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
