from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
import bpy
import os
import re
import uuid
import mathutils
import json

bl_info = {
    "name": "Export to ARENA (to folder)",
    "author": "Nuno Pereira",
    "version": (0, 1, 2),
    "blender": (2, 93, 5),
    "location": "File > Export > ARENA Scene (to folder)",
    "description": "Export > ARENA Scene (to folder)",
    "warning": "",
    "category": "Import-Export"
}

def export_arena_scene(context, scene_id, filepath, arena_username, arena_realm, filestore_path, check_existing, export_format, export_selection, export_animations, export_extras, export_draco_mesh_compression_enable):
    print("export... ", filepath)

    gltf_ext = 'gltf'
    if export_format == 'GLB': gltf_ext = 'glb'

    export_objs = []
    if export_selection:
        export_objs = [obj for obj in bpy.context.selected_objects if obj.parent == None]
    else:
        export_objs = [obj for obj in bpy.context.scene.collection.all_objects if obj.parent == None]

    # save file
    if bpy.data.filepath:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

    arena_objects = []

    # iterate collections
    for obj in export_objs:
        obj_name = re.sub('_+', '_', re.sub('\W', '_', obj.name).lower())
        gltf_filepath = os.path.join(filepath, obj_name)
        print("export... ", gltf_filepath)

        # clear selected objects
        bpy.ops.object.select_all(action='DESELECT')

        # select object hierarchy
        for cobj in obj.children: cobj.select_set(True)
        obj.select_set(True)

        obj.rotation_mode = 'QUATERNION'

        # save location and rotation and move object to origin
        saved_loc = obj.matrix_world.to_translation()
        saved_rot = obj.matrix_world.to_quaternion()
        obj.location = (0, 0, 0)
        obj.rotation_quaternion = (1, 0, 0, 0)

        bpy.ops.export_scene.gltf(
            filepath=gltf_filepath,
            check_existing=check_existing,
            export_format=export_format,
            export_animations=export_animations,
            export_extras=export_extras,
            export_draco_mesh_compression_enable=export_draco_mesh_compression_enable,
            use_selection = True,
        )
        obj.location = saved_loc
        obj.rotation_quaternion = saved_rot

        arena_objects.append({
          "namespace": arena_username,
          "realm": arena_realm,
          "sceneId": scene_id,
          "object_id": f'be_{scene_id}_{obj_name}',
          "persist": True,
          "type": "object",
          "action": "create",
          "attributes": {
            "object_type": "gltf-model",
            "url": f'/store/users/{arena_username}/blender-exports/{scene_id}/{obj_name}.{gltf_ext}',
            "position": {
              "x": saved_loc[0],
              "y": saved_loc[2],
              "z": saved_loc[1] * -1
            },
            "rotation": {
              "x": saved_rot[1],
              "y": saved_rot[3],
              "z": saved_rot[2] * -1,
              "w": saved_rot[0]
            },
            "scale": {
              "x": 1,
              "y": 1,
              "z": 1
            }
          }
        })

    msg = f'Copy folder ({filepath}) to the ARENA filestore at {filestore_path}/{scene_id})'
    show_message_box(title="ARENA Export", icon='INFO', lines=("ARENA Scene Exported",msg))
    context.workspace.status_text_set(f'ARENA Scene Exported. NOTE: {msg}')

    json_filepath = os.path.join(filepath, 'scene.json')
    f = open(json_filepath, 'w', encoding='utf-8')
    f.write(json.dumps(arena_objects))
    f.close()

    return {'FINISHED'}

def username_update(self, context):
    self.filestore_path=f'/store/user/{self.arena_username}/blender-exports'

class ExportARENAScene(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export_arena.scene"
    bl_label = "Export to Folder"
    bl_options = {'UNDO'}

    filename_ext = ''

    # List of operator properties

    export_format: EnumProperty(
        name="Format",
        description="Choose Asset Format",
        items=(
            ('GLB', "GLB", "GLB"),
            ('GLTF_EMBEDDED', "GLTF Embedded", "GLTF Embedded"),
            ('GLTF_SEPARATE', "GLTF Seperate", "GLTF Seperate"),

        ),
        default='GLB',
    )

    arena_username: StringProperty(
        name="ARENA Username",
        description="ARENA Username; Used for the filestore path below (assets uploaded to the filestore)",
        default='wiselab',
        maxlen=100,
        update=username_update
    )

    arena_realm: StringProperty(
        name="ARENA Realm",
        description="ARENA Realm; Used to create the json file",
        default='realm',
        maxlen=100
    )

    export_selection: BoolProperty(
        name="Export Selection",
        description="Export selected objects only",
        default=False,
    )

    export_animations: BoolProperty(
        name="Export Animations",
        description="Exports active actions and NLA tracks as glTF animations",
        default=True,
    )

    export_extras: BoolProperty(
        name="Export Extras",
        description="Export custom properties as glTF extras",
        default=True,
    )

    export_draco_mesh_compression_enable: BoolProperty(
        name="Draco Compression",
        description="Compress mesh using Draco",
        default=False,
    )

    filestore_path: StringProperty(
        name="Filestore Path",
        description="ARENA filestore path to where assets will be uploaded (defaults to <filestore-home>/blender-exports)",
        default='/store/user/wiselab/blender-exports',
        maxlen=300
    )

    def execute(self, context):
        create_folder_if_does_not_exist(self.filepath)
        self.scene_id = os.path.basename(self.filepath)
        return export_arena_scene(
                    context,
                    self.scene_id,
                    self.filepath,
                    self.arena_username,
                    self.arena_realm,
                    self.filestore_path,
                    self.check_existing,
                    self.export_format,
                    self.export_selection,
                    self.export_animations,
                    self.export_extras,
                    self.export_draco_mesh_compression_enable
                    )

    def invoke(self, context, event):
        self.scene_id = f'untitled-scene'
        self.filepath = self.scene_id
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def create_folder_if_does_not_exist(folder_path):
    if os.path.isdir(folder_path):
        return
    os.mkdir(folder_path)

def show_message_box(title = "Message Box", icon = 'INFO', lines=""):
    myLines=lines
    def draw(self, context):
        for n in myLines:
            self.layout.label(text=n)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

def menu_func_export(self, context):
    self.layout.operator(ExportARENAScene.bl_idname, text="Export to ARENA")

def register():
    bpy.utils.register_class(ExportARENAScene)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ExportARENAScene)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_arena.scene('INVOKE_DEFAULT')
