import pathlib
import subprocess


def cli_executable_path(filename: str) -> str:
    return str(pathlib.Path(__file__).parent.joinpath(filename))


def test_stub_returns_output() -> None:
    process = subprocess.check_output([cli_executable_path("./bitwarden_client_stub.py"), "login"])
    assert process == b"You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"


def test_stub_can_be_executed() -> None:
    capture_output = subprocess.check_call([cli_executable_path("./bitwarden_client_stub.py"), "login"])
    assert capture_output == 0


def test_stub_login() -> None:
    status_code = subprocess.check_call([cli_executable_path("./bitwarden_client_stub.py"), "login"])
    assert status_code == 0
