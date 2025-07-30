import os
import click
from teresa.inteface import createSlcStack
from teresa.inteface import createCoregistion

@click.group()
def cli():
    pass

@cli.command()
@click.option(
    "--parms_path",
    required = True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True),
    help="The source directory where S1 SLC folders/zip files are stored.",
)
def coregister(parms_path):
    """
    Coregistrating a stack of SAR SLC images from source directory
    """

    if not os.path.exists(parms_path):
        raise FileNotFoundError(f"File not found: {parms_path}")

    click.echo(f"Coregistration started with parameters from {parms_path}")

    slc_stack = createSlcStack(parms_path)
    coregister = createCoregistion(parms_path, slc_stack)
    coregister.run()

    click.echo("Coregistration completed successfully.")


