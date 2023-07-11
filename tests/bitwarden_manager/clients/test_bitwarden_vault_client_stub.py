import subprocess


def test_stub_returns_output():
    process = subprocess.check_output(["./bitwarden_client_stub.py", "login"])
    assert process == b"You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"


def test_stub_can_be_executed():
    capture_output = subprocess.check_call(["./bitwarden_client_stub.py", "login"])
    assert capture_output == 0


def test_stub_login():
    status_code = subprocess.check_call(["./bitwarden_client_stub.py", "login"])
    assert status_code == 0
