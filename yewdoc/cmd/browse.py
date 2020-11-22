import os
import sys

import click
from jinja2 import Template

from .. import shared
from .. import file_system as fs

try:
    import pypandoc
except Exception:
    print("pypandoc won't load; convert cmd will not work")


@shared.cli.command()
@click.argument("name", required=False)
@click.argument("template", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--tags", "-t", required=False)
@click.pass_context
def browse(ctx, name, template, list_docs, tags):
    """Convert to html and attempt to load in web browser.

    Provide a name spec or tags to select documents.

    You can provide your own Jinja (http://jinja.pocoo.org/)
    template. Leave this out to use the default.

    """
    yew = ctx.obj["YEW"]
    if template:
        template_path = template
    else:
        # get our default
        p = os.path.realpath(__file__)
        template_path = os.path.dirname(p)
        template_path = os.path.join(template_path, "..", "template_0.html")
    if not os.path.exists(template_path):
        click.echo("does not exist: {}".format(template_path))
        sys.exit(1)

    input_formats = ["md", "rst"]

    
    tags = tags.split(",") if tags else list()
    docs = yew.store.get_docs(name_frag=name, tags=tags)

    nav = ""
    for doc in docs:
        tmp_dir = fs.get_tmp_directory()
        tmp_file = os.path.join(tmp_dir, doc.get_safe_name() + ".html")
        a = '<a href="file://%s">%s</a><br/>\n' % (tmp_file, doc.name)
        nav += a
    for doc in docs:
        if doc.kind == "md":
            #  html = markdown.markdown(doc.get_content())
            pdoc_args = ["--mathjax"]

            html = pypandoc.convert(
                doc.get_path(), format="md", to="html5", extra_args=pdoc_args
            )

        else:
            if doc.kind not in input_formats:
                kind = "md"
            else:
                kind = doc.kind
            html = pypandoc.convert(doc.get_path(), format=kind, to="html")
        tmp_dir = fs.get_tmp_directory()
        tmp_file = os.path.join(tmp_dir, doc.get_safe_name() + ".html")
        with click.open_file(template_path, "r") as f:
            t = f.read()

        template = Template(t)
        data = {"title": doc.name, "content": html, "nav": nav}
        dest = template.render(data)

        # template = string.Template(t)
        # dest = template.substitute(
        #     title=doc.name,
        #     content=html,
        #     nav=nav
        # )
        with open(tmp_file, "w") as f:
            f.write(dest)
        click.echo(f"Wrote {tmp_file}")
    click.launch(tmp_file)
