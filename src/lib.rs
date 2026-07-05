pub const APP_NAME: &str = "pinkflow-rust";
pub const VERSION: &str = include_str!("../version.txt");
pub const SUMMARY: &str = "Minimal Rust workspace scaffold with synchronized version management.";

pub fn version() -> &'static str {
    VERSION.trim()
}

pub fn summary() -> String {
    format!("{APP_NAME} v{}\n{SUMMARY}", version())
}

pub fn command_output(command: Option<&str>) -> String {
    match command {
        Some("version") => version().to_owned(),
        Some("summary") | None => summary(),
        Some("help") | Some("--help") | Some("-h") => {
            format!("Usage: {APP_NAME} [summary|version|help]")
        }
        Some(other) => {
            format!("Unknown command: {other}\nUsage: {APP_NAME} [summary|version|help]")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{APP_NAME, command_output, summary, version};

    #[test]
    fn version_matches_cargo_package_version() {
        assert_eq!(version(), env!("CARGO_PKG_VERSION"));
    }

    #[test]
    fn summary_mentions_project_name() {
        assert!(summary().contains(APP_NAME));
    }

    #[test]
    fn version_command_returns_plain_version() {
        assert_eq!(command_output(Some("version")), version());
    }
}
