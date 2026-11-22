"""ANP discovery contracts using synthetic HTML and published link examples.

URL examples: ANP, Produção de Petróleo e Gás Natural por Poço, sections
2021–2023; Fase de Desenvolvimento e Produção, Produção Nacional, accessed
2026-10-19. The source URLs are the index constants below. No production
measurements or engineering acceptance limits are used.
"""

from http import HTTPStatus
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from worldenergydata.brazil_anp.production.source_discovery import (
    NATIONAL_PRODUCTION_INDEX,
    WELL_PRODUCTION_INDEX,
    discover_production_resources,
    parse_production_resources,
)

# ANP index sections cited in the module docstring; directory names are
# published addresses, not a rule for synthesizing future download URLs.
OPEN_DATA = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos"
WELL_FILES = (
    f"{OPEN_DATA}/arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco"
)
NATIONAL_FILES = (
    f"{OPEN_DATA}/arquivos/arquivos-fase-de-desenvolvimento-e-producao/"
    "arquivos-producao-de-petroleo-e-gas-natural-nacional"
)


@pytest.mark.parametrize(
    "filename",
    [
        "2021_01_producao.zip",
        "2021-08-producao.zip",
        "2022/producao-2022-01.zip",
        "2022/2022_05_producao.zip",
        "2023/producao-12.zip",
        "producao-por-poco-2020.zip",
    ],
)
def test_preserves_published_irregular_zip_addresses(filename):
    """Expected URL is the literal published href; no date template applies."""
    url = f"{WELL_FILES}/{filename}"
    resources = parse_production_resources(
        f'<a href="{url}">Production archive</a>', index_url=WELL_PRODUCTION_INDEX
    )

    assert [(r.url, r.title, r.format, r.index_url) for r in resources] == [
        (url, "Production archive", "zip", WELL_PRODUCTION_INDEX)
    ]


@pytest.mark.parametrize(
    "filename",
    [
        "pm/producao-mar-2026.csv",
        "pm/producao_por_poco_2024.csv",
        "pm/producao-mar-1941-1979.csv",
        "pt/2026/producao_por_poco_terra_2026_2_trim.csv",
    ],
)
def test_discovers_national_csv_without_inventing_period_or_units(filename):
    """Expected href is from the national index, including its exceptional name."""
    url = f"{NATIONAL_FILES}/{filename}"
    resources = parse_production_resources(
        f'<a href="{url}">Production CSV</a>', index_url=NATIONAL_PRODUCTION_INDEX
    )

    assert [(r.url, r.format) for r in resources] == [(url, "csv")]


def test_resolves_relative_links_and_keeps_first_title_in_document_order():
    """Hand enumeration: repeated archive A, archive B yields [A, B]."""
    relative = "arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco/"
    html = (
        f'<a href="{relative}2023/producao-12.zip#download">'
        "  <strong>December</strong> &amp; archive </a>"
        f'<a href="{WELL_FILES}/2023/producao-12.zip">Repeated</a>'
        f'<a href="{WELL_FILES}/2022/2022_05_producao.zip">May</a>'
    )

    resources = parse_production_resources(html, index_url=WELL_PRODUCTION_INDEX)

    assert [(r.url, r.title) for r in resources] == [
        (f"{WELL_FILES}/2023/producao-12.zip", "December & archive"),
        (f"{WELL_FILES}/2022/2022_05_producao.zip", "May"),
    ]


@pytest.mark.parametrize(
    "unrelated",
    [
        "https://example.org/production.zip",
        "https://www.gov.br.example.org/anp/production.zip",
        "http://www.gov.br/anp/production.zip",
        f"{WELL_FILES}/metadados.pdf",
        f"{NATIONAL_FILES}/pm/producao-mar-2026.csv",
        f"{WELL_FILES}/../unrelated/production.zip",
        f"{WELL_FILES}/%2e%2e/unrelated/production.zip",
        "https://cdp.anp.gov.br/ords/r/cdp_apex/consulta-dados-publicos-cdp/",
        "javascript:void(0)",
    ],
)
def test_ignores_unrelated_or_interactive_links(unrelated):
    """Only the explicitly published production archive belongs in the result."""
    url = f"{WELL_FILES}/2023/producao-12.zip"
    html = f'<a href="{unrelated}">Other</a><a href="{url}">Archive</a>'

    assert [
        r.url for r in parse_production_resources(html, index_url=WELL_PRODUCTION_INDEX)
    ] == [url]


