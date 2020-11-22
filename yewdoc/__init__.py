# -*- coding: utf-8 -*-
"""
    Yewdocs
    ~~~~~~~

    Yewdocs is a personal document manager that makes creating and
editing text documents from the command line easier than using an
editor and filesystem commands.

    :copyright: (c) 2017 by Paul Wolf.
    :license: BSD, see LICENSE for more details.

"""
__version__ = "0.2.0"
__author__ = "Paul Wolf"
__license__ = "BSD"

from .shared import cli
from .cmd import (
    apply,
    generate_index,
    path,
    purge,
    attach,
    status,
    ls,
    ping,
    info,
    sync,
    edit,
    register,
    user_pref,
    read,
    take,
    configure,
    authenticate,
    create,
    tag,
    tags,
    convert,
    browse,
    context,
    encrypt,
    decrypt,
    api,
    kind,
    find,
    rename,
    head,
    tail,
    push,
    archive,
    delete,
    show,
    describe,
    verify,
    diff,
    rls,
)
