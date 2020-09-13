# NHC Cones
# Author: Protuhj
# License: MIT
# Description:
# Takes the current storm data from the National Hurricane Center (NHC) and plots all of the forecast cones onto the
# 5 day forecast graphics

import glob
import zipfile
from xml.dom import minidom
import re
import urllib.request
import requests
import os.path
from os import path
from urllib.parse import urlparse
from PIL import Image, ImageFont, ImageDraw
import xml.etree.ElementTree as ET

nhcBaseURL = 'https://www.nhc.noaa.gov'
addDisclaimerText = True
cleanUpFiles = True


def scrape_page():
    page = requests.get('https://www.nhc.noaa.gov/gis/')
    content = page.content.decode('UTF-8')
    # content = curContent
    kmz_files = re.findall(r'a href=\'(/storm_graphics/api/\w+_CONE_latest.kmz)', content)
    for file_match in kmz_files:
        full_url = "{}{}".format(nhcBaseURL, file_match.strip())
        url = urlparse(full_url)
        print("file: ", full_url)
        file_name = path.basename(url.path)
        if not (os.path.exists(file_name)):
            urllib.request.urlretrieve(full_url, file_name)
        else:
            print("file ", file_name, " already downloaded")
        kmz_to_kml(file_name)


def get_latest_base_image(image_url):
    url_parsed = urlparse(image_url)
    file_name = path.basename(url_parsed.path)
    if not (os.path.exists(file_name)):
        urllib.request.urlretrieve(image_url, file_name)


# Maps the Y coordinate on the image to an associated latitude
latitude_points = []
latitude_points.append((595, 5))  # lower limit
latitude_points.append((511, 10))
latitude_points.append((462, 15))
latitude_points.append((413, 20))
latitude_points.append((364, 25))
latitude_points.append((309, 30))
latitude_points.append((254, 35))
latitude_points.append((194, 40))
latitude_points.append((131, 45))
latitude_points.append((64, 50))  # upper limit


def get_atl_image_latitude_y_pixel(decimal_latitude):
    for pair in latitude_points:
        if pair[1] < decimal_latitude:
            prev_pair = pair
            continue
        elif pair[1] > decimal_latitude:
            lower_lat_bound = prev_pair[0]
            upper_lat_bound = pair[0]
            delta = (pair[1] - decimal_latitude) / 5.0
            pixel_delta = (lower_lat_bound - upper_lat_bound)
            ret_val = int(upper_lat_bound + (pixel_delta * delta))
            if ret_val < 64:
                return 64
            elif ret_val > 595:
                return 595
            return ret_val


def get_atl_image_longitude_x_pixel(decimal_longitude):
    # for ATL basin image 47 pixels = 5 degrees longitude, and doesn't change
    return int(abs(((-105 - decimal_longitude) / 5) * 47))


def do_mod_atl_image():
    with Image.open('two_atl_5d0.png').convert('RGB') as image:
        if addDisclaimerText:
            font = ImageFont.truetype('Pillow/Tests/fonts/FreeMono.ttf', 15)
            draw = ImageDraw.Draw(image)
            draw.text((700, 100), "!!UNOFFICIAL IMAGE!!", (255, 255, 255), font=font)
            draw.text((700, 540), "!!UNOFFICIAL IMAGE!!", (255, 255, 255), font=font)
            draw.text((15, 500), "!!UNOFFICIAL IMAGE!!", (255, 255, 255), font=font)
            draw.text((80, 40), "!!UNOFFICIAL IMAGE!!", (0, 0, 0), font=font)
            draw.text((660, 40), "!!UNOFFICIAL IMAGE!!", (0, 0, 0), font=font)
        width, height = image.size
        for file in glob.glob("*.kml"):
            print("Handling file: ", file)
            tree = ET.parse(file)
            root = tree.getroot()
            coords = root[0][3][1][0][0][0].text.strip().split()
            for coord in coords:
                split = coord.split(',')
                x_coord = get_atl_image_longitude_x_pixel(float(split[0]))
                y_coord = get_atl_image_latitude_y_pixel(float(split[1]))
                # print("latitude ", split[1], " gave y_coord: ", y_coord)
                image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        image.save('atl_latest.png')

    # clean up
    if cleanUpFiles:
        for file in glob.glob("*.km*"):
            os.remove(file)
        os.remove("two_atl_5d0.png")


# Function:     kmz_to_kml
# Author:
# Dan.Patterson@carleton.ca
#
# References: many
# Purpose: convert kmz to kml base script
def kmz_to_kml(fname):
    """save kmz to kml"""
    zf = zipfile.ZipFile(fname, 'r')
    for fn in zf.namelist():
        if fn.endswith('.kml'):
            content = zf.read(fn)
            xmldoc = minidom.parseString(content)
            out_name = (fname.replace(".kmz", ".kml")).replace("\\", "/")
            out = open(out_name, 'w')
            out.writelines(xmldoc.toxml())
            out.close()
        else:
            print("no kml file")


if __name__ == "__main__":
    scrape_page()
    get_latest_base_image('https://www.nhc.noaa.gov/xgtwo/two_atl_5d0.png')
    do_mod_atl_image()
