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
from lxml import html

nhcBaseURL = 'https://www.nhc.noaa.gov'
addDisclaimerText = True
cleanUpFiles = True
generateAtlantic = True
generateCentralPacific = True
generateEasternPacific = True


# Atlantic which_td = 2
# Eastern Pacific which_td = 3
# Central Pacific which_td = 4
def scrape_page(which_td):
    page = requests.get('https://www.nhc.noaa.gov/gis/')
    content = page.content.decode('UTF-8')
    tree = html.fromstring(content)
    kmz_files = []
    links = tree.xpath("/html/body/div[5]/div/table[1]/tr[3]/td[{}]/a".format(which_td))
    for link in links:
        if re.match(r'.*/\w+_CONE_latest.kmz', link.attrib['href']):
            kmz_files.append(link.attrib['href'])
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


def bound_x_to_image(image_width, x_coord):
    if x_coord < 0:
        return 0
    elif x_coord > (image_width - 1):
        return image_width - 1
    return x_coord


def get_image_latitude_y_pixel_with_list(latitude_list, decimal_latitude):
    if decimal_latitude <= latitude_list[0][1]:
        return latitude_list[0][0]
    if decimal_latitude >= latitude_list[-1][1]:
        return latitude_list[-1][0]
    for pair in latitude_list:
        if pair[1] < decimal_latitude:
            prev_pair = pair
        elif pair[1] > decimal_latitude:
            lower_lat_bound = prev_pair[0]
            upper_lat_bound = pair[0]
            delta = (pair[1] - decimal_latitude) / 5.0
            pixel_delta = (lower_lat_bound - upper_lat_bound)
            ret_val = int(upper_lat_bound + (pixel_delta * delta))
            # Bound to map
            if ret_val < latitude_list[-1][0]:
                return latitude_list[-1][0]
            elif ret_val > latitude_list[0][0]:
                return latitude_list[0][0]
            return ret_val
        else:
            return pair[0]


def get_image_longitude_x_pixel_with_list(longitude_list, decimal_longitude):
    if decimal_longitude >= longitude_list[0][1]:
        return longitude_list[0][0]
    if decimal_longitude <= longitude_list[-1][1]:
        return longitude_list[-1][0]
    for pair in longitude_list:
        if pair[1] > decimal_longitude:
            prev_pair = pair
        elif pair[1] < decimal_longitude:
            lower_long_bound = prev_pair[0]
            upper_long_bound = pair[0]
            delta = (decimal_longitude - pair[1]) / 5.0
            pixel_delta = (lower_long_bound - upper_long_bound)
            ret_val = int(upper_long_bound + (pixel_delta * delta))
            # Bound to map
            if ret_val < longitude_list[-1][0]:
                return longitude_list[-1][0]
            elif ret_val > longitude_list[0][0]:
                return longitude_list[0][0]
            return ret_val
        else:
            return pair[0]


# Maps the X coordinate on the image to an associated longitude
atl_longitude_points = []
atl_longitude_points.append((899, -10))  # Eastern limit
atl_longitude_points.append((852, -15))
atl_longitude_points.append((805, -20))
atl_longitude_points.append((757, -25))
atl_longitude_points.append((710, -30))
atl_longitude_points.append((662, -35))
atl_longitude_points.append((615, -40))
atl_longitude_points.append((568, -45))
atl_longitude_points.append((520, -50))
atl_longitude_points.append((473, -55))
atl_longitude_points.append((426, -60))
atl_longitude_points.append((378, -65))
atl_longitude_points.append((331, -70))
atl_longitude_points.append((284, -75))
atl_longitude_points.append((236, -80))
atl_longitude_points.append((189, -85))
atl_longitude_points.append((141, -90))
atl_longitude_points.append((94, -95))
atl_longitude_points.append((47, -100))
atl_longitude_points.append((0, -105))  # Western limit

# Maps the Y coordinate on the image to an associated latitude
atl_latitude_points = []
atl_latitude_points.append((595, 0))  # lower limit
atl_latitude_points.append((558, 5))
atl_latitude_points.append((511, 10))
atl_latitude_points.append((462, 15))
atl_latitude_points.append((413, 20))
atl_latitude_points.append((362, 25))
atl_latitude_points.append((309, 30))
atl_latitude_points.append((254, 35))
atl_latitude_points.append((194, 40))
atl_latitude_points.append((131, 45))
atl_latitude_points.append((64, 50))  # upper limit


def get_atl_image_latitude_y_pixel(decimal_latitude):
    return get_image_latitude_y_pixel_with_list(atl_latitude_points, decimal_latitude)


