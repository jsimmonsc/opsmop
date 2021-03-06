# Copyright 2018 Michael DeHaan LLC, <michael@michaeldehaan.net>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from opsmop.core.callback import BaseCallback
from opsmop.core.role import Role
from opsmop.types.type import Type

# NOTE: this interface is subject to change

INDENT="  "

class CliCallbacks(BaseCallback):

    """
    Callback class for the default CLI implementation.
    Improvements are welcome.
    """

    __slots__ = [ 'dry_run', 'role', 'last_role', 'phase', 'count' ]

    def __init__(self):
        super()
        self.dry_run = False
        self.role = None
        self.last_role = None
        self.phase = None
        self.count = 0

    def set_phase(self, phase):
        self.phase = phase

    def banner(self, msg, big=False):
        msg_len = len(msg)
        sep = None
        if big:
            sep = "=" * msg_len
        else:
            sep = "-" * msg_len
        self.i1(sep)
        self.i1(msg)
        if big:
            self.i1(sep)

    def on_command_echo(self, echo):
        if echo == "":
            return
        self.i5("| %s" % echo.rstrip())

    def on_echo(self, echo):
        self.i5("| %s" % echo)

    def on_execute_command(self, command):
        if command.echo:
            self.i5("# %s" % command.cmd)

    def on_plan(self, provider):
        self.provider = provider
        if self.provider.skip_plan_stage():
            return
        self.i3("planning...")

    def on_apply(self, provider):
        self.i3(provider.verb())
    
    def on_planned_actions(self, provider, actions_planned):
        if self.provider.skip_plan_stage():
            return
        self.provider = provider
        if len(actions_planned):
            self.i3("planned:")
            for x in actions_planned:
                self.i5(f"| {x}")
        else:
            self.i3("no changes needed")

    def on_taken_actions(self, provider, actions_taken):
        if provider.skip_plan_stage():
            return
        self.provider = provider
        taken = sorted([ str(x) for x in provider.actions_taken ])
        planned = sorted([ str(x) for x in provider.actions_planned ])
        if (taken != planned):
            self.i5("ERROR: actions planned do not equal actions taken: %s" % taken)
            self.on_fatal()
        self.i3("actions:")
        for x in actions_taken:
            self.i5("| %s" % str(x))

    def on_result(self, result):
        self.i3(str(result))

    def on_command_result(self, result):
        self.i5("= %s" % result)

    def on_skipped(self, skipped, is_handler=False):
        if self.phase != 'validate' and not is_handler and issubclass(type(skipped), Type):
            self.i3("skipped")

    def on_begin_role(self, role):
        self.phase = 'resource'

    def on_validate(self):
        self.phase = 'validate'

    def on_begin_handlers(self):
        self.phase = 'handlers'

    def on_resource(self, resource, is_handler):
        if self.phase == 'validate':
            return
        self.i1("")
        role = resource.role()
        self.count = self.count + 1
        self.banner(f"{self.count} :: {role.__class__.__name__} :: {resource}")
        self.i1("")
        if is_handler:
            self.i3("handler")

    def on_flagged(self, flagged):
        self.i3("flagged: %s" % flagged)

    def on_complete(self, policy):
        self.i1("")
        self.i1("complete!")
        self.summarize()

    def on_role(self, role):
        self.role = role

    def summarize(self):
        # TODO: reimplement the counter and percentages summary
        pass

    def on_fatal(self, msg=None):
        if msg:
            self.i1("FAILED: %s" % msg)
        else:
            self.i1("FAILED")
        self.summarize()
        # TODO: we should not exit here but raise an Exception, Api and PullApi will want to catch it.
        # TODO: further, run_callbacks in Context() should catch any exceptions from *ALL* callbacks and re-raise
        sys.exit(1)

    def on_update_variables(self, variables):
        self.i3("registered:")
        for (k,v) in variables.items():
            self.on_echo("%s => %s" % (k,v))

    def i1(self, msg):
        # indent methods
        self._indent(0, msg)

    def i2(self, msg):
        self._indent(1, msg)

    def i3(self, msg):
        self._indent(2, msg)

    def i4(self, msg):
        self._indent(3, msg)

    def i5(self, msg):
        self._indent(4, msg)
    
    def _indent(self, level, msg):
        spc = INDENT * level
        print("%s%s" % (spc, msg))
