// app.system('start "" "PRISMLIBS/Python311/Prism.exe" "PLUGINROOT/Scripts/Prism_Illustrator_MenuTools.py" "PRISMROOT" Settings')
// app.system('start "" "PRISMLIBS/Python311/Prism.exe" "PLUGINROOT/Scripts/Prism_Illustrator_MenuTools.py" "PRISMROOT" Tools')
// Get the path to the user's Documents folder
var documentsFolder = Folder.myDocuments;

// Create the path to the .bat file in the Documents folder
var batFile = new File(documentsFolder + "/run_prism_Settings.bat");

// Check if the .bat file already exists; if not, create and write to it
if (!batFile.exists) {
    batFile.open("w");
    // Write the command to start the Python script with the necessary paths
    batFile.writeln('start "" "PRISMLIBS/Python311/Prism.exe" "PLUGINROOT/Scripts/Prism_Illustrator_MenuTools.py" "PRISMROOT" Settings');
    batFile.close();
}

// Execute the batch file
batFile.execute();

// Wait a moment to ensure the batch file has finished executing
$.sleep(1000);

// Delete the .bat file after execution
if (batFile.exists) {
    batFile.remove();
}