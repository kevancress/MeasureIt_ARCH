# MeasureIt_ARCH Dimension, Annotation and Linework tools for Blender 2.8

MeasureIt_ARCH is a fork of Antonio Vazquez's MeasureIt Addon.











### MeasureIt_ARCH Scene Settings
Found in the Scene Tab of the Properties Editor.

![image](images/__ui-scene.jpg)

#### MeasureIt_ARCH Unit Settings

![image](images/__ui-units.jpg)

MeasureIt_ARCH Unit Settings can be found in Blender's Scene Settings under the Units panel.

##### Metric Precision
 * Defines the number of decimal places included in dimensions when using the Metric Unit System.

##### Angle Precision
  * Defines the number of decimal places included in angle dimensions.

##### Imperial Precision
 * Fractional Precision to be used when using the Imperial Unit System.

 ##### Default Scale
  * Scale used for text and other scale-dependant elements if no view has been defined.


#### Styles

Styles have a nearly identical user interface to their corresponding items. Style-able properties can be found in the item's settings.

![image](images/__ui-styles.jpg)

Note that some settings, like an Annotations Offset, or a Dimensions Distance, are still set per item, even when using a style.



#### Schedules
Create Schedules that can exported to a .csv spreadsheet

![image](images/__ui-schedules.jpg)

__General Settings__
* __Generate Schedule__: Exports a .csv schedule to the output path
* __Collection__: The collection of objects to include in this schedule
* __Output Path__: The path to export the schedule to
* __Date Folder__: Adds a folder with todays date to the output path
* __Sort Subcollections__: Will Create Categories for subcollection in the exported .csv
* __Group Rows__: Will group and count identical rows when creating the schedule

__Column Settings__
Use the Plus and Minus buttons to add and remove Columns, and the arrow buttons to re-order columns

* __Name__: The name for this column
* __Column Data Type__: Sets the type of data to be displayed in this column
    * __RNA Prop__: Display a user specified RNA Property in this column
        * __NOTE__: This functions similarly to Blender's Driver definitions.
    * __Dimension__: Display the objects X, Y, or Z bounding box dimension in this column.

####  Settings

![image](images/__ui-settings.jpg)

##### Hide Units

 * Show or hide the unit text on Metric Dimension elements.

##### Evaluate Depsgraph

* Evaluate Blender's Dependency Graph before drawing MeasureIt_ARCH elements.
* __WARNING__: By default, MeasureIt_ARCH does not evaluate the Dependency Graph to improve performance and because some generative modifiers can give unpredictable results. Enabling this setting will make MeasureIt_ARCH attempt to evaluate these modifiers during its calculations. It can be slow and give unexpected results.
* This can be enabled for individual elements as well, please only enable this for the whole scene if absolutely necessary

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
   * __WARNING__: Text on instanced Dimensions will not account for changes in the instances local scale or rotation.

![image](images/ui-instance.jpg)

#### Object Settings

 * Dimension, Annotation, and Line Group settings can be found in Object Tab of the Properties Editor.
   * To add dimensions, annotations or line groups use the main tool panel.




