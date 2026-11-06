"""The packaged app's launcher points the certificate paths at a file that is not there; use_bundled() must repair that."""

import os
import ssl

from ocarina import certs


def test_a_missing_certificate_file_is_replaced_by_the_bundled_one(monkeypatch):
    monkeypatch.setenv("SSL_CERT_FILE", "/no/such/file")
    monkeypatch.setenv("SSL_CERT_DIR", "/no/such/dir")
    certs.use_bundled()
    assert os.path.isfile(os.environ["SSL_CERT_FILE"]) and "SSL_CERT_DIR" not in os.environ
    ssl.create_default_context()  # fails with FileNotFoundError when the paths are wrong


def test_a_working_setting_is_left_alone(monkeypatch, tmp_path):
    mine = tmp_path / "ca.pem"
    mine.write_text("x")
    monkeypatch.setenv("SSL_CERT_FILE", str(mine))
    certs.use_bundled()
    assert os.environ["SSL_CERT_FILE"] == str(mine)
