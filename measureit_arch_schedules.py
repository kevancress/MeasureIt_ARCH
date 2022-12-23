import bpy
import csv
import os
import copy

from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    StringProperty,
    EnumProperty,
    PointerProperty
)
from bpy.types import (
    PropertyGroup,
    Panel,
    Operator,
    UIList,
    Collection
)
from datetime import datetime

from .measureit_arch_units import format_distance


class ColumnProps(PropertyGroup):
    name: StringProperty()

    data_path: StringProperty(
        name="Data Path",
        description="Data to use for this column",
        default="",
    )

    data: EnumProperty(
        items=(('.dimensions[0]', "Dimension X", "", 'DRIVER_DISTANCE', 1),
               ('.dimensions[1]', "Dimension Y", "", 'DRIVER_DISTANCE', 2),
               ('.dimensions[2]', "Dimension Z", "", 'DRIVER_DISTANCE', 3),
               ('--', "RNA Prop", "", 'RNA', 99)),
        name="Data",
        description="data")


class ScheduleProperties(PropertyGroup):

    name: StringProperty()

    date_folder: BoolProperty(
        name="Date Folder",
        description="Adds a Folder with todays date to the end of the output path",
        default=False)

    group_rows: BoolProperty(
        name="Group Rows",
        description="Group Identical Rows and include a Count",
        default=False)

    sort_subcollections: BoolProperty(
        name="Sort Sub Collections",
        description="Adds A section Header to the .csv to Sub Collections",
        default=False)

    output_path: StringProperty(
        name="Output Path",
        description="Render Output Path for this Schedule",
        subtype='FILE_PATH',
        default="",
    )

    collection: PointerProperty(type=Collection)

    columns: CollectionProperty(type=ColumnProps)


class ScheduleContainer(PropertyGroup):
    active_index: IntProperty(
        name='Active Schedule Index', min=0, max=1000, default=0,
        description='Index of the current Schedule')

    show_settings: BoolProperty(
        name='Show Schedule Settings', default=False)

    # Array of schedules
    schedules: CollectionProperty(type=ScheduleProperties)


class AddColumnButton(Operator):
    bl_idname = "measureit_arch.addschedulecolumn"
    bl_label = "Add"
    bl_description = "Add a column to this Schedule"
    bl_category = 'MeasureitArch'

    removeFlag: BoolProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):

        # Add Columns
        Generator = context.scene.ScheduleGenerator
        schedule = Generator.schedules[Generator.active_index]

        if self.removeFlag:
            schedule.columns.remove(len(schedule.columns) - 1)
        else:
            col = schedule.columns.add()
            col.name = "Column " + str(len(schedule.columns))
            col.data_path = ""
            col.data = '.dimensions[0]'

        # redraw
        context.area.tag_redraw()
        return {'FINISHED'}


class DeleteScheduleButton(Operator):
    bl_idname = "measureit_arch.deleteschedulebutton"
    bl_label = "Delete Schedule"
    bl_description = "Delete a Schedule"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    tag: IntProperty()

    def execute(self, context):
        # Add properties

        Generator = context.scene.ScheduleGenerator
        Generator.schedules.remove(Generator.active_index)

        return {'FINISHED'}


