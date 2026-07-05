use pinkflow_rust::command_output;

fn main() {
    let command = std::env::args().nth(1);
    println!("{}", command_output(command.as_deref()));
}
