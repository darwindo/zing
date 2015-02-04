#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2012 Zuza Software Foundation
# Copyright 2013-2015 Evernote Corporation
#
# This file is part of Pootle.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import datetime
import logging
import sys

from optparse import make_option

from django.core.management.base import BaseCommand, NoArgsCommand

from pootle_project.models import Project
from pootle_translationproject.models import TranslationProject


class PootleCommand(NoArgsCommand):
    """Base class for handling recursive pootle store management commands."""
    shared_option_list = (
        make_option('--project', action='append', dest='projects',
                    help='Project to refresh'),
        make_option('--language', action='append', dest='languages',
                    help='Language to refresh'),
        )
    option_list = NoArgsCommand.option_list + shared_option_list
    process_disabled_projects = False

    def __init__(self, *args, **kwargs):
        self.languages = []
        self.projects = []
        super(PootleCommand, self).__init__(*args, **kwargs)

    def do_translation_project(self, tp, **options):
        process_stores = True

        if hasattr(self, "handle_translation_project"):
            logging.info(u"Running %s over %s", self.name, tp)
            try:
                process_stores = self.handle_translation_project(tp, **options)
            except Exception:
                logging.exception(u"Failed to run %s over %s", self.name, tp)
                return

            if not process_stores:
                return

        if hasattr(self, "handle_all_stores"):
            logging.info(u"Running %s over %s's files", self.name, tp)
            try:
                self.handle_all_stores(tp, **options)
            except Exception:
                logging.exception(u"Failed to run %s over %s's files",
                                  self.name, tp)
                return
        elif hasattr(self, "handle_store"):
            store_query = tp.stores.all()
            for store in store_query.iterator():
                logging.info(u"Running %s over %s",
                             self.name, store.pootle_path)
                try:
                    self.handle_store(store, **options)
                except Exception:
                    logging.exception(u"Failed to run %s over %s",
                                      self.name, store.pootle_path)

    def handle_noargs(self, **options):
        # adjust debug level to the verbosity option
        verbosity = int(options.get('verbosity', 1))
        debug_levels = {
            0: logging.ERROR,
            1: logging.WARNING,
            2: logging.INFO,
            3: logging.DEBUG
        }
        debug_level = debug_levels.get(verbosity, logging.DEBUG)
        logging.getLogger().setLevel(debug_level)

        # reduce size of parse pool early on
        self.name = self.__class__.__module__.split('.')[-1]
        from pootle_store.fields import TranslationStoreFieldFile
        TranslationStoreFieldFile._store_cache.maxsize = 2
        TranslationStoreFieldFile._store_cache.cullsize = 2
        TranslationProject._non_db_state_cache.maxsize = 2
        TranslationProject._non_db_state_cache.cullsize = 2

        self.projects = options.get('projects', [])
        self.languages = options.get('languages', [])

        # info start
        start = datetime.datetime.now()
        logging.info('Start running of %s', self.name)

        self.handle_all(**options)

        # info finish
        end = datetime.datetime.now()
        logging.info('All done for %s in %s', self.name, end - start)

    def handle_all(self, **options):
        if self.process_disabled_projects:
            project_query = Project.objects.all()
        else:
            project_query = Project.objects.enabled()

        if self.projects:
            project_query = project_query.filter(code__in=self.projects)

        for project in project_query.iterator():
            tp_query = project.translationproject_set \
                              .order_by('language__code')

            if self.languages:
                tp_query = tp_query.filter(language__code__in=self.languages)

            for tp in tp_query.iterator():
                self.do_translation_project(tp, **options)


class NoArgsCommandMixin(NoArgsCommand):
    """Intermediary class to allow multiple inheritance from
    :class:`NoArgsCommand` and mixins that implement :func:`handle_noargs`.
    Classes derived from this will provide the implementation for
    :func:`handle_noargs`.
    """

    def handle_noargs(self, **options):
        pass


class ModifiedSinceMixin(object):
    option_modified_since = (
        make_option('--modified-since', action='store', dest='modified_since',
                type=int,
                help="Only process translations newer than CHANGE_ID "
                     "(as given by latest_change_id)"),
        )

    def __init__(self, *args, **kwargs):
        super(ModifiedSinceMixin, self).__init__(*args, **kwargs)
        self.__class__.option_list += self.__class__.option_modified_since

    def handle_noargs(self, **options):
        change_id = options.get('modified_since', None)

        if change_id is None or change_id == 0:
            options.pop('modified_since')
            if change_id == 0:
                logging.info(u"Change ID is zero, no modified-since filtering.")
        elif change_id < 0:
            logging.error(u"Change IDs must be positive integers.")
            sys.exit(1)
        else:
            from pootle_statistics.models import Submission
            try:
                latest = Submission.objects.values_list('id', flat=True) \
                                           .select_related('').latest()
            except Submission.DoesNotExist:
                latest = 0
            if change_id > latest:
                logging.warning(u"The given change ID is higher than the "
                                u"latest known change.\nAborting.")
                sys.exit(1)

        super(ModifiedSinceMixin, self).handle_noargs(**options)


class BaseRunCommand(BaseCommand):
    """Base class to build new server runners.

    Based on code from `django-shoes
    <https://bitbucket.org/mlzboy/django-shoes/>`_."""
    hostport_option_list = (
        make_option('--host', action='store', dest='host', default='127.0.0.1',
            help='Hostname to listen on.'),
        make_option('--port', action='store', dest='port', default=8000,
            type=int, help='The TCP port to listen on.'),
    )

    option_list = BaseCommand.option_list + hostport_option_list

    def handle(self, *args, **options):
        return self.serve_forever(*args, **options)

    def get_app(self):
        from django.contrib.staticfiles.handlers import StaticFilesHandler
        from django.core.handlers.wsgi import WSGIHandler

        app = StaticFilesHandler(WSGIHandler())
        return app

    def serve_forever(self, *args, **kwargs):
        raise NotImplementedError
