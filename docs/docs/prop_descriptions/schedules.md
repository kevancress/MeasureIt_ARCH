# Schedules
Create Schedules that can be exported to a .csv spreadsheet

![image](images/__ui-schedules.jpg)

__General Settings__

* __Generate Schedule__: Exports a .csv schedule to the output path
* __Collection__: The collection of objects to include in this schedule
* __Output Path__: The path to export the schedule to
* __Date Folder__: Adds a folder with today's date to the output path
* __Sort Sub-Collections__: Will Create Categories for sub-Collection in the exported .csv
* __Group Rows__: Will group and count identical rows when creating the schedule

__Column Settings__
Use the Plus and Minus buttons to add and remove Columns, and the arrow buttons to re-order columns

* __Name__: The name for this column.
* __Column Data Type__: Sets the type of data to be displayed in this column
    * __RNA Prop__: Display a user specified RNA Property in this column
    !!! NOTE
        RNA Prop paths are defined in the same way as Blender's Driver definitions and TextField's Custom Properties AutoFill definitions

        For Example:

        - `[<Property Name]` would autofill the value of the custom property with matching `<Property Name>`
        - `.name` would autofill the name of the object
        - `.location[0]` would autofill the X location of the object
        - `.material_slots[0].name` would autofill the name of the first material on the object
        
    * __Dimension__: Display the objects X, Y, or Z bounding box dimension in this column.