########## Differences relative to previous version (circa 10/22/2020) of script ##########

# Updated to better facilitate future changes in what M would be - both the broad types of predictors and # of lag
# terms corresponding to each
# An additional, important user input is # of lag-terms needed for each predictor
# A function calculates response at each time-point- again to facilitate future changes
# Script now reads in 2 files, 1st containing values and 2nd containing binary flags indicating whether data is valid
# Now, TRUE = Good, FALSE = Bad -> Based on change in data cleaning upstream
# Some efficiency updates

import os
import numpy as np
import pandas as pd

########## User inputs ##########

# Paths to read raw data files from and to store outputs in
path_to_raw_data = os.path.join(os.getcwd(), "inputs_to_code")
raw_data_values_file_name = "input_values_for_M_by_N_creating_script.csv"
raw_data_validity_flags_file_name = "input_validity_flags_for_M_by_N_creating_script.csv"
path_to_store_outputs_at = os.path.join(os.getcwd(), "outputs_from_code")
trainval_inputs_data_file_name = "trainval_inputs.pkl"
trainval_output_data_file_name = "trainval_output.pkl"
datetimes_for_trainval_data_file_name = "trainval_datetimes.pkl"

# Constants
# Entries in the following array MUST EXACTLY correspond to the columns in the raw_data_values/validity flag files
# Ignore datetime column, which becomes the index of the dataframe
# +1->Forecast time, 0->Present time, -1->1 time step in past, -2->2 time steps in past... you get the idea.
# start = -2, end = -1 implies only include values from 2 past time steps.
lag_term_start_predictors = np.array([-2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2])
lag_term_end_predictors = np.array([1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
# Those associated with calculating calendar terms - currently solar hour angle and day angle
longitude = -119.4179  # Roughly passing through the center of CA
time_difference_from_UTC = -8  # hours. Timestamps for input data are in PST
# TODO: Consider having option to disallow overlaps between subsequent training samples
# One of the calendar terms is supposed to be # of days since the first date in our training set
# This will account for increasing nameplate, improving forecast accuracy and other phenomena
# that take place over time.
# TODO: Currently, start_date = first date in training set. Consider setting it to a static date if need be later"

# Labels to help identify what entry is what in the output files to be generated by this script
# Labels for all predictors (Inputs to ML model). Order must respect order of predictor types, i.e raw data values
# columns and the number of lag and leading terms for each predictor as defined above
labels_for_predictors = ["RTPD_Load_Forecast_T-2", "RTPD_Load_Forecast_T-1", "RTPD_Load_Forecast_T0", "RTPD_Load_Forecast_T+1",
                         "RTPD_Solar_Forecast_T-2", "RTPD_Solar_Forecast_T-1", "RTPD_Solar_Forecast_T0", "RTPD_Solar_Forecast_T+1",
                         "RTPD_Wind_Forecast_T-2", "RTPD_Wind_Forecast_T-1", "RTPD_Wind_Forecast_T0", "RTPD_Wind_Forecast_T+1",
                         "RTD_1_Load_Forecast_T-2", "RTD_1_Load_Forecast_T-1",
                         "RTD_1_Solar_Forecast_T-2", "RTD_1_Solar_Forecast_T-1",
                         "RTD_1_Wind_Forecast_T-2", "RTD_1_Wind_Forecast_T-1",
                         "RTD_2_Load_Forecast_T-2", "RTD_2_Load_Forecast_T-1",
                         "RTD_2_Solar_Forecast_T-2", "RTD_2_Solar_Forecast_T-1",
                         "RTD_2_Wind_Forecast_T-2", "RTD_2_Wind_Forecast_T-1",
                         "RTD_3_Load_Forecast_T-2", "RTD_3_Load_Forecast_T-1",
                         "RTD_3_Solar_Forecast_T-2", "RTD_3_Solar_Forecast_T-1",
                         "RTD_3_Wind_Forecast_T-2", "RTD_3_Wind_Forecast_T-1",
                         "Solar_Hour_Angle_T+1", "Solar_Day_Angle_T+1", "Num_Days_from_Start_Date_T+1"]
# Labels for response (output model is trained to predict)
labels_for_response = ["Net_Load_Forecast_Error_T+1"]
# Labels for datetimes for a trainval sample. Must span across all predictor lag term predictors and response lead term
# These are neither predictors nor response.
# Just used to split dataset into cross-val folds in a separate script downstream
labels_for_datetimes = ["T-2", "T-1", "T0", "T+1"]

# User needs to define what the response variable is
def calculate_response_variable(raw_data_values_df):
    """
    Calculates and stores response variable that the ML model will be trained to predict
    :param raw_data_values_df:
    :return: response_values_df - carrying the same data format as raw_data_values_df but
    with the response variable calculated
    """
    # Initialize dfs to hold response variable value and validity
    response_values_df = pd.DataFrame(index = raw_data_values_df.index)
    response_validity_flags_df = pd.DataFrame(index = raw_data_values_df.index)

    # Fill it in per user provided definition of the response variable
    # NOTE: When a response is calculated using a predictor that was pd.NA, you want the response
    # to be pd.NA as well. Thus, be careful with using functions like pd.sum() which yield sum
    # of NAs to be = 0 for example.
    net_load_rtpd_forecast = raw_data_values_df["Load_RTPD_Forecast"].values - \
                             raw_data_values_df["Solar_RTPD_Forecast"].values - \
                             raw_data_values_df["Wind_RTPD_Forecast"].values
    net_load_rtd_1_forecast = raw_data_values_df["Load_RTD_1_Forecast"].values - \
                             raw_data_values_df["Solar_RTD_1_Forecast"].values - \
                             raw_data_values_df["Wind_RTD_1_Forecast"].values
    net_load_rtd_2_forecast = raw_data_values_df["Load_RTD_2_Forecast"].values - \
                              raw_data_values_df["Solar_RTD_2_Forecast"].values - \
                              raw_data_values_df["Wind_RTD_2_Forecast"].values
    net_load_rtd_3_forecast = raw_data_values_df["Load_RTD_3_Forecast"].values - \
                              raw_data_values_df["Solar_RTD_3_Forecast"].values - \
                              raw_data_values_df["Wind_RTD_3_Forecast"].values

    response_values_df[response_col_name] = net_load_rtpd_forecast - (net_load_rtd_1_forecast + net_load_rtd_2_forecast + \
                                                                      net_load_rtd_3_forecast) / 3.0

    return response_values_df

########## Constants for use in script that DON'T need to be user defined ##########

# 3 calendar terms are currently used, each at time of forecast, i.e T+1
lag_term_start_predictors = np.append(lag_term_start_predictors, np.array([1, 1, 1]))
lag_term_end_predictors = np.append(lag_term_end_predictors, np.array([1, 1, 1]))
num_predictors = (lag_term_end_predictors - lag_term_start_predictors + 1).sum()
hour_angle_col_name = "Hour_Angle"
day_angle_col_name = "Day_Angle"
days_from_start_date_col_name = "Days_from_Start_Date"

# Inputs associated with response variable
response_col_name = "Net_Load_Forecast_Error"
lead_term_response = 1 # As a gentle reminder, its relative to present time, T0. So, 1 implies T0+1

# Inputs associated with datetime index
max_num_lag_terms = 0
if(lag_term_start_predictors.min() < 0):
    max_num_lag_terms = lag_term_start_predictors.min() * (-1)
else:
    max_num_lag_terms = 0
lag_term_datetime_start = lag_term_start_predictors.min()
lag_term_datetime_end = lead_term_response
num_datetimes_per_trainval_sample = lag_term_datetime_end - lag_term_datetime_start + 1

########## Helper functions that don't need user intervention ##########

def calculate_calendar_based_predictors(datetime_arr, longitude, time_difference_from_UTC, start_date=None):
    """
    Calculated calendar-based inputs at each time point in the trainval set for ML model. Currently includes solar hour,
    day angle and # of days passed since a start-date which can either be a user input or the first day in the trainval
    dataset.

    Inputs:
    datetime_arr(pd.DatetimeIndex)
    longitude(float): Longitude to be used to calculate local solar time in degrees. East->postive, West->Negative
    time_difference_from_from_UTC(int/float): Time-difference (in hours) between local time and
    Universal Coordinated TIme (UTC)
    start_date(DateTime) = Unless user-specified, is set to first entry in datetime_arr

    Output:
    solar_hour_angle_arr (Array of floats): Hour angle in degrees for each timepoint in datetime_arr
    solar_day_angle_arr (Array of floats): Day angle in degrees for each timepoint in datetime_arr
    days_from_start_date_arr (Array of ints): Days passed since a particular start date, defined for each timepoint in datetime_arr

    Reference for formulae:https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time
    """
    # Steps leading up to calculation of local solar time
    day_of_year_arr = datetime_arr.dayofyear
    # Equation of time (EoT) corrects for eccentricity of earth's orbit and axial tilt
    solar_day_angle_arr = (360 / 365) * (day_of_year_arr - 81)  # degrees
    solar_day_angle_in_radians_arr = np.deg2rad(solar_day_angle_arr)  # radians
    EoT_arr = 9.87 * np.sin(2 * solar_day_angle_in_radians_arr) - 7.53 * np.cos(
        solar_day_angle_in_radians_arr) - 1.5 * np.sin(solar_day_angle_in_radians_arr)  # minutes
    # Time correction sums up time difference due to EoT and longitudinal difference between local time
    # zone and local longitude
    local_std_time_meridian = 15 * time_difference_from_UTC  # degrees
    time_correction_arr = 4 * (longitude - local_std_time_meridian) + EoT_arr  # minutes
    # Calculate local solar time using local time and time correction calculated above
    local_solar_time_arr = datetime_arr.hour + (datetime_arr.minute / 60) + (time_correction_arr / 60)  # hours
    # Calculate solar hour angle corresponding to the local solar time
    solar_hour_angle_arr = 15 * (local_solar_time_arr - 12)  # degrees

    # Calculate days passed since start date
    if start_date == None:
        start_date = datetime_arr[0]
    days_from_start_date_arr = (datetime_arr - start_date).days

    return solar_hour_angle_arr, solar_day_angle_arr, days_from_start_date_arr


########## Reading in raw data, doing any modifications/edits before creating trainval samples ##########

# Read in raw data to be used to create predictors and response variables
raw_data_values_df = pd.read_csv(os.path.join(path_to_raw_data, raw_data_values_file_name), index_col = 0)
raw_data_validity_flags_df = pd.read_csv(os.path.join(path_to_raw_data, raw_data_validity_flags_file_name), index_col = 0)
# Embed info about validity into df holding values so we can use the latter alone going forward
raw_data_values_df = raw_data_values_df.where(cond = raw_data_validity_flags_df, other = pd.NA)
num_time_points = raw_data_values_df.shape[0]

# Add calendar terms to predictors
print("Calculating calendar-based predictors....")
all_datetimes = pd.to_datetime(raw_data_values_df.index.values)
raw_data_values_df[hour_angle_col_name], raw_data_values_df[day_angle_col_name], raw_data_values_df[days_from_start_date_col_name] = \
    calculate_calendar_based_predictors(all_datetimes, longitude, time_difference_from_UTC)
print("Done")

# Calculate response variable
print("Calculating response....")
response_values_df = calculate_response_variable(raw_data_values_df)
print("Done")

# Initialize collectors to hold (and later save) trainval data in
trainval_inputs_data_df = pd.DataFrame(index = labels_for_predictors, columns = np.arange(max_num_lag_terms, num_time_points - lead_term_response),
                                        data = pd.NA)
trainval_output_data_df = pd.DataFrame(index = labels_for_response, columns = np.arange(max_num_lag_terms, num_time_points - lead_term_response),
                                        data = pd.NA)
# Datetimes are just stored for reference. Not part of the trainval inputs/outputs - atleast not at the moment
datetimes_for_trainval_data_df = pd.DataFrame(index = labels_for_datetimes, columns = np.arange(max_num_lag_terms, num_time_points - lead_term_response),
                                        data = pd.NA)

########## Creating and saving valid trainval samples ##########

print("Have begun creating trainval samples for all time-points ....")
# First collect predictors for all trainval samples
start_idx = 0
# Iterate over each predictor type
for value_type_idx, value_type in enumerate(raw_data_values_df.columns):
    lag_term_start = lag_term_start_predictors[value_type_idx]
    lag_term_end = lag_term_end_predictors[value_type_idx]
    num_time_steps_per_trainval_sample = lag_term_end - lag_term_start + 1
    # Iterate over each time step for current predictor type
    for time_step_idx, time_step in enumerate(range(lag_term_start, lag_term_end + 1)):
        trainval_inputs_data_df.iloc[start_idx + time_step_idx, :] = raw_data_values_df.iloc[max_num_lag_terms + time_step:num_time_points - lead_term_response + time_step, value_type_idx].values
    start_idx += num_time_steps_per_trainval_sample

# Next collect response for all trainval samples
trainval_output_data_df.iloc[0, :] = response_values_df.iloc[max_num_lag_terms + lead_term_response:num_time_points, 0].values

# Finally, collect datetimes corresponding to each trainval sample
# Iterate over each time-step involved in a trainval sample
for time_step_idx, time_step in enumerate(range(lag_term_datetime_start, lag_term_datetime_end + 1)):
    datetimes_for_trainval_data_df.iloc[time_step_idx, :] = raw_data_values_df.index[max_num_lag_terms + time_step:num_time_points - lead_term_response + time_step].values


# Delete trainval samples with invalid data
print("Identifying trainval samples with invalid data....")
# Identify trainval samples wherein predictor(s) and response are both valid
# If any entry is pd.NA, it is invalid
predictors_are_valid = (trainval_inputs_data_df.notnull()).all(axis = 0)
response_is_valid = (trainval_output_data_df.notnull()).all(axis = 0)
predictors_and_response_are_valid = predictors_are_valid & response_is_valid
print("{} of {} trainval samples are valid. Proceeding to delete the rest....".format(predictors_and_response_are_valid.sum(),
                                                                                    predictors_and_response_are_valid.size))

# Only retain trainval samples wherein  predictor(s) and response are both valid
trainval_inputs_data_df = trainval_inputs_data_df.loc[:, predictors_and_response_are_valid]
trainval_output_data_df = trainval_output_data_df.loc[:, predictors_and_response_are_valid]
datetimes_for_trainval_data_df = datetimes_for_trainval_data_df.loc[:, predictors_and_response_are_valid]
print("Done")

# Save trainval samples
print("Saving files......")
trainval_inputs_data_df.to_pickle(os.path.join(path_to_store_outputs_at, trainval_inputs_data_file_name))
trainval_output_data_df.to_pickle(os.path.join(path_to_store_outputs_at, trainval_output_data_file_name))
datetimes_for_trainval_data_df.to_pickle(os.path.join(path_to_store_outputs_at, datetimes_for_trainval_data_file_name))
print("All done!")






