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

import os
import shutil
from pathlib import Path

from opsmop.core.errors import ProviderError
from opsmop.core.filetests import FileTests
from opsmop.core.template import Template
from opsmop.providers.provider import Provider

# FIXME: the file provider is a little (lot) long at the moment because it contains code to support
# copies, templates, mode changes, and more.  It  needs to be broken into
# smaller parts - still one provider, but use more helper classes

# FIXME: make use of FileTests

# FIXME: we need to split the file and directory provider code
# not all of these parameters are needed for directory

# FIXME: modes don't work.

class File(Provider):

    """
    Manages file operations
    """
   
    def _plan_safety(self):
        """
        Conversions between files and directories are not allowed.  Block them with fatal errors.
        """
        if self.directory and self.f_file:
            raise ProviderError(self, 'unsafe transition: requested directory but a file was already present')
        elif self.directory and self.f_wants_copy:
            raise ProviderError(self, 'unsafe transition: cannot copy file over directory')

    def _plan_file_removal_actions(self):
        if not self.f_exists:
            return
        if self.f_file:
            self.needs("rm")
        elif self.f_dir:
            self.needs("rmdir")

    def _should_maybe_replace_file(self):
        if self.overwrite:
            return True
        return False

    def _should_replace_using_template(self):
        if not self.f_exists:
            return True
        evaluated = Template.from_file(self.from_template, self.resource)
        contents = Path(self.name).read_text()
        return evaluated != contents
    
    def _should_replace_using_content(self):
        if not self.f_exists:
            return True
        contents = Path(self.name).read_text()
        return contents != self.from_content

    def _should_replace_using_file(self):
        if not self.f_exists:
            return True
        # FIXME: move into something like a FileUtils (replacing FilePath)
        s1 = self.test("sha1sum %s" % self.name).split()[0]
        s2 = self.test("sha1sum %s" % self.from_file).split()[0]
        return s1 != s2

    def _plan_content_actions(self):
        if self.f_wants_copy:
            if self._should_maybe_replace_file():
                if self.from_template:
                    if self._should_replace_using_template():
                        self.needs('copy_template')
                elif self.from_file:
                    if self._should_replace_using_file():
                        self.needs('copy_file')
                elif self.from_content:
                    if self._should_replace_using_content():
                        self.needs('copy_content')
        else:
            if not self.f_exists:
                if self.directory:
                    self.needs('mkdir')
                else:
                    raise ProviderError(self, "file path does not exist: %s" % self.name)

    def _plan_metadata_actions(self):
        if self.owner and ((self.f_dir and self.recursive) or not (self.f_owner == self.owner)):
            self.needs('chown')
        if self.group and ((self.f_dir and self.recursive) or not (self.f_group == self.group)):
            self.needs('chgrp')
        if self.mode and ((self.f_dir and self.recursive) or not (self.f_mode == self.mode)):
            self.needs('chmod')

    def plan(self):

        self.path         = Path(self.name)
        self.f_tests      = FileTests(self.name)
        self.f_exists     = self.f_tests.exists()
        self.f_file       = self.f_tests.is_file()
        self.f_dir        = self.f_tests.is_directory()
        self.f_mode       = self.f_tests.mode()
        self.f_owner      = self.f_tests.owner()
        self.f_group      = self.f_tests.group()
        self.f_wants_copy = self.from_content or self.from_template or self.from_file
        self._plan_safety()

        if self.absent:
            self._plan_file_removal_actions()
        else:
            self._plan_content_actions()
            self._plan_metadata_actions()

    def apply(self):
        """
        Apply homebrew status changes.
        """

        # TODO: from_url would be a great feature to have
        
        if self.should('rm'):
            self.do('rm')
            self.path.unlink()
            return self.ok()
        
        if self.should('rmdir'):
            self.do('rmdir')
            self.path.rmdir()
            return self.ok()

        if self.should('mkdir'):
            self.do('mkdir')
            if self.mode:
                os.makedirs(self.name, self.mode)
            else:
                os.makedirs(self.name)

        elif self.should('copy_file'):
            self.do('copy_file')
            shutil.copy2(self.from_file, self.name)

        elif self.should('copy_template'):
            self.do('copy_template')
            template_data = Template.from_file(self.from_template, self.resource)
            data = open(self.name, "w")  
            data.write(template_data)
            data.close()

        elif self.should('copy_content'):
            self.do('copy_content')
            data = open(self.name, "w")
            data.write(self.from_content)
            data.close()

        if self.should('chmod'):
            self.do('chmod')
            # FIXME: implement recursive support for directories.
            # FIXME: if the input is a string, convert to Octal, otherwise if int assume Octal
            os.chmod(self.name, self.mode)

        if self.should('chown'):
            self.do('chown')
            # TODO: move these into something like a FileUtils class
            # (eliminating FileTests, so to not repeat this everywhere)
            try:
                shutil.chown(self.name, user=self.owner)
            except PermissionError:
                return self.fatal("chown failed")

        if self.should('chgrp'):
            self.do('chgrp')
            try:
                shutil.chown(self.name, group=self.group)
            except PermissionError:
                return self.fatal("chgrp failed")

        return self.ok()