def get_atl_image_longitude_x_pixel(decimal_longitude):
    return get_image_longitude_x_pixel_with_list(atl_longitude_points, decimal_longitude)


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
                x_coord = bound_x_to_image(width, get_atl_image_longitude_x_pixel(float(split[0])))
                y_coord = get_atl_image_latitude_y_pixel(float(split[1]))
                # print("latitude ", split[1], " gave y_coord: ", y_coord)
                image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        # testing coordinate generation
        # for longitude in range(0, 45):
        #     longitude = -105 + (longitude * 2.5)
        #     x_coord = bound_x_to_image(width, get_atl_image_longitude_x_pixel(longitude))
        #     print("longitude: ", longitude, " x_coord: ", x_coord)
        #     for latitude in range(0, 25):
        #         latitude = latitude * 2.5
        #         y_coord = get_atl_image_latitude_y_pixel(latitude)
        #         # print("latitude ", latitude, " gave y_coord: ", y_coord)
        #         image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        image.save('atl_latest.png')


# Maps the X coordinate on the image to an associated longitude
east_pac_longitude_points = []
east_pac_longitude_points.append((899, -75))  # Eastern limit
east_pac_longitude_points.append((835, -80))
east_pac_longitude_points.append((771, -85))
east_pac_longitude_points.append((706, -90))
east_pac_longitude_points.append((642, -95))
east_pac_longitude_points.append((578, -100))
east_pac_longitude_points.append((514, -105))
east_pac_longitude_points.append((449, -110))
east_pac_longitude_points.append((385, -115))
east_pac_longitude_points.append((321, -120))
east_pac_longitude_points.append((256, -125))
east_pac_longitude_points.append((192, -130))
east_pac_longitude_points.append((128, -135))
east_pac_longitude_points.append((64, -140))
east_pac_longitude_points.append((0, -145))  # Western limit

# Maps the Y coordinate on the image to an associated latitude
east_pac_latitude_points = []
east_pac_latitude_points.append((595, 0))  # lower limit
east_pac_latitude_points.append((533, 5))
east_pac_latitude_points.append((468, 10))
east_pac_latitude_points.append((403, 15))
east_pac_latitude_points.append((335, 20))
east_pac_latitude_points.append((266, 25))
east_pac_latitude_points.append((194, 30))
east_pac_latitude_points.append((118, 35))
east_pac_latitude_points.append((64, 40))  # upper limit


def get_east_pac_image_latitude_y_pixel(decimal_latitude):
    return get_image_latitude_y_pixel_with_list(east_pac_latitude_points, decimal_latitude)


def get_east_pac_image_longitude_x_pixel(decimal_longitude):
    return get_image_longitude_x_pixel_with_list(east_pac_longitude_points, decimal_longitude)


def do_mod_east_pac_image():
    with Image.open('two_pac_5d0.png').convert('RGB') as image:
        width, height = image.size
        if addDisclaimerText:
            font = ImageFont.truetype('Pillow/Tests/fonts/FreeMono.ttf', 15)
            draw = ImageDraw.Draw(image)
            draw.text((60, 40), "!!UNOFFICIAL IMAGE!!", (0, 0, 0), font=font)
            draw.text((15, 500), "!!UNOFFICIAL IMAGE!!", (255, 255, 255), font=font)
            draw.text((15, 100), "!!UNOFFICIAL IMAGE!!", (255, 255, 255), font=font)
            draw.text((700, 540), "!!UNOFFICIAL IMAGE!!", (255, 255, 255), font=font)
            draw.text((660, 40), "!!UNOFFICIAL IMAGE!!", (0, 0, 0), font=font)
        for file in glob.glob("*.kml"):
            print("Handling file: ", file)
            tree = ET.parse(file)
            root = tree.getroot()
            coords = root[0][3][1][0][0][0].text.strip().split()
            for coord in coords:
                split = coord.split(',')
                x_coord = bound_x_to_image(width, get_east_pac_image_longitude_x_pixel(float(split[0])))
                y_coord = get_east_pac_image_latitude_y_pixel(float(split[1]))
                # print("latitude ", split[1], " gave y_coord: ", y_coord)
                image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        # testing coordinate generation
        # for longitude in range(0, 45):
        #     longitude = -145 + (longitude * 2.5)
        #
        #     x_coord = bound_x_to_image(width, get_east_pac_image_longitude_x_pixel(longitude))
        #     print("longitude: ", longitude, " x_coord: ", x_coord)
        #     for latitude in range(0, 20):
        #         latitude = latitude * 2.5
        #         y_coord = get_east_pac_image_latitude_y_pixel(latitude)
        #         # print("latitude ", latitude, " gave y_coord: ", y_coord)
        #         image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        image.save('epac_latest.png')


# Maps the X coordinate on the image to an associated longitude
# From -180 to -120
cpac_longitude_points_negative = []
cpac_longitude_points_negative.append((899, -120))  # Eastern limit
cpac_longitude_points_negative.append((839, -125))
cpac_longitude_points_negative.append((774, -130))
cpac_longitude_points_negative.append((709, -135))
cpac_longitude_points_negative.append((644, -140))
cpac_longitude_points_negative.append((579, -145))
cpac_longitude_points_negative.append((514, -150))
cpac_longitude_points_negative.append((449, -155))
cpac_longitude_points_negative.append((384, -160))
cpac_longitude_points_negative.append((319, -165))
cpac_longitude_points_negative.append((255, -170))
cpac_longitude_points_negative.append((190, -175))
cpac_longitude_points_negative.append((125, -180))  # Western limit

