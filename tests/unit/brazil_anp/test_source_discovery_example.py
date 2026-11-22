"""Exercise the saved-HTML CLI with hand-authored, neutral fixtures.

Expected metadata is enumerated by hand from each anchor below: resolve its
relative path beside the selected index, discard the fragment, collapse title
whitespace, decode the entity and retain the first duplicate. Synthetic file
names are not claims about published files. No values come from the parser.
"""

import json
import runpy
import socket
import sys
from pathlib import Path

import pytest

# Hand-counted ancestors: brazil_anp, unit, tests, repository root.
EXAMPLE = (
    Path(__file__).resolve().parents[3]
    / "examples/brazil_anp/list_saved_production_resources.py"
)


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def refuse_network(*args, **kwargs):
        pytest.fail("The saved-index example must not access the network")

    monkeypatch.setattr(socket, "socket", refuse_network)
    monkeypatch.setattr(socket, "create_connection", refuse_network)
    monkeypatch.setattr(socket, "getaddrinfo", refuse_network)


def run_example(monkeypatch, saved_html, index):
    monkeypatch.setattr(sys, "argv", [str(EXAMPLE), str(saved_html), "--index", index])
    runpy.run_path(str(EXAMPLE), run_name="__main__")


@pytest.mark.parametrize(
    ("index", "html", "expected"),
    [
        (
            "well",
            '<a href="arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco/'
            'sample.zip#download">  <strong>Produção</strong> &amp; archive </a>'
            '<a href="arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco/'
            'sample.zip">Later title</a>',
            [
                {
                    "url": (
                        "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
                        "arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco/"
                        "sample.zip"
                    ),
                    "title": "Produção & archive",
                    "format": "zip",
                    "index_url": (
                        "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
                        "producao-de-petroleo-e-gas-natural-por-poco"
                    ),
                }
            ],
        ),
        (
            "national",
            '<a href="arquivos/arquivos-fase-de-desenvolvimento-e-producao/'
            'arquivos-producao-de-petroleo-e-gas-natural-nacional/sample.csv#download">'
            "  National\n <strong>produção</strong> &amp; table </a>"
            '<a href="arquivos/arquivos-fase-de-desenvolvimento-e-producao/'
            'arquivos-producao-de-petroleo-e-gas-natural-nacional/sample.csv">'
            "Later title</a>",
            [
                {
                    "url": (
                        "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
                        "arquivos/arquivos-fase-de-desenvolvimento-e-producao/"
                        "arquivos-producao-de-petroleo-e-gas-natural-nacional/sample.csv"
                    ),
                    "title": "National produção & table",
                    "format": "csv",
                    "index_url": (
                        "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
                        "fase-de-desenvolvimento-e-producao"
                    ),
                }
            ],
        ),
    ],
)
def test_saved_index_example_preserves_resource_metadata(
    tmp_path, monkeypatch, capsys, index, html, expected
):
    saved_html = tmp_path / "saved-index.html"
    saved_html.write_text(html, encoding="utf-8")

    run_example(monkeypatch, saved_html, index)

    output = capsys.readouterr()
    assert json.loads(output.out) == expected
    assert output.err == ""


@pytest.mark.parametrize("index", ["well", "national"])
@pytest.mark.parametrize(
    "html",
    [
        "",
        "<html>Access denied</html>",
        '<a href="https://example.org/other.zip">Other</a>',
    ],
)
def test_saved_index_example_refuses_empty_catalogue(
    tmp_path, monkeypatch, capsys, index, html
):
    saved_html = tmp_path / "saved-index.html"
    saved_html.write_text(html, encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        run_example(monkeypatch, saved_html, index)

    assert error.value.code
    output = capsys.readouterr()
    assert output.out == ""
    assert "No production files found in ANP index" in output.err


@pytest.mark.parametrize("contents", [None, b"\xff"])
def test_saved_index_example_refuses_unreadable_input(
    tmp_path, monkeypatch, capsys, contents
):
    saved_html = tmp_path / "saved-index.html"
    if contents is not None:
        saved_html.write_bytes(contents)

    with pytest.raises(SystemExit) as error:
        run_example(monkeypatch, saved_html, "well")

    assert error.value.code
    output = capsys.readouterr()
    assert output.out == ""
    assert "error:" in output.err


def test_saved_index_example_requires_supported_index(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit) as error:
        run_example(monkeypatch, tmp_path / "absent.html", "other")

    assert error.value.code
    output = capsys.readouterr()
    assert output.out == ""
    assert "invalid choice" in output.err
