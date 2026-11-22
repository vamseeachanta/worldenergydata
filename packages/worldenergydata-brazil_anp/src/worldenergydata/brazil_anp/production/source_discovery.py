"""Discover published ANP production files without assuming a REST API.

Sources: ANP, Produção de Petróleo e Gás Natural por Poço, and Fase de
Desenvolvimento e Produção, Produção Nacional (accessed 2026-10-19).
The index constants are the source addresses. File names vary within these
indexes; a link is evidence of publication, not proof of payload availability,
reuse rights, a production period, or units. No production data is downloaded.
"""

from dataclasses import dataclass
from html.parser import HTMLParser
from http import HTTPStatus
from http.client import HTTPSConnection
from posixpath import normpath
from urllib.error import HTTPError
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

_OPEN_DATA = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos"
WELL_PRODUCTION_INDEX = f"{_OPEN_DATA}/producao-de-petroleo-e-gas-natural-por-poco"
NATIONAL_PRODUCTION_INDEX = f"{_OPEN_DATA}/fase-de-desenvolvimento-e-producao"

# Literal directories and formats observed in the cited ANP indexes, not URL
# templates. National production excludes zone and installation datasets.
_CATALOGS = {
    WELL_PRODUCTION_INDEX: (
        f"{_OPEN_DATA}/arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco/",
        "zip",
    ),
    NATIONAL_PRODUCTION_INDEX: (
        (
            f"{_OPEN_DATA}/arquivos/arquivos-fase-de-desenvolvimento-e-producao/"
            "arquivos-producao-de-petroleo-e-gas-natural-nacional/"
        ),
        "csv",
    ),
}


@dataclass(frozen=True)
class ProductionResource:
    """An observed file link; title and provenance are preserved separately."""

    url: str
    title: str
    format: str
    index_url: str


def _validate_index(index_url: str) -> None:
    if index_url not in _CATALOGS:
        raise ValueError("Unsupported ANP production index")


class _ProductionLinkParser(HTMLParser):
    def __init__(self, index_url: str):
        super().__init__(convert_charrefs=True)
        self.index_url = index_url
        self.root, self.format = _CATALOGS[index_url]
        self.resources: list[ProductionResource] = []
        self._seen: set[str] = set()
        self._url: str | None = None
        self._title: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        self._url = None
        self._title = []
        href = dict(attrs).get("href")
        if not href:
            return
        url, _ = urldefrag(urljoin(self.index_url, href))
        parts = urlsplit(url)
        root = urlsplit(self.root)
        path = normpath(unquote(parts.path))
        if (
            parts.scheme == root.scheme
            and parts.netloc == root.netloc
            and path.startswith(root.path)
            and path.lower().endswith(f".{self.format}")
        ):
            self._url = url

    def handle_data(self, data):
        if self._url is not None:
            self._title.append(data)

    def handle_endtag(self, tag):
        if tag != "a" or self._url is None:
            return
        if self._url not in self._seen:
            self.resources.append(
                ProductionResource(
                    url=self._url,
                    title=" ".join("".join(self._title).split()),
                    format=self.format,
                    index_url=self.index_url,
                )
            )
            self._seen.add(self._url)
        self._url = None


def parse_production_resources(
    html: str, *, index_url: str
) -> list[ProductionResource]:
    """Parse an official index, keeping distinct links in document order.

    An empty result raises instead of silently treating a denial page or a
    changed catalog as an empty production dataset. It says nothing about API
    existence. Only the supported production-file directories are accepted.
    """
    _validate_index(index_url)
    parser = _ProductionLinkParser(index_url)
    parser.feed(html)
    parser.close()
    if not parser.resources:
        raise ValueError("No production files found in ANP index; inspect the page")
    return parser.resources


def discover_production_resources(
    index_url: str, *, timeout: float
) -> list[ProductionResource]:
    """GET an official index; propagate access/transport errors unchanged.

    The caller supplies a timeout in seconds as operational policy. The
    browser-compatible user agent was used for the source observations on
    2026-10-19. No credentials, retries, cache writes or payload fetches occur.
    Redirects are not followed. HTTP status handling follows RFC 9110 (2022),
    section 15.3.1 (200 OK); any other status raises HTTPError.
    """
    _validate_index(index_url)
    connection = HTTPSConnection("www.gov.br", timeout=timeout)
    try:
        connection.request(
            "GET",
            urlsplit(index_url).path,
            headers={"User-Agent": "Mozilla/5.0 (compatible; worldenergydata)"},
        )
        response = connection.getresponse()
        if response.status != HTTPStatus.OK:
            raise HTTPError(
                index_url, response.status, response.reason, response.headers, None
            )
        encoding = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(encoding)
    finally:
        connection.close()
    return parse_production_resources(html, index_url=index_url)
