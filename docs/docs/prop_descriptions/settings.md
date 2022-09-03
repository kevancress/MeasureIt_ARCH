#  Settings

![image](images/__ui-settings.jpg)

##### Hide Units

 * Show or hide the unit text on Metric Dimension elements.

##### Evaluate Depsgraph

* Evaluate Blender's Dependency Graph before drawing MeasureIt_ARCH elements.

!!! WARNING
    By default, MeasureIt_ARCH only evaluates the Dependency Graph for an object when exiting edit mode to improve drawing performance. Enabling this setting will make MeasureIt_ARCH attempt to evaluate the dependency graph every time the scene draws, this can be very slow.

    Depsgraph Evaluation can be enabled per element as well, please only enable it for the whole scene if absolutely necessary

##### Use Text Autoplacement
 * Automatically move dimension text to the outside of the dimension line if it is too large to fit within.

##### Default Resolution
  * Resolution to use for text rendering if no view resolution has been defined

##### Debug Text
 * Writes Dimension Text to an image for Debug

##### Debug Text Cards
  * Draw Dimension Text Cards for Debug

##### Enable Experimental
  * Enable Experimental Features in MeasureIt_ARCH

##### Instance Dimensions
 * Will Enable Dimension Instancing.

!!! WARNING
    Text on instanced Dimensions will not account for changes in the instances scale or rotation.

![image](images/ui-instance.jpg)