import arcpy
import os
from urllib.request import urlretrieve

dom_grid = "DOM_GRID"

class Toolbox:

    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Visibility Tools"
        self.alias = "visibility"

        # List of tool classes associated with this toolbox
        self.tools = [PrepareDOM_and_DTM]


class PrepareDOM_and_DTM(object):

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Download DOM and DTM Tiles"
        self.description = ""

    def getParameterInfo(self):

        input_feature = arcpy.Parameter(
            displayName="Input Feature",
            name="input_feature",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        dom_buffer = arcpy.Parameter(
            displayName="DOM Buffer Distance (m)",
            name="dom_buffer",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        dtm_buffer = arcpy.Parameter(
            displayName="DTM Buffer Distance (m)",
            name="dtm_buffer",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )

        resolution = arcpy.Parameter(
            displayName="Raster Resolution (m)",
            name="resolution",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        resolution.filter.type = "ValueList"
        resolution.filter.list = ["1", "10", "50"]

        return [input_feature, dom_buffer, dtm_buffer, resolution]


  

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):

        project_gdb = arcpy.mp.ArcGISProject(
            "CURRENT"
        ).defaultGeodatabase

        arcpy.env.workspace = project_gdb


        input_feature = parameters[0].valueAsText
        dom_buffer = parameters[1].value
        dtm_buffer = parameters[2].value
        resolution = int(parameters[3].valueAsText)

        if not arcpy.Exists(dom_grid):
            raise Exception(
            f"DOM_GRID not found: {dom_grid}"
        )
        
        desc = arcpy.Describe(input_feature)

        feature_name = arcpy.ValidateTableName(
            desc.name,
            arcpy.env.workspace
        )

        arcpy.AddMessage(f"Input feature: {feature_name}")
        
        dom_buffer_name = f"{feature_name}_DOM_buffer"
        dtm_buffer_name = f"{feature_name}_DTM_buffer"
        
        arcpy.AddMessage(f"DOM buffer: {dom_buffer_name}")
        arcpy.AddMessage(f"DTM buffer: {dtm_buffer_name}")

        if arcpy.Exists(dom_buffer_name):
            arcpy.management.Delete(dom_buffer_name)
        
        if arcpy.Exists(dtm_buffer_name):
            arcpy.management.Delete(dtm_buffer_name)
        
        arcpy.analysis.Buffer(
            in_features=input_feature,
            out_feature_class=dom_buffer_name,
            buffer_distance_or_field=f"{dom_buffer} Meters",
            line_side="FULL",
            line_end_type="ROUND",
            dissolve_option="NONE",
            method="PLANAR"
        )

        arcpy.AddMessage(
            f"Created DOM buffer: {dom_buffer_name}"
        )

        if dtm_buffer:

            arcpy.analysis.Buffer(
                in_features=input_feature,
                out_feature_class=dtm_buffer_name,
                buffer_distance_or_field=f"{dtm_buffer} Meters",
                line_side="FULL",
                line_end_type="ROUND",
                dissolve_option="NONE",
                method="PLANAR"
            )

            arcpy.AddMessage(
               f"Created DTM buffer: {dtm_buffer_name}"
            )

        project_gdb = arcpy.mp.ArcGISProject(
            "CURRENT"
        ).defaultGeodatabase

        tile_selection_fc = os.path.join(
            project_gdb,
            f"{feature_name}_DOM_tiles"
        )

        if arcpy.Exists(tile_selection_fc):
            arcpy.management.Delete(tile_selection_fc)

        arcpy.analysis.Intersect(
            in_features=[dom_grid, dom_buffer_name],
            out_feature_class=tile_selection_fc,
            join_attributes="ALL",
            output_type="INPUT"
        )

        count = int(arcpy.management.GetCount(tile_selection_fc)[0])

        arcpy.AddMessage(
            f"Intersect features count: {count}"
        )

        if not arcpy.Exists(tile_selection_fc):
            raise Exception(
            f"Intersect output was not created: {tile_selection_fc}"
        )

        tiles = sorted(set(
            row[0]
            for row in arcpy.da.SearchCursor(
                tile_selection_fc,
                ["TileName"]
                )
        ))

        if len(tiles) == 0:
            raise Exception(
            "No DOM tiles intersect the analysis area."
        )

        arcpy.AddMessage(
            f"Found {len(tiles)} DOM tiles."
        )

        project_folder = arcpy.mp.ArcGISProject(
            "CURRENT"
            ).homeFolder
        
        download_folder = os.path.join(
            project_folder,
            f"{feature_name}_DOM_tiles_download"
        )

        os.makedirs(
            download_folder,
            exist_ok=True
        )

        for tile in tiles:
            url = (
                f"https://nedlasting.geonorge.no/hoydedata/DOM{resolution}/{tile}.tif"
                
            )
            output_file = os.path.join(
                download_folder,
                f"{tile}.tif"
            )

            if os.path.exists(output_file):
                arcpy.AddMessage(
                    f"Already downloaded: {tile}"
                )
                continue
            try:
                urlretrieve(url, output_file)
                arcpy.AddMessage(
                    f"Downloaded: {tile}"
                )
            except Exception as e:
                arcpy.AddWarning(
                    f"Failed to download {tile}: {e}"
                )
                continue
      

        if dtm_buffer:

            arcpy.AddMessage(
                "Starting DTM workflow..."
            )

            dtm_download_folder = os.path.join(
                project_folder,
                f"{feature_name}_DTM_tiles_download"
            )

            os.makedirs(
                dtm_download_folder,
                exist_ok=True
            )

            for tile in tiles:

                url = (
                    f"https://nedlasting.geonorge.no/hoydedata/DTM{resolution}/{tile}.tif"
                )

                output_file = os.path.join(
                    dtm_download_folder,
                    f"{tile}.tif"
                )

                if os.path.exists(output_file):

                    arcpy.AddMessage(
                        f"Already downloaded: {tile}"
                    )
                    continue

                try:
                    urlretrieve(url, output_file)
                    arcpy.AddMessage(
                        f"Downloaded DTM: {tile}"
                    )

                except Exception as e:
                    arcpy.AddWarning(
                        f"Failed to download DTM {tile}: {e}"
                    )
                    continue

            
            output_dtm = f"{feature_name}_DTM.tif"


        arcpy.AddMessage(
            f"Downloaded {len(tiles)} DOM tiles."
        )

        if dtm_buffer:

            arcpy.AddMessage(
                f"Downloaded {len(tiles)} DTM tiles."
            )

        arcpy.AddMessage(
            "Download workflow completed."
        )

        dom_rasters = []

        for file in os.listdir(download_folder):
            if file.lower().endswith(".tif"):
                dom_rasters.append(os.path.join(download_folder, file))

        if len(dom_rasters) == 0:
            raise Exception(
                "No DOM rasters found in the download folder."
            )

        dom_raw = f"{feature_name}_DOM_raw.tif"

        dom_raw_path = os.path.join(
            download_folder,
            dom_raw
        )

        if arcpy.Exists(dom_raw_path):
            arcpy.management.Delete(dom_raw_path)

        arcpy.management.MosaicToNewRaster(
            input_rasters=dom_rasters,
            output_location=download_folder,
            raster_dataset_name_with_extension=dom_raw,
            coordinate_system_for_the_raster=arcpy.SpatialReference(25833),
            pixel_type="32_BIT_FLOAT",
            cellsize=1,
            number_of_bands=1,
            mosaic_method="LAST",
            mosaic_colormap_mode="FIRST"
        )

        dtm_rasters = []

        for file in os.listdir(dtm_download_folder):
            if file.lower().endswith(".tif"):
                dtm_rasters.append(os.path.join(dtm_download_folder, file))

        if len(dtm_rasters) == 0:
            raise Exception(
                "No DTM rasters found in the download folder."
            )

        dtm_raw = f"{feature_name}_DTM_raw.tif"

        dtm_raw_path = os.path.join(
            dtm_download_folder,
            dtm_raw
        )

        if arcpy.Exists(dtm_raw_path):
            arcpy.management.Delete(dtm_raw_path)

        arcpy.management.MosaicToNewRaster(
            input_rasters=dtm_rasters,
            output_location=dtm_download_folder,
            raster_dataset_name_with_extension=dtm_raw,
            coordinate_system_for_the_raster=arcpy.SpatialReference(25833),
            pixel_type="32_BIT_FLOAT",
            cellsize=1,
            number_of_bands=1,
            mosaic_method="LAST",
            mosaic_colormap_mode="FIRST"
        )

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
