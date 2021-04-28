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
import logging
import os
import sys
import traceback


def ScriptLogging():
    """Enables console and log file logging; see test script for comments on functionality"""
    current_directory = os.getcwd()
    script_filename = os.path.basename(sys.argv[0])
    log_filename = os.path.splitext(script_filename)[0]
    log_file = os.path.join(current_directory, f"{log_filename}.log")
    if not os.path.exists(log_file):
        with open(log_file, "w"):
            pass
    message_formatting = "%(asctime)s - %(levelname)s - %(message)s"
    date_formatting = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=message_formatting, datefmt=date_formatting)
    logging_output = logging.getLogger(f"{log_filename}")
    logging_output.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logging_output.addHandler(console_handler)
    logging.basicConfig(format=message_formatting, datefmt=date_formatting, filename=log_file, filemode="w", level=logging.INFO)
    return logging_output


def LateralLines():
    """Create lateral lines using PACP observations"""

    # Logging
    def logging_lines(name):
        """Use this wrapper to insert a message before and after the function for logging purposes"""
        if type(name) == str:
            def logging_decorator(function):
                def logging_wrapper(*exception):
                    logger.info(f"{name} Start")
                    function(*exception)
                    logger.info(f"{name} Complete")
                return logging_wrapper
            return logging_decorator

    logger = ScriptLogging()
    logger.info("Script Execution Start")

    # Paths
    fgdb_services = r"F:\Shares\FGDB_Services"
    sde = os.path.join(fgdb_services, r"DatabaseConnections\COSPW@imSPFLD@MCWINTCWDB.sde")
    sewer_stormwater = os.path.join(sde, "SewerStormwater")
    gravity_mains = os.path.join(sewer_stormwater, "ssGravityMain")
    lateral_lines = os.path.join(fgdb_services, r"Data\LateralLines.gdb")
    pacp_observations_temp = os.path.join(lateral_lines, "Connections")
    gravity_mains_temp = os.path.join(lateral_lines, "ssGravityMain")
    event_table = r"\\mcwintcw01\GNET_DATA$\GNET_SanitaryObservation.gdb\GNet_WwMainlineObservation"

    # Routes
    routes = os.path.join(lateral_lines, "Routes")
    laterals = os.path.join(lateral_lines, "Laterals")

    # Environment
    arcpy.env.overwriteOutput = True

    # Create temporary data
    arcpy.FeatureClassToFeatureClass_conversion(gravity_mains, lateral_lines, "ssGravityMain", "OWNEDBY = 1 And WATERTYPE <> 'SW' And Stage = 0")
    arcpy.MakeFeatureLayer_management(gravity_mains_temp, "ssGravityMain")

    @logging_lines("Add Bearing")
    def AddBearing():
        """Add a bearing field"""

        arcpy.AddField_management("ssGravityMain", "BEARING", "DOUBLE", field_length=5, field_alias="Bearing")
        arcpy.CalculateGeometryAttributes_management("ssGravityMain", [["BEARING", "LINE_BEARING"]])

    @logging_lines("Create Lines")
    def PlacePoints():
        """Place observations along gravity mains based off of length and direction"""

        arcpy.CreateRoutes_lr("ssGravityMain", "FACILITYID", routes)
        arcpy.MakeFeatureLayer_management(routes, "Routes")
        arcpy.MakeRouteEventLayer_lr("Routes", "FACILITYID", event_table, "AssetName POINT AtDistance", "RouteEvents")
        arcpy.SpatialJoin_analysis("RouteEvents", "ssGravityMain", pacp_observations_temp, "JOIN_ONE_TO_ONE", "KEEP_ALL")
        arcpy.MakeFeatureLayer_management(pacp_observations_temp, "Connections")

    @logging_lines("Add Fields")
    def AddFields():
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

    @logging_lines("Bearing Calculation")
    def BearingCalculation():
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

    # Try running above scripts
    try:
        AddBearing()
        PlacePoints()
        AddFields()
        BearingCalculation()
    except (IOError, KeyError, NameError, IndexError, TypeError, UnboundLocalError, ValueError):
        traceback_info = traceback.format_exc()
        try:
            logger.info(traceback_info)
        except NameError:
            print(traceback_info)
    except arcpy.ExecuteError:
        try:
            logger.error(arcpy.GetMessages(2))
        except NameError:
            print(arcpy.GetMessages(2))
    except:
        logger.exception("Picked up an exception!")
    finally:
        try:
            logger.info("Script Execution Complete")
        except NameError:
            pass


def main():
    LateralLines()


if __name__ == '__main__':
    main()
