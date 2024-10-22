import bpy
import bmesh
import gpu
import os

from mathutils import Vector, Matrix
from addon_utils import check, paths
from sys import getrecursionlimit, setrecursionlimit
from datetime import datetime

from .measureit_arch_units import BU_TO_INCHES

__all__ = (
    'get_view',
    'get_rv3d',
    'interpolate3d',
    'get_selected_faces',
    'get_selected_vertex',
    'get_selected_vertex_history',
    'get_smart_selected',
    'local_attrs',
    'multi_getattr',
    'multi_setattr',
)

_imp_scales_dict ={
        "1' = 1'" : (1,1),
        "2\" = 1'" : (1,6),
        "1\" = 1'" : (1,12),
        "3/4\" = 1'" : (1,16),
        "1/2\" = 1'" : (1,24),
        "3/8\" = 1'" : (1,32),
        "1/4\" = 1'" : (1,48),
        "3/16\" = 1'": (1,64),
        "1/8\" = 1'" : (1,96),
        "3/32\" = 1'" : (1,128),
        "1/16\" = 1'" : (1,192),
}


_metric_scales_dict ={
        "1:1" : (1,1),
        "1:2" : (1,2),
        "1:5" : (1,5),
        "1:10" : (1,10),
        "1:20" : (1,20),
        "1:50" : (1,50),
        "1:100" : (1,100),
        "1:200" : (1,200),
        "1:500" : (1,500),
}

_cad_col_dict = {
    0 : (0,0,0,1),
    1 : (1,0,0,1),
    2 : (1,1,0,1),
    3 : (0,1,0,1),
    4 : (0,1,1,1),
    5 : (0,0,1,1),
    6 : (1,0,1,1),
    7 : (1,1,1,1),
    8 : (0.5,0.5,0.5,1),
    9 : (0.75,0.75,0.75,1),
    255: (1,1,1,1)
}


def load_shader_str(file, directory = ""):
    path = os.path.dirname(os.path.abspath(__file__))
    shader_path = os.path.join(path,"glsl")
    if directory != "":
        shader_path = os.path.join(shader_path,directory)
    shader_path = os.path.join(shader_path,file)
    shader_file = open(shader_path)
    shader_str = shader_file.read()
    shader_file.close()
    return shader_str


def safe_name(name, is_dxf = False):

    if is_dxf:
        pass

    try:
        ascii_name = name.encode('ascii','strict')
        safe_name = ascii_name.decode()
    except:
        ascii_name = name.encode('ascii','ignore')
        safe_name = ascii_name.decode()
        print("Extended ASCII Characters Not Supported. Extended Character has been Ignored, Please Rename: {}".format(name))

    return safe_name

class recursionlimit:
    def __init__(self, limit):
        self.limit = limit
        self.old_limit = getrecursionlimit()

    def __enter__(self):
        setrecursionlimit(self.limit)

    def __exit__(self, type, value, tb):
        setrecursionlimit(self.old_limit)



def rgb_gamma_correct(rawRGB):
    return Vector((
        pow(rawRGB[0], (1 / 2.2)),
        pow(rawRGB[1], (1 / 2.2)),
        pow(rawRGB[2], (1 / 2.2)),
        rawRGB[3]))

# Convert Pts definitions to px
def pts_to_px(pts):
    INCH_TO_PT = 72
    res = get_resolution() # Get Pixels per inch

    inch_size = pts * 1/INCH_TO_PT
    px_size = inch_size * res
    return px_size

def px_to_m(px, paper_space = False):
    res = get_resolution() # Get Pixels per inch
    scale = get_scale()

    m_size = px / res * 1/BU_TO_INCHES

    if paper_space:
        m_size *= scale

    return m_size

