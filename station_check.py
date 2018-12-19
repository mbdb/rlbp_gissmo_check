#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Usage:
    station_check.py --sta <sta>

Example:
    station_check.py --sta CHMF

Options:
    -h --help           Show this screen.
    --version           Show version.
    -s --sta <sta>      Set station code.
"""
from docopt import docopt
import numpy as np
import re
import requests


class bcolors:
    ERROR = '\033[31m[error]\033[0m'
    WARNING = '\033[33m[warning]\033[0m'


def get_json(url):
    req = requests.get(url)
    if req.status_code != 200:
        req.raise_for_status()
    data = req.json()
    return data


def get_station_json(sta_code, url):
    return get_json("%s/%s%s" % (url, "sites/?code=", sta_code))


def get_docs_from_station(sta_id, url):
    all_doc_list = get_json("%s/%s" % (url, "documents"))
    sta_url = "https://gissmo.unistra.fr/api/v1/sites/%s/" % (sta_id)
    doc_list = list()
    for d in all_doc_list:
        if d['station'] == sta_url:
            doc_list.append(d)
    return doc_list


def get_equip_from_station(sta_code, url):
    return get_json("%s/%s%s" % (url, "equipments/?station=", sta_code))


def get_chan_from_station(sta_code, url):
    return get_json("%s/%s%s" % (url, "channels/?station=", sta_code))


def get_parameter_from_chan(chan_id, url):
    return get_json("%s/%s%s" % (url, "channel_parameters/?channel=", chan_id))


def get_ip_from_equip(equip_id, url):
    return get_json("%s/%s%s" % (url, "ipaddresses/?equipment=", equip_id))


def get_service_from_equip(equip_id, url):
    return get_json("%s/%s%s" % (url, "services/?equipment=", equip_id))


def _check_position(some_json):
    # tested
    if some_json['latitude'] is None or \
       np.absolute(float(some_json['latitude'])) > 90:
        print("%s latitude is %s" % (bcolors.ERROR, some_json['latitude']))

    if some_json['longitude'] is None or \
       np.absolute(float(some_json['longitude'])) > 180:
        print("%s longitude is %s" % (bcolors.ERROR, some_json['longitude']))

    if some_json['elevation'] is None or \
       float(some_json['elevation']) < -11000 or \
       float(some_json['elevation']) > 9000:
        print("%s elevation is %s" % (bcolors.ERROR, some_json['elevation']))

    if some_json['latitude_unit'] is None:
        print("%s latitude unit is None" % (bcolors.ERROR))
    if some_json['longitude_unit'] is None:
        print("%s longitude unit is None" % (bcolors.ERROR))
    if some_json['elevation_unit'] is None:
        print("%s elevation unit is None" % (bcolors.ERROR))


def _check_chan_mseed_standard(chan_json):
    # tested
    azimuth = float(chan_json['azimuth'])
    dip = float(chan_json['dip'])

    if azimuth < 0 or azimuth > 360:
        msg = "(should be in [0, 360]) not a consistent azimuth at channel"
        print("%s %.2f %s %s" % (bcolors.ERROR, azimuth, msg,
                                 chan_json['code']))
    else:
        if chan_json['code'][-1] == 'E':
            if np.absolute(azimuth - 90) > 5:
                msg = "(should be in [85, 95]) not a consistent azimuth at \
channel"
                print("%s %.2f %s %s" % (bcolors.ERROR, azimuth, msg,
                                         chan_json['code']))
        elif chan_json['code'][-1] == 'N':
            if azimuth > 5 and azimuth < 355:
                msg = "(should not be in [5, 355]) not a consistent azimuth \
at channel"
                print("%s %.2f %s %s" % (bcolors.ERROR, azimuth, msg,
                                         chan_json['code']))
        elif chan_json['code'][-1] == '1':
            if azimuth < 5 or azimuth > 355:
                print("%s azimuth is %.2f, component should be 'N'" %
                      (bcolors.ERROR, azimuth))
        elif chan_json['code'][-1] == '2':
            if np.absolute(azimuth - 90) < 5:
                msg = "(should not be in [85, 95]) not a consistent azimuth \
at channel"
                print("%s %.2f %s %s" % (bcolors.ERROR, azimuth, msg,
                                         chan_json['code']))
        elif chan_json['code'][-1] == 'Z':
            if azimuth != 0:
                msg = "(should be '0.0') not a consistent azimuth at channel"
                print("%s %.2f %s %s" % (bcolors.ERROR, azimuth, msg,
                                         chan_json['code']))

    if chan_json['code'][-1] in ['E', 'N', '1', '2']:
        if dip != 0:
            msg = "(should be '0.0') not a consistent dip at channel"
            print("%s %.2f %s %s" % (bcolors.ERROR, dip, msg,
                                     chan_json['code']))
    elif chan_json['code'][-1] == 'Z':
        if dip != -90:
            msg = "(should be '-90.0') not a consistent dip at channel"
            print("%s %.2f %s %s" % (bcolors.ERROR, dip, msg,
                                     chan_json['code']))

    if chan_json['code'][0] == 'L' and chan_json['location_code'] == '00':
        if float(chan_json['sample_rate']) != 1:
            msg = "(should be '1.0') not a consistent sample rate at channel"
            print("%s %.2f %s %s" % (bcolors.ERROR, chan_json['sample_rate'],
                                     msg, chan_json['code']))
    elif chan_json['code'][0] == 'H' and chan_json['location_code'] == '00':
        if float(chan_json['sample_rate']) != 100:
            msg = "(should be '100.0') not a consistent sample rate at channel"
            print("%s %.2f %s %s" % (bcolors.ERROR, chan_json['sample_rate'],
                                     msg, chan_json['code']))

    if 'CONTINUOUS' not in chan_json['datatypes']:
        msg = "'CONTINUOUS' not in datatypes at channel"
        print("%s %s %s" % (bcolors.ERROR, msg, chan_json['code']))
    if 'GEOPHYSICAL' not in chan_json['datatypes']:
        msg = "'GEOPHYSICAL' not in datatypes at channel"
        print("%s %s %s" % (bcolors.ERROR, msg, chan_json['code']))

    requested = ['Velocimeter', 'Datalogger']
    for e in chan_json['equipments']:
        _c_equip = get_json(e)
        requested.pop(requested.index(_c_equip['type']))
    for r in requested:
        msg = "missing at channel"
        print("%s %s %s %s" % (bcolors.ERROR, r, msg,
                               chan_json['code']))


def _check_chan_attribute(chan_list, param):
    # tested
    _param_list = [_chan[param] for _chan in chan_list]
    if isinstance(_param_list[0], list):
        for _p in _param_list:
            _p.sort()
    if _param_list.count(_param_list[0]) != len(_param_list):
        msg = "are not consistent between channels"
        print("%s %s %s" % (bcolors.ERROR, param, msg))


def check_station(sta_list):
    # tested
    sta_json = sta_list[0]
    operator_json = get_json(sta_json['operator'])

    print("Station code: %s" % (sta_json['code']))
    print("Name: %s" % (sta_json['name']))
    print("Position:")
    print("    Latitude: %s %s" % (sta_json['latitude'],
                                   sta_json['latitude_unit']))
    print("    Longitude: %s %s" % (sta_json['longitude'],
                                    sta_json['longitude_unit']))
    print("    Elevation: %s %s" % (sta_json['elevation'],
                                    sta_json['elevation_unit']))
    print("Type: %s" % (sta_json['type']))
    print("Status: %s" % (sta_json['status']))
    print("Geology: %s" % (sta_json['geology']))
    print("Operator organization: %s" % (operator_json['name']))

    _check_position(sta_json)

    if sta_json['status'] != "Running":
        print("%s current status is '%s'" % (bcolors.ERROR,
                                             sta_json['status']))

    if sta_json['geology'] == '':
        print("%s geology not filled" % (bcolors.WARNING))

    if operator_json['name'] == "Unknown":
        print("%s operator unknown" % (bcolors.ERROR))

    if sta_json['type'] != "Measuring site":
        print("%s current type is '%s'" % (bcolors.ERROR, sta_json['type']))


def check_docs(doc_list):
    # tested
    requested = ["Lease", "Datasheet", "Picture", "Analysis report",
                 "Site proposal"]
    if len(doc_list) == 0:
        print("%s no document related to this station" % (bcolors.ERROR))
    else:
        print("Documents:")
        for d in doc_list:
            print("    %s '%s' available at %s" % (d['doctype'], d['title'],
                                                   d['link']))
            if d['doctype'] in requested:
                requested.pop(requested.index(d['doctype']))
            if re.search("dossier_proposition_site_", d['link']) and \
               d['doctype'] == "Analysis report":
                    requested.pop(requested.index("Site proposal"))

        if len(requested) > 0:
            for r in requested:
                print("%s no %s related to this station" % (bcolors.ERROR, r))


def check_sta_equipments(equip_list):
    # tested
    requested = ["Velocimeter", "Datalogger", "Armoire BT", "Armoire TBT",
                 "Modem"]

    if len(equip_list) == 0:
        print("%s no equipement installed at this station" % (bcolors.ERROR))
    else:
        print("Current equipments:")
        for e in equip_list:
            print("    %s %s #%s %s" % (e['type'], e['name'],
                                        e['serial_number'], e['status']))
            if e['type'] in requested:
                requested.pop(requested.index(e['type']))
            elif re.search('modem', e['type'].lower())\
                 or re.search('routeur', e['type'].lower()):
                requested.pop(requested.index("Modem"))

        for e in equip_list:
            if e['status'] != "Running":
                print("%s %s %s #%s current status is '%s'" %
                      (bcolors.ERROR, e['type'], e['name'], e['serial_number'],
                       e['status']))
        if len(requested) > 0:
            for r in requested:
                print("%s no %s installed at this station" %
                      (bcolors.ERROR, r))


def check_ips(ip_list):
    # tested
    public_ip = list()
    print("Wide Area Network configuration (found on the modem):")
    for ip in ip_list:
        if ip['ip'][:7] != '192.168' and ip['ip'][:3] != '10.' and \
           ip['netmask'] == '0.0.0.0':
            public_ip.append(ip)
    if len(public_ip) == 0:
        msg = "no public ip found, should be configured at modem level"
        print("%s %s" % (bcolors.ERROR, msg))
    else:
        for ip in public_ip:
            print("    Public IP: %s" % (ip['ip']))


def check_services(ser_list):
    # tested
    if len(ser_list) == 0:
        msg = "no network services available"
        print("%s %s" % (bcolors.ERROR, msg))
    else:
        for s in ser_list:
            print("    %s available on port %s (%s)" % (s['protocol'],
                                                        s['port'],
                                                        s['description']))


def check_chan_list(chan_list, url):
    print("Velocimtric channels affiliated to RLBP network \
(net='FR', loc='00', cha='?H?'):")
    if len(chan_list) == 0:
        msg = "no channel related to this station"
        print("%s %s" % (bcolors.ERROR, msg))
    else:
        # filter open 'H' channels with net code 'FR' and loc code '00'
        kept_chan_list = list()
        for c in chan_list:
            net = get_json(c['network'])['code']
            if c['end_date'] is None and net == 'FR' and \
               c['location_code'] == '00' and c['code'][1] == 'H':
                kept_chan_list.append(c)

        if len(kept_chan_list) == 0:
            msg = "available channels are not affiliated to RLBP network"
            print("%s %s" % (bcolors.ERROR, msg))
        else:
            # test if station code is coherent between channels (should be)
            _check_chan_attribute(chan_list, 'station')
            sta_json = get_json(kept_chan_list[0]['station'])

            # test if HH streams are present (mandatory)
            _stream_list = [_chan['code'][:2] for _chan in kept_chan_list]
            if _stream_list.count('HH') != 3:
                    msg = "no or missing 'HH' channels, mandatory"
                    print("%s %s" % (bcolors.ERROR, msg))
            # test if H streams are consistent (ie Z12 or ZNE, not Z1N)
            # TODO
            else:
                # test if LH streams are present
                if _stream_list.count('LH') != 3:
                    msg = "no or missing 'LH' channels"
                    print("%s %s" % (bcolors.ERROR, msg))
                _chan_list = [_chan['code'] for _chan in kept_chan_list]
                _azimuth_list = [_chan['azimuth'] for _chan in kept_chan_list]
                _dip_list = [_chan['dip'] for _chan in kept_chan_list]
                for _chan in _chan_list:
                    # test if components are identical between streams
                    if _chan.replace(_chan[:2], 'HH') not in _chan_list:
                        msg = "comp. codes not consistent with HH at channel"
                        print("%s %s %s" % (bcolors.ERROR, msg, _chan))
                    else:
                        # test azimuth between streams
                        if _azimuth_list[_chan_list.index(_chan)] != \
                           _azimuth_list[_chan_list.index(
                                         _chan.replace(_chan[:1], 'H'))]:
                            msg = "azimuth not consistent with HH at channel"
                            print("%s %s %s" % (bcolors.ERROR, msg, _chan))
                        # test dip between streams
                        if _dip_list[_chan_list.index(_chan)] != \
                           _dip_list[_chan_list.index(_chan.replace(_chan[:1],
                                                                    'H'))]:
                            msg = "dip not consistent with HH at channel"
                            print("%s %s %s" % (bcolors.ERROR, msg, _chan))
                        # test if azimuth are consistent between channels
                        if _chan[-1] in ['1', 'N']:
                            _index_n = _chan_list.index(_chan)
                            if _chan[-1] == '1':
                                _index_e = _chan_list.index(_chan.replace('1',
                                                                          '2'))
                            elif _chan[-1] == 'N':
                                _index_e = _chan_list.index(_chan.replace('N',
                                                                          'E'))
                            _az_n = _azimuth_list[_index_n]
                            _az_e = _azimuth_list[_index_e]
                            if "%.1f" % ((float(_az_n) + 90) % 360) != _az_e:
                                msg = "azimuth not consistent between \
horizontal channels, check"
                                print("%s %s %s" % (bcolors.ERROR, msg,
                                                    _chan[:2]))

                _check_chan_attribute(kept_chan_list, 'depth')
                _check_chan_attribute(kept_chan_list, 'depth_unit')
                _check_chan_attribute(kept_chan_list, 'latitude')
                _check_chan_attribute(kept_chan_list, 'latitude_unit')
                _check_chan_attribute(kept_chan_list, 'longitude')
                _check_chan_attribute(kept_chan_list, 'longitude_unit')
                _check_chan_attribute(kept_chan_list, 'elevation')
                _check_chan_attribute(kept_chan_list, 'elevation_unit')
                _check_chan_attribute(kept_chan_list, 'clock_drift')
                _check_chan_attribute(kept_chan_list, 'clock_drift_unit')
                _check_chan_attribute(kept_chan_list, 'sample_rate_unit')
                _check_chan_attribute(kept_chan_list, 'calibration_units')
                _check_chan_attribute(kept_chan_list, 'datatypes')
                _check_chan_attribute(kept_chan_list, 'storage_format')
                _check_chan_attribute(kept_chan_list, 'equipments')

                # get channel parameters of HHZ channel as reference
                _hhz_all_param = None
                for c in kept_chan_list:
                    if c['code'] == 'HHZ':
                            _hhz_all_param = get_parameter_from_chan(c['id'],
                                                                     url)
                            _hhz_model_list = [_param['model']
                                               for _param in _hhz_all_param]
                            _hhz_param_list = [_param['parameter']
                                               for _param in _hhz_all_param]
                            _hhz_value_list = [_param['value']
                                               for _param in _hhz_all_param]
                            _hhz_model_list.sort()
                            _hhz_param_list.sort()
                            _hhz_value_list.sort()

                for c in kept_chan_list:
                    _check_chan_mseed_standard(c)
                    # test position coherence and if different from station
                    _check_position(c)
                    if c['latitude'] != sta_json['latitude'] or \
                       c['longitude'] != sta_json['longitude'] or \
                       c['elevation'] != sta_json['elevation']:
                        msg = "channel position differs from station position"
                        print("%s %s %s" % (bcolors.WARNING, c['code'], msg))

                    # test equipments parameters between channels
                    _c_all_param = get_parameter_from_chan(c['id'], url)
                    if len(_c_all_param) == 0:
                        msg = "no parameters at channel"
                        print("%s %s %s" % (bcolors.ERROR, msg, c['code']))
                    elif _hhz_all_param is not None:
                        _model_list = [_param['model']
                                       for _param in _c_all_param]
                        _param_list = [_param['parameter']
                                       for _param in _c_all_param]
                        _value_list = [_param['value']
                                       for _param in _c_all_param]
                        _model_list.sort()
                        _param_list.sort()
                        _value_list.sort()
                        if _value_list != _hhz_value_list:
                            msg = "parameters not consistent for channel"
                            print("%s %s %s" % (bcolors.ERROR, msg, c['code']))

                # plotting stats
                net = 'FR'
                sta = sta_json['code']
                for c in kept_chan_list:
                    loc = c['location_code']
                    cha = c['code']
                    print("    %s.%s.%s.%s" % (net, sta, loc, cha))
                    if c['code'][-1] == 'Z':
                        print("        Sample rate: %s %s" %
                              (c['sample_rate'], c['sample_rate_unit']))

                for c in kept_chan_list:
                    if c['code'] == 'HHZ':
                        c_hhz = c
                    elif c['code'] == 'HH1' or c['code'] == 'HHN':
                        c_hhn = c

                velocimeter_json = None
                datalogger_json = None
                for e in c_hhz['equipments']:
                    e_json = get_json(e)
                    if e_json['type'] == 'Datalogger':
                        datalogger_json = e_json
                    elif e_json['type'] == 'Velocimeter':
                        velocimeter_json = e_json
                p_list = get_parameter_from_chan(c_hhz['id'], url)

                print("    All velocimetric channels:")
                print("        Latitude: %s %s" % (c_hhz['latitude'],
                                                   c_hhz['latitude_unit']))
                print("        Longitude: %s %s" % (c_hhz['longitude'],
                                                    c_hhz['longitude_unit']))
                print("        Elevation: %s %s" % (c_hhz['elevation'],
                                                    c_hhz['elevation_unit']))
                print("        Depth: %s %s" % (c_hhz['depth'],
                                                c_hhz['depth_unit']))
                print("        Azimuth: %s %s" % (c_hhn['azimuth'],
                                                  c_hhn['azimuth_unit']))
                print("        Vertical dip: %s %s" % (c_hhz['dip'],
                                                       c_hhn['dip_unit']))
                if velocimeter_json is not None:
                    print("        Velocimeter: %s #%s" %
                          (velocimeter_json['name'],
                           velocimeter_json['serial_number']))
                if datalogger_json is not None:
                    print("        Datalogger: %s #%s" %
                          (datalogger_json['name'],
                           datalogger_json['serial_number']))
                if len(c_hhz['datatypes']) > 0:
                    print("        Datatypes:")
                    for d in c_hhz['datatypes']:
                        print("            %s" % d)
                if len(p_list) > 0:
                    print("        Instrument parameters:")
                    for p in p_list:
                        print("            %s %s %s" % (p['model'],
                                                        p['parameter'],
                                                        p['value']))


def check_overall_single_station(sta_code, url):

    sta_list = get_station_json(sta_code, url)
    if len(sta_list) == 0:
        print("%s station code not existing in database" % (bcolors.ERROR))
    else:
        doc_list = get_docs_from_station(sta_list[0]['id'], url)
        equip_list = get_equip_from_station(sta_code, url)
        chan_list = get_chan_from_station(sta_code, url)

        net_equipment = None
        for e in equip_list:
            if re.search('modem', e['type'].lower()) or \
               re.search('routeur', e['type'].lower()):
                net_equipment = e

        ip_list = list()
        ser_list = list()
        if net_equipment is not None:
            ip_list = get_ip_from_equip(net_equipment['id'], url)
            ser_list = get_service_from_equip(net_equipment['id'], url)

        check_station(sta_list)
        check_docs(doc_list)
        check_sta_equipments(equip_list)
        check_ips(ip_list)
        check_services(ser_list)
        check_chan_list(chan_list, url)


if __name__ == '__main__':
    args = docopt(__doc__, version='station_check.py 0.2')
    # Uncomment for debug
    # print(args)

    gissmo_url = 'https://gissmo.unistra.fr/api/v1'
    check_overall_single_station(args['--sta'], gissmo_url)
