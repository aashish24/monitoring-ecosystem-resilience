---
title: 'pyveg: A Python package for analysing the time evolution of patterned vegetation using Google Earth Engine'
tags:
  - Python
  - Ecology
  - Remote sensing
  - Time Series Analysis
  - Early warnings 
authors:
  - name: Nick Barlow
    affiliation: 1
  - name: Camila Rangel Smith
    affiliation: 1
  - name: Samuel Van Stroud
    affiliation: 1, 2
affiliations:
 - name: The Alan Turing Institute
   index: 1
 - name: University College London
   index: 2
date: 01 June 2020
bibliography: paper.bib
---

# Introduction

Periodic vegetation patterns (PVP) arise from the interplay between 
forces that drive the growth and mortality of plants. Inter-plant 
competetion for resources, in particular water, can lead to the 
formation of PVP. Arid and semi-arid ecosystems may be under threat 
due to changing precipitation dynamics driven by macroscopic changes 
in climate. These regions disiplay some noteable examples of PVP, 
for example the "tiger bush" patterns found in West Africa.

The mophology of the periodic pattern has been suggested to be 
linked to the resiliance of the ecosystem [@Mander:2017; @Trichon:2018]. 
Using remote sensing techniques,  vegetation patterns in these regions 
can be studied, and an analysis of the resiliance of the ecosystem can 
be performed.

The `pyveg` package implements functionality to download and process data
from Google Earth Engine (GEE), and to subsequently perform a 
resiliance analysis on the aquired data. The results can be used
to search for typical early warning signals of an ecological collapse 
[@Dakos:2008]. Google Earth Engine Editor scripts are also provided to help
researchers discover locations of ecosystems which may be in
decline.

`pyveg` is being developed as part of a research project 
looking for evidence of early warning signals of ecosystem
collapse using remote sensing data. `pyveg` allows such 
research to be carried out at scale, and hence can be an 
important tool in understanding changing arid and semi-arid 
ecosystem dynamics.


# Downloading data from Google Earth Engine

In order to interact with the GEE API, the user must sign up to GEE 
and obtain an API key. Upon running `pyveg` for the first time, the 
user will be prompted to enter their API key. The `run_pyveg_pipeline`
command initiates the downloading of time series data at a single
coordinate location. The job is configured using a configuration file 
specified by the `--config_file` argument.

Within the configuration file, the user can specify the following:
coordinates of the download location, start and end dates of the 
time series, frequency with which to sample, choice of GEE collections 
to download from (currently vegetation and precipitation collections are 
supported).

`pyveg` will then form a series of date ranges, and query GEE for the relevant
data in each date range. Colour (RGB) and Normalised Difference vegetation
Index (NDVI) images are downloaded from vegetation collections. Cloud masking 
logic is included to improve data quality. For precipitation and temperature 
information, `pyveg` defaults to using the ERA5 collection.


# Network centrality metrics

After completetion of the download job, `pyveg` computes the network centrality 
of the vegetation [@Mander:2017]. To achieve this, the NDVI image is broken up 
into smaller $50 \times 50$ pixel sub-images. Each sub-image is then thresholded
using the NDVI pixel intensity, and subgraph connectivity is computed for each
binarized sub-image. The resulting metrics are stored, along with mean NDVI pixel 
intensities for each sub-image.


# Time series analysis 

`pyveg` analysis functionality is exposed via a `pveg_gee_analysis` command.
This commands accepts an argument, `input_dir`, which points to a directory 
previously created by a download job. Data in this location is processed and 
analysed. During data processing, which is also configurable, `pyveg` is able 
to drop time series outliers and resample the time series to clean the data 
and avoid gaps. A smoothed time series is constructed using LOESS smoothing, 
and residuals between the raw and smoothed time series are calculated. 
Additionally, a deseasonalised time series is constructed via the first 
difference method.

Time series plots are produced, along with auto- and cross-correlation plots.
Early warning signals are also computed, including Lag-1 autocorrelation
and standard deviation moving window plots. A sensitivity and significance
analysis is also performed, in order to determine whether any declines 
(quantified by Kendall tau values) are statistically significant.


# Acknowledgements

We acknowledge support from Tim Lenton, Chris Boulton, 
and Jessie Abrams during the course of this project.


# References