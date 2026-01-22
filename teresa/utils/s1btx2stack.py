import argparse
import datetime
import fnmatch
import json
import os
import sys
import re
import shutil
from s1tbx_stack import S1tbxStacks

from lxml import etree

from helpers import filesystem

M = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4,
     'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
     'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12}
SPEED_OF_LIGHT = 299792458.0  # m/s


class S1tbxStacks(object):

    re_master_file = "[0-9a-zA-Z_]*_mst_[0-9]{2}[a-zA-Z]{3}[0-9]{4}.img" # matches <xxxxxxxx>_mst_<ddMMMyyyy>.img

    def __init__(self, dir, all, run):
        self.dir = dir
        self.all = all
        self.run = run

    @staticmethod
    def locate_re(pattern, root=os.curdir):
        '''Locate all files matching supplied filename pattern in and below
        supplied root directory.'''
        result = []
        for path, dirs, files in os.walk(os.path.abspath(root)):
            for filename in files:
                reg_pattern = re.compile(pattern)
                if reg_pattern.search(filename):
                    result.append(os.path.join(path, filename))
        result.sort()
        return result

    def find_sym_link(self, files):
        result = []
        for file in files:
            result.append(os.path.abspath(os.readlink(file)))
        return result

    def remove_duplicates(self, source_list, duplicates_list):
        result_list = []
        for source in source_list:
            match = False
            for duplicate in duplicates_list:
                if (source.split("/")[-3] == duplicate.split("/")[-3]):
                    match = True
            if(match==False):
                result_list.append(source)
        return result_list

    def remove_files(self, files):
        for file in files:
            print("removing " + str(file))
            if(self.run):
                os.remove(file)

    def do_cleanup_s1tbx_stacks(self):
        dir_list = os.listdir(self.dir)
        dir_list.sort()

        for dir in dir_list:
            self.do_remove_old_master_images(os.path.join(self.dir, dir))

    def do_remove_old_master_images(self, dir):

        # if called directly, get dir from settings
        if(dir == None):
            dir = self.dir
        s1_image_root_dir = os.path.join(dir, "process_s1tbx/")
        process_root_dir = os.path.join(dir, "process/")

        # first find all master files in process and process_s1tbx directories of the project
        s1_images = self.locate_re(S1tbxStacks.re_master_file, s1_image_root_dir)
        process_images = self.locate_re(S1tbxStacks.re_master_file, process_root_dir)

        # find the master image to save, either in the process directory, or otherwise the first master image in the process_s1tbx directory
        #  find the master images files that are linked to from the process_s1tbx directory
        master_image_to_save = self.find_sym_link(process_images)
        if( len(master_image_to_save)==0):
            # find the first master image in the process_s1tbx stack
            master_image_to_save = []
            if len(s1_images) > 0:
                master_image_to_save.append(s1_images[0])
            else:
                print("warning: " + str(s1_image_root_dir) + " is a  inconsistent stack, no master image found")

        # remove from the list of master images in the process_s1tbx dir, the master images that are used in the process dir.
        s1_images_to_remove = self.remove_duplicates(s1_images, master_image_to_save)
        # delete all master images from the process_s1tbx dir that are not used.
        self.remove_files(s1_images_to_remove)

    def do(self):
        if (not (self.run)):
            print("testrun, no actual files will be removed from the system")

        if (self.all):
            self.do_cleanup_s1tbx_stacks()
        else:
            self.do_remove_old_master_images(None)

def parsedate(datestr):
    # split in pieces
    for a in ['-', ' ', ':', '.']:
        datestr = datestr.replace(a, 'x')
    day, month, year, h, m, s, ms = datestr.split('x')
    # convert month
    month = M[month]
    # make all integer
    year, day, h, m, s, ms = map(int, [year, day, h, m, s, ms])
    return datetime.datetime(year, month, day, h, m, s, ms)


def attrfind(ff, name, frmt=lambda x: x):
    for f in ff:
        if f.attrib['name'] == name:
            return frmt(f.text)
    return None


def locate(pattern, root=os.curdir):
    '''Locate all files matching supplied filename pattern in and below
    supplied root directory.'''
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


def makedirs_if_not_exists(dir_name):
    try:
        os.makedirs(dir_name)
    except OSError as e:
        if not os.path.isdir(dir_name):
            raise e


def do_dem(processdir):
    source_dem_dir = "../../process_s1tbx/dem/merged_with_dem.data/" #TODO: too hardcoded?
    dest_dir = os.path.join(processdir, "dem")
    makedirs_if_not_exists(dest_dir)
    files_to_link = ["elevation.img", "elevation.hdr"]
    for f in files_to_link:
        try:
            os.symlink(os.path.join(source_dem_dir, f),
                       os.path.join(dest_dir, f))
        except Exception as e:
            print (e)

def do_remove_master_images(image_root_dir):

    s1tbx_stack = S1tbxStacks(os.path.dirname(image_root_dir), False, True)
    s1tbx_stack.do()

def main(filename, role='slave', processdir='process'):
    print('Now work on ', filename)
    p = etree.parse(filename)
    r = p.getroot()
    basepath = os.path.split(filename)[0]

    # Get all the abstracted metadata fields
    #
    # Go for field
    #
    #    Dataset_Sources / metadata / Abstracted_Metadata / <attributes>
    #
    read_role = {'slave': 'Slave_Metadata', 'master': 'Abstracted_Metadata'}[role]

    ff1 = [q for q in r.find('Dataset_Sources/MDElem').iter() if q.attrib['name'] == 'metadata'][0]
    ff2 = [q for q in ff1.getchildren() if q.attrib['name'] == read_role][
        0]  # read either master or slave depending on role

    if role == 'master':
        ff = ff2.getchildren()
    else:
        ff = ff2.getchildren()[1].getchildren()

    # Get attributes
    data = {}
    data['esa_id'] = attrfind(ff, 'PRODUCT')
    data['sensor'] = attrfind(ff, 'MISSION')
    data['mode'] = attrfind(ff, 'ACQUISITION_MODE')
    data['swath'] = attrfind(ff, 'SWATH')
    data['track'] = attrfind(ff, 'REL_ORBIT', float)
    data['polarisation'] = attrfind(ff, 'mds1_tx_rx_polar')
    data['is_ascending'] = attrfind(ff, 'PASS') == 'ASCENDING'
    data['RSR'] = attrfind(ff, 'range_sampling_rate', float) * 1e6  # [Hz]
    data['wavelength'] = SPEED_OF_LIGHT / (float(attrfind(ff, 'radar_frequency')) * 1e6)  # [m]
    data['bandwidthRa'] = attrfind(ff, 'range_bandwidth', float) * 1e6  # [Hz]
    data['bandwidthAz'] = attrfind(ff, 'azimuth_bandwidth', float)  # [Hz]
    data['Scenecentrelatitude'] = 0.5 * (min(attrfind(ff, 'first_near_lat', float),
                                             attrfind(ff, 'first_far_lat', float),
                                             attrfind(ff, 'last_near_lat', float),
                                             attrfind(ff, 'last_far_lat', float))
                                         +
                                         max(attrfind(ff, 'first_near_lat', float),
                                             attrfind(ff, 'first_far_lat', float),
                                             attrfind(ff, 'last_near_lat', float),
                                             attrfind(ff, 'last_far_lat', float)))  # [deg]
    data['Scenecentrelongitude'] = 0.5 * (min(attrfind(ff, 'first_near_long', float),
                                              attrfind(ff, 'first_far_long', float),
                                              attrfind(ff, 'last_near_long', float),
                                              attrfind(ff, 'last_far_long', float))
                                          +
                                          max(attrfind(ff, 'first_near_long', float),
                                              attrfind(ff, 'first_far_long', float),
                                              attrfind(ff, 'last_near_long', float),
                                              attrfind(ff, 'last_far_long', float)))  # [deg]
    data['timeToFirstPixel'] = 2 * float(
        attrfind(ff, 'slant_range_to_first_pixel')) / SPEED_OF_LIGHT  # [s]

    ff1 = [q for q in r.find('Dataset_Sources/MDElem').iter() if q.attrib['name'] == 'azimuthFrequency'][0]
    data['PRF'] = float(ff1.text)

    # Get date
    datestr = attrfind(ff, 'first_line_time')
    d = parsedate(datestr)
    simpledate = d.strftime('%Y%m%d')
    data['date'] = datestr
    data['timeOfDay'] = d.hour * 3600 + d.minute * 60 + d.second + 01e-6 * d.microsecond

    # Get orbit
    orbit = [f for f in ff if f.attrib['name'] == 'Orbit_State_Vectors'][0]
    orbitdata = {'time': [],
                 'x_pos': [], 'y_pos': [], 'z_pos': [],
                 'x_vel': [], 'y_vel': [], 'z_vel': [],}
    for o in orbit.getchildren():
        for i in o.getchildren():
            par = i.attrib['name']
            val_str = i.text
            if par == 'time':
                pd = parsedate(val_str)
                val = pd.hour * 3600 + pd.minute * 60 + pd.second + 01e-6 * pd.microsecond
                # val = parsedate(val_str).isoformat()
            else:
                val = float(val_str)
            orbitdata[par].append(val)

    data['orbit'] = orbitdata

    data['n_pixels'] = int(r.find('Raster_Dimensions/NCOLS').text)
    data['n_lines'] = int(r.find('Raster_Dimensions/NROWS').text)

    # Bands in the file (some are real data, others computed)
    bb = r.findall('Image_Interpretation/Spectral_Band_Info')
    bands = {}
    for b in bb:
        # just use the real bands
        if b.find('EXPRESSION') is None:
            bands[b.find('BAND_INDEX').text] = {
                'data_type': b.find('DATA_TYPE').text,
                'unit': b.find('PHYSICAL_UNIT').text}

    # Where to find data
    for d in r.findall('Data_Access/Data_File'):
        index = d.find('BAND_INDEX').text
        bands[index]['filepath'] = d.find('DATA_FILE_PATH').attrib['href']

    # just keep the slave
    data['filepaths'] = {}

    if role == 'slave':  # what to look for in the filenames (keep master or slave files)
        lookfor = 'slv'
    else:
        lookfor = 'mst'

    for b in bands.values():

        if lookfor in b['filepath'] and b['unit'] == 'real':
            data['filepaths']['real'] = b
        if lookfor in b['filepath'] and b['unit'] == 'imaginary':
            data['filepaths']['imag'] = b
        if 'derampDemodPhase' in b['filepath']:
            data['filepaths']['deramp'] = b

    # move the files to processdir / date
    goaldir = os.path.join(processdir, simpledate)
    filesystem.makedirs_if_not_exists(goaldir)

    for name, thing in data['filepaths'].items():

        if name == 'deramp' and role == 'master': continue
        # move the header files (imag and real and also derampDemodPhase)
        frompath = os.path.join(basepath, thing['filepath'])
        frompath = os.path.join('..', '..', frompath[frompath.find('process_s1tbx'):])
        filename = os.path.split(frompath)[1]
        topath = os.path.join(goaldir, filename)
        print('Link {} to {}'.format(topath, frompath))
        try:
            if os.path.lexists(topath):
                os.remove(topath)
            os.symlink(frompath, topath)
        except Exception as e:
            print (e)

        # same for image file
        frompath = os.path.splitext(frompath)[0] + '.img'
        frompath = os.path.join('..', '..', frompath[frompath.find('process_s1tbx'):])
        topath = os.path.splitext(topath)[0] + '.img'
        topath_relative = os.path.split(topath)[1]

        data['filepaths'][name]['filepath'] = topath_relative
        print('Link {} to {}'.format(topath, frompath))
        try:
            if os.path.lexists(topath):
                os.remove(topath)
            os.symlink(frompath, topath)
        except Exception as e:
            print (e)

    jsonfile = os.path.join(goaldir, role + '.json')
    with open(jsonfile, 'w') as fo:
        json.dump(data, fo, indent=4)
    print('Wrote image info to {}'.format(jsonfile))

    if role == 'master':
        jsonfile = os.path.join(processdir, 's1tbxstack.json')
        with open(jsonfile, 'w') as fo:
            json.dump({'master': simpledate}, fo)
        print('Wrote stack master info to {}'.format(jsonfile))

    return

