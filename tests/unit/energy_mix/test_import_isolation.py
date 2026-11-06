"""Exercise real imports and a local query without optional packages or transport.

All observations below are authored synthetic fixtures, not source data.
Independent selection by hand: Alpha in the inclusive interval 2022--2024
retains the 2024, 2023 and 2022 rows in input order; Beta, 2021 and 2025
are excluded. Measurements are copied literally in MW and GWh, including
decimal precision, blank values and reported zeroes; no conversion is applied.
"""

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

# The generous minute is solely a deadlock/hang guard, not a speed requirement.
SUBPROCESS_TIMEOUT_SECONDS = 60

SYNTHETIC_CSV = (
    "country,iso_code,year,technology,capacity_mw,generation_gwh,source_url,citation\n"
    "Synthetic Alpha,,2021,offshore wind,1,2,https://example.invalid/older,Excluded older\n"
    "Synthetic Alpha,,2024,offshore wind,12.50,6.25,https://example.invalid/measured,Synthetic measured\n"
    "Synthetic Beta,,2023,offshore wind,3,4,https://example.invalid/other,Excluded country\n"
    "Synthetic Alpha,,2023,offshore wind,0,,https://example.invalid/missing,Synthetic unavailable\n"
    "Synthetic Alpha,,2022,offshore wind,,0,https://example.invalid/zero,Synthetic reported zero\n"
    "Synthetic Alpha,,2025,offshore wind,5,6,https://example.invalid/newer,Excluded newer\n"
)

# Hand-written expected rows, independent of loader/query output and constants.
EXPECTED_CSV = (
    "country,iso_code,year,technology,capacity_mw,generation_gwh,source_url,citation\n"
    "Synthetic Alpha,,2024,offshore wind,12.50,6.25,https://example.invalid/measured,Synthetic measured\n"
    "Synthetic Alpha,,2023,offshore wind,0,,https://example.invalid/missing,Synthetic unavailable\n"
    "Synthetic Alpha,,2022,offshore wind,,0,https://example.invalid/zero,Synthetic reported zero\n"
)


def test_local_query_in_fresh_interpreter_without_optional_imports(tmp_path):
    """Imports and exact filtered output must succeed with both traps installed."""
    source_root = Path(__file__).resolve().parents[3] / "src"
    env = os.environ.copy()
    # Repository-supported src layout; do not inherit cwd-relative import paths.
    env["PYTHONPATH"] = str(source_root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONOPTIMIZE", None)  # Child assertions must always execute.
    child = dedent(
        """
        import importlib.abc
        import socket
        import sys
        from urllib import request

        optional_packages = {"pandas", "numpy", "xarray", "requests"}
        import_attempts = []
        network_attempts = []

        def optional_modules():
            return {
                name for name in sys.modules
                if name.partition(".")[0] in optional_packages
            }

        assert not optional_modules(), "Optional packages loaded before the guard"
        assert "worldenergydata" not in sys.modules, "Package already loaded"

        class BlockOptionalImports(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.partition(".")[0] in optional_packages:
                    import_attempts.append(fullname)
                    raise ModuleNotFoundError(
                        "Optional package forbidden: " + fullname, name=fullname
                    )
                return None

        sys.meta_path.insert(0, BlockOptionalImports())

        def deny_network(*args, **kwargs):
            network_attempts.append("transport")
            raise AssertionError("Network access forbidden")

        def audit_network(event, args):
            if event.startswith("socket.") or event == "urllib.Request":
                deny_network()

        # Audit events also cover direct sockets and DNS, before any real I/O.
        sys.addaudithook(audit_network)
        socket.socket.connect = deny_network
        socket.socket.connect_ex = deny_network
        socket.create_connection = deny_network
        socket.getaddrinfo = deny_network
        request.urlopen = deny_network

        from worldenergydata.energy_mix import irena, query

        assert callable(irena.load_export)
        result = query.query_export(
            sys.stdin.buffer.read(),
            countries=["synthetic alpha"],
            start_year=2022,
            end_year=2024,
            generation_unit="GWh",
        )
        assert not import_attempts, import_attempts
        assert not optional_modules(), optional_modules()
        assert not network_attempts, network_attempts
        sys.stdout.buffer.write(result)
        """
    )
    completed = subprocess.run(
        # -S prevents site startup from preloading optional packages or hooks.
        [sys.executable, "-S", "-c", child],
        input=SYNTHETIC_CSV.encode("utf-8"),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    assert completed.stdout == EXPECTED_CSV.encode("utf-8")
