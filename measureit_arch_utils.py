import bpy
import bmesh
import bgl

from mathutils import Vector
from addon_utils import check, paths
from sys import getrecursionlimit, setrecursionlimit

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



def safe_name(name):
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

class Set_Render:
    def __init__(self, sceneProps, is_vector=False):
        self.sceneProps = sceneProps
        self.is_vector = is_vector

    def __enter__(self):
        self.sceneProps.is_vector_draw = self.is_vector
        self.sceneProps.is_render_draw = True

    def __exit__(self, type, value, tb):
        self.sceneProps.is_vector_draw = False
        self.sceneProps.is_render_draw = False


class OpenGL_Settings:
    def __init__(self,props):
        self.props = props

    def __enter__(self):
        self.set_OpenGL_Settings(True)

    def __exit__(self, type, value, tb):
        self.set_OpenGL_Settings(False)

    def set_OpenGL_Settings(self, toggleBool, props=None):

        if toggleBool:
            bgl.glEnable(bgl.GL_MULTISAMPLE)
            bgl.glEnable(bgl.GL_BLEND)
            bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
            bgl.glBlendEquation(bgl.GL_FUNC_ADD)

            bgl.glDepthFunc(bgl.GL_LEQUAL)
            bgl.glDepthMask(True)

            if self.props and self.props.inFront:
                bgl.glDisable(bgl.GL_DEPTH_TEST)
            else:
                bgl.glEnable(bgl.GL_DEPTH_TEST)

        else:
            bgl.glDisable(bgl.GL_MULTISAMPLE)
            bgl.glDisable(bgl.GL_BLEND)
            bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
            bgl.glBlendEquation(bgl.GL_FUNC_ADD)

            bgl.glDisable(bgl.GL_DEPTH_TEST)
            bgl.glDepthFunc(bgl.GL_LEQUAL)
            bgl.glDepthMask(False)

            bgl.glDisable(bgl.GL_POLYGON_SMOOTH)

def get_view():
    scene = bpy.context.scene
    ViewGen = scene.ViewGenerator
    view = None

    try:
        view = ViewGen.views[ViewGen.active_index]
    except:
        view = None

    return view

def get_camera_z():
    camera = bpy.context.scene.camera
    mat = camera.matrix_world
    camera_rot = mat.to_quaternion()
    camera_z = Vector((0, 0, -1))
    camera_z.rotate(camera_rot)
    camera_z.normalize()
    return camera_z

def get_camera_z_dist(location):
    camera = bpy.context.scene.camera
    location = Vector(location)
    camera_z = get_camera_z()
    dist_vec = location - camera.location
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
                        warningStr = ("More than 2 Verticies selected across multiple objects\n"
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