@pytest.mark.parametrize("html", ["", "<html>Access denied</html>", "<a>No href</a>"])
def test_empty_or_changed_index_is_visible_to_caller(html):
    """No observed files cannot be treated as evidence that an API exists."""
    with pytest.raises(ValueError, match="No production files"):
        parse_production_resources(html, index_url=WELL_PRODUCTION_INDEX)


def test_rejects_unknown_index_before_network_access():
    with (
        patch(
            "worldenergydata.brazil_anp.production.source_discovery.HTTPSConnection"
        ) as connect,
        pytest.raises(ValueError, match="Unsupported ANP production index"),
    ):
        discover_production_resources("https://example.org/index", timeout=1)
    connect.assert_not_called()


@pytest.mark.parametrize("charset", ["utf-8", None])
def test_discovery_fetches_only_index_and_does_not_download_payloads(charset):
    """One published anchor yields one descriptor; timeout is caller policy."""
    url = f"{WELL_FILES}/2023/producao-12.zip"
    response = MagicMock()
    response.read.return_value = f'<a href="{url}">Archive</a>'.encode()
    response.headers.get_content_charset.return_value = charset
    response.status = HTTPStatus.OK
    with patch(
        "worldenergydata.brazil_anp.production.source_discovery.HTTPSConnection"
    ) as connect:
        connection = connect.return_value
        connection.getresponse.return_value = response

        resources = discover_production_resources(WELL_PRODUCTION_INDEX, timeout=1)

    connect.assert_called_once_with("www.gov.br", timeout=1)
    connection.request.assert_called_once()
    assert connection.request.call_args.args == (
        "GET",
        (
            "/anp/pt-br/centrais-de-conteudo/dados-abertos/"
            "producao-de-petroleo-e-gas-natural-por-poco"
        ),
    )
    assert connection.request.call_args.kwargs["headers"]["User-Agent"]
    connection.close.assert_called_once()
    assert [r.url for r in resources] == [url]


@pytest.mark.parametrize(
    "error",
    [
        HTTPError(WELL_PRODUCTION_INDEX, 403, "Forbidden", {}, None),
        URLError("Unavailable"),
        TimeoutError("Timed out"),
    ],
)
def test_transport_failures_propagate_without_claiming_api_absence(error):
    """HTTP 403 is RFC 9110 (2022), section 15.5.4; it is not API evidence."""
    with patch(
        "worldenergydata.brazil_anp.production.source_discovery.HTTPSConnection"
    ) as connect:
        connection = connect.return_value
        connection.getresponse.side_effect = error
        with pytest.raises(type(error)):
            discover_production_resources(WELL_PRODUCTION_INDEX, timeout=1)
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "status", [HTTPStatus.FOUND, HTTPStatus.FORBIDDEN, HTTPStatus.SERVICE_UNAVAILABLE]
)
def test_non_success_status_is_not_parsed_as_a_production_catalog(status):
    """RFC 9110 (2022), sections 15.4.3, 15.5.4 and 15.6.4 define these statuses."""
    response = MagicMock()
    response.status = status
    with patch(
        "worldenergydata.brazil_anp.production.source_discovery.HTTPSConnection"
    ) as connect:
        connection = connect.return_value
        connection.getresponse.return_value = response
        with pytest.raises(HTTPError) as error:
            discover_production_resources(WELL_PRODUCTION_INDEX, timeout=1)
    assert error.value.code == status
    response.read.assert_not_called()
    connection.request.assert_called_once()
    connection.close.assert_called_once()
