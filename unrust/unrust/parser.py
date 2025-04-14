import json
import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .models import Crate, Function
from .exceptions import FunctionParseException


class SourceParser:
    def parse(self, source_href: str, response_text: str) -> tuple[str, bool]:
        soup = BeautifulSoup(response_text, 'html.parser')
        raw_lines = soup.find_all('code')[0].text.split("\n")
        lines = self._extract_source_lines_without_line_numbers(
            source_href, raw_lines)
        # FIXME: Assumes first code line starts with the function signature
        return "\n".join(lines), self._parse_unsafe(lines[0])

    def _extract_source_lines_without_line_numbers(self, source_href: str, raw_lines: list[str]) -> list[str]:
        lines = []
        lower, upper = self._parse_source_boundaries(source_href)

        for line_number, raw_line in enumerate(raw_lines, start=1):
            if lower <= line_number and line_number <= upper:
                lines.append(self._strip_line_number(line_number, raw_line))

        return lines

    def _parse_source_boundaries(self, source_href: str) -> tuple[int, int]:
        fragment = urlparse(source_href).fragment
        if "-" in fragment:
            lower, upper = (int(boundary) for boundary in fragment.split('-'))
        else:
            lower = upper = int(fragment)
        return lower, upper

    def _strip_line_number(self, line_number: int, raw_line: str) -> str:
        return re.match(
            f'^{line_number}(?P<line>.*)$', raw_line).group('line')

    def _parse_unsafe(self, function_signature_line: str) -> bool:
        return re.match('^[^(]*unsafe[^(]*fn.*$', function_signature_line) is not None


class CrateParser:
    def __init__(self, source_parser: SourceParser):
        self.source_parser = source_parser

    def parse_source(self, source_href: str, response_text: str) -> tuple[str, bool]:
        return self.source_parser.parse(source_href, response_text)

    def parse_crate(self, name: str, response_text: str) -> tuple[Crate, list[str]]:
        logging.info(f'parsing crate {name}')
        soup = BeautifulSoup(response_text, 'html.parser')
        version = soup.find_all(lambda tag: tag.name == 'span' and tag.has_attr(
            'class') and 'version' in tag['class'])[0].string
        function_hrefs = [tag['href'] for tag in soup.find_all(
            lambda tag: tag.name == 'a' and tag.has_attr('class') and 'fn' in tag['class'])]
        return Crate(name, version), function_hrefs

    def parse_function(self, response_text: str) -> tuple[Function, str]:
        soup = BeautifulSoup(response_text, 'html.parser')

        try:
            name = soup.find_all(lambda tag: tag.name == 'span' and tag.has_attr(
                'class') and 'fn' in tag['class'])[0].string
        except IndexError:
            raise FunctionParseException("Could not parse function name")

        source_href = soup.find_all(lambda tag: tag.name == 'a' and tag.has_attr(
            'class') and 'src' in tag['class'])[0]['href']
        return Function(name), source_href


class CrateListParser:
    def extract_crate_names(self, response_text: str) -> list[str]:
        response = json.loads(response_text)
        return [crate['name'] for crate in response['crates']]