# From +170 to +180
cpac_longitude_points_positive = []
cpac_longitude_points_positive.append((125, 180))  # Eastern limit
cpac_longitude_points_positive.append((60, 175))
cpac_longitude_points_positive.append((0, 170))  # Western limit


# Maps the Y coordinate on the image to an associated latitude
cpac_latitude_points = []
cpac_latitude_points.append((587, 0))  # lower limit
cpac_latitude_points.append((526, 5))
cpac_latitude_points.append((462, 10))
cpac_latitude_points.append((398, 15))
cpac_latitude_points.append((332, 20))
cpac_latitude_points.append((263, 25))
cpac_latitude_points.append((192, 30))
cpac_latitude_points.append((117, 35))
cpac_latitude_points.append((64, 40))  # upper limit


def get_cpac_image_latitude_y_pixel(decimal_latitude):
    return get_image_latitude_y_pixel_with_list(cpac_latitude_points, decimal_latitude)


def get_cpac_image_longitude_x_pixel(decimal_longitude):
    if decimal_longitude < 0:
        return get_image_longitude_x_pixel_with_list(cpac_longitude_points_negative, decimal_longitude)
    else:
        return get_image_longitude_x_pixel_with_list(cpac_longitude_points_positive, decimal_longitude)


def do_mod_cpac_image():
    with Image.open('two_cpac_5d0.png').convert('RGB') as image:
        width, height = image.size
        if addDisclaimerText:
            font = ImageFont.truetype('Pillow/Tests/fonts/FreeMono.ttf', 15)
            draw = ImageDraw.Draw(image)
            draw.text((60, 40), "!!UNOFFICIAL IMAGE!!", (0, 0, 0), font=font)
            draw.text((15, 500), "!!UNOFFICIAL IMAGE!!", (255, 255, 255), font=font)
            draw.text((700, 150), "!!UNOFFICIAL IMAGE!!", (255, 255, 255), font=font)
            draw.text((700, 540), "!!UNOFFICIAL IMAGE!!", (255, 255, 255), font=font)
            draw.text((660, 40), "!!UNOFFICIAL IMAGE!!", (0, 0, 0), font=font)
        for file in glob.glob("*.kml"):
            print("Handling file: ", file)
            tree = ET.parse(file)
            root = tree.getroot()
            coords = root[0][3][1][0][0][0].text.strip().split()
            for coord in coords:
                split = coord.split(',')
                x_coord = bound_x_to_image(width, get_cpac_image_longitude_x_pixel(float(split[0])))
                y_coord = get_cpac_image_latitude_y_pixel(float(split[1]))
                # print("latitude ", split[1], " gave y_coord: ", y_coord)
                image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        # testing coordinate generation
        # for longitude in range(0, 45):
        #    longitude = -180 + (longitude * 2.5)
        #    x_coord = bound_x_to_image(width, get_cpac_image_longitude_x_pixel(longitude))
        #    print("longitude: ", longitude, " x_coord: ", x_coord)
        #    for latitude in range(0, 20):
        #        latitude = latitude * 2.5
        #        y_coord = get_cpac_image_latitude_y_pixel(latitude)
        #        # print("latitude ", latitude, " gave y_coord: ", y_coord)
        #        image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        # for longitude in range(0, 4):
        #     longitude = 170 + (longitude * 2.5)
        #     x_coord = bound_x_to_image(width, get_cpac_image_longitude_x_pixel(longitude))
        #     print("longitude: ", longitude, " x_coord: ", x_coord)
        #     for latitude in range(0, 20):
        #        latitude = latitude * 2.5
        #        y_coord = get_cpac_image_latitude_y_pixel(latitude)
        #        # print("latitude ", latitude, " gave y_coord: ", y_coord)
        #        image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        image.save('cpac_latest.png')


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


def main():
    # scrape_page args:
    # Atlantic which_td = 2
    # Eastern Pacific which_td = 3
    # Central Pacific which_td = 4

    if generateAtlantic:
        # Atlantic
        scrape_page(2)
        get_latest_base_image('https://www.nhc.noaa.gov/xgtwo/two_atl_5d0.png')
        do_mod_atl_image()
        # clean up
        if cleanUpFiles:
            for file in glob.glob("*.km*"):
                os.remove(file)
            os.remove("two_atl_5d0.png")

    if generateEasternPacific:
        # Eastern Pacific
        scrape_page(3)
        get_latest_base_image('https://www.nhc.noaa.gov/xgtwo/two_pac_5d0.png')
        do_mod_east_pac_image()
        # clean up
        if cleanUpFiles:
            for file in glob.glob("*.km*"):
                os.remove(file)
            os.remove("two_pac_5d0.png")

    if generateCentralPacific:
        # Central Pacific
        scrape_page(4)
        get_latest_base_image('https://www.nhc.noaa.gov/xgtwo/two_cpac_5d0.png')
        do_mod_cpac_image()
        # clean up
        if cleanUpFiles:
            for file in glob.glob("*.km*"):
                os.remove(file)
            os.remove("two_cpac_5d0.png")


if __name__ == "__main__":
    main()
