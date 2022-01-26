import click

from qtbooks import gui, model


@click.group()
@click.option("-u", "--user", type=str)
@click.option("-f", "--db-file", type=click.Path(dir_okay=False, writable=True))
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def cli(ctx: click.Context, user: str, db_file: str, verbose: bool) -> None:
    ctx.ensure_object(dict)
    ctx.obj["user"] = user
    ctx.obj["db_file"] = db_file
    ctx.obj["verbose"] = verbose


@cli.command()
@click.pass_context
def qtgui(ctx) -> None:
    gui.main(ctx.obj)


if __name__ == "__main__":
    cli(obj={})
