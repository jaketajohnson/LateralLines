"""
 SYNOPSIS

     SnowRisk.py

 DESCRIPTION

     This script performs COF, POF, and Risk calculations for snow operations

 REQUIREMENTS

     Python 3
     arcpy
 """

import arcpy
import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler


def start_rotating_logging(log_file=None, max_bytes=10000, backup_count=1, suppress_requests_messages=True):
    """Creates a logger that outputs to stdout and a log file; outputs start and completion of functions or attribution of functions"""

    formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Paths to desired log file
    script_folder = os.path.dirname(sys.argv[0])
    script_name = os.path.basename(sys.argv[0])
    script_name_no_ext = os.path.splitext(script_name)[0]
    log_folder = os.path.join(script_folder, "Log_Files")
    if not log_file:
        log_file = os.path.join(log_folder, f"{script_name_no_ext}.log")

    # Start logging
    the_logger = logging.getLogger(script_name)
    the_logger.setLevel(logging.DEBUG)

    # Add the rotating file handler
    log_handler = RotatingFileHandler(filename=log_file, maxBytes=max_bytes, backupCount=backup_count)
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(formatter)
    the_logger.addHandler(log_handler)

    # Add the console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    the_logger.addHandler(console_handler)

    # Suppress SSL warnings in logs if instructed to
    if suppress_requests_messages:
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    return the_logger


def LateralLines():

    # Paths
    fgdb_services = r"F:\Shares\FGDB_Services"
    sde = os.path.join(fgdb_services, r"DatabaseConnections\da@mcwintcwdb.cwprod@imspfld.sde")
    lateral_lines = os.path.join(fgdb_services, r"Data\LateralLines.gdb")
    event_table = r"\\mcwintcw01\GNET_DATA$\GNET_SanitaryObservation.gdb\GNet_WwMainlineObservation"
    sewer_engineering = os.path.join(sde, "SewerEngineering")
    pacp_observations = os.path.join(sewer_engineering, "pacpObservations")
    pacp_observations_temp = os.path.join(lateral_lines, "Connections")
    sewer_stormwater = os.path.join(sde, "SewerStormwater")
    gravity_mains = os.path.join(sewer_stormwater, "ssGravityMain")
    gravity_mains_temp = os.path.join(lateral_lines, "ssGravityMain")

    # Routes
    routes = os.path.join(lateral_lines, "Routes")
    laterals = os.path.join(lateral_lines, "Laterals")

    # Environment
    arcpy.env.workspace = lateral_lines
    arcpy.env.overwriteOutput = True
    arcpy.SpatialReference(3436)

    # Create temporary data
    arcpy.FeatureClassToFeatureClass_conversion(gravity_mains, lateral_lines, "ssGravityMain", "OWNEDBY = 1 And WATERTYPE <> 'SW' And Stage = 0")
    arcpy.MakeFeatureLayer_management(gravity_mains_temp, "ssGravityMain")
    arcpy.FeatureClassToFeatureClass_conversion(pacp_observations, lateral_lines, "Connections", "Code IN ('TB', 'TBA', 'TBB', 'TBD', 'TBI', 'TF', 'TFA', 'TFB', 'TFC', 'TFD', 'TFI', 'TS', 'TSD')")
    arcpy.MakeFeatureLayer_management(pacp_observations_temp, "Connections")

    def AddBearing():

        # Add/remove fields
        arcpy.AddField_management("ssGravityMain", "BEARING", "DOUBLE", field_length=5, field_alias="Bearing")
        arcpy.CalculateGeometryAttributes_management("ssGravityMain", [["BEARING", "LINE_BEARING"]])

    def CreateLines():
        # Place observations along gravity mains based off of length and direction
        arcpy.CreateRoutes_lr("ssGravityMain", "FACILITYID", routes)
        arcpy.MakeFeatureLayer_management(routes, "Routes")
        arcpy.MakeRouteEventLayer_lr("Routes", "FACILITYID", event_table, "AssetName POINT AtDistance", "RouteEvents")
        arcpy.SpatialJoin_analysis("RouteEvents", "ssGravityMain", "Connections", "JOIN_ONE_TO_ONE", "KEEP_ALL")

    def AddFields():
        # Add more fields
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
                                      "PercentageUOM"])

    def BearingCalculation():
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
        selected_connections = arcpy.SelectLayerByAttribute_management("Connections", "NEW_SELECTION", "BEARING IS NOT NULL")
        arcpy.BearingDistanceToLine_management(selected_connections, laterals, "POINT_X", "POINT_Y", "LATDIST", "FEET", "BEARING")

    # Run the above functions with logger error catching and formatting

    logger = start_rotating_logging()

    try:
        logger.info("--- Script Execution Started ---")

        logger.info("--- --- --- --- Add Fields Start")
        AddBearing()
        logger.info("--- --- --- --- Add Fields Complete")

        logger.info("--- --- --- --- Create Lines Start")
        CreateLines()
        logger.info("--- --- --- --- Create Lines Complete")

        logger.info("--- --- --- --- Create Lines Start")
        AddFields()
        logger.info("--- --- --- --- Create Lines Complete")

        logger.info("--- --- --- --- Create Lines Start")
        BearingCalculation()
        logger.info("--- --- --- --- Create Lines Complete")

    except (IOError, KeyError, NameError, IndexError, TypeError, UnboundLocalError):
        tbinfo = traceback.format_exc()
        try:
            logger.error(tbinfo)
        except NameError:
            print(tbinfo)

    except arcpy.ExecuteError:
        try:
            tbinfo = traceback.format_exc(2)
            logger.error(tbinfo)
        except NameError:
            print(arcpy.GetMessages(2))

    except:
        logger.exception("Picked up an exception:")

    finally:
        try:
            logger.info("--- Script Execution Completed ---")
            logging.shutdown()
        except NameError:
            pass


def main():
    LateralLines()


if __name__ == '__main__':
    main()
