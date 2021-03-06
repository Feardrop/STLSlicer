import json
import logging
import os
import trimesh
from datetime import datetime
from typing import Union, Text, List
import util

log = logging.getLogger("STL Slicer")
log.setLevel(logging.DEBUG)
trimesh.util.attach_to_log()

STR_DATETIME_FORMAT = "%Y%m%d-%H%M%S"


class STLSlicer:
    def __init__(self):
        self.layers: dict = {}
        self.distance: float
        self.full_filename: Text = ""
        self.filename: Text = ""
        self.mesh = None
        self.mesh_watertight: bool = False

    def load_mesh(self, f: Union[str, bytes, os.PathLike]):
        """
        :param f: Filename
        Import meshes from binary/ASCII STL, Wavefront OBJ, ASCII OFF,
        binary/ASCII PLY, GLTF/GLB 2.0, 3MF, XAML, 3DXML, etc.

        Mesh objects can be loaded from a file name or from a buffer
        you can pass any of the kwargs for the `Trimesh` constructor
        to `trimesh.load`, including `process=False` if you would like
        to preserve the original loaded data without merging vertices
        STL files will be a soup of disconnected triangles without
        merging vertices however and will not register as watertight.
        """
        self.full_filename = f
        self.filename = os.path.splitext(f)[0]
        try:
            self.mesh = trimesh.load(f, process=False)
            self.mesh.units = "mm"
            log.info(f"File '{f}' loaded. Units set to '{self.mesh.units}'.")
        except Exception as e:
            log.info(f"File '{f}' not loaded. ERROR: {e}")
            raise e

        if repair_mesh_watertight(self.mesh):
            self.mesh_watertight = True
            log.debug(f"Mesh is watertight.")

    def slice_mesh(self, distance: float = None):
        """
        Slice meshes with one or multiple arbitrary planes and return the
        resulting surface

        +++
        Uses: Trimesh.section_multiplane()`

            Returns multiple parallel cross sections of the current mesh in 2D.

            Parameters
            ------------
            plane_normal: (3) vector for plane normal
              Normal vector of section plane
            plane_origin : (3, ) float
              Point on the cross section plane
            heights : (n, ) float
              Each section is offset by height along
              the plane normal.

            Returns
            ---------
            paths : (n, ) Path2D or None
              2D cross sections at specified heights.
              path.metadata['to_3D'] contains transform
              to return 2D section back into 3D space.
        +++

        :return:
        """
        distance = distance or self.distance

        # bounds = [[x_min,y_min,z_min],
        #           [x_max,y_max,z_max]]
        bounds: List = self.mesh.bounds
        z_min: float = bounds[0, 2]
        z_max: float = bounds[1, 2]
        origin = list(self.mesh.centroid[:2]) + [z_min]
        no_of_planes = int((z_max - z_min) / distance)
        z_list = [i * distance for i in range(no_of_planes + 1)]
        log.debug(
            f"Layer heights between {z_list[0]}{self.mesh.units} and "
            f"{z_list[-1]}{self.mesh.units}. "
            f"Distance: {distance}{self.mesh.units}. Count: {len(z_list)}."
        )

        slices_2D = self.mesh.section_multiplane(
            plane_origin=origin, plane_normal=[0, 0, 1], heights=z_list
        )

        layers = {}
        for i in range(len(slices_2D)):
            layers[z_list[i]] = slices_2D[i]

        self.layers = layers

        return layers

    def export_layers(self, exp_type: Text = "json", layers=None):
        """
        Exports all layers. Possible file-types: `json`, `dxf`, `svg`.

        :param layers: List of `trimesh.Path2D` objects.
        :param exp_type: [`json`, `dxf`, `svg`]
        :return: True if successful.
        """

        layers = layers or self.layers

        # Build dictionary
        slice_data = {
            "source": self.full_filename,
            "units": str(self.mesh.units),
            "watertight": self.mesh_watertight,
            "layers": layers,
        }

        # Export to JSON
        if exp_type == "json":
            exp_filename = f"{self.filename}.{exp_type}"
            with open(exp_filename, "w") as exp_file:
                # NumpyArrayEncoder handles the transformation of Path2D objects
                exp_string = json.dumps(
                    slice_data, cls=util.NumpyArrayEncoder, indent=2
                )
                exp_file.write(exp_string)
                log.debug(f"Export to {exp_filename} finished.")

            return True

        elif exp_type in ["dxf", "svg"]:
            # make directory for multiple files according to expansion type
            while True:
                date_time_str = datetime.now().strftime(STR_DATETIME_FORMAT)
                dir_name = "_".join([self.filename, exp_type, date_time_str])
                try:
                    # Raises an OSError if dir already exists.
                    os.makedirs(dir_name, exist_ok=False)
                    break
                except OSError:
                    continue

            base_name = os.path.split(self.filename)[1]

            # export to visual file-types
            with open(f"{dir_name}/{base_name}_info.json", "w") as json_file:
                json_dict = slice_data.copy()
                layers = json_dict.pop("layers")
                json_dict["files"] = {}

                for height, path2D in layers.items():
                    layer_filename_full = f"{dir_name}/{base_name}_{height}.{exp_type}"
                    try:
                        path2D.export(file_obj=layer_filename_full, file_type=exp_type)
                        json_dict["files"][height] = layer_filename_full
                    except AttributeError:
                        log.debug(
                            f"{layer_filename_full} not created. No data to display."
                        )

                exp_string = json.dumps(json_dict, cls=util.NumpyArrayEncoder, indent=2)
                json_file.write(exp_string)
                log.debug(f"Export to {dir_name} finished.")

            return True

        else:
            log.error(
                f"Extension '{exp_type}' not supported. "
                f"Currently supported: ['json', 'dxf', 'svg']"
            )

            return False


def repair_mesh_watertight(mesh):
    if not mesh.is_watertight:
        log.debug(f"Mesh not watertight. Fixing normals.")
        if not mesh.fix_normals:
            log.debug(f"Mesh not watertight. Filling holes.")
            if not mesh.fill_holes:
                log.debug(f"Mesh is not watertight. Not fixed!")
                return False
    return True
