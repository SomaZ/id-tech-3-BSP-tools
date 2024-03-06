import sys
import os
import copy
from math import ceil
from pyidtech3lib import BSP_READER as BSP
from pyidtech3lib import Q3VFS, Import_Settings


def main():
	try:
		file_name = sys.argv[1]
	except Exception:
		print("No file specified for operation")
		return
	
	fixed_file_path = file_name.replace("\\", "/")
	split_folder = "/maps/"
	split = fixed_file_path.split(split_folder, 1)
	if len(split) < 2:
		print("Could not find base path in: " , fixed_file_path)
		print("BSP file must be in the 'maps' folder in the base path")
		return
	base_path = split[0] + '/'
	print("Guessed base path:" + base_path)

	vfs = Q3VFS()
	vfs.add_base(base_path)
	vfs.build_index()

	import_settings = Import_Settings(
		file=file_name.replace("\\", "/")
	)

	bsp = BSP(vfs, import_settings)
	map_name = bsp.map_name
	if map_name.startswith("maps/"):
		map_name = map_name[len("maps/"):]

	print("BSP:", map_name, "[{0} {1}]".format(bsp.header.magic_nr.decode('ASCII'), bsp.header.version_nr))
	for lump in bsp.lumps:
		print(lump, "Number of Elements:", len(bsp.lumps[lump]))

	shader_path = "shaders/"
	if not os.path.exists(base_path + shader_path):
		shader_path = "scripts/"

	if not os.path.exists(base_path + shader_path):
		os.makedirs(base_path + shader_path)
		print("Created new folder for the shader file:", base_path + shader_path)

	print("External lightmaps:", bsp.external_lm_files)
	print("Shader path:", shader_path)

	nomip_shader_names = [
		"{}/force_nomip_{}".format(map_name, i) for i in range(
			ceil(len(bsp.external_lm_files) / 8)
			)
		]
	
	shader_file = vfs.get("{}q3map2_{}.shader".format(shader_path, map_name))
	lines = shader_file.decode(encoding="latin-1").splitlines()
	new_shader_file_lines = []
	open_shader = 0
	for line in lines:
		if line.strip() in nomip_shader_names:
			open_shader = 1
			continue
		if open_shader > 0 and line.strip().startswith("{"):
			open_shader += 1
			continue
		if open_shader > 0 and line.strip().startswith("}"):
			open_shader -= 1
			continue
		if open_shader > 0:
			continue
		new_shader_file_lines.append(line)

	for id, shader_name in enumerate(nomip_shader_names):
		first_external_lightmap_index = id * 8
		last_external_lightmap_index = min(len(bsp.external_lm_files), first_external_lightmap_index + 8)
		external_lightmaps = bsp.external_lm_files[first_external_lightmap_index:last_external_lightmap_index]
		new_shader_file_lines.append(shader_name)
		new_shader_file_lines.append("{")
		new_shader_file_lines.append("nomipmaps")
		for lm in external_lightmaps:
			new_shader_file_lines.append("\t{")
			new_shader_file_lines.append("\t\tmap {}".format(lm))
			new_shader_file_lines.append("\t}")
		new_shader_file_lines.append("}")
		new_shader_file_lines.append("")

	new_surface_lump = []
	for shader_name in nomip_shader_names:
		if len(shader_name) > 62:
			print("Shader name would be bigger than 63 chars. Shortening the bsp file name might help.")
			print("Aborting")
			return
		new_shader = bsp.lump_info["shaders"]()
		new_shader.name = bytes(shader_name, "latin-1")
		bsp.lumps["shaders"].append(new_shader)

		new_surface = copy.copy(bsp.lumps["surfaces"][0])
		new_surface.texture = bsp.lumps["shaders"].index(new_shader)
		new_surface_lump.append(new_surface)
	
	for leaf in bsp.lumps["leaffaces"]:
		leaf.face += len(new_surface_lump)
	for model in bsp.lumps["models"]:
		model.face += len(new_surface_lump)

	bsp.lumps["surfaces"] = new_surface_lump + bsp.lumps["surfaces"]

	new_bsp_bytes = bsp.to_bytes()
	try:
		new_file_name = import_settings.file[:-(len(".bsp"))]+"_nomip_ext_lm.bsp"
		with open(new_file_name, "wb") as new_file:
			print("Writing new file: ", new_file_name)
			new_file.write(new_bsp_bytes)
			
	except PermissionError:
		print("Doesn't have permission to write to ", new_file_name)
		print("Aborting")

	try:
		new_file_name ="{}q3map2_{}.shader".format(base_path + shader_path, map_name)
		with open(new_file_name, "w") as new_file:
			print("Writing new file: ", new_file_name)
			for line in new_shader_file_lines:
				new_file.write(line+"\n")
			
	except PermissionError:
		print("Doesn't have permission to write to ", new_file_name)
		print("Aborting")

if __name__ == "__main__":
	main()