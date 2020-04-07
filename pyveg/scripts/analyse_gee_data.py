#!/usr/bin/env python

"""
Scripts to process the output of the GEE images and json files with network centrality measures.

The json outputs are turned into a dataframe and the values of a particular metric a plotted
as a function of time.

Finally a GIF file is produced with all of the network metric images, as well as the original 10km x 10km dowloaded images.
"""

import argparse
import os

from pyveg.src.data_analysis_utils import (
    variable_read_json_to_dataframe,
    drop_veg_outliers,
    smooth_veg_data,
    make_time_series,
    create_lat_long_metric_figures,
    convert_to_geopandas,
    coarse_dataframe,
    write_slimmed_csv,
    get_AR1_parameter_estimate
)

from pyveg.src.plotting import (
    plot_time_series, 
    plot_smoothed_time_series, 
    plot_autocorrelation_function,
    plot_feature_vectors
)

from pyveg.src.image_utils import (
    create_gif_from_images
)


def main():
    """
    CLI interface for gee data analysis.
    """
    parser = argparse.ArgumentParser(description="process json files with network centrality measures from from GEE images")
    parser.add_argument("--input_dir",help="results directory from `download_gee_data` script, containing `results_summary.json`")
    parser.add_argument('--spatial_plot', action='store_true')
    parser.add_argument('--time_series_plot', action='store_true', default=True)
    
    print('-'*35)
    print('Running analyse_gee_data.py')
    print('-'*35)

    # parse args
    args = parser.parse_args()
    input_dir = args.input_dir

    # put output plots in the results dir
    output_dir = os.path.join(input_dir, 'analysis')

    # check input file exists
    json_summary_path = os.path.join(input_dir, 'results_summary.json')
    if not os.path.exists(json_summary_path):
        raise FileNotFoundError(f'Could not find file "{os.path.abspath(json_summary_path)}".')

    # make output subdir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # read all json files in the directory and produce a dataframe
    print(f"Reading results from '{os.path.abspath(json_summary_path)}'...")
    dfs = variable_read_json_to_dataframe(json_summary_path)


    # spatial analysis and plotting 
    # ------------------------------------------------
    if args.spatial_plot:

        # from the dataframe, produce network metric figure for each avalaible date
        print('\nCreating spatial plots...')

        # create new subdir for time series analysis
        spatial_subdir = os.path.join(output_dir, 'spatial')
        if not os.path.exists(spatial_subdir):
            os.makedirs(spatial_subdir, exist_ok=True)

        for collection_name, df in dfs.items():
            if collection_name == 'COPERNICUS/S2' or 'LANDSAT' in collection_name:
                data_df_geo = convert_to_geopandas(df)
                data_df_geo_coarse = coarse_dataframe(data_df_geo, 2)
                create_lat_long_metric_figures(data_df_geo_coarse, 'offset50', spatial_subdir)
    # ------------------------------------------------

    # time series analysis and plotting 
    # ------------------------------------------------
    if args.time_series_plot:

        # create new subdir for time series analysis
        #tsa_subdir = os.path.join(output_dir, 'time-series') # if we start to have more and more results
        tsa_subdir = output_dir

        if not os.path.exists(tsa_subdir):
            os.makedirs(tsa_subdir, exist_ok=True)

        # convert to time series
        time_series_dfs = make_time_series(dfs.copy())

        # make the old time series plot
        #print('\nPlotting time series...')
        #plot_time_series(time_series_dfs, tsa_subdir)

        # remove outliers from the time series
        dfs = drop_veg_outliers(dfs, sigmas=3) # not convinced this is really helping much

        # plot the feature vectors averaged over all time points and sub images
        plot_feature_vectors(dfs, tsa_subdir)

        # LOESS smoothing on sub-image time series
        smoothed_time_series_dfs = make_time_series(smooth_veg_data(dfs.copy(), n=5)) # increase smoothing with n>5

        # make a smoothed time series plot
        plot_smoothed_time_series(smoothed_time_series_dfs, tsa_subdir)

        # make autocorrelation plots
        plot_autocorrelation_function(smoothed_time_series_dfs, tsa_subdir)

        # write csv for easy external analysis
        write_slimmed_csv(smoothed_time_series_dfs, tsa_subdir)
    # ------------------------------------------------

    print('\nDone!\n')



if __name__ == "__main__":
    main()
