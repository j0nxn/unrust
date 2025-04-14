
import logging

import click

from . import config
from .builder import CrateListBuilder, CrateBuilder
from .client import WebClient, FileClient, CargoClient, GhidraClient
from .exceptions import CrateDllBuildException
from .parser import CrateListParser, CrateParser, SourceParser
from .writer import Writer


logging.basicConfig(level=config.LOG_LEVEL)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('outfile')
@click.argument('target')
@click.option('--top', type=int, default=100)
@click.option('--sort', default="downloads")
def build_crates_dependencies(outfile, target, top, sort):
    crate_list_builder = CrateListBuilder(WebClient(), CrateListParser())
    crate_names = crate_list_builder.build_crate_names(top, sort)
    Writer().write_crates_dependency_file(target, crate_names, outfile)


@cli.command()
@click.argument('crate-name')
@click.option('--outdir')
def build_crate_csv(crate_name, outdir):
    crate_builder = CrateBuilder(
        WebClient(),
        CrateParser(SourceParser()),
        FileClient(),
        CargoClient(),
        GhidraClient(),
        outdir
    )

    try:
        crate = crate_builder.build_crate(crate_name)
        logging.debug(crate)
    except CrateDllBuildException as e:
        crate = None
        logging.exception(e)

    Writer().write_crate_functions_csv(crate, f'{outdir}/{crate_name}.csv')