class GenerateSchedule(Operator):
    bl_idname = "measureit_arch.generateschedule"
    bl_label = "Generate Schedule"
    bl_description = "Generate a Schedule and save it to a .csv file"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}

    def check_collections(self, collection, schedule, depth=0):
        data = []
        rows = []  # Group of rows to be added to the data

        if schedule.sort_subcollections:
            namerow = []
            namerow.append(str(collection.name))
            rows.append(namerow)

        for obj in collection.objects:
            row = []
            if schedule.sort_subcollections:
                row.append('')
            for column in schedule.columns:
                row.append(self.get_column_data(column, obj))
            rows.append(row)

        if schedule.group_rows:
            rows = self.group_data(rows)

        data.append(rows)

        if len(collection.children) > 0:
            for subCol in collection.children:
                returned_rows = self.check_collections(
                    subCol, schedule, depth=depth + 1)
                data.append(returned_rows)

        return data

    def get_column_data(self, column, obj):
        try:
            if column.data == '--':
                # TODO: `eval` considered harmful
                data = eval(
                    'bpy.data.objects[\'' + obj.name + '\']' + column.data_path)
            else:
                # TODO: here too
                data = eval(
                    'bpy.data.objects[\'' + obj.name + '\']' + column.data)

                # Format distances
                if '.dim' in column.data:
                    data = format_distance(data)
            return data
        except:
            return '--'

    def group_data(self, data):
        Generator = bpy.context.scene.ScheduleGenerator
        schedule = Generator.schedules[Generator.active_index]

        dataCopy = copy.deepcopy(data)
        # Get Counts
        print(data)
        for checkrow in data:

            if schedule.sort_subcollections and checkrow[0] != '':
                pass
            else:
                rowCount = 0
                for row in dataCopy:
                    if checkrow == row:
                        rowCount += 1
                checkrow.append(rowCount)

        # Purge Duplicates
        for i, checkrow in enumerate(data):
            for j, row in reversed(list(enumerate(data))):
                if i != j and row == checkrow:
                    data.remove(row)

        return data

    def unpack_data(self, data, depth=0):
        row_list = []
        if type(data[0]) != str:
            for item in data:
                return_list = self.unpack_data(item, depth=depth + 1)
                for row in return_list:
                    row_list.append(row)

        else:
            row_list.append(data)

        return row_list

    def execute(self, context):
        # Add properties

        Generator = context.scene.ScheduleGenerator
        schedule = Generator.schedules[Generator.active_index]
        file_name = schedule.name + '.csv'
        file_path = schedule.output_path
        file_path = bpy.path.abspath(font_file)

        if schedule.date_folder:
            today = datetime.now()
            datepath = os.path.join(file_path, today.strftime('%Y%m%d'))
            if not os.path.exists(datepath):
                os.mkdir(datepath)
            file_path = datepath

        row_list = []

        # title each column
        firstRow = []
        if schedule.sort_subcollections:
            firstRow.append('')

        for column in schedule.columns:
            firstRow.append(column.name)

        # Add Count Column
        if schedule.group_rows:
            firstRow.append('Count')

        data = self.check_collections(schedule.collection, schedule)

        # Unpack Data
        data_list = self.unpack_data(data)

        for row in data_list:
            row_list.append(row)

        row_list.insert(0, firstRow)

        try:
            with open(os.path.join(file_path, file_name), 'w', newline='') as file:
                writer = csv.writer(file, lineterminator=',\n')
                writer.writerows(row_list)

        except PermissionError:
            self.report(
                {'ERROR'}, "Permission Error: File may be open in an External Application?")
            return {'FINISHED'}

        return {'FINISHED'}


class DuplicateScheduleButton(Operator):
    bl_idname = "measureit_arch.duplicateschedulebutton"
    bl_label = "Delete Schedule"
    bl_description = "Delete a Schedule"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    tag: IntProperty()

    # @classmethod
    # def poll(cls, context):
    #    Generator = context.scene.ScheduleGenerator
    #
    #    try:
    #        ActiveSchedule = Generator.shedules[Generator.active_index]
    #        return True
    #    except:
    #        return False

    def execute(self, context):
        # Add properties

        Generator = context.scene.ScheduleGenerator
        ActiveSchedule = Generator.schedules[Generator.active_index]
        newSchedule = Generator.schedules.add()
        newSchedule.name = ActiveSchedule.name + ' copy'

        # Get props to loop through
        for key in Generator.schedules[Generator.active_index].__annotations__.keys():
            try:
                newSchedule[key] = ActiveSchedule[key]
            except:
                pass

        return {'FINISHED'}


class M_ARCH_UL_Schedules_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            schedule = item
            layout.use_property_decorate = False
            row = layout.row(align=True)
            subrow = row.row()
            subrow.prop(schedule, "name", text="", emboss=False)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')


class SCENE_PT_Schedules(Panel):
    """ A panel in the Object properties window """

    bl_parent_id = 'SCENE_PT_Panel'
    bl_label = "Schedules"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='PRESET')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        ScheduleGen = scene.ScheduleGenerator

        row = layout.row()

        # Draw The UI List
        row.template_list("M_ARCH_UL_Schedules_list", "", ScheduleGen,
                          "schedules", ScheduleGen, "active_index", rows=2, type='DEFAULT')

        # Operators Next to List
        col = row.column(align=True)
        col.operator("measureit_arch.addschedulebutton", icon='ADD', text="")
        op = col.operator(
            "measureit_arch.deleteschedulebutton", text="", icon="X")
        op.tag = ScheduleGen.active_index  # saves internal data

        col.separator()
        up = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_UP")
        up.genPath = "bpy.context.scene.ScheduleGenerator"
        up.item_type = "schedules"
        up.upDown = -1

        down = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_DOWN")
        down.genPath = "bpy.context.scene.ScheduleGenerator"
        down.item_type = "schedules"
        down.upDown = 1

        col.separator()
        col.menu("SCENE_MT_Schedules_menu", icon='DOWNARROW_HLT', text="")

        # Settings Below List
        if len(ScheduleGen.schedules) > 0 and ScheduleGen.active_index < len(ScheduleGen.schedules):

            schedule = ScheduleGen.schedules[ScheduleGen.active_index]

            if ScheduleGen.show_settings:
                settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                settingsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(ScheduleGen, 'show_settings', text="",
                     icon=settingsIcon, emboss=False)

            row.label(text=schedule.name + ' Settings:')

            if ScheduleGen.show_settings:
                col = box.column()
                op = col.operator('measureit_arch.generateschedule',
                                  text="Generate Schedule", icon='FILE_NEW')

                col.prop_search(schedule, 'collection', bpy.data,
                                'collections', text="Collection", icon='GROUP')
                col.prop(schedule, "output_path")
                col.prop(schedule, "date_folder", text="Date Folder")
                col.prop(schedule, "sort_subcollections",
                         text="Sort Subcollections")
                col.prop(schedule, "group_rows", text="Group Rows")

                col = box.column()
                row = col.row(align=True,)
                row.label(text=schedule.name + ' Columns:')
                row.emboss = 'PULLDOWN_MENU'
                op = row.operator(
                    'measureit_arch.addschedulecolumn', text="", icon='ADD')
                op.removeFlag = False
                op = row.operator(
                    'measureit_arch.addschedulecolumn', text="", icon='REMOVE')
                op.removeFlag = True

                col = box.column()
                idx = 0
                for column in schedule.columns:
                    row = col.row(align=True)
                    row.prop(column, "name", text="")
                    row.prop(column, "data", text="")
                    if column.data == '--':
                        row.prop(column, "data_path", text="", icon="RNA")

                    row.emboss = 'PULLDOWN_MENU'
                    op = row.operator('measureit_arch.moveitem',
                                      text="", icon='TRIA_DOWN')
                    op.propPath = 'bpy.context.scene.ScheduleGenerator.schedules[bpy.context.scene.ScheduleGenerator.active_index].columns'
                    op.upDown = 1
                    op.idx = idx

                    op = row.operator('measureit_arch.moveitem',
                                      text="", icon='TRIA_UP')
                    op.propPath = 'bpy.context.scene.ScheduleGenerator.schedules[bpy.context.scene.ScheduleGenerator.active_index].columns'
                    op.upDown = -1
                    op.idx = idx

                    idx += 1


class SCENE_MT_Schedules_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self, context):
        layout = self.layout
        layout.operator(
            'measureit_arch.duplicateschedulebutton',
            text="Duplicate Selected Schedule", icon='DUPLICATE')


class AddScheduleButton(Operator):
    bl_idname = "measureit_arch.addschedulebutton"
    bl_label = "Add"
    bl_description = "Create A New Schedule"
    bl_category = 'MeasureitArch'

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties

                    scene = context.scene
                    ScheduleGen = scene.ScheduleGenerator

                    newSchedule = ScheduleGen.schedules.add()
                    newSchedule.name = 'Schedule ' + \
                        str(len(ScheduleGen.schedules))

                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}
