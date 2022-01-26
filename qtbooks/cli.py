import click

from qtbooks import gui, model


@click.group()
@click.option("-u", "--user", type=str)
@click.option("-f", "--db-file", type=click.Path(dir_okay=False, writable=True))
@click.option("-v", "--verbose", is_flag=True)
@click.option("--config", type=click.Path(dir_okay=False))
@click.pass_context
def cli(
    ctx: click.Context, user: str, db_file: str, verbose: bool, config: str
) -> None:
    ctx.ensure_object(dict)
    for k, v in locals().items():
        if k != "ctx":
            ctx.obj[k] = v


@cli.command()
@click.pass_context
def qtgui(ctx) -> None:
    gui.main(ctx.obj)


if __name__ == "__main__":
    cli(obj={})
