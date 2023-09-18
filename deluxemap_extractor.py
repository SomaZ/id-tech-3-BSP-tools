import sys
import os
from ctypes import (LittleEndianStructure, 
                    c_char, c_float, c_int, c_ubyte, sizeof, c_short, c_int16, c_byte)

from pyidtech3lib import BSP_READER as BSP
from pyidtech3lib import Q3VFS, Import_Settings

class TGA_HEADER(LittleEndianStructure):
    _fields_ = [
        ("idlength", c_byte),
        ("colourmaptype", c_byte),
        ("datatypecode", c_byte),
        ("colourmaporigin", c_int16),
        ("colourmaplength", c_int16),
        ("colourmapdepth", c_byte),
        ("x_origin", c_byte),
        ("y_origin", c_byte),
        ("width", c_short),
        ("height", c_short),
        ("bitsperpixel", c_byte),
        ("imagedescriptor", c_byte)
    ]

def save_lightmap_tga(file_name, lightmap):
    new_tga_header = TGA_HEADER()
    new_tga_header.idlength = 0
    new_tga_header.colourmaptype = 0
    new_tga_header.datatypecode = 2
    new_tga_header.colourmaporigin = 0
    new_tga_header.colourmaplength = 0
    new_tga_header.colourmapdepth = 0
    new_tga_header.x_origin = 0
    new_tga_header.y_origin = 0
    new_tga_header.width = 128
    new_tga_header.height = 128
    new_tga_header.bitsperpixel = 24
    new_tga_header.imagedescriptor = 0

    byte_array = bytearray()
    offset = 0

    byte_array += bytes(new_tga_header)
    offset += sizeof(new_tga_header)

    with open(file_name, "wb") as file:
        file.write(byte_array)
        for i in range(128 * 128):
            column = i % 128
            rowIndex = 128 - int(i/128) - 1
            index = column + rowIndex * 128
            file.write(c_byte(lightmap.map[index*3 + 2]))
            file.write(c_byte(lightmap.map[index*3 + 1]))
            file.write(c_byte(lightmap.map[index*3    ]))
		file.write(b'TRUEVISION-XFILE.\0')


def main():
    try:
        file_name = sys.argv[1]
    except Exception:
        print("No file specified for operation")
        return

    vfs = Q3VFS()
    vfs.build_index()

    import_settings = Import_Settings(
        file=file_name.replace("\\", "/")
    )

    bsp = BSP(vfs, import_settings)

    print("BSP: ", bsp.map_name, "[{0} {1}]".format(bsp.header.magic_nr.decode('ASCII'), bsp.header.version_nr))
    for lump in bsp.lumps:
        print(lump, "Number of Elements:", len(bsp.lumps[lump]))

    lightmap_lump = bsp.lumps["lightmaps"]
    if len(lightmap_lump) < 2:
        print("No internal deluxemaps found")
        return
    
    bsp.compute_lightmap_info(vfs)
    print("Deluxemapping: ", bsp.deluxemapping)

    if not bsp.deluxemapping:
        return
    
    new_file_name = import_settings.file[:-(len(".bsp"))]+"_noDeluxe.bsp"
    deluxemap_path = new_file_name[:-(len(".bsp"))]+"/"

    if not os.path.exists(deluxemap_path):
        os.makedirs(deluxemap_path)
    
    # remove deluxemaps and save them to disk
    new_lightmap_lump = []
    for id, lightmap in enumerate(lightmap_lump):
        if id % 2 == 1:
            new_fn = deluxemap_path + "dm_{0}.tga".format(str(id>>1).zfill(4))
            print("Lightmap ID ", id, "is deluxe: ", new_fn)
            save_lightmap_tga(new_fn, lightmap)
        else:
            new_lightmap_lump.append(lightmap)
    bsp.lumps["lightmaps"] = new_lightmap_lump

    # fix lightmap ids
    for surf in bsp.lumps["surfaces"]:
        if bsp.lightmaps == 4:
            for i in range(4):
                if surf.lm_indexes[i] < 0:
                    continue
                surf.lm_indexes[i] = surf.lm_indexes[i]>>1
        else:
            if surf.lm_indexes < 0:
                continue
            surf.lm_indexes = surf.lm_indexes>>1

    new_bsp_bytes = bsp.to_bytes()
    try:
        with open(new_file_name, "wb") as new_file:
            print("Writing new file: ", new_file_name)
            new_file.write(new_bsp_bytes)
            
    except PermissionError:
        print("Doesn't have permission to write to ", new_file_name)
        print("Aborting")

if __name__ == "__main__":
	main()