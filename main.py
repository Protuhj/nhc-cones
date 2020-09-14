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
from PIL import Image, ImageFont, ImageDraw, ImageColor
import xml.etree.ElementTree as ET
from lxml import html
import datetime
import pytz

UNOFFICIAL_STRING = '!!UNOFFICIAL IMAGE!!'
NHC_BASE_URL = 'https://www.nhc.noaa.gov'
DRAW_FONT = ImageFont.truetype('Pillow/Tests/fonts/FreeMono.ttf', 15)
DRAW_WHITE = ImageColor.getrgb('white')
DRAW_BLACK = ImageColor.getrgb('black')
addDisclaimerText = True
cleanUpFiles = True
generateAtlantic = True
generateCentralPacific = True
generateEasternPacific = True
drawEPacOnCPac = True
# Controls whether or not pixels are drawn that are outside of the viewport
# When drawing EPac on CPac, this will happen a lot
drawOnExtents = False


# Gets the namespace from an element
def get_namespace(element):
    m = re.match(r'{.*}', element.tag)
    return m.group(0) if m else ''


def extract_coords_from_kml(file):
    print("Reading file: ", file)
    tree = ET.parse(file)
    root = tree.getroot()
    namespace = get_namespace(root)
    # print("namespace is: ", namespace)
    coords = []
    for node in root.findall(".//{0}LinearRing/{0}coordinates".format(namespace)):
        coord_text_split = node.text.strip().split()
        for coord_text in coord_text_split:
            coords.append(coord_text)
    # For processing TRACK data
    # for node in root.findall(".//{0}LineString/{0}coordinates".format(namespace)):
    #     coord_text_split = node.text.strip().split()
    #     for coord_text in coord_text_split:
    #         coords.append(coord_text)
    if not coords:
        # Fall back to brute-force
        print("WARNING: Failed to get coords from ", file)
        coords = root[0][3][1][0][0][0].text.strip().split()
    return coords


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
        full_url = "{}{}".format(NHC_BASE_URL, file_match.strip())
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
    if x_coord is None:
        return None
    if x_coord < 0:
        if drawOnExtents:
            return 0
        else:
            return None
    elif x_coord > (image_width - 1):
        if drawOnExtents:
            return image_width - 1
        else:
            return None
    return x_coord


def get_pixel_coord(coord_list, cur_delta, lower_bound, upper_bound):
    pixel_delta = (lower_bound - upper_bound)
    ret_val = int(upper_bound + (pixel_delta * cur_delta))
    # Bound to map
    if ret_val < coord_list[-1][0]:
        if drawOnExtents:
            return coord_list[-1][0]
        else:
            return None
    elif ret_val > coord_list[0][0]:
        if drawOnExtents:
            return coord_list[0][0]
        else:
            return None
    return ret_val


def get_image_latitude_y_pixel_with_list(latitude_list, decimal_latitude):
    if decimal_latitude <= latitude_list[0][1]:
        if drawOnExtents:
            return latitude_list[0][0]
        else:
            return None
    if decimal_latitude >= latitude_list[-1][1]:
        if drawOnExtents:
            return latitude_list[-1][0]
        else:
            return None

    prev_pair = latitude_list[0]
    for pair in latitude_list:
        if pair[1] < decimal_latitude:
            prev_pair = pair
        elif pair[1] > decimal_latitude:
            lower_lat_bound = prev_pair[0]
            upper_lat_bound = pair[0]
            delta = (pair[1] - decimal_latitude) / 5.0
            return get_pixel_coord(latitude_list, delta, lower_lat_bound, upper_lat_bound)
        else:
            return pair[0]


def get_image_longitude_x_pixel_with_list(longitude_list, decimal_longitude):
    if decimal_longitude >= longitude_list[0][1]:
        if drawOnExtents:
            return longitude_list[0][0]
        else:
            return None
    if decimal_longitude <= longitude_list[-1][1]:
        if drawOnExtents:
            return longitude_list[-1][0]
        else:
            return None
    prev_pair = longitude_list[0]
    for pair in longitude_list:
        if pair[1] > decimal_longitude:
            prev_pair = pair
        elif pair[1] < decimal_longitude:
            lower_long_bound = prev_pair[0]
            upper_long_bound = pair[0]
            delta = (decimal_longitude - pair[1]) / 5.0
            return get_pixel_coord(longitude_list, delta, lower_long_bound, upper_long_bound)
        else:
            return pair[0]


def remove_logos_and_add_unofficial_text(image_draw, text_position_data):
    # Remove Logos
    image_draw.rectangle((0, 0, 63, 61), DRAW_WHITE)
    image_draw.rectangle((838, 0, 898, 61), DRAW_WHITE)
    if addDisclaimerText:
        for loc in text_position_data:
            image_draw.text((loc[0], loc[1]), UNOFFICIAL_STRING, loc[2], font=DRAW_FONT)


def modify_image(image, lat_func, long_func):
    skip_count = 0
    for file in glob.glob("*.kml"):
        coords = extract_coords_from_kml(file)
        for coord in coords:
            split = coord.split(',')
            x_coord = bound_x_to_image(image.size[0], long_func(float(split[0])))
            y_coord = lat_func(float(split[1]))
            if not drawOnExtents and (x_coord is None or y_coord is None):
                skip_count += 1
                continue
            # print("latitude ", split[1], " gave y_coord: ", y_coord)
            image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        if skip_count > 0:
            print("Skipped ", skip_count, " in ", file)


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


