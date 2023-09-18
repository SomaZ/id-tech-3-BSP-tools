import sys
import pyidtech3lib
from ctypes import (LittleEndianStructure,
                    c_char, c_float, c_int, c_ubyte, sizeof)

class BSP_SPHERE_LIGHT_FAKK(LittleEndianStructure):
    _fields_ = [
        ("position", c_float*3),
        ("color", c_float*3),
        ("intensity", c_float),
        ("leaf", c_int),

        ("needs_trace", c_int),
        ("spot_light", c_int),
        ("spot_dir", c_float*3),
        ("spot_radiusbydistance", c_float),
    ]

class BSP_SPHERE_LIGHT_ALICE(LittleEndianStructure):
    _fields_ = [
        ("position", c_float*3),
        ("color", c_float*3),
        ("intensity", c_float),
        ("style_maybe", c_int),
        ("leaf", c_int),

        ("needs_trace", c_int),
        ("spot_light", c_int),
        ("spot_dir", c_float*3),
        ("spot_radiusbydistance", c_float),
    ]

def main():
    try:
        file_name = sys.argv[1]
    except Exception:
        print("No file specified for operation")
        return
    vfs = pyidtech3lib.Q3VFS()
    vfs.build_index()

    if file_name.endswith(".map"):
        file_name = file_name[:-len("map")] + "bsp"

    import_settings = pyidtech3lib.Import_Settings(
        file=file_name.replace("\\", "/")
    )

    bsp = pyidtech3lib.BSP_READER(vfs, import_settings)

    if (bsp.header.magic_nr != b'FAKK' or bsp.header.version_nr != 12):
        print("File not a FAKK BSP, aborting")
        print("magic_nr", bsp.header.magic_nr)
        print("version_nr", bsp.header.version_nr)
        return

    print("magic_nr", bsp.header.magic_nr)
    print("version_nr", bsp.header.version_nr)
    print("checksum", bsp.header.checksum)

    num_light_ents = 0
    light_ents = {}
    lights = []
    entities = bsp.get_bsp_entity_objects()
    for ent in entities:
        if ent.startswith("light_"):
            #print(hash(tuple(entities[ent].position)))
            light_ents[hash(tuple(entities[ent].position))] = num_light_ents
            lights.append(entities[ent])
            num_light_ents += 1

    print("Light entities: ", num_light_ents)
    print("Stored lights: ", len(bsp.lumps["entlights"]) / sizeof(BSP_SPHERE_LIGHT_FAKK))
    byte_array = bytearray()
    for char in bsp.lumps["entlights"]:
        byte_array += char

    new_dlight_lump = []
    for light_id in range(int(len(bsp.lumps["entlights"]) / sizeof(BSP_SPHERE_LIGHT_FAKK))):
        current_fakk_light = BSP_SPHERE_LIGHT_FAKK.from_buffer_copy(
            byte_array,
            light_id * sizeof(BSP_SPHERE_LIGHT_FAKK)
        )
        new_light = BSP_SPHERE_LIGHT_ALICE()
        new_light.position = current_fakk_light.position
        new_light.color = current_fakk_light.color
        new_light.intensity = current_fakk_light.intensity
        new_light.leaf = current_fakk_light.leaf
        new_light.needs_trace = current_fakk_light.needs_trace
        new_light.spot_light = current_fakk_light.spot_light
        new_light.spot_dir = current_fakk_light.spot_dir
        new_light.spot_radiusbydistance = current_fakk_light.spot_radiusbydistance

        new_light.style_maybe = int(current_fakk_light.intensity * 0.5)

        new_dlight_lump.append(new_light)

    bsp.lumps["entlights"] = new_dlight_lump
    bsp.header.version_nr = 42

    bsp_bytes = bsp.to_bytes()

    new_file_name = import_settings.file[:-(len(".bsp"))]+"_alice.bsp"
    try:
        with open(new_file_name, "wb") as f:
            print("Writing new file: ", new_file_name)
            f.write(bsp_bytes)
    except PermissionError:
        print("Doesn't have permission to write to ", new_file_name)
        print("Aborting")

if __name__ == "__main__":
	main()