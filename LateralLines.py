"""
 SYNOPSIS

     LateralLines.py

 DESCRIPTION

     This script converts tap PACP observations from GNET into lateral lines including an estimated bearing.

 REQUIREMENTS

     Python 3
     arcpy
 """

import arcpy
import os
import traceback
import sys
sys.path.insert(0, "C:/Scripts")
import Logging

# Environment
arcpy.env.overwriteOutput = True

# Paths
fgdb_services = r"F:\Shares\FGDB_Services"

# Gravity Mains
sde = os.path.join(fgdb_services, r"DatabaseConnections\COSPW@imSPFLD@MCWINTCWDB.sde")
sewer_stormwater = os.path.join(sde, "SewerStormwater")
gravity_mains = os.path.join(sewer_stormwater, "ssGravityMain")

# Lateral Lines
lateral_lines = os.path.join(fgdb_services, r"Data\LateralLines.gdb")
pacp_observations_temp = os.path.join(lateral_lines, "Connections")
gravity_mains_temp = os.path.join(lateral_lines, "ssGravityMain")

# Event Table
event_table = r"\\mcwintcw01\GNET_DATA$\GNET_SanitaryObservation.gdb\GNet_WwMainlineObservation"

# Routes
routes = os.path.join(lateral_lines, "Routes")
laterals = os.path.join(lateral_lines, "Laterals")


@Logging.insert("Initialize", 1)
def initialize():
    # Create temporary data
    arcpy.FeatureClassToFeatureClass_conversion(gravity_mains, lateral_lines, "ssGravityMain", "OWNEDBY = 1 And WATERTYPE <> 'SW' And Stage = 0")
    arcpy.MakeFeatureLayer_management(gravity_mains_temp, "ssGravityMain")


@Logging.insert("Add Bearing", 1)
def add_bearing():
    """Add a bearing field"""

    arcpy.AddField_management("ssGravityMain", "BEARING", "DOUBLE", field_length=5, field_alias="Bearing")
    arcpy.CalculateGeometryAttributes_management("ssGravityMain", [["BEARING", "LINE_BEARING"]])


@Logging.insert("Create Lines", 1)
def place_points():
    """Place observations along gravity mains based off of length and direction"""

    arcpy.CreateRoutes_lr("ssGravityMain", "FACILITYID", routes)
    arcpy.MakeFeatureLayer_management(routes, "Routes")
    arcpy.MakeRouteEventLayer_lr("Routes", "FACILITYID", event_table, "AssetName POINT AtDistance", "RouteEvents")
    arcpy.SpatialJoin_analysis("RouteEvents", "ssGravityMain", pacp_observations_temp, "JOIN_ONE_TO_ONE", "KEEP_ALL")
    arcpy.MakeFeatureLayer_management(pacp_observations_temp, "Connections")


@Logging.insert("Add Fields", 1)
def add_fields():
    """Add more fields: LATID, LATDIST; remove a lot of unnecessary fields"""

    arcpy.AddXY_management("Connections")
    arcpy.AddFields_management("Connections",
                               [["LATID", "TEXT", None, 30],
                                ["LATDIST", "DOUBLE"]])
    arcpy.DeleteField_management("Connections",
                                 ["Join_County", "TARGET_FID", "MODIFIER", "CollectedBy", "CorrectiveActionRequired", "CorrectiveActionTaken", "Rating", "SedimentDepth", "PercentageCapacityLoss", "DefectSource",
                                  "Altitude", "Satellites", "HDOP", "PDOP", "SNR", "GpsSource", "ContinuousMark", "StillImage1", "StillImage2", "StillImage3", "VideoSegment", "RefPoint", "RefAngleUOM",
                                  "Continuous", "SedimentDepthUOM", "PercentageCapacityLossUOM", "Quantification1", "Quantification2s", "SurvDistance", "FACILITYID", "InstallDate", "Material", "Diameter",
                                  "MAINSHAPE", "LINEDYEAR", "LINERTYPE", "WATERTYPE", "ENABLED", "ACTIVEFLAG", "OWNEDBY", "MAINTBY", "SUMFLOW", "LASTUPDATE", "LASTEDITOR", "DOWNELEV", "UPELEV", "SLOPE",
                                  "COMMENT", "SPATAILID", "ADDRESS", "DISTRICT", "PLANT", "SOURCEID", "SOURCEATT", "SOURCEZ", "SOURCEXY", "NAD83XSTART", "NAD83YSTART", "SPATAILSTART", "NAD83XEND", "NAD83YEND",
                                  "SPATAILEND", "SURFCOND", "SURVMATERIAL", "SURVHEIGHT", "SURVSHAPE", "SURVDSELEV", "SURVUSELEV", "SURVLENGTH", "SURVSLOPE", "GXPCITY", "SLRATID", "SLRATSCORE", "SLRATSTATUS",
                                  "STAGE", "SLRATCOND", "CCTVCOND", "CCTVDATE", "ID", "AssetID", "Join_Count", "AssetSubType", "Percentage", "Length", "LengthUOM", "UntilAngle", "UntilAngleUOM",
                                  "PercentageUOM", "AtAngleUOM", "IsAtJoint", "Latitude", "Longitude", "RefAngle", "Comments", "ToDistanceUOM", "Quantification2", "SURVWIDTH", "SLRATDATE", "FROMMH1", "TOMH1",
                                  "POINT_M"])


@Logging.insert("Bearing Calculation", 1)
def bearing_calculation():
    """Calculate a bearing using PACP clock position and direction"""

    # Calculate LATDIST
    arcpy.CalculateField_management("Connections", "LATDIST", 25, "PYTHON3")

    # Calculate LATID
    selected_connections = arcpy.SelectLayerByAttribute_management("Connections", "NEW_SELECTION", "'FROMMH' IS NOT NULL AND 'AtAngle' IS NOT NULL")
    arcpy.CalculateField_management(selected_connections, "LATID", "str(!FROMMH!) + '_' + str(round(!AtDistance!, 0))", "PYTHON3")

    # LATID upstream left
    selected_connections = arcpy.SelectLayerByAttribute_management("Connections", "NEW_SELECTION", "SurvDirection = 'Upstream node' AND AtAngle > 6 AND AtAngle < 12")
    arcpy.CalculateFields_management(selected_connections, "PYTHON3",
                                     [["LATID", "!LATID! + 'L'"],
                                      ["BEARING", "!BEARING!-90"]])

    # LATID downstream left
    selected_connections = arcpy.SelectLayerByAttribute_management("Connections", "NEW_SELECTION", "SurvDirection = 'Downstream node' AND AtAngle > 0 AND AtAngle < 6")
    arcpy.CalculateFields_management(selected_connections, "PYTHON3",
                                     [["LATID", "!LATID! + 'L'"],
                                      ["BEARING", "!BEARING!-90"]])

    # LATID upstream right
    selected_connections = arcpy.SelectLayerByAttribute_management("Connections", "NEW_SELECTION", "SurvDirection = 'Upstream node' AND AtAngle > 0 AND AtAngle < 6")
    arcpy.CalculateFields_management(selected_connections, "PYTHON3",
                                     [["LATID", "!LATID! + 'R'"],
                                      ["BEARING", "!BEARING!+90"]])

    # LATID downstream right
    selected_connections = arcpy.SelectLayerByAttribute_management("Connections", "NEW_SELECTION", "SurvDirection = 'Downstream node' AND AtAngle > 6 AND AtAngle < 12")
    arcpy.CalculateFields_management(selected_connections, "PYTHON3",
                                     [["LATID", "!LATID! + 'R'"],
                                      ["BEARING", "!BEARING!+90"]])

    # Use all of this new information to make a 25ft line running at a bearing determined by direction and angle
    selected_connections = arcpy.SelectLayerByAttribute_management("Connections", "NEW_SELECTION", "BEARING IS NOT NULL AND "
                                                                                                   "Code IN ('TB', 'TBA', 'TBB', 'TBD', 'TBI', 'TF', 'TFA', 'TFB', 'TFC', 'TFD', 'TFI', 'TS', 'TSD') AND "
                                                                                                   "SurvDirection IS NOT NULL AND "
                                                                                                   "AtAngle IS NOT NULL")
    arcpy.BearingDistanceToLine_management(selected_connections, laterals, "POINT_X", "POINT_Y", "LATDIST", "FEET", "BEARING")


if __name__ == "__main__":
    traceback_info = traceback.format_exc()
    try:
        Logging.logger.info("Script Execution Started")
        initialize()
        add_bearing()
        place_points()
        add_fields()
        bearing_calculation()
        Logging.logger.info("Script Execution Finished")
    except (IOError, NameError, KeyError, IndexError, TypeError, UnboundLocalError, ValueError):
        Logging.logger.info(traceback_info)
    except NameError:
        print(traceback_info)
    except arcpy.ExecuteError:
        Logging.logger.error(arcpy.GetMessages(2))
    except:
        Logging.logger.info("An unspecified exception occurred")
