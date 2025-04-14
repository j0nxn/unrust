import base64
import csv
from string import Template

from .models import Crate, Function


class Writer:
    def write_crate_functions_csv(self, crate: Crate | None, outfile):
        with open(outfile, 'w', newline='') as file:
            csvwriter = csv.writer(file, delimiter=',')
            if crate is not None:
                for function in crate.functions:
                    for row in self._prepare_crate_function_rows(crate, function):
                        csvwriter.writerow(row)

    def _prepare_crate_function_rows(self, crate: Crate, function: Function) -> list[list[str]]:
        rows = []
        for decompile in function.decompiles:
            rows.append(
                self._prepare_crate_function_row(crate, function, decompile)
            )
        return rows

    def _prepare_crate_function_row(self, crate: Crate, function: Function, decompile: str):
        return [
            crate.name,
            crate.version,
            function.name,
            function.unsafe,
            base64.b64encode(bytes(function.source, 'utf-8')).decode(),
            base64.b64encode(
                bytes(decompile, 'utf-8').replace(b'\r\n', b'\n')
            ).decode()
        ]

    def write_crates_dependency_file(self, target: str, crate_names: str, output: str):
        with open(output, 'w', newline='') as file:
            file.write(f"{target}:")
            for crate_name in crate_names:
                file.write(f" data/{crate_name}.csv")
