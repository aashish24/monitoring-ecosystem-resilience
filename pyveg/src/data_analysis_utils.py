import json
import pandas as pd
import os
from os.path import isfile, join

import geopandas as gpd
from shapely.geometry import Point
import matplotlib
matplotlib.use('PS')
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.cm as cm


def read_json_to_dataframe(filename):
    """
    Read a json file and convert the result to a Geopandas DataFrame.

    Parameters
    ----------
    filename : str
        Full path to input json file.

    Returns
    ----------
    DataFrame
        The saved results in a DataFrame format.
    """
    # check file exists
    if not os.path.exists(filename):
        raise FileNotFoundError

    # json read
    data = None
    with open(filename) as json_file:
        data = json.load(json_file)

    # start with empty output dataframes
    veg_df = pd.DataFrame(columns=['date', 'lat', 'long'])
    weather_df = pd.DataFrame(columns=['date'])

    # dataframe index
    i = 0

    # first loop over collections and put vegetation results into one
    # dataframe
    for collection_name, coll_results in data.items():

        # skip non-vegetation data
        if coll_results['type'] != 'vegetation':
            continue

        # loop over time series
        for time_point in coll_results['time-series-data'].values():

            # check we have data for this time point
            if time_point is None:
                continue

            # for each space point
            for space_point in time_point.values():

                # get coordinates
                date = space_point['date']
                lat = space_point['latitude']
                long = space_point['longitude']

                # find other indices in the dataframe which match the date and coordinates
                match_criteria = (veg_df['date'] == date) & (veg_df['lat'] == lat) & (veg_df['long'] == long)
                matched_indices = veg_df.index[match_criteria].tolist()

                # if there is no matching entry
                if len(matched_indices) == 0:

                    # add a new entry to the dataframe
                    veg_df.loc[i, 'date'] = space_point['date']
                    veg_df.loc[i, 'lat'] = space_point['latitude']
                    veg_df.loc[i, 'long'] = space_point['longitude']
                    veg_df.loc[i, f'{collection_name}_offset50'] = space_point['offset50']

                    # increment dataframe index
                    i += 1

                # if we find a row that matches the date and coordinates
                elif len(matched_indices) == 1:

                    # get the index of the matched row
                    index = matched_indices[0]

                    # add information in a new column
                    veg_df.loc[index, f'{collection_name}_offset50'] = space_point['offset50']

                else:
                    raise RuntimeError('Error when building DataFrame, check input json.')

    # next, loop again and put weather data into another dataframe
    # reset dataframe index
    i = 0

    # loop over collections
    for collection_name, coll_results in data.items():

        # skip vegetation data
        if coll_results['type'] == 'vegetation':
            continue

        # loop over time series
        for date, values in coll_results['time-series-data'].items():

            # check we have data
            if values is None:
                continue

            # check if this we already have a row with this date
            matched_indices = weather_df.index[(weather_df['date'] == date)]

            # if there is no matching entry
            if len(matched_indices) == 0:

                # loop over weather data and add to the same date
                for metric, value in values.items():
                    weather_df.loc[i, 'date'] = date
                    weather_df.loc[i, metric] = value

                i += 1

            # if we find a row that matches the date and coordinates
            elif len(matched_indices) == 1:

                # get the index of the matched row
                index = matched_indices[0]

                # loop over weather data and add to the same date
                for metric, value in values.items():

                    # add information in a new column
                    weather_df.loc[index, metric] = value

            else:
                raise RuntimeError('Error when building DataFrame, check input json.')

    # combine dataframes in a missing value friendly way
    df = pd.merge(veg_df, weather_df, on='date', how='outer')

    # turn lat, long into geopandas
    df['geometry'] = [Point(xy) for xy in zip(df.lat, df.long)]
    crs = {'init': 'epsg:4326'}
    data_geo_pd = gpd.GeoDataFrame(df, crs=crs, geometry=df['geometry'])

    return data_geo_pd




def variable_read_json_to_dataframe(filename):
    """
    Read a json file and convert the result to Geopandas DataFrame(s).

    Parameters
    ----------
    filename : str
        Full path to input json file.

    Returns
    ----------
    dict
        A dict of the saved results in a DataFrame format. Keys are
        names of collections and the values are DataFrame of results
        for that collection.
    """
    # check file exists
    if not os.path.exists(filename):
        raise FileNotFoundError

    # json read
    json_file = open(filename)
    data = json.load(json_file)

    # start with empty output dataframes
    dfs = {}

    # loop over collections and make a DataFrame from the results of each
    for collection_name, coll_results in data.items():

        df = pd.DataFrame()
        rows_list = []

        # loop over time series
        for date, time_point in coll_results['time-series-data'].items():\

            # check we have data for this time point
            if time_point is None  or time_point == {}:
                continue

            # if we are looking at veg data, loop over space points
            if isinstance(list(time_point.values())[0], dict):
                for space_point in time_point.values():
                    print(space_point)
                    rows_list.append(space_point)

            # otherwise, just add the row
            else:
                # the key of each object in the time series is the date, and data
                # for this date should be the values. Here we just add the date
                # as a value to enable us to add the whole row in one go later.
                time_point['date'] = date

                rows_list.append(time_point)

        print(rows_list)
        # make a DataFrame and add it to the dict of DataFrames
        df = pd.DataFrame(rows_list)
        dfs[collection_name] = df

    return dfs


def convert_to_geopandas(df):
    """
    Given a pandas DatFrame with `lat` and `long` columns, convert
    to geopandas DataFrame.

    Parameters
    ----------
    df : DataFrame
        Pandas DatFrame with `lat` and `long` columns.

    Returns
    ----------
    geopandas DataFrame
    """
    df['geometry'] = [Point(xy) for xy in zip(df.lat, df.long)]
    crs = {'init': 'epsg:4326'}
    df = gpd.GeoDataFrame(df, crs=crs, geometry=df['geometry'])