def find_first_master(dir):
    master_files = S1tbxStacks.locate_re(S1tbxStacks.re_master_file, dir)
    split_list = master_files[0].split('/')
    master_file_dim = ''
    for index in range(len(split_list) -2):
        master_file_dim += split_list[index] + '/'
    master_file_dim += 'merged.dim'

    return master_file_dim

def what_to_do(settings):
    # provide a file or directory as first argument
    # for a directory, look for all the files in there
    todo = []

    # if you give a directory name
    if settings.dir:

        assert (os.path.isdir(settings.dir))
        # do them all as slave
        files = list(locate('*.dim', settings.dir))
        files.sort()

        print("\nReceived a directory: now do all {} images in there\n".format(len(files)))
        for file in files:
            print('Set to do : ', file, ' S')
            todo.append((file, 'slave'))
        # and also do one to copy master files (take the first one, other master image files have been cleaned up)
        file_master = find_first_master(settings.dir)
        print('Set to do : ', file_master, ' M')
        todo.append((file_master, 'master'))

    elif settings.file:

        # always do as slave
        assert (os.path.exists(filename))
        todo.append((filename, 'slave'))

        # when it is the first one (no master yet), also extract the master
        if not os.path.exists(os.path.join(settings.processdir, 's1tbxstack.json')):
            todo.append((filename, role))

    else:
        raise (Exception('Please provide either a directory or single file'))

    return todo

