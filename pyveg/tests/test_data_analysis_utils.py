"""
Test the functions in data_analysis_utils.py
"""

from pyveg.src.data_analysis_utils import *



def test_read_json_to_dataframe():
    test_df = read_json_to_dataframe(os.path.join(os.path.dirname(__file__),"..","..","testdata","network_json_data","test-results-summary.json"))

    assert (test_df.shape[0] == 484)
    assert (test_df.shape[1] == 7)


def test_coarse_dataframe():


    test_df = variable_read_json_to_dataframe(os.path.join(os.path.dirname(__file__),"..","..","testdata","network_json_data/test-results-summary.json"))

    data_df = convert_to_geopandas(test_df['COPERNICUS/S2'])

    data_df = coarse_dataframe(data_df,11)

    n_blocks = len(np.unique([i for i in data_df['category']])) / len(np.unique(data_df['date']))

    assert (n_blocks==4)




def test_create_lat_long_metric_figures():

    dir_path = os.path.join(os.path.dirname(__file__),"..","..","testdata","network_json_data/")

    test_df = variable_read_json_to_dataframe(os.path.join(os.path.dirname(__file__),"..","..","testdata","network_json_data/test-results-summary.json"))

    data_df = convert_to_geopandas(test_df['COPERNICUS/S2'])

    create_lat_long_metric_figures(data_df, 'offset50', dir_path)

    list_png_files = [f for f in os.listdir(dir_path) if (isfile(join(dir_path, f)) and f.endswith(".png"))]
    len_dates = len(np.unique(data_df['date']))

    assert (len(list_png_files)==len_dates)



def test_variable_read_json_to_dataframe():

    test_df_dict = variable_read_json_to_dataframe(os.path.join(os.path.dirname(__file__),"..","..","testdata","network_json_data/test-results-summary.json"))

    dict_len = len(test_df_dict.keys())

    test_df = test_df_dict['COPERNICUS/S2']

    assert (test_df.shape[0] == 484)
    assert (test_df.shape[1] == 8)
    assert (dict_len == 2)