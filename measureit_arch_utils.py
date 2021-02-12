import bpy
import bmesh

__all__ = (
    'get_view',
    'get_selected_faces',
    'get_selected_vertex',
    'get_selected_vertex_history',
    'get_smart_selected'
)


def get_view():
    scene = bpy.context.scene
    ViewGen = scene.ViewGenerator
    view = None

    try:
        view = ViewGen.views[ViewGen.active_index]
    except:
        view = None

    return view


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

    return (pointList, warningStr)