def do_clean_target_dir(dir):
    if os.path.exists(dir):
        shutil.rmtree(dir, onerror=True)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Transform the results of Sentinel-1 Toolbox stack')
    parser.add_argument('-f', '--file', dest='file', default=False, help='do a single file', type=str)
    parser.add_argument('-d', '--dir', dest='dir', default=False, help='do a whole directory', type=str)
    parser.add_argument('-p', '--processdir', dest='processdir',
                        type=str, default='process', help='Directory to put the results')
    parser.add_argument('-r', '--run', dest='run', action='store_true', help='Run this (defaults to dryrun)')
    settings = parser.parse_args()

    print()
    print('*' * 40)
    for k, v in vars(settings).items():
        print('{:>20s} : {}'.format(k, v))
    print('*' * 40)
    print()
    try:
        todo = what_to_do(settings)
    except Exception as e:
        print('ERROR ', e.message, '\n')
        sys.exit()

    print()

    if settings.run:
        if os.path.basename(settings.dir) != 'process_s1tbx':
            print('input directory should be named process_s1tbx')
            sys.exit()
        if os.path.abspath(settings.dir) == os.path.abspath(settings.processdir):
            print('ERROR : Please do not put the same directory for data and process dir!')
            sys.exit()
        print('*' * 40)
        print('Now run:')
        print('*' * 40)
#        do_clean_target_dir(settings.processdir)
        for filename, role in todo:
            main(filename, role=role, processdir=settings.processdir)
        do_dem(settings.processdir)
        do_remove_master_images(settings.dir)
    else:
        print('This was just a dryrun, use -r or --run to really do something\n')
