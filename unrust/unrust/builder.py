import logging

from .models import Crate, Function
from .client import WebClient, FileClient, CargoClient, GhidraClient
from .parser import CrateParser, CrateListParser
from .exceptions import FunctionParseException, HTTPRequestException


class CrateBuilder:
    def __init__(self, web_client: WebClient, crate_parser: CrateParser, file_client: FileClient, cargo_client: CargoClient, ghidra_client: GhidraClient, outdir: str):
        self.web_client = web_client
        self.crate_parser = crate_parser
        self.file_client = file_client
        self.cargo_client = cargo_client
        self.ghidra_client = ghidra_client
        self.outdir = outdir

    def build_crate(self, crate_name: str) -> Crate:
        crate, function_hrefs = self.crate_parser.parse_crate(
            crate_name, self.web_client.get_crate_docs(crate_name))
        crate.functions = self.build_functions(crate, function_hrefs)

        return crate

    def build_functions(self, crate: Crate, function_hrefs: list) -> list[Function]:
        functions = []
        for function_href in function_hrefs:
            try:
                functions.append(self.build_function(crate, function_href))
            except (FunctionParseException, HTTPRequestException) as e:
                logging.exception(e)
        return functions

    def build_function(self, crate: Crate, function_href: str) -> Function:
        function, source_href = self.crate_parser.parse_function(
            self.web_client.get_function_docs(crate, function_href))
        function.source, function.unsafe = self.build_source(
            crate, source_href)
        function.decompiles = self.build_decompiles(crate, function.name)
        if len(function.decompiles) == 0:
            logging.debug(
                f'Did not find any decompiles for function {function.name}')
        return function

    def build_source(self, crate: Crate, source_href: str) -> tuple[str, bool]:
        return self.crate_parser.parse_source(source_href, self.web_client.get_function_source_docs(crate, source_href))

    def build_decompiles(self, crate: Crate, function_name: str) -> list[str]:
        filename = self.web_client.get_crate_as_tar(crate, self.outdir)
        crate_dir = self.file_client.untar(crate, filename, self.outdir)
        dll_path = self.cargo_client.build_dll(crate_dir, crate.name)
        return self.ghidra_client.decompile(dll_path, crate, function_name)


class CrateListBuilder:
    def __init__(self, web_client: WebClient, crate_list_parser: CrateListParser):
        self.web_client = web_client
        self.crate_list_parser = crate_list_parser

    def build_crate_names(self, top, sort):
        return self.crate_list_parser.extract_crate_names(self.web_client.get_crate_names(top, sort))