def make_time_series(dfs):
    """
    Given a DataFrame which may contian many rows per time point (corresponding
    to the network centrality values of different sub-locations), collapse this
    into a time series by calculating the mean and std of the different sub-
    locations at each date.

    Parameters
    ----------
    df : DataFrame
        Input DataFrame read by `read_json_to_dataframe`.

    Returns
    ----------
    DataFrame
        The time-series results averaged over sub-locations.
    """

    # loop over collections
    for col_name, df in dfs.items():

        # if vegetation data
        if col_name == 'COPERNICUS/S2' or  'LANDSAT' in col_name:

            # group by date to collapse all network centrality measurements
            groups = df.groupby('date')

            # get summaries
            means = groups.mean()
            stds = groups.std()

            # rename columns
            stds = stds.rename(columns={'offset50': 'offset50_std'})

            # merge
            stds = stds[['offset50_std']]
            df = pd.merge(means, stds, on='date', how='inner')
            dfs[col_name] = df

    return dfs





def create_lat_long_metric_figures(data_df, metric,output_dir):

    """

    From input data-frame with processed network metrics create 2D gird figure for each date available using Geopandas.

    :param data_df -- input dataframe
    :param metric -- variable to plot
    :param output_dir -- directory to save the figures

    :return:
    """

    if set(['date',metric]).issubset(data_df.columns):

        #data_df['abs_metric'] = data_df[metric]*-1

        # get min and max values observed in the data to create a range

        vmin = 0
        vmax = max(data_df[metric])

        # get all dates available

        list_of_dates = np.unique(data_df['date'])

        for date in list_of_dates:

            fig, ax = plt.subplots(1, figsize=(6, 6))


            if (data_df[data_df['date'] == date][metric].isnull().values.any()):
                print('Problem with date ' + date_str + ' nan entries found.')
                continue


            cmap = cm.coolwarm
            data_df[data_df['date'] == date].plot(marker='s', ax=ax, alpha=.5, markersize=100, column=metric, \
                                                          figsize=(10, 10), linewidth=0.8, edgecolor='0.8', cmap=cmap)

            # from datetime type to a string
            date_str = pd.to_datetime(str(date)).strftime('%Y-%m-%d')

            # create a date annotation on the figure
            ax.annotate(date_str, xy=(0.15, 0.08), xycoords='figure fraction',
                        horizontalalignment='left', verticalalignment='top',
                        fontsize=25)

            # Create colorbar as a legend
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
            sm._A = []
            fig.colorbar(sm)

            # create output directory
            if not os.path.exists(output_dir):
               os.makedirs(output_dir)

            metric_output_name = metric.replace("/", "_")

            # this saves the figure as a high-res png in the output path.
            filepath = os.path.join(output_dir, metric_output_name+'_network_2D_grid_' + date_str + '.png')
            fig.savefig(filepath, dpi=200)
            fig.clear()

    else:
        raise RuntimeError("Expected variables not present in input dataframe")


def coarse_dataframe(data_df, side_square):
    """

    Coarse the granularity of a dataframe by grouping lat,long points that are close to each other in a square of L = size_square
    :param data_df:  Input dataframe
    :param side_square: Side of the square
    :return: a coarser dataframe
    """

    # initialise the categories
    data_df['category'] = -1

    category = 0
    for n in range(data_df.shape[0]):

        # only process lat,long point that do not have a category
        if data_df['category'].iloc[n] == -1:

            # find the closest points and sort
            distances = [(i, pt.distance(data_df['geometry'].iloc[n]),data_df['category'].iloc[n]) for i, pt in enumerate(data_df['geometry'])]
            distances.sort(key=lambda x: x[1])

            # only use point that do not have a category assigned
            distances = [i for i in distances if i[2] == -1]

            # find the max distance observed in the given squared
            max_dist = np.max(np.unique([dist[1] for dist in distances])[:2 * side_square])

            # find the indexes of point in the dataframe that are within that max distance
            indexes = [dist[0] for dist in distances if (dist[1] <= max_dist)]


            # assing them all to the same categorty
            data_df.loc[indexes,'category'] = str(category)

            category = category + 1

    # create unique categories per date
    data_df['category'] =  data_df['category'].str.cat(data_df['date'],sep="_")

    data_df = data_df.dissolve(by=['category','date'], aggfunc='mean')

    # re-assing the date because we are losing it
    data_df['date']= [i[1] for i in data_df.index]

    return data_df







if __name__ == "__main__":
    data_df = read_json_to_dataframe('/Users/crangelsmith/PycharmProjects/monitoring-ecosystem-resilience/results_summary')
    data_df['lat'] = data_df['lat'].astype('float64', copy=False)
    data_df['long'] = data_df['long'].astype('float64', copy=False)


    print (data_df.shape)
    data_df = coarse_dataframe(data_df,1)

    print (data_df.columns)
    create_lat_long_metric_figures(data_df, 'LANDSAT/LC08/C01/T1_SR_offset50','/Users/crangelsmith/PycharmProjects/monitoring-ecosystem-resilience/output/')

    from pyveg.src.image_utils import (
    create_gif_from_images
    )

    create_gif_from_images('/Users/crangelsmith/PycharmProjects/monitoring-ecosystem-resilience/output/', 'LANDSAT_LC08_C01_T1_SR_offset50_dates.gif','LANDSAT_LC08_C01_T1_SR_offset50')


