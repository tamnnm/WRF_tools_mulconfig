#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 21:28:01 2025

@author: doan
"""

import os
from datetime import datetime, timedelta
import math
import cdsapi

class ERA5DataDownloader:
    def __init__(self, run_period, domain_center, domain, download_dir):
        self.run_period = run_period
        self.domain_center = domain_center
        self.domain = domain
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self.client = cdsapi.Client()

    def get_rectangle_bounds(self):
        """Calculate the latitude and longitude bounds of a rectangle centered at the domain center."""
        KM_PER_DEGREE_LAT = 111.0
        KM_PER_DEGREE_LON = 111.0 * math.cos(math.radians(self.domain_center['lat']))

        width_km = self.domain['dx'] * self.domain['e_we_ini'][0] / 1000 * 2
        half_width_lat = (width_km / 2) / KM_PER_DEGREE_LAT
        half_width_lon = (width_km / 2) / KM_PER_DEGREE_LON

        return {
            "north": round(self.domain_center['lat'] + half_width_lat, 2),
            "south": round(self.domain_center['lat'] - half_width_lat, 2),
            "east": round(self.domain_center['lon'] + half_width_lon, 2),
            "west": round(self.domain_center['lon'] - half_width_lon, 2)
        }


    def generate_date_range(self):
        """Generate a list of dates between start_date and end_date in YYYY-MM-DD format."""
        start_date = datetime.strptime(self.run_period['start_date'], '%Y-%m-%d %H')
        end_date = datetime.strptime(self.run_period['end_date'], '%Y-%m-%d %H')

        if end_date.hour > 0:
            end_date += timedelta(days=1)

        return [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') 
                for i in range((end_date - start_date).days + 1)]

    def download_pressure_level_data(self, date, area):
        """Download ERA5 pressure-level data for a specific date."""
        year, month, day = date.split('-')
        pressure_file = os.path.join(self.download_dir, f'era5_ungrib_pressure_levels_{year}{month}{day}.grib')
        
        self.client.retrieve(
            'reanalysis-era5-pressure-levels',
            {
                'product_type': 'reanalysis',
                'format': 'grib',
                'variable': [
                    'geopotential', 'relative_humidity', 'temperature',
                    'u_component_of_wind', 'v_component_of_wind'
                ],
                'pressure_level': [
                    '1', '2', '3', '5', '7', '10', '20', '30', '50', '70', '100', '125',
                    '150', '175', '200', '225', '250', '300', '350', '400', '450', '500',
                    '550', '600', '650', '700', '750', '775', '800', '825', '850', '875',
                    '900', '925', '950', '975', '1000'
                ],
                'year': year,
                'month': month,
                'day': day,
                'time': ['00:00', '06:00', '12:00', '18:00'],
                'area': area,
            },
            pressure_file
        )

    def download_surface_level_data(self, date, area):
        """Download ERA5 surface-level data for a specific date."""
        year, month, day = date.split('-')
        surface_file = os.path.join(self.download_dir, f'era5_ungrib_surface_levels_{year}{month}{day}.grib')

        self.client.retrieve(
            'reanalysis-era5-single-levels',
            {
                'product_type': 'reanalysis',
                'format': 'grib',
                'variable': [
                    '10m_u_component_of_wind', '10m_v_component_of_wind', '2m_dewpoint_temperature',
                    '2m_temperature', 'land_sea_mask', 'mean_sea_level_pressure', 'sea_ice_cover',
                    'sea_surface_temperature', 'skin_temperature', 'snow_depth',
                    'soil_temperature_level_1', 'soil_temperature_level_2', 'soil_temperature_level_3',
                    'soil_temperature_level_4', 'surface_pressure',
                    'volumetric_soil_water_layer_1', 'volumetric_soil_water_layer_2',
                    'volumetric_soil_water_layer_3', 'volumetric_soil_water_layer_4'
                ],
                'year': year,
                'month': month,
                'day': day,
                'time': ['00:00', '06:00', '12:00', '18:00'],
                'area': area,
            },
            surface_file
        )

    def download_data(self):
        """Main method to download ERA5 pressure-level and surface-level data."""
        bounds = self.get_rectangle_bounds()
        area = [ bounds['north'], bounds['west'], bounds['south'], bounds['east']]
        
        print(f"Downloading data for area: {area}")
        
        for date in self.generate_date_range():
            print(f"Downloading data for {date}...")
            self.download_pressure_level_data(date, area)
            self.download_surface_level_data(date, area)
            print(f"Completed data download for {date}.")


if __name__ == "__main__":
    run_period = {
        'start_date': "2024-01-01 00",
        'end_date': "2024-01-02 12"
    }

    domain_center = {
        'id': 'Mogadishu',
        'lat': 2.05,
        'lon': 45.32
    }

    domain = {
        'dx': 6000,
        'e_we_ini': (50, 50, 50)
    }

    download_dir = f"/Volumes/work/WRF_program/era5/{domain_center['id']}/"
    downloader = ERA5DataDownloader(run_period, domain_center, domain, download_dir)
    downloader.download_data()
