# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

"""Language fixtures.

NOTE: when adding new language fixtures, it should require the
``english`` fixture first, otherwise the behavior can be unpredicted when
creating projects and translation projects later on.
"""

import pytest


def _require_language(code, fullname, plurals=2, plural_equation='(n != 1)'):
    """Helper to get/create a new language."""
    from pootle_language.models import Language

    criteria = {
        'code': code,
        'fullname': fullname,
        'nplurals': plurals,
        'pluralequation': plural_equation,
    }
    language, created = Language.objects.get_or_create(**criteria)
    if created:
        language.save()
    return language


@pytest.fixture
def english(po_directory):
    """Require the English language."""
    from pootle_language.models import Language
    return Language.objects.get(code="en")


@pytest.fixture
def templates(po_directory):
    """Require the special Templates language."""
    return _require_language("templates", "Templates")


@pytest.fixture
def afrikaans(po_directory):
    """Require the Afrikaans language."""
    return _require_language('af', 'Afrikaans')


@pytest.fixture
def arabic(po_directory):
    """Require the Arabic language."""
    return _require_language('ar', 'Arabic')


@pytest.fixture
def italian(po_directory):
    """Require the Italian language."""
    return _require_language('it', 'Italian')


@pytest.fixture
def russian(po_directory):
    """Require the Russian language."""
    return _require_language('ru', 'Russian')


@pytest.fixture
def language0(po_directory):
    """language0 Language"""
    from pootle_language.models import Language

    return Language.objects.get(code="language0")


@pytest.fixture
def language1(po_directory):
    """language1 Language"""
    from pootle_language.models import Language

    return Language.objects.get(code="language1")
