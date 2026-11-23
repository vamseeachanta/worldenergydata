"""Read the packaged publisher register without network or filesystem writes."""

import json
from importlib.resources import files


def load_register() -> dict:
    resource = files("worldenergydata.metocean").joinpath("data/source_register.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def get_source(identifier: str) -> dict:
    for source in load_register()["sources"]:
        if source["id"] == identifier:
            return source
    raise ValueError(f"Unknown registered source: {identifier}")