atl_text_locations = []
atl_text_locations.append((20, 40, DRAW_BLACK))
atl_text_locations.append((700, 40, DRAW_BLACK))
atl_text_locations.append((15, 525, DRAW_WHITE))
atl_text_locations.append((700, 100, DRAW_WHITE))
atl_text_locations.append((700, 540, DRAW_WHITE))


def do_mod_atl_image():
    eastern = pytz.timezone('US/Eastern')
    now_time_loc = datetime.datetime.now(eastern)
    time_string = now_time_loc.strftime("!! %I:%M %p %Z !!")
    date_string = now_time_loc.strftime("!! %a %b %d %Y !!")
    with Image.open('two_atl_5d0.png').convert('RGB') as image:
        draw = ImageDraw.Draw(image)
        remove_logos_and_add_unofficial_text(draw, atl_text_locations)

        # Add time and date the image was generated
        draw.text((700, 115), time_string, (255, 255, 255), font=DRAW_FONT)
        draw.text((700, 130), date_string, (255, 255, 255), font=DRAW_FONT)
        modify_image(image, get_atl_image_latitude_y_pixel, get_atl_image_longitude_x_pixel)
        # testing coordinate generation
        # for longitude in range(0, 45):
        #     longitude = -105 + (longitude * 2.5)
        #     x_coord = bound_x_to_image(image.size[0], get_atl_image_longitude_x_pixel(longitude))
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


east_pac_text_locations = []
east_pac_text_locations.append((20, 40, DRAW_BLACK))
east_pac_text_locations.append((700, 40, DRAW_BLACK))
east_pac_text_locations.append((15, 500, DRAW_WHITE))
east_pac_text_locations.append((15, 100, DRAW_WHITE))
east_pac_text_locations.append((685, 540, DRAW_WHITE))


def do_mod_east_pac_image():
    pacific = pytz.timezone('US/Pacific')
    now_time_loc = datetime.datetime.now(pacific)
    time_string = now_time_loc.strftime("!! %I:%M %p %Z !!")
    date_string = now_time_loc.strftime("!! %a %b %d %Y !!")
    with Image.open('two_pac_5d0.png').convert('RGB') as image:
        draw = ImageDraw.Draw(image)
        remove_logos_and_add_unofficial_text(draw, east_pac_text_locations)
        # Add time and date the image was generated
        draw.text((15, 130), time_string, (255, 255, 255), font=DRAW_FONT)
        draw.text((15, 145), date_string, (255, 255, 255), font=DRAW_FONT)
        modify_image(image, get_east_pac_image_latitude_y_pixel, get_east_pac_image_longitude_x_pixel)

        # testing coordinate generation
        # for longitude in range(0, 45):
        #     longitude = -145 + (longitude * 2.5)
        #
        #     x_coord = bound_x_to_image(image.size[0], get_east_pac_image_longitude_x_pixel(longitude))
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


cpac_text_locations = []
cpac_text_locations.append((20, 40, DRAW_BLACK))
cpac_text_locations.append((700, 40, DRAW_BLACK))
cpac_text_locations.append((15, 500, DRAW_WHITE))
cpac_text_locations.append((700, 150, DRAW_WHITE))
cpac_text_locations.append((700, 540, DRAW_WHITE))


def do_mod_cpac_image():
    hawaii = pytz.timezone('US/Hawaii')
    now_time_loc = datetime.datetime.now(hawaii)
    time_string = now_time_loc.strftime("!! %I:%M %p %Z !!")
    date_string = now_time_loc.strftime("!! %a %b %d %Y !!")
    with Image.open('two_cpac_5d0.png').convert('RGB') as image:
        draw = ImageDraw.Draw(image)
        remove_logos_and_add_unofficial_text(draw, cpac_text_locations)
        # Add time and date the image was generated
        draw.text((700, 165), time_string, (255, 255, 255), font=DRAW_FONT)
        draw.text((700, 180), date_string, (255, 255, 255), font=DRAW_FONT)
        modify_image(image, get_cpac_image_latitude_y_pixel, get_cpac_image_longitude_x_pixel)

        # testing coordinate generation
        # for longitude in range(0, 45):
        #    longitude = -180 + (longitude * 2.5)
        #    x_coord = bound_x_to_image(image.size[0], get_cpac_image_longitude_x_pixel(longitude))
        #    print("longitude: ", longitude, " x_coord: ", x_coord)
        #    for latitude in range(0, 20):
        #        latitude = latitude * 2.5
        #        y_coord = get_cpac_image_latitude_y_pixel(latitude)
        #        # print("latitude ", latitude, " gave y_coord: ", y_coord)
        #        image.putpixel((x_coord, y_coord), (0, 0, 0, 255))
        # for longitude in range(0, 4):
        #     longitude = 170 + (longitude * 2.5)
        #     x_coord = bound_x_to_image(image.size[0], get_cpac_image_longitude_x_pixel(longitude))
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
            # The CPAC image overlaps the EPAC
            if not generateCentralPacific or not drawEPacOnCPac:
                print("Clean up")
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
