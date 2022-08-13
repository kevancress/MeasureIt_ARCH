
# Annotations


## Add Annotations

##### Annotation:
 * Adds an Annotation to the selected Object or Vertex.
 ![image](images/ui-annotation-examples.jpg)

##### Annotation Style (Color Swatch Icon):
  * Style to be assigned to new Annotation on creation.


## Annotation Menu

![image](images/ui-annotations.jpg)

 * __Color__: Sets Annotation Color.
 * __Link Style (Link or Broken Link Icon)__: Toggles if this Annotation uses a Style.
 * __Visibility (Eye Icon)__: Toggles the Annotations visibility.
 * __Delete (x Icon)__: Deletes the Annotation.
 * __Annotation Menu (Chevron Icon)__
   * __Add Text Field__: Adds a text field to the selected Annotation.
   * __Remove Text Field__: Removes the last text field from the selected Annotation.

#### Annotation Settings

![image](images/ui-annotation-settings.jpg)

 * __Text Field__: Sets the text for the annotation.
   * Annotations can have multiple text fields, each new text field will display as a new line in the Annotation Text.
 * __Font__: Lets you select a custom font for the Annotation from your system.
 * __Text Source__: MeasureIt_ARCH can pull annotation text from an objects Custom Properties metadata. This field defines the source custom property.
   * If two text fields are available, MeasureIt_ARCH will use the first to display the custom properties name, and the second to display the value.
   * If only one text field is available, only the value will be displayed.
 * __Size__: The Annotation font size.
 * __Resolution__: The Annotation font resolution.
 * __Justification__: Text Justification relative to the end of the Annotation leader line (Left, Center, Right).
 * __Position__: Text Position relative to the end of the Annotation leader line (Top, Middle, Bottom).
 * __Endcap__
   * __Dot__: Adds a Circle to the end of the Annotation Leader.
   * __Triangle__: Adds an Arrow to the end of the Annotation Leader.
 * __Endcap Size__: Sets the size of the Dimension Leader Endcap.
 * __Line Weight__: Line Weight of the Annotation leader.
 * __Offset__: The XYZ offset from the object or vertex that the annotation is attached to.
 * __Rotation__: The XYZ rotation of the annotation text.
 * __Draw In Front__: Makes this element Ignore Visibility tests.