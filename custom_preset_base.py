import bpy
from bpy.types import Menu, Operator
from bpy.props import StringProperty, BoolProperty
import os

class Custom_Preset_Base:
    # bl_idname = "script.preset_base_add"
    # bl_label = "Add a Python Preset"
    bl_options = {'REGISTER'}  # only because invoke_props_popup requires.

    name = StringProperty(
            name="Name",
            description="Name of the preset, used to make the path name",
            maxlen=64,
            options={'SKIP_SAVE'},
            )
    remove_active = BoolProperty(
            default=False,
            options={'HIDDEN', 'SKIP_SAVE'},
            )
           
    @staticmethod
    def as_filename(name):  # could reuse for other presets
        for char in " !@#$%^&*(){}:\";'[]<>,.\\/?":
            name = name.replace(char, '_')
        return name.lower().strip()

    def execute(self, context):
        import os

        preset_menu_class = getattr(bpy.types, self.preset_menu)

        ext = ".py"
        
        if not self.remove_active:
            name = self.name.strip()
            if not name:
                return {'FINISHED'}

            filename = self.as_filename(name)

            preset_path = os.path.join("addons\MeasureIt-ARCH\presets", self.preset_subdir)
            scripts_path = bpy.utils.script_path_user()
            target_path = os.path.join(scripts_path,preset_path)
            
            print (target_path)
            if not target_path:
                self.report({'WARNING'}, "Failed to create presets path")
                return {'CANCELLED'}

            filepath = os.path.join(target_path, filename) + ext

            if hasattr(self, "add"):
                self.add(context, filepath)
            else:
                print("Writing Preset: %r" % filepath)

                file_preset = open(filepath, 'w')
                file_preset.write("import bpy\n")

                if hasattr(self, "preset_defines"):
                    for rna_path in self.preset_defines:
                        exec(rna_path)
                        file_preset.write("%s\n" % rna_path)
                    file_preset.write("\n")

                for rna_path in self.preset_values:
                    value = eval(rna_path)
                    # convert thin wrapped sequences
                    # to simple lists to repr()
                    try:
                        value = value[:]
                    except:
                        pass

                    file_preset.write("%s = %r\n" % (rna_path, value))

                file_preset.close()

            preset_menu_class.bl_label = filename
            print (preset_menu_class)

        else:
            preset_active = Custom_Preset_Base.as_filename(preset_menu_class.bl_label)
            print (preset_active)
            preset_path = os.path.join("addons\MeasureIt-ARCH\presets", self.preset_subdir)
            scripts_path = bpy.utils.script_path_user()
            target_path = os.path.join(scripts_path,preset_path)
            
            filepath = os.path.join(target_path,preset_active)
            filepath = filepath + '.py'

            if not filepath:
                return {'CANCELLED'}

            try:
                os.remove(filepath)
            except:
                import traceback
                traceback.print_exc()

            # XXX, stupid!
            preset_menu_class.bl_label = preset_menu_class.default_lable

        return {'FINISHED'}

    def check(self, context):
        self.name = self.as_filename(self.name.strip())

    def invoke(self, context, event):
        if not self.remove_active:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw_preset(self, context):
            """
            Define these on the subclass:
            - preset_operator (string)
            - preset_subdir (string)
            Optionally:
            - preset_extensions (set of strings)
            - preset_operator_defaults (dict of keyword args)
            """
            
            ext_valid = getattr(self, "preset_extensions", {".py", ".xml"})
            props_default = getattr(self, "preset_operator_defaults", None)
            
            preset_path = os.path.join("addons\MeasureIt-ARCH\presets", self.preset_subdir)
            
            self.path_menu(bpy.utils.script_paths(preset_path),
                           self.preset_operator,
                           props_default=props_default,
                           filter_ext=lambda ext: ext.lower() in ext_valid)
    
