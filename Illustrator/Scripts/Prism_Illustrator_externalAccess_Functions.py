# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import subprocess

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Illustrator_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.core.registerCallback(
            "projectBrowser_loadUI", self.projectBrowser_loadUI, plugin=self.plugin
        )
        self.core.registerCallback("getPresetScenes", self.getPresetScenes, plugin=self.plugin)
        ssheetPath = os.path.join(
            self.pluginDirectory,
            "UserInterfaces",
            "IllustratorStyleSheet"
        )
        self.core.registerStyleSheet(ssheetPath)

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin):
        """
        Retrieves the auto-backup path and supported file formats for Illustrator.
        """
        autobackpath = ""  # Placeholder for the auto-backup path logic

        # Generate the file format string for Illustrator
        fileStr = "Illustrator Files ("
        for fmt in self.sceneFormats:
            fileStr += f"*{fmt} "

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def projectBrowser_loadUI(self, origin):
        if self.core.appPlugin.pluginName == "Standalone":
            illustratorMenu = QMenu("Illustrator")
            path = os.path.join(self.pluginDirectory, "UserInterfaces", "Illustrator.ico")
            icon = QIcon(path)
            illustratorMenu.setIcon(icon)
            
            illustratorAction = QAction("Connect", origin)
            illustratorAction.triggered.connect(lambda: self.connectToIllustrator(origin))
            
            illustratorMenu.addAction(illustratorAction)
            origin.menuTools.addSeparator()
            origin.menuTools.addMenu(illustratorMenu)

    @err_catcher(name=__name__)
    def customizeExecutable(self, origin, appPath, filepath):
        self.connectToIllustrator(origin, filepath=filepath)
        return True

    @err_catcher(name=__name__)
    def connectToIllustrator(self, origin, filepath=""):
        pythonPath = self.core.getPythonPath(executable="Prism")

        # Assuming there's an Illustrator-specific script similar to "Prism_Photoshop_MenuTools.py"
        plugin = self.core.getPlugin("Illustrator")
        menuPath = os.path.join(plugin.pluginPath, "Prism_Illustrator_MenuTools.py")
        
        # Launch the Python script to connect to Illustrator
        subprocess.Popen([pythonPath, menuPath, self.core.prismRoot, "Tools", filepath])

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes):
        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes
