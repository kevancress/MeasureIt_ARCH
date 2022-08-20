# Installing MeasureIt_ARCH

## Basic Installation
 * [Install the latest stable version of Blender](https://www.blender.org/download/)
 * Download a zip file of the latest version of MeasureIt_ARCH from https://github.com/kevancress/MeasureIt_ARCH
 * Open the __Add-on Preferences (Edit -> Preferences -> Add-ons)__ and click install.

![image](images/install-1.jpg)

 * Navigate to and double click on the "MeasureIt_ARCH.zip" file you downloaded
 * Search for the MeasureIt_ARCH addon
 * Click the Checkbox to enable the addon

---

## Cloned Installation (Scripts Folder)
This method is recomended if you'd like to easily keep MeasureIt_ARCH up to date with the development branch of the repository and get easy access to new features and bug fixes. These instructions use GitHub Desktop to manage the repo, but any git client, (or command line git) will work.

 * [Install the latest stable version of Blender](https://www.blender.org/download/)
 * Install GitHub Desktop and create a GitHub account (if you haven't already)
 * Create and assign a custom scripts folder in Blenders User Preferences (Edit -> Preferences -> File Paths -> Scripts)
 * Ensure that the Scripts folder has `addons`, `modules`, and `startup` subdirectories.
 * Use GitHub Desktop to Clone the MeasureIt_ARCH repositiory from GitHub to the "addons" subdirectory of the scripts folder.
 * Restart Blender
 * Search for MeasureIt_ARCH in the add-ons menu
 * Click the Checkbox to enable the Add-on

With this setup, you can open GitHub Desktop and use the "Fetch" and "Pull Origin" buttons to update to the latest version of MeasureIt_ARCH

---

## Cloned Installation - For Development (APPDATA)
This method is recomended if you'd like to develop or make changes to MeasureIt_ARCH. These instructions use GitHub Desktop to manage the repo, but any git client, (or command line git) will work.
 
 * [Install the latest stable version of Blender](https://www.blender.org/download/)
 * Install GitHub Desktop and create a GitHub account (if you haven't already)
 * Download and install Visual Studio Code.
 * Install the Blender Development Extension for Visual Studio Code.
 * Clone the MeasureIt_ARCH repositiory from GitHub to a directory of your choice.
 * Open the MeasureIt_ARCH repository in Visual Studio Code
 * Use `Ctrl+Shift+P` to open the Command Palette in Visual Studio Code
 * Search for the `Blender: Start` command.
 * Navigate to your Blender executable when prompted.

This will create a symbolic link to the MeasureIt_ARCH repository in Blenders app data. Using MeasureIt_ARCH this way allows you to make use of VSCode's debugging tools. You can edit the addon code in VSCode and use the `Blender: Reload Addons` command from the Command Palette to reload the addon.