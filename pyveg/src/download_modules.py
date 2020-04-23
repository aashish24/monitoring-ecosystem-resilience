"""
Classes for modules that download from GEE
"""

import os
import requests
from datetime import datetime, timedelta
import dateparser

from geetools import cloud_mask
import cv2 as cv

import ee
ee.Initialize()

from pyveg.src.date_utils import (
    find_mid_period,
    get_num_n_day_slices,
    slice_time_period_into_n,
    slice_time_period
    )
from pyveg.src.file_utils import download_and_unzip
from pyveg.src.coordinate_utils import get_region_string
from pyveg.src.gee_interface import apply_mask_cloud, add_NDVI

from pyveg.src.pyveg_pipeline import BaseModule

# silence google API WARNING
import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)


class BaseDownloader(BaseModule):
    """
    Most of the code needed to download images from GEE is common to all
    types of data, so we put it in this base class, and have data-type-specific
    code in subclasses.
    """
    def __init__(self, name):
        super().__init__(name)
        # some parameters that are common to all Downloaders
        self.params +=  [("collection_name",str),
                         ("coords", list),
                         ("date_range", list),
                         ("region_size", float),
                         ("scale", int),
                         ("output_dir", str)]
        return


    def set_default_parameters(self):
        """
        Set some basic defaults that should be common to all downloaders
        """

        if not "region_size" in vars(self):
            self.region_size = 0.1
        if not "scale" in vars(self):
            self.scale = 10
        if not "output_dir" in vars(self):
            if self.parent:
                self.output_dir = self.parent.output_dir
            else:
                self.set_output_dir()
        return


    def configure(self, config_dict=None):
        super().configure(config_dict)


    def prep_data(self, date_range):
        """
        Interact with the Google Earth Engine API to get in ImageCollection,
        filter it, and convert (e.g. via median or sum) into a list of Images,
        then get the download URLs for those.

        Parameters
        ----------
        date_range: list of strings 'YYYY-MM-DD'.  Note that this will generally
                    be a sub-range of the overall date-range, as this function
                    is called in the loop over time slices.

        Returns
        -------
        url_list:  a list of URLs from which zipfiles can be downloaded from GEE.
        """
        region  = get_region_string(self.coords, self.region_size)
        start_date, end_date = date_range

        image_coll = ee.ImageCollection(self.collection_name)
        geom = ee.Geometry.Point(self.coords)

        dataset = image_coll.filterBounds(geom).filterDate(start_date,end_date)
        dataset_size = dataset.size().getInfo()

        if dataset_size == 0:
            print('No images found in this date rage, skipping.')
            log_msg = 'WARN >>> No data found.'
            return []
        # concrete class will do more filtering, and prepare Images for download
        image_list = self.prep_images(dataset)
        url_list =[]
        for image in image_list:
            # get a URL from which we can download the resulting data
            try:
                url = image.getDownloadURL(
                    {'region': region,
                     'scale': self.scale}
                )
                url_list.append(url)
            except Exception as e:
                print("Unable to get URL: {}".format(e))

            logging.info(f'OK   >>> Found {dataset.size().getInfo()}/{dataset_size} valid images after cloud filtering.')
        return url_list


    def download_data(self, download_urls, date_range):
        """
        Download zip file(s) from GEE to configured output location.

        Parameters
        ---------
        download_urls: list of strings (URLs) from gee_prep_data
        date_range: list of strings 'YYYY-MM-DD' - note that this will
                    generally be a sub range of the object's overall
                    date_range.
        """
        if len(download_urls) == 0:
            return None, "{}: No URLs found for {} {}".format(self.name,
                                                              self.coords,
                                                              date_range)

        mid_date = find_mid_period(date_range[0], date_range[1])
        download_dir = os.path.join(self.output_dir, mid_date, "RAW")

        # download files and unzip to temporary directory
        for download_url in download_urls:
            download_and_unzip(download_url, download_dir)

        # return the path so downloaded files can be handled by caller
        return download_dir


    def set_output_dir(self, output_dir=None):
        """
        If provided an output directory name, set it here,
        otherwise, construct one from coords and collection name.
        """
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = f'gee_{self.coords[0]}_{self.coords[1]}'\
                +"_"+self.collection_name.replace('/', '-')


    def run(self):
        start_date, end_date = self.date_range
        num_slices = get_num_n_day_slices(start_date,
                                          end_date,
                                          self.num_days_per_point)
        date_ranges = slice_time_period_into_n(start_date,
                                               end_date,
                                               num_slices)
        download_dirs = []
        for date_range in date_ranges:
            urls = self.prep_data(date_range)
            print("{}: got URL {} for date range {}".format(self.name,
                                                            urls,
                                                            date_range))
            download_dir = self.download_data(urls, date_range)
            download_dirs.append(download_dir)
        return download_dirs


##############################################################################
# Below here are specializations of the BaseDownloader class.
# e.g. for downloading vegetation imagery, or weather data.
##############################################################################


class VegetationDownloader(BaseDownloader):
    """
    Specialization of the BaseDownloader class, to deal with
    imagery from Sentinel 2 or Landsat 5-8 satellites, and
    get NDVI band from combining red and near-infra-red.
    """

    def __init__(self, name=None):
        super().__init__(name)
        self.params += [("mask_cloud", bool),
                        ("cloudy_pix_flag", str),
                        ("cloudy_pix_frac", int),
                        ("RGB_bands", list),
                        ("NIR_band", str),
                        ("num_days_per_point", int)
        ]


    def set_default_parameters(self):
        """
        Set some defaults for the chosen satellite
        """
        # set basic things like region_size and scale in the base class
        super().set_default_parameters()
        if "Sentinel2" in self.name:
            self.collection_name = "COPERNICUS/S2"
            self.RGB_bands = ["B4","B3","B2"]
            self.NIR_band = "B8"
            self.mask_cloud = True
            self.cloudy_pix_flag = "CLOUDY_PIXEL_PERCENTAGE"
            self.cloudy_pix_frac = 50
            self.num_days_per_point = 30


    def prep_images(self, dataset):
        """
        Take a dataset that has already been filtered by date and location.
        Then apply specific filters, take the median, and calculate NDVI.

        Parameters
        ----------
        dataset : ee.ImageCollection
            The ImageCollection of images filtered by location and date.

        Returns
        ----------
        image_list : list(ee.Image)
            List of Images to be downloaded
        """
        # Apply cloud mask
        dataset = apply_mask_cloud(dataset,
                                   self.collection_name,
                                   self.cloudy_pix_flag)
        # Take median
        image = dataset.median()
        # Calculate NDVI
        image = add_NDVI(image, self.RGB_bands[0], self.NIR_band)
        # select only RGB + NDVI bands to download
        bands_to_select = self.RGB_bands + ['NDVI']
        image = image.select(bands_to_select)
        return [image]


class WeatherDownloader(BaseDownloader):
    """
    Download precipitation and temperature data.
    """

    def __init__(self,name=None):
        super().__init__(name)
        self.params += [("temperature_band", list),
                        ("precipitation_band", list),
                        ("num_days_per_point", int)
        ]


    def set_default_parameters(self):
        """
        Set some defaults for the chosen satellite
        """
        # set basic things like region_size and scale in the base class
        super().set_default_parameters()
        if "ERA5" in self.name:
            self.collection_name = "ECMWF/ERA5/MONTHLY"
            self.temperature_band = ['mean_2m_air_temperature']
            self.precipitation_band = ['total_precipitation']
            self.num_days_per_point = 30


    def prep_images(self, dataset):
        """
        Take a dataset that has already been filtered by date and location,
        and combine into Images by summing (for precipitation) and taking
        average (for temperature).

        Parameters
        ----------
        dataset : ee.ImageCollection
            The ImageCollection of images filtered by location and date.

        Returns
        ----------
        image_list : list(ee.Image)
            List of Images to be downloaded
        """
        image_list = []
        image_weather = dataset.select(self.precipitation_band).sum()
        image_list.append(image_weather)
        image_temp = dataset.select(self.temperature_band).mean()
        image_list.append(image_temp)

        return image_list
