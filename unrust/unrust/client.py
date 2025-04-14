import datetime
import importlib.metadata
import logging
import os
import subprocess
import tarfile
import time

from urllib.parse import urlparse

import pyghidra
import requests
import toml

from . import config
from .models import Crate
from .exceptions import CrateDllBuildException, HTTPRequestException

logging.basicConfig(level=config.LOG_LEVEL)


class WebClient:
    HEADERS = {
        'User-Agent':  f'unrust@{importlib.metadata.version("unrust")} executed by {config.CONTACT_EMAIL}'
    }

    def __init__(self):
        self.last_request_time: datetime.datetime | None = None

    def get_crate_names(self, top: int = 100, sort: str = 'downloads'):
        return self._get(f'https://crates.io/api/v1/crates?page=1&per_page={top}&sort={sort}').text

    def get_crate_docs(self, name: str, version: str = 'latest'):
        return self._get(f'https://docs.rs/{name}/{version}/{name}/').text

    def get_function_docs(self, crate: Crate, function_href: str):
        if self._is_relative_href(function_href):
            url = f'https://docs.rs/{crate.name}/{crate.version}/{crate.name}/{function_href}'
        else:
            url = function_href
        return self._get(url).text

    def get_function_source_docs(self, crate: Crate, source_href: str):
        if self._is_relative_href(source_href):
            url = f'https://docs.rs/{crate.name}/{crate.version}/{crate.name}/{source_href}'
        else:
            url = source_href
        return self._get(url).text

    def _is_relative_href(self, href: str) -> bool:
        parsed = urlparse(href)
        return parsed.netloc == '' and not parsed.path.startswith('/')

    def get_crate_as_tar(self, crate: Crate, outdir: str) -> str:
        filename = f'{outdir}/{crate.name}.tar'
        if not os.path.exists(filename):
            self._get_file(
                f'https://crates.io/api/v1/crates/{crate.name}/{crate.version}/download', filename)
        return filename

    def _get_file(self, url: str, filename: str):
        with open(filename, 'wb') as file:
            file.write(self._get(url).content)
        logging.info(f'{filename} written')

    def _get(self, url: str) -> requests.Response:
        self._honor_request_rate_limit()
        logging.info(f'fetching {url}')
        response = requests.get(url, headers=WebClient.HEADERS)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise HTTPRequestException(e)
        return response

    def _honor_request_rate_limit(self):
        if self.last_request_time is not None:
            time_delta_since_last_request = datetime.datetime.now() - self.last_request_time
            if time_delta_since_last_request < config.MIN_TIME_DELTA_SINCE_LAST_REQUEST:
                time_delta_until_rate_limit_satisfied = \
                    config.MIN_TIME_DELTA_SINCE_LAST_REQUEST - time_delta_since_last_request
                seconds_to_sleep = time_delta_until_rate_limit_satisfied.microseconds / 10**6
                logging.info(
                    f'sleeping {seconds_to_sleep} seconds to satisfy crates.io rate limit')
                time.sleep(seconds_to_sleep)
        self.last_request_time = datetime.datetime.now()


class FileClient:
    def untar(self, crate: Crate, filename: str, outdir: str):
        crate_dir = f'{outdir}/{crate.name}-{crate.version}'
        if not os.path.exists(crate_dir):
            with tarfile.open(filename) as file:
                file.extractall(outdir)
                logging.info(f'{filename} extracted to {crate_dir}')
        return crate_dir


class CargoClient:
    def build_dll(self, crate_dir: str, crate_name: str) -> str:
        dll_path = f'{crate_dir}/target/debug/{crate_name}.dll'
        if not os.path.exists(dll_path):
            self._add_dylib_to_cargo_toml(f'{crate_dir}/Cargo.toml')
            try:
                subprocess.run(['cargo', 'build', '--all-features'],
                               cwd=crate_dir, check=True)
            except subprocess.CalledProcessError as e:
                raise CrateDllBuildException(e)
        return dll_path

    def _add_dylib_to_cargo_toml(self, cargo_toml_path: str):
        with open(cargo_toml_path, 'r') as f:
            cargo_toml = toml.load(f)
        cargo_toml |= {
            'lib': {
                'crate-type': ["dylib"]
            }
        }
        with open(cargo_toml_path, 'w') as f:
            toml.dump(cargo_toml, f)


class GhidraClient:
    def decompile(self, dll_path: str, crate: Crate, function_name: str) -> list[str]:
        decompiles = []

        logging.info(f"opening ghidra project to analyze {dll_path}")
        with pyghidra.open_program(dll_path) as program_api:
            decompiler_api = self._get_decompiler_api(program_api)
            symbols = self._get_symbols(program_api)
            external_entry_points = self._get_external_entrypoints(symbols)
            for entry_point in external_entry_points:
                if self._symbol_valid(symbols.getPrimarySymbol(entry_point), crate, function_name):
                    try:
                        decompiles.append(decompiler_api.decompile(
                            program_api.getFunctionAt(entry_point)))
                    except Exception as e:
                        logging.exception(e)

        return decompiles

    def _get_decompiler_api(self, program_api):
        from ghidra.app.decompiler.flatapi import FlatDecompilerAPI
        return FlatDecompilerAPI(program_api)

    def _get_symbols(self, program_api):
        return program_api.getCurrentProgram().getSymbolTable()

    def _get_external_entrypoints(self, symbols):
        return symbols.getExternalEntryPointIterator()

    def _symbol_valid(self, symbol, crate: Crate, function_name: str) -> bool:
        return (symbol is not None
                and self._symbol_points_to_function(symbol)
                and self._symbol_matches_function_name(symbol, crate, function_name))

    def _symbol_points_to_function(self, symbol):
        return str(symbol.getSymbolType()) == 'Function'

    def _symbol_matches_function_name(self, symbol, crate: Crate, function_name: str):
        name = symbol.getName(True)
        return name == f'{crate.name}::{function_name}' or name.startswith(f'{crate.name}::{function_name}<')