class Set_Render:

    def __init__(self, sceneProps, is_vector=False, is_dxf = False, offset_x = 0, offset_y =0):
        self.sceneProps = sceneProps
        self.is_vector = is_vector
        self.is_dxf = is_dxf
        self.offset_x_2d = offset_x
        self.offset_y_2d = offset_y

    def __enter__(self):
        self.sceneProps.is_vector_draw = self.is_vector
        self.sceneProps.is_dxf_draw = self.is_dxf
        self.sceneProps.is_render_draw = True
        self.sceneProps.offset_x_2d = self.offset_x_2d
        self.sceneProps.offset_y_2d = self.offset_y_2d

    def __exit__(self, type, value, tb):
        self.sceneProps.is_vector_draw = False
        self.sceneProps.is_render_draw = False
        self.sceneProps.is_dxf_draw = False
        self.sceneProps.offset_x_2d = 0
        self.sceneProps.offset_y_2d = 0


class OpenGL_Settings:
    def __init__(self,props):
        self.props = props

    def __enter__(self):
        self.set_OpenGL_Settings(True)

    def __exit__(self, type, value, tb):
        self.set_OpenGL_Settings(False)

    def set_OpenGL_Settings(self, toggleBool, props=None):

        if toggleBool:
            #bgl.glEnable(bgl.GL_MULTISAMPLE)
            #bgl.glEnable(bgl.GL_BLEND)
            gpu.state.blend_set('ALPHA')
            #bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
            #bgl.glBlendEquation(bgl.GL_FUNC_ADD)

            gpu.state.depth_test_set('LESS_EQUAL')
            gpu.state.depth_mask_set(True)

            if self.props and self.props.inFront:
                gpu.state.depth_test_set('NONE')

        else:
           # bgl.glDisable(bgl.GL_MULTISAMPLE)
            #bgl.glDisable(bgl.GL_BLEND)
            gpu.state.blend_set('ALPHA')
            #bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
            #bgl.glBlendEquation(bgl.GL_FUNC_ADD)

            gpu.state.depth_test_set('NONE')
            gpu.state.depth_mask_set(False)

def get_projection_matrix():
    scene = bpy.context.scene
    render = scene.render
    camera = scene.camera
    sceneProps = scene.MeasureItArchProps

    if sceneProps.is_render_draw:
        deps = bpy.context.evaluated_depsgraph_get()
        modelview_matrix = camera.matrix_world.inverted()
        projection_matrix = camera.calc_matrix_camera(
            deps,
            x=render.resolution_x,
            y=render.resolution_y,
            scale_x=render.pixel_aspect_x,
            scale_y=render.pixel_aspect_y,
            )

        modelViewProjectionMatrix = projection_matrix @ modelview_matrix

    else:
        modelViewProjectionMatrix = bpy.context.region_data.perspective_matrix

    return modelViewProjectionMatrix

def get_view():
    scene = bpy.context.scene
    ViewGen = scene.ViewGenerator
    view = None

    try:
        view = ViewGen.views[ViewGen.active_index]
    except:
        print('MeasureIt_ARCH View Required, Creating A Placeholder')
        try:
            view = ViewGen.views.add()
            view.name = 'Default View'
            if scene.camera != None:
                view.camera = scene.camera
        except AttributeError:
            print('Could not create view in get_view()')
    return view


def get_view_outpath(scene, view, suffix, relative = False):
    # Reset default outpath for older files
    if view.output_path == "//Renders\\":
        view.output_path = "//Renders"

    if view.output_path:
        filenameStr =  "{}_{}".format(view.view_num, view.name)
        outpath = os.path.join(view.output_path, filenameStr)
    else:
        outpath = scene.render.filepath
    

    filepath = "{}_{}".format(bpy.path.abspath(outpath), suffix)

    dir, filename = os.path.split(filepath)
    if not os.path.exists(dir):
        os.mkdir(dir)

    #print(dir)
    if view.name_folder:
        bn= bpy.path.basename(bpy.context.blend_data.filepath)
        bn = bn.replace('.blend','')
        namedir = os.path.join(dir,bn)
        if not os.path.exists(namedir):
            os.mkdir(namedir)
        dir = namedir

    #print(dir)
    if view.date_folder:
        today = datetime.now()
        datedir = os.path.join(dir, today.strftime('%Y%m%d'))
        if not os.path.exists(datedir):
            os.mkdir(datedir)
        dir = datedir

    #print(dir)
    filepath = os.path.join(dir, filename)
    if relative:
        filepath = filenameStr
    
    print(filepath)
    return filepath

def get_scale():
    scene = bpy.context.scene
    sceneProps = scene.MeasureItArchProps

    view = get_view()
    scale = sceneProps.default_scale

    if view is None or view.camera is None:
        return scale

    if view.camera.data.type == 'ORTHO' and view.res_type == 'PAPER':
        scale = view.model_scale / view.paper_scale

    return scale

def get_resolution(update_flag = False):
    scene = bpy.context.scene
    sceneProps = scene.MeasureItArchProps
    view = get_view()

    view_valid = view is not None and view.camera is not None and view.res_type == 'PAPER'

    # RENDER, SVG, or DXF DRAW:
    if sceneProps.is_render_draw or sceneProps.is_vector_draw or sceneProps.is_dxf_draw or update_flag:
        # If We're using View resolution
        if view.use_resolution_override and view_valid:
            return view.res
        else:
            return sceneProps.render_resolution

    # We're in the viewport
    else:
        if sceneProps.use_preview_res:  # If we Use Preview Res
            return sceneProps.preview_resolution

        else:  # Otherwise Get the view resolution
            if view.use_resolution_override and view_valid:
                return view.res

    # If all else fails, just use the render resolution
    return sceneProps.render_resolution

def get_camera_z():
    camera = bpy.context.scene.camera
    mat = camera.matrix_world

    # Account for negative scale
    scale = camera.scale
    scale_mat_x = Matrix.Scale(scale.x,4,Vector((1,0,0)))
    scale_mat_y = Matrix.Scale(scale.y,4,Vector((0,1,0)))
    scale_mat_z = Matrix.Scale(scale.z,4,Vector((0,0,1)))

    scale_mat = scale_mat_z @ scale_mat_y @ scale_mat_x

    camera_rot = (scale_mat@ mat).to_quaternion()
    camera_z = Vector((0, 0, -1))
    camera_z.rotate(camera_rot)
    camera_z.normalize()
    return camera_z

def get_camera_z_dist(location):
    camera = bpy.context.scene.camera
    location = Vector(location)
    camera_z = get_camera_z()
    camera_trans_mat = camera.matrix_world.to_translation()
    dist_vec = location - camera_trans_mat
    dist_along_camera_z = dist_vec.dot(camera_z)
    return dist_along_camera_z

def get_loaded_addons():
    paths_list = paths()
    addon_list = []
    for path in paths_list:
        for mod_name, mod_path in bpy.path.module_names(path):
            is_enabled, is_loaded = check(mod_name)
            if is_enabled and is_loaded:
                addon_list.append(mod_name)
    return addon_list

def get_rv3d():
    spaces = bpy.context.area.spaces
    rv3d = None
    for space in spaces:
        if space.type == 'VIEW_3D':
            rv3d = space.region_3d
    return rv3d

def get_sv3d():
    spaces = bpy.context.area.spaces
    sv3d = None
    for space in spaces:
        if space.type == 'VIEW_3D':
            sv3d = space
    return sv3d

def interpolate3d(v1, v2, d1):
    """
    Interpolate 2 points in 3D space

    :param v1: first point
    :type v1: Vector
    :param v2: second point
    :type v2: Vector
    :param d1: distance
    :type d1: Float
    :return: interpolate point
    :return type: Vector
    """

    assert isinstance(v1, Vector)
    assert isinstance(v2, Vector)
    assert isinstance(d1, float)

    # calculate vector
    v = v2 - v1

    # calculate distance between points
    d0 = v.length

    # calculate interpolate factor (distance from origin / distance total)
    # if d1 > d0, the point is projected in 3D space
    if d0 > 0:
        x = d1 / d0
    else:
        x = d1

    return Vector((v1[0] + (v[0] * x), v1[1] + (v[1] * x), v1[2] + (v[2] * x)))


