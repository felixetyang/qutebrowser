# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Contains the Command class, a skeleton for a command."""

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWebKit import QWebSettings

from qutebrowser.commands import cmdexc, argparser
from qutebrowser.utils import log, utils, message


class Command:

    """Base skeleton for a command.

    Attributes:
        name: The main name of the command.
        split: Whether to split the arguments.
        hide: Whether to hide the arguments or not.
        count: Whether the command supports a count, or not.
        desc: The description of the command.
        instance: How to get to the "self" argument of the handler.
                  A dotted string as viewed from app.py, or None.
        handler: The handler function to call.
        completion: Completions to use for arguments, as a list of strings.
        needs_js: Whether the command needs javascript enabled
        debug: Whether this is a debugging command (only shown with --debug).
        parser: The ArgumentParser to use to parse this command.
    """

    # TODO:
    # we should probably have some kind of typing / argument casting for args
    # this might be combined with help texts or so as well

    def __init__(self, name, split, hide, count, desc, instance, handler,
                 completion, modes, not_modes, needs_js, debug, parser):
        # I really don't know how to solve this in a better way, I tried.
        # pylint: disable=too-many-arguments
        self.name = name
        self.split = split
        self.hide = hide
        self.count = count
        self.desc = desc
        self.instance = instance
        self.handler = handler
        self.completion = completion
        self.modes = modes
        self.not_modes = not_modes
        self.needs_js = needs_js
        self.debug = debug
        self.parser = parser

    def _check_prerequisites(self):
        """Check if the command is permitted to run currently.

        Raise:
            PrerequisitesError if the command can't be called currently.
        """
        # We don't use modeman.instance() here to avoid a circular import
        # of qutebrowser.keyinput.modeman.
        curmode = QCoreApplication.instance().modeman.mode()
        if self.modes is not None and curmode not in self.modes:
            mode_names = '/'.join(mode.name for mode in self.modes)
            raise cmdexc.PrerequisitesError(
                "{}: This command is only allowed in {} mode.".format(
                    self.name, mode_names))
        elif self.not_modes is not None and curmode in self.not_modes:
            mode_names = '/'.join(mode.name for mode in self.not_modes)
            raise cmdexc.PrerequisitesError(
                "{}: This command is not allowed in {} mode.".format(
                    self.name, mode_names))
        if self.needs_js and not QWebSettings.globalSettings().testAttribute(
                QWebSettings.JavascriptEnabled):
            raise cmdexc.PrerequisitesError(
                "{}: This command needs javascript enabled.".format(self.name))

    def run(self, args=None, count=None):
        """Run the command.

        Note we don't catch CommandError here as it might happen async.

        Args:
            args: Arguments to the command.
            count: Command repetition count.
        """
        dbgout = ["command called:", self.name]
        if args:
            dbgout.append(str(args))
        if count is not None:
            dbgout.append("(count={})".format(count))
        log.commands.debug(' '.join(dbgout))

        posargs = []
        kwargs = {}
        app = QCoreApplication.instance()

        try:
            namespace = self.parser.parse_args(args)
        except argparser.ArgumentParserError as e:
            message.error(str(e))
            return

        for name, arg in vars(namespace).items():
            if isinstance(arg, list):
                # If we got a list, we assume that's our *args, so we don't add
                # it to kwargs.
                # FIXME: This approach is rather naive, but for now it works.
                posargs += arg
            else:
                kwargs[name] = arg

        if self.instance is not None:
            # Add the 'self' parameter.
            if self.instance == '':
                obj = app
            else:
                obj = utils.dotted_getattr(app, self.instance)
            posargs.insert(0, obj)

        if count is not None and self.count:
            kwargs = {'count': count}

        self._check_prerequisites()
        log.commands.debug('posargs: {}'.format(posargs))
        log.commands.debug('kwargs: {}'.format(kwargs))
        self.handler(*posargs, **kwargs)
