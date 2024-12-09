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
import sys
import platform
import subprocess
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if platform.system() == "Windows":
    import win32com.client
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_Illustrator_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.win = platform.system() == "Windows"
        self.core.registerCallback(
            "onSaveExtendedOpen", self.onSaveExtendedOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onGetSaveExtendedDetails", self.onGetSaveExtendedDetails, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin
        )

    def startup(self, origin):
        """
        Initializes the connection to Adobe Illustrator and sets up the environment.
        """
        origin.timer.stop()
        self.core.setActiveStyleSheet("Illustrator")
        appIcon = QIcon(
            os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png"
            )
        )
        qApp.setWindowIcon(appIcon)

        if self.win:  # For Windows
            excludes = []
            while True:
                dname = self.getIllustratorDispatchName(excludes=excludes)
                self.ilApp = None
                if dname:
                    try:
                        self.ilApp = win32com.client.Dispatch(dname)
                    except:
                        self.ilApp = None
                        excludes.append(dname)
                        continue
                    else:
                        try:
                            self.ilApp.Application.ActiveDocument
                        except AttributeError:
                            self.ilApp = None
                            excludes.append(dname)
                            continue
                        except:
                            pass

                if not self.ilApp:
                    msg = "Could not connect to Illustrator."
                    self.core.popup(msg)
                    return

                self.dispatchSuffix = dname.replace("Illustrator.Application", "")
                logger.debug("Using %s" % dname)
                break
        else:  # For macOS
            self.ilAppName = "Adobe Illustrator 2023"
            for foldercont in os.walk("/Applications"):
                for folder in reversed(sorted(foldercont[1])):
                    if folder.startswith("Adobe Illustrator"):
                        self.ilAppName = folder
                        break
                break

            scpt = (
                """
                tell application "%s"
                    activate
                end tell
                """
                % self.ilAppName
            )
            self.executeAppleScript(scpt)


    @err_catcher(name=__name__)
    def getIllustratorDispatchName(self, excludes=None):
        """
        Finds an appropriate Illustrator dispatch name for Windows.
        """
        envkey = os.getenv("PRISM_ILLUSTRATOR_KEY")
        if envkey:
            return envkey

        name = "Illustrator.Application"
        classBase = "SOFTWARE\\Classes\\"

        try:
            if excludes and name in excludes:
                raise Exception()

            _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                classBase + name,
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )
        except:
            classKey = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                classBase,
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )
            try:
                i = 0
                keyName = None
                while True:
                    classNameKey = _winreg.EnumKey(classKey, i)
                    if sys.version[0] == "2":
                        classNameKey = unicode(classNameKey)

                    if excludes and classNameKey in excludes:
                        i += 1
                        continue

                    if classNameKey.startswith("Illustrator.Application."):
                        if keyName:
                            try:
                                if float(classNameKey.replace("Illustrator.Application.", "")) > float(keyName.replace("Illustrator.Application.", "")):
                                    keyName = classNameKey
                            except:
                                pass
                        else:
                            keyName = classNameKey

                    elif keyName:
                        return keyName

                    i += 1
            except WindowsError:
                pass

        else:
            return name


    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        pass

    @err_catcher(name=__name__)
    def executeAppleScript(self, script):
        try:
            p = subprocess.Popen(
                ["osascript"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True  # Ensures proper string handling for Python 3
            )
            stdout, stderr = p.communicate(script)
            if p.returncode != 0:
                # Log the error message for debugging
                self.core.popup(f"AppleScript execution failed:\n{stderr.strip()}")
                return None

            return stdout.strip()  # Clean up the output
        except Exception as e:
            self.core.popup(f"An error occurred while executing AppleScript:\n{str(e)}")
            return None
    
    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        """
        Get the current file name of the active document in Illustrator.
        If `path` is False, only the file name is returned.
        """
        try:
            if self.win:  # For Windows
                doc = self.ilApp.Application.ActiveDocument  # Access Illustrator application
                currentFileName = doc.FullName if doc.FullName  else "" #If the FullName property exists, the file has been saved at least once
            else:  # For macOS
                scpt = (
                    """
                    tell application "Adobe Illustrator"
                        set fpath to file path of current document
                        if fpath is missing value then
                            return ""
                        else
                            return POSIX path of fpath
                        end if
                    end tell
                    """
                )
                currentFileName = self.executeAppleScript(scpt)

                if currentFileName is None:
                    raise Exception("No file path found")

                if currentFileName.endswith("\n"):
                    currentFileName = currentFileName[:-1]

        except Exception as e:
            currentFileName = ""
            print(f"Error getting current file name: {e}")

        if not path and currentFileName != "":
            currentFileName = os.path.basename(currentFileName)

        return currentFileName

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        doc = self.core.getCurrentFileName()
        if doc != "":
            return os.path.splitext(doc)[1]

        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def onSaveExtendedOpen(self, origin):
        origin.l_format = QLabel("Save as:")
        origin.cb_format = QComboBox()
        origin.cb_format.addItems(self.sceneFormats)
        curFilename = self.core.getCurrentFileName()
        if curFilename:
            ext = os.path.splitext(curFilename)[1]
            idx = self.sceneFormats.index(ext)
            if idx != -1:
                origin.cb_format.setCurrentIndex(idx)
        rowIdx = origin.w_details.layout().rowCount()
        origin.w_details.layout().addWidget(origin.l_format, rowIdx, 0)
        origin.w_details.layout().addWidget(origin.cb_format, rowIdx, 1)

    @err_catcher(name=__name__)
    def onGetSaveExtendedDetails(self, origin, details):
        details["fileFormat"] = origin.cb_format.currentText()

    # Adobe Illustrator does not have native equivalents for CharIDToTypeID and StringIDToTypeID, 
    # as these are specific to Photoshop's scripting model.
    # Instead, we added error handling to notify the user if these methods are called.
    @err_catcher(name=__name__)
    def getCharID(self, s):
        try:
            return self.ilApp.CharIDToTypeID(s)
        except AttributeError:
            self.core.popup("Illustrator does not support CharIDToTypeID.")
            return None

    @err_catcher(name=__name__)
    def getStringID(self, s):
        try:
            return self.ilApp.StringIDToTypeID(s)
        except AttributeError:
            self.core.popup("Illustrator does not support StringIDToTypeID.")
            return None

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        """
        Saves the current Illustrator document to the specified filepath.
        If "fileFormat" is in `details`, appends the file extension to the filepath.
        """
        try:
            # Access the active document
            if self.win:  # Windows
                doc = self.ilApp.Application.ActiveDocument
            else:  # macOS
                scpt = (
                    """
                    tell application "Adobe Illustrator"
                        set doc to the current document
                        if doc is missing value then return ""
                        set docName to name of doc
                    end tell
                    """
                )
                doc = self.executeAppleScript(scpt)
                if doc is None or doc == "":
                    raise Exception("No active document found")

        except Exception as e:
            self.core.popup("There is no active document in Illustrator.")
            print(f"Error: {e}")
            return False

        # Handle file extension
        if "fileFormat" in details:
            filepath = os.path.splitext(filepath)[0] + details["fileFormat"]

        try:
            # Save the document
            if self.win:  # Windows
                filepath = os.path.normpath(filepath)
                doc.SaveAs(filepath)
            else:  # macOS
                scpt = """
                tell application "Adobe Illustrator"
                    save current document in POSIX file "%s" as Illustrator
                end tell
                """ % filepath
                result = self.executeAppleScript(scpt)
                if result is None:
                    raise Exception("Failed to save document")

        except Exception as e:
            self.core.popup(f"Failed to save the document: {e}")
            return False

        return True

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        return False

    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        pass

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame):
        pass

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        pass

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        if self.win:
            version = self.ilApp.Version
        else:
            scpt = (
                """
                tell application "%s"
                    application version
                end tell
            """
                % self.psAppName
            )
            version = self.executeAppleScript(scpt)

        return version

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        origin.setWindowIcon(QIcon(self.appIcon))
        origin.actionStateManager.setEnabled(False)
        ilMenu = QMenu("Illustrator", origin)
        ilAction = QAction("Open tools", origin)
        ilAction.triggered.connect(self.openIllustratorTools)
        ilMenu.addAction(ilAction)
        origin.menuTools.addSeparator()
        origin.menuTools.addMenu(ilMenu)

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        if not force and os.path.splitext(filepath)[1] not in self.sceneFormats:
            return False

        if self.win:
            self.ilApp.Open(filepath)
        else:
            scpt = """
                tell application "%s"
                    open file "%s"
                end tell
            """ % (
                self.psAppName,
                filepath,
            )
            self.executeAppleScript(scpt)

        return True

    # @err_catcher(name=__name__)
    # def importImages(self, origin):
    #     self.core.popup("importing IMGS")
    #     self.illustratorImportSource(origin)

    # @err_catcher(name=__name__)
    # def illustratorImportSource(self, origin):
    #     filepath = origin.seq[origin.getCurrentFrame()].replace("\\", "/")
    #     # self.openScene(origin, filepath, force=True)
    #     doc = self.ilApp.ActiveDocument
    #     try:
    #         # Place the image
    #         placed_item = doc.PlacedItems.Add()
    #         placed_item.File = filepath  # Set the image file path
            
    #         # Optional: Set the position (x, y) in points (0,0 is bottom-left corner)
    #         placed_item.Top = 500  # Y-coordinate
    #         placed_item.Left = 100  # X-coordinate

    #         # Optional: Scale the placed image
    #         placed_item.Width = 200  # Set the width in points
    #         placed_item.Height = 150  # Set the height in points

    #         self.core.popup(f"Image successfully placed in Illustrator: {filepath}")

    #     except Exception as e:
    #         print(f"Error placing the image: {e}")


    @err_catcher(name=__name__)
    def openIllustratorTools(self):
        self.dlg_tools = QDialog()

        self.dlg_tools.setWindowIcon(QIcon(self.appIcon))

        lo_tools = QVBoxLayout()
        self.dlg_tools.setLayout(lo_tools)

        b_saveVersion = QPushButton("Save Version")
        b_saveComment = QPushButton("Save Extended")
        b_export = QPushButton("Export")
        b_projectBrowser = QPushButton("Project Browser")
        b_settings = QPushButton("Settings")

        b_saveVersion.clicked.connect(self.core.saveScene)
        b_saveComment.clicked.connect(self.core.saveWithComment)
        b_export.clicked.connect(self.exportImage)
        b_projectBrowser.clicked.connect(self.core.projectBrowser)
        b_settings.clicked.connect(self.core.prismSettings)

        lo_tools.addWidget(b_saveVersion)
        lo_tools.addWidget(b_saveComment)
        lo_tools.addWidget(b_export)
        lo_tools.addWidget(b_projectBrowser)
        lo_tools.addWidget(b_settings)

        self.core.parentWindow(self.dlg_tools)
        self.dlg_tools.setWindowTitle("Prism")

        self.dlg_tools.show()
        self.dlg_tools.resize(self.dlg_tools.width()*1.5, self.dlg_tools.height())

        return True

    @err_catcher(name=__name__)
    def exportImage(self):
        if not self.core.projects.ensureProject():
            return False

        if not self.core.users.ensureUser():
            return False

        curfile = self.core.getCurrentFileName()
        fname = self.core.getScenefileData(curfile)

        if "type" in fname:
            entityType = fname["type"]
        else:
            entityType = "context"

        self.dlg_export = QDialog()
        self.core.parentWindow(self.dlg_export)
        self.dlg_export.setWindowTitle("Prism - Export image")

        lo_export = QVBoxLayout()
        self.dlg_export.setLayout(lo_export)

        self.rb_task = QRadioButton("Export into current %s" % entityType)
        self.w_task = QWidget()
        lo_prismExport = QVBoxLayout()
        lo_task = QHBoxLayout()
        self.w_comment = QWidget()
        lo_comment = QHBoxLayout()
        self.w_comment.setLayout(lo_comment)
        lo_comment.setContentsMargins(0, 0, 0, 0)
        lo_version = QHBoxLayout()
        lo_extension = QHBoxLayout()
        lo_localOut = QHBoxLayout()
        l_task = QLabel("Identifier:")
        l_task.setMinimumWidth(110)
        self.le_task = QLineEdit()
        self.le_task.setText(fname.get("task", ""))
        self.b_task = QPushButton(u"▼")
        self.b_task.setMinimumSize(35, 0)
        self.b_task.setMaximumSize(35, 500)
        l_comment = QLabel("Comment (optional):")
        l_comment.setMinimumWidth(110)
        self.le_comment = QLineEdit()
        self.chb_useNextVersion = QCheckBox("Use next version")
        self.chb_useNextVersion.setChecked(True)
        self.chb_useNextVersion.setMinimumWidth(110)
        self.cb_versions = QComboBox()
        self.cb_versions.setEnabled(False)
        l_ext = QLabel("Format:")
        l_ext.setMinimumWidth(110)
        self.cb_formats = QComboBox()
        self.cb_formats.addItems([".jpg", ".png", ".tif", ".svg", ".psd"])
        self.w_location = QWidget()
        self.lo_location = QHBoxLayout()
        self.lo_location.setContentsMargins(0, 0, 0, 0)
        self.w_location.setLayout(self.lo_location)
        self.l_location = QLabel("Location:")
        self.l_location.setMinimumWidth(140)
        self.cb_location = QComboBox()
        self.export_paths = self.core.paths.getRenderProductBasePaths()
        self.cb_location.addItems(list(self.export_paths.keys()))
        self.lo_location.addWidget(self.l_location)
        self.lo_location.addWidget(self.cb_location)
        if len(self.export_paths) < 2:
            self.w_location.setVisible(False)

        self.w_master = QWidget()
        self.lo_master = QHBoxLayout()
        self.lo_master.setContentsMargins(0, 0, 0, 0)
        self.w_master.setLayout(self.lo_master)
        self.l_master = QLabel("Master Version:")
        self.l_master.setMinimumWidth(140)
        self.cb_master = QComboBox()
        self.export_paths = self.core.paths.getRenderProductBasePaths()
        self.lo_master.addWidget(self.l_master)
        self.lo_master.addWidget(self.cb_master)

        masterItems = ["Set as master", "Add to master", "Don't update master"]
        self.cb_master.addItems(masterItems)

        if not self.core.mediaProducts.getUseMaster():
            self.w_master.setVisible(False)

        lo_task.addWidget(l_task)
        lo_task.addWidget(self.le_task)
        lo_task.addWidget(self.b_task)
        lo_comment.addWidget(l_comment)
        lo_comment.addWidget(self.le_comment)
        lo_version.addWidget(self.chb_useNextVersion)
        lo_version.addWidget(self.cb_versions)
        lo_extension.addWidget(l_ext)
        lo_extension.addWidget(self.cb_formats)
        lo_localOut.addWidget(self.w_location)
        lo_prismExport.addLayout(lo_task)
        lo_prismExport.addWidget(self.w_comment)
        lo_prismExport.addLayout(lo_version)
        lo_prismExport.addLayout(lo_extension)
        lo_prismExport.addWidget(self.w_master)
        self.w_task.setLayout(lo_prismExport)
        lo_version.setContentsMargins(0, 0, 0, 0)

        rb_custom = QRadioButton("Export to custom location")

        self.b_export = QPushButton("Export")

        lo_export.addWidget(self.rb_task)
        lo_export.addWidget(self.w_task)
        lo_export.addWidget(rb_custom)
        lo_export.addStretch()
        lo_export.addWidget(self.b_export)

        self.rb_task.setChecked(True)
        self.dlg_export.resize(400, 300)

        self.rb_task.toggled.connect(self.exportToggle)
        self.b_task.clicked.connect(self.exportShowTasks)
        self.le_comment.textChanged.connect(self.validateComment)
        self.chb_useNextVersion.toggled.connect(self.exportVersionToggled)
        self.le_task.editingFinished.connect(self.exportGetVersions)
        self.b_export.clicked.connect(self.saveExport)

        self.exportGetTasks()
        self.core.callback(
            name="Illustrator_onExportOpen",
            args=[self],
        )

        self.dlg_export.show()

        self.cb_versions.setMinimumWidth(300)
        self.cb_formats.setMinimumWidth(300)

        return True

    @err_catcher(name=__name__)
    def exportToggle(self, checked):
        self.w_task.setEnabled(checked)

    @err_catcher(name=__name__)
    def exportGetTasks(self):
        self.taskList = self.core.getTaskNames("2d")

        if len(self.taskList) == 0:
            self.b_task.setHidden(True)
        else:
            if "_ShotCam" in self.taskList:
                self.taskList.remove("_ShotCam")

    @err_catcher(name=__name__)
    def exportShowTasks(self):
        tmenu = QMenu(self.dlg_export)

        for i in sorted(self.taskList, key=lambda x: x.lower()):
            tAct = QAction(i, self.dlg_export)
            tAct.triggered.connect(lambda x=None, t=i: self.le_task.setText(t))
            tAct.triggered.connect(self.exportGetVersions)
            tmenu.addAction(tAct)

        tmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def exportGetVersions(self):
        existingVersions = []
        outData = self.exportGetOutputName()
        if outData is not None:
            versionDir = os.path.dirname(outData[1])

            if os.path.exists(versionDir):
                for i in reversed(sorted(os.listdir(versionDir))):
                    if len(i) < 5 or not i.startswith("v"):
                        continue

                    if sys.version[0] == "2":
                        if not unicode(i[1:5]).isnumeric():
                            continue
                    else:
                        if not i[1:5].isnumeric():
                            continue

                    existingVersions.append(i)

        self.cb_versions.clear()
        self.cb_versions.addItems(existingVersions)

    @err_catcher(name=__name__)
    def exportGetOutputName(self, useVersion="next"):
        if self.le_task.text() == "":
            return

        task = self.le_task.text()
        extension = self.cb_formats.currentText()
        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)

        if "type" not in fnameData:
            return

        location = self.cb_location.currentText()
        outputPathData = self.core.mediaProducts.generateMediaProductPath(
            entity=fnameData,
            task=task,
            extension=extension,
            comment=fnameData.get("comment", ""),
            framePadding="",
            version=useVersion if useVersion != "next" else None,
            location=location,
            returnDetails=True,
            mediaType="2drenders",
        )

        outputFolder = os.path.dirname(outputPathData["path"])
        hVersion = outputPathData["version"]

        return outputPathData["path"], outputFolder, hVersion

    @err_catcher(name=__name__)
    def exportVersionToggled(self, checked):
        self.cb_versions.setEnabled(not checked)
        self.w_comment.setEnabled(checked)

    @err_catcher(name=__name__)
    def validateComment(self, text):
        self.core.validateLineEdit(self.le_comment)

    @err_catcher(name=__name__)
    def saveExport(self):
        if self.rb_task.isChecked():
            taskName = self.le_task.text()
            if taskName is None or taskName == "":
                QMessageBox.warning(
                    self.core.messageParent, "Warning", "Please choose an identifier"
                )
                return

            if not self.core.fileInPipeline():
                self.core.showFileNotInProjectWarning(title="Warning")
                return False

            oversion = "next"
            if not self.chb_useNextVersion.isChecked():
                oversion = self.cb_versions.currentText()

            if oversion is None or oversion == "":
                QMessageBox.warning(
                    self.core.messageParent, "Warning", "Invalid version"
                )
                return

            outputPath, outputDir, hVersion = self.exportGetOutputName(oversion)

            outLength = len(outputPath)
            if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
                msg = (
                    "The output path is longer than 255 characters (%s), which is not supported on Windows. Please shorten the output path by changing the comment, identifier, or project path."
                    % outLength
                )
                self.core.popup(msg)
                return

            if not os.path.exists(outputDir):
                os.makedirs(outputDir)

            fileName = self.core.getCurrentFileName()
            context = self.core.getScenefileData(fileName)

            details = context.copy()
            if "filename" in details:
                del details["filename"]

            if "extension" in details:
                del details["extension"]

            details["version"] = hVersion
            details["sourceScene"] = fileName
            details["identifier"] = self.le_task.text()

            self.core.saveVersionInfo(
                filepath=os.path.dirname(outputPath),
                details=details,
            )
        else:
            startLocation = self.core.projects.getResolvedProjectStructurePath("textures")
            outputPath = QFileDialog.getSaveFileName(
                self.dlg_export,
                "Enter output filename",
                startLocation,
                "JPEG (*.jpg *.jpeg);;PNG (*.png);;TIFF (*.tif *.tiff);;SVG (*.svg);;PSD (*.psd)",
            )[0]

            if outputPath == "":
                return

        self.exportImageToPath(outputPath)
        self.handleMasterVersion(outputPath)
        self.dlg_export.accept()
        self.core.copyToClipboard(outputPath, file=True)
        self.core.callback(name="illustrator_onImageExported", args=[self, outputPath])

        try:
            self.core.pb.refreshRender()
        except:
            pass

        if os.path.exists(outputPath):
            QMessageBox.information(
                self.core.messageParent,
                "Export",
                "Successfully exported the image.\n(Path is in the clipboard)",
            )
        else:
            QMessageBox.warning(
                self.core.messageParent,
                "Export",
                "Unknown error. Image file doesn't exist:\n\n%s" % outputPath,
            )


    @err_catcher(name=__name__)
    def exportImageToPath(self, outputPath):
        ext = os.path.splitext(outputPath)[1].lower()
        activeDoc = self.ilApp.ActiveDocument
        
        # self.core.popup(f"{activeDoc}")
        # self.core.copyToClipboard(f"{win32com.client.constants.aiPNG24}")
        # self.core.popup(f"constants: \npng: {win32com.client.constants.aiPNG24}\njpg: {win32com.client.constants.aiJPEG}")

        try:
            # Check if the file extension is supported
            if ext in [".jpg", ".jpeg"]:
                exportOptions = win32com.client.Dispatch("Illustrator.ExportOptionsJPEG")
                exportOptions.QualitySetting = 100  # Maximum quality
                exportOptions.AntiAliasing = True
                exportType = win32com.client.constants.aiJPEG #1  # Illustrator constant for JPEG

            elif ext == ".png":
                exportOptions = win32com.client.Dispatch("Illustrator.ExportOptionsPNG24")
                exportOptions.AntiAliasing = True
                exportOptions.Transparency = True  # Maintain transparency
                exportOptions.ArtBoardClipping = True
                exportOptions.VerticalScale = 100
                exportOptions.HorizontalScale = 100
                exportType = win32com.client.constants.aiPNG24 #5

            elif ext in [".tif", ".tiff"]:
                exportOptions = win32com.client.Dispatch("Illustrator.ExportOptionsTIFF")
                exportOptions.Resolution = 300  # DPI
                exportOptions.ByteOrder = 1  # Byte order (1 = IBM PC, 2 = Macintosh)
                exportOptions.ImageColorSpace = 2  # RGB (2 = RGB, 1 = CMYK)
                exportType = win32com.client.constants.aiTIFF #9  # Illustrator constant for TIFF

            elif ext == ".svg":
                exportOptions = win32com.client.Dispatch("Illustrator.ExportOptionsSVG")
                exportOptions.FontSubsetting = 1  # Subset fonts (1 = None, 2 = Subset)
                exportOptions.CoordinatePrecision = 2  # Precision for SVG coordinates
                exportOptions.EmbedRasterImages = True  # Embed raster images
                exportType =  win32com.client.constants.aiSVG# 3 # Illustrator constant for SVG

            elif ext == ".psd":
                exportOptions = win32com.client.Dispatch("Illustrator.ExportOptionsPhotoshop")
                exportOptions.MaximumEditability = True  # Keep layers editable
                exportOptions.WriteLayers = True  # Export layers
                exportOptions.Resolution = 300  # DPI
                exportOptions.ImageColorSpace = 2  # RGB (2 = RGB, 1 = CMYK)
                exportType = win32com.client.constants.aiPhotoshop  # Illustrator constant for Photoshop

            

            else:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Export",
                    f"Unsupported export format: {ext}",
                )
                return False

            # Export the file
            activeDoc.Export(outputPath, exportType, exportOptions)
            return True

        except Exception as e:
            self.core.popup(f"Failed to export the file: {str(e)}")
            return False


    @err_catcher(name=__name__)
    def isUsingMasterVersion(self):
        useMaster = self.core.mediaProducts.getUseMaster()
        if not useMaster:
            return False

        masterAction = self.cb_master.currentText()
        if masterAction == "Don't update master":
            return False

        return True

    @err_catcher(name=__name__)
    def handleMasterVersion(self, outputName):
        if not self.isUsingMasterVersion():
            return

        masterAction = self.cb_master.currentText()
        if masterAction == "Set as master":
            self.core.mediaProducts.updateMasterVersion(outputName, mediaType="2drenders")
        elif masterAction == "Add to master":
            self.core.mediaProducts.addToMasterVersion(outputName, mediaType="2drenders")

    @err_catcher(name=__name__)
    def captureViewportThumbnail(self):
        import tempfile
        path = tempfile.NamedTemporaryFile(suffix=".jpg").name
        self.exportImageToPath(path.replace("\\", "/"))
        pm = self.core.media.getPixmapFromPath(path)
        try:
            os.remove(path)
        except:
            pass

        return pm
