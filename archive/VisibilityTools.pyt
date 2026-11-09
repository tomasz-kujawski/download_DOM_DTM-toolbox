import arcpy
import os
from urllib.request import urlretrieve
from arcpy.sa import ExtractByMask

toolbox_folder = os.path.dirname(__file__)

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
        self.label = "Prepare DOM"
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
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        dtm_buffer = arcpy.Parameter(
            displayName="DTM Buffer Distance (m)",
            name="dtm_buffer",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )

        return [input_feature, dom_buffer, dtm_buffer]


  

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


        input_feature = parameters[0].valueAsText
        dom_buffer = parameters[1].value
        dtm_buffer = parameters[2].value

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
                f"https://nedlasting.geonorge.no/hoydedata/DOM1/{tile}.tif"
                
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


        arcpy.CheckOutExtension("Spatial")

        clipped_folder = os.path.join(
            project_folder,
            f"{feature_name}_DOM_tiles_clipped"
        )

        os.makedirs(
            clipped_folder,
            exist_ok=True
        )

        for file in os.listdir(download_folder):
            
            if not file.lower().endswith(".tif"):
                continue

            input_raster = os.path.join(
                download_folder,
                file
            )

            output_raster = os.path.join(
                clipped_folder,
                file.replace(".tif", "_clipped.tif")
            )

            arcpy.AddMessage(
                f"Clipping {file}"
            )

            arcpy.AddMessage(f"Raster: {input_raster}")
            arcpy.AddMessage(f"Raster exists: {arcpy.Exists(input_raster)}")

            arcpy.AddMessage(f"Mask: {dom_buffer_name}")
            arcpy.AddMessage(f"Mask exists: {arcpy.Exists(dom_buffer_name)}")

            arcpy.AddMessage(
                f"Raster size: {os.path.getsize(input_raster)} bytes"
            )

            try:
                arcpy.AddMessage(
                f"Raster size: {os.path.getsize(input_raster)} bytes"
                )
            except:
                pass

            arcpy.AddMessage("---------------")
            
            result = ExtractByMask(
                input_raster,
                dom_buffer_name
            )

            result.save(output_raster)

            arcpy.AddMessage(
                f"Saved: {os.path.basename(output_raster)}"
            )


        dom_rasters_clipped =[]

        for file in os.listdir(clipped_folder):
            if file.lower().endswith("_clipped.tif"):
                dom_rasters_clipped.append(
                    os.path.join(
                        clipped_folder,
                        file
                    )
                )

        arcpy.AddMessage(
            f"Found {len(dom_rasters_clipped)} clipped rasters."
        )

        dom_output_folder = os.path.join(
            project_folder,
            f"{feature_name}_DOM"
        )

        os.makedirs(
            dom_output_folder,
            exist_ok=True
        )

        output_dom = f"{feature_name}_DOM.tif"

        arcpy.AddMessage(
            f"DTM clipped rasters: {len(dtm_rasters_clipped)}"
        )

        for raster in dtm_rasters_clipped:
            arcpy.AddMessage(raster)

        for raster in dtm_rasters_clipped:

            desc = arcpy.Describe(raster)

            arcpy.AddMessage(
                f"{os.path.basename(raster)} | "
                f"{desc.width} x {desc.height}"
            )

        output_dtm_full = os.path.join(
            dtm_output_folder,
            output_dtm
        )

        if arcpy.Exists(output_dtm_full):

            arcpy.management.Delete(
                output_dtm_full
            )

        arcpy.management.MosaicToNewRaster(
            input_rasters=dom_rasters_clipped,
            output_location=dom_output_folder,
            raster_dataset_name_with_extension=output_dom,
            pixel_type="32_BIT_FLOAT",
            number_of_bands=1,
            mosaic_method="LAST",
            cellsize=1,
            coordinate_system_for_the_raster=arcpy.SpatialReference(25833),
            mosaic_colormap_mode="FIRST"
        )

        arcpy.AddMessage(
            f"Mosaicked DOM raster created: {output_dom}"
        )

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
                    f"https://nedlasting.geonorge.no/hoydedata/DTM1/{tile}.tif"
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

            arcpy.CheckOutExtension("Spatial")
            
            clipped_folder_DTM = os.path.join(
                project_folder,
                f"{feature_name}_DTM_tiles_clipped"
            )
            
            os.makedirs(
                clipped_folder_DTM,
                exist_ok=True
            )
            
            for file in os.listdir(dtm_download_folder):
                        
                if not file.lower().endswith(".tif"):
                    continue
            
                input_raster = os.path.join(
                    dtm_download_folder,
                    file
                    )
            
                output_raster = os.path.join(
                    clipped_folder_DTM,
                    file.replace(".tif", "_clipped.tif")
                )
            
                arcpy.AddMessage(
                    f"Clipping {file}"
                )

                arcpy.AddMessage(f"Raster: {input_raster}")
                arcpy.AddMessage(f"Raster exists: {arcpy.Exists(input_raster)}")

                arcpy.AddMessage(f"Mask: {dtm_buffer_name}")
                arcpy.AddMessage(f"Mask exists: {arcpy.Exists(dtm_buffer_name)}")

                desc = arcpy.Describe(input_raster)
                arcpy.AddMessage(desc.dataType)

                arcpy.AddMessage(
                    f"File size: {os.path.getsize(input_raster)} bytes"
                )


                result_DTM = ExtractByMask(
                    input_raster,
                    dtm_buffer_name
                )
            
                result_DTM.save(output_raster)
            
            
            dtm_rasters_clipped =[]
            
            for file in os.listdir(clipped_folder_DTM):
                if file.lower().endswith("_clipped.tif"):
                    dtm_rasters_clipped.append(
                       os.path.join(
                            clipped_folder_DTM,
                            file
                        )
                    )
            
            arcpy.AddMessage(
                f"Found {len(dtm_rasters_clipped)} clipped rasters."
            )
            
            dtm_output_folder = os.path.join(
                project_folder,
                f"{feature_name}_DTM"
            )
            
            os.makedirs(
                dtm_output_folder,
                exist_ok=True
            )
            
            output_dtm = f"{feature_name}_DTM.tif"

            arcpy.management.MosaicToNewRaster(
                input_rasters=dtm_rasters_clipped,
                output_location=dtm_output_folder,
                raster_dataset_name_with_extension=output_dtm,
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