def get_selected_faces(myobject):
    """
    Get vertex selected faces
    """
    mylist = []
    # if not mesh, no vertex
    if myobject.type != "MESH":
        return mylist

    # meshes
    oldobj = bpy.context.object
    bpy.context.view_layer.objects.active = myobject
    in_edit_mode = False
    if myobject.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
        in_edit_mode = True

    bm = bmesh.from_edit_mesh(myobject.data)
    for face in bm.faces:
        if face.select:
            mylist.append(face.index)

    if in_edit_mode:
        bpy.ops.object.editmode_toggle()

    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    return mylist


def get_selected_vertex(myobject):
    """
    Get vertex selected
    """

    mylist = []
    # if not mesh, no vertex
    if myobject.type != "MESH":
        return mylist

    # meshes
    oldobj = bpy.context.object
    bpy.context.view_layer.objects.active = myobject

    in_edit_mode = False
    if myobject.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
        in_edit_mode = True

    bm = bmesh.from_edit_mesh(myobject.data)
    bmhistory = bm.select_history
    if len(bmhistory) > 0:
        for v in bmhistory:
            if len(mylist) == 0:
                mylist.append(v.index)
            else:
                mylist.append(v.index)
                mylist.append(v.index)

    if in_edit_mode:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    return mylist


def get_selected_vertex_history(myobject):
    """
    Get vertex selected
    """
    mylist = []
    # if not mesh, no vertex
    if myobject.type != "MESH":
        return mylist

    # meshes
    oldobj = bpy.context.object
    bpy.context.view_layer.objects.active = myobject
    in_edit_mode = False
    if myobject.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
        in_edit_mode = True

    bm = bmesh.from_edit_mesh(myobject.data)
    for v in bm.select_history:
        mylist.extend([v.index])

    if in_edit_mode:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    return mylist


def get_smart_selected(filterObj=None, forceEdges=False, usePairs=True):
    """
    Get verticies and their parent object depending on selection type
    """
    # Adds verts to a vertex dictionary to be processed by the add function
    pointList = []
    warningStr = ''

    # Object Mode
    if bpy.context.mode == 'OBJECT':
        objs = bpy.context.selected_objects
        print('In Object Mode')
        idx = 0
        if len(objs) > 2 and usePairs:
            warningStr = "More than 2 objects selected, Order may not be as expected"

        # Sort Objects into Pairs
        idx = 0
        for obj in objs:
            pointData = {}
            pointData['vert'] = 9999999
            pointData['obj'] = obj
            if obj == bpy.context.active_object:
                pointList.insert(0,pointData)
            else:
                pointList.append(pointData)

            if usePairs:
                try:
                    pointData = {}
                    pointData['vert'] = 9999999
                    pointData['obj'] = objs[idx + 1]
                    pointList.append(pointData)
                except IndexError:
                    pass

            idx += 1

    # Edit Mode
    elif bpy.context.mode == 'EDIT_MESH':
        objs = bpy.context.objects_in_mode
        selectionMode = bpy.context.scene.tool_settings.mesh_select_mode

        # For each obj in edit mode
        for obj in objs:
            if filterObj is None or obj.name == filterObj.name:
                bm = bmesh.from_edit_mesh(obj.data)
                dupFlag = False

                # Ignore force Edges if Selection History exists
                if len(bm.select_history) >= 2:
                    forceEdges = False

                # Vertex Selection
                if selectionMode[0] and not forceEdges:
                    # Get Selected Verts:
                    verts = []
                    # use History if avaialable fall back to basic selection
                    if len(bm.select_history) > 0:
                        for vert in bm.select_history:
                            verts.append(vert)
                    else:
                        for v in obj.data.vertices:
                            if v.select:
                                verts.append(v)

                    # reverse selection history
                    verts.reverse()
                    idx = 0

                    # Flag to add a duplicate if were coming from a different obj
                    if ((len(pointList) % 2) == 1) and usePairs:
                        dupFlag = True

                    # Warning Text for too many verts
                    if len(verts) > 2 and len(objs) > 2:
                        warningStr = ("More than 2 Vertices selected across multiple objects\n"
                                      "Order may not be as expected")

                    for vert in verts:
                        pointData = {}
                        pointData['vert'] = vert.index
                        pointData['obj'] = obj
                        pointList.append(pointData)

                        if dupFlag:
                            pointData = {}
                            pointData['vert'] = vert.index
                            pointData['obj'] = obj
                            pointList.append(pointData)
                            dupFlag = False

                        if usePairs:
                            try:
                                pointData = {}
                                pointData['vert'] = verts[idx + 1].index
                                pointData['obj'] = obj
                                pointList.append(pointData)

                            except IndexError:
                                pass
                        idx += 1

                # Edge Selection
                elif selectionMode[1] or forceEdges:
                    for e in bm.edges:
                        if e.select:
                            for vert in e.verts:
                                pointData = {}
                                pointData['vert'] = vert.index
                                pointData['obj'] = obj
                                pointList.append(pointData)

        print('In Edit Mode')

    # Curve Selection
    elif bpy.context.mode == 'EDIT_CURVE':

        objs = bpy.context.objects_in_mode
        for obj in objs:
            spline_id=0
            for spline in obj.data.splines:
                point_id =0
                if spline.type != "BEZIER":
                    for point in spline.points:
                        if point.select:
                            pointData = {}
                            pointData['spline'] = spline_id
                            pointData['vert'] = point_id
                            pointData['obj'] = obj
                            pointList.append(pointData)
                else:
                    for point in spline.bezier_points:
                        if point.select_control_point:
                            pointData = {}
                            pointData['spline'] = spline_id
                            pointData['vert'] = point_id
                            pointData['obj'] = obj
                            pointList.append(pointData)
                        point_id += 1
                spline_id += 1




    return (pointList, warningStr)


class local_attrs(object):
    def __init__(self, obj, property_list):
        """
        Context manager that allows you to modify object attributes in a code
        block, and restore them to the values as of the beginning of the code
        block when done.

        :param obj: object for which attributes need to be restored
        :param property_list: list of attributes
          (they may contain dots for nested attributes)
        :type property_list: list of strings
        """
        self.obj = obj
        self.property_list = property_list
        self.state = {}

    def __enter__(self):
        for prop in self.property_list:
            self.state[prop] = multi_getattr(self.obj, prop)

    def __exit__(self, type, value, traceback):
        for prop in self.property_list:
            multi_setattr(self.obj, prop, self.state[prop])

# From:
# https://code.activestate.com/recipes/577346-getattr-with-arbitrary-depth/

def multi_getattr(obj, attr, default=None):
    """
    Get a named attribute from an object; multi_getattr(x, 'a.b.c.d') is
    equivalent to x.a.b.c.d. When a default argument is given, it is returned
    when any attribute in the chain doesn't exist; without it, an exception is
    raised when a missing attribute is encountered.
    """
    attributes = attr.split(".")
    for i in attributes:
        try:
            obj = getattr(obj, i)
        except AttributeError:
            if default:
                return default
            else:
                raise
    return obj


def multi_setattr(obj, attr, value):
    """
    Set a named attribute from an object; multi_setattr(x, 'a.b.c.d', value)
    is equivalent to x.a.b.c.d = value. An exception is raised when a missing
    attribute is encountered.
    """
    try:
        init, last = attr.rsplit(".", 1)
    except ValueError:
        init, last = [], attr
    else:
        init = init.split(".")
    for i in init:
        try:
            obj = getattr(obj, i)
        except AttributeError:
            raise
    setattr(obj, last, value)
