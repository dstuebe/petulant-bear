#!/usr/bin/env python
'''
COPYRIGHT 2013 RPS ASA

This file is part of  Petulant Bear.

    Petulant Bear is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Petulant Bear is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Petulant Bear.  If not, see <http://www.gnu.org/licenses/>.

@author David Stuebe <dstuebe@asasscience.com>
@file netcdf2ncml.py
@date 07/16/13
@description Definition of static strings and functions for creating NCML from a NetCDF4
Dataset object.
'''
from __future__ import unicode_literals

import io

import numpy

NETCDF = 'netcdf'
VARIABLE = 'variable'
DIMENSION = 'dimension'
ATTRIBUTE = 'attribute'
GROUP = 'group'
VALUES = 'values'

NAME = 'name'
SHAPE = 'shape'
LENGTH = 'length'
ISUNLIMITED = 'isUnlimited'
VALUE = 'value'
TYPE = 'type'

NCML = 'ncml'
LOCATION = 'location'
XMLNS = 'xmlns'
NAMESPACE = 'http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2'
# TODO: Figure out how to re-add utf-8 encoding when using utf-8 encoded string
# and etree
HEADER      = ''''''

# common types...
type_map = {
    numpy.int8: 'byte',
    numpy.int16: 'short',
    numpy.int32: 'int',
    numpy.int64: 'long',
    numpy.float32: 'float',
    numpy.float64: 'double',
    numpy.string_: 'char',
    # This is weak sauuce... type(str) == type !
    type(str): 'char'
}

inverse_type_map = {
    'byte': numpy.int8,
    'short': numpy.int16,
    'int': numpy.int32,
    'long': numpy.int64,
    'float': numpy.float32,
    'double': numpy.float64,
    'char': str,
}

try:
    bs = basestring
except NameError:
    bs = str


def sanitize(string, spaces=True):
    string = string.replace('"', '&quote;')
    string = string.replace('&', '&amp;')

    if spaces is True:
        string = string.replace(' ', '_')
    string = string.replace('<', '&lt;')
    string = string.replace('>', '&gt;')

    return string


def parse_dim(output, dim, indent):
    if dim.isunlimited():
        output.write('''{indent}<{dimension} {name}="{dimname}" {length}="{dimlen}" {isunlimited}="true"/>\n'''.format(
            indent=indent,
            dimension=DIMENSION,
            name=NAME,
            dimname=sanitize(dim._name),
            length=LENGTH,
            dimlen=len(dim),
            isunlimited=ISUNLIMITED
        )
        )
    else:
        output.write('''{indent}<{dimension} {name}="{dimname}" {length}="{dimlen}"/>\n'''.format(
            indent=indent,
            dimension=DIMENSION,
            name=NAME,
            dimname=sanitize(dim._name),
            length=LENGTH,
            dimlen=len(dim)
        )
        )


def parse_att(output, att, indent):
    """
    att is a tuple: (name, value)
    """
    if isinstance(att[1], bs):
        outputStr = '''{indent}<{attribute} {name}="{attname}" {value}="{attvalue}"/>\n'''.format(
            indent=indent,
            attribute=ATTRIBUTE,
            name=NAME,
            attname=sanitize(att[0], spaces=False),
            value=VALUE,
            attvalue=sanitize(att[1])
        )
        if 'We have created a bathymetric digital elevation model' in att[1]:
            foo = io.StringIO()
            foo.write(outputStr)
        output.write(outputStr)
    else:
        att_type = type_map.get(type(att[1]), 'unknown')
        output.write('''{indent}<{attribute} {name}="{attname}" {type}="{att_type}" {value}="{attvalue}"/>\n'''.format(
            indent=indent,
            attribute=ATTRIBUTE,
            name=NAME,
            attname=sanitize(att[0]),
            type=TYPE,
            att_type=att_type,
            value=VALUE,
            attvalue=att[1]
        )
        )


def parse_var(output, var, indent):

    try:
        vtype = var.dtype.type
    except AttributeError:
        vtype = var.dtype

    if len(var.ncattrs()) == 0:
        output.write('''{indent}<{variable} {name}="{varname}" {shape}="{vardims}" {type}="{vartype}"/>\n'''.format(
            indent=indent,
            variable=VARIABLE,
            name=NAME,
            varname=sanitize(str(var._name)),
            shape=SHAPE,
            vardims=' '.join([sanitize(str(dname))
                              for dname in var.dimensions]),
            type=TYPE,
            vartype=type_map.get(vtype, 'unknown'),
        )
        )
    else:
        output.write('''{indent}<{variable} {name}="{varname}" {shape}="{vardims}" {type}="{vartype}">\n'''.format(
            indent=indent,
            variable=VARIABLE,
            name=NAME,
            varname=sanitize(var._name),
            shape=SHAPE,
            vardims=' '.join([sanitize(str(dname))
                              for dname in var.dimensions]),
            type=TYPE,
            vartype=type_map.get(vtype, 'unknown'),
        )
        )

        new_indent = indent + '  '

        for attname in var.ncattrs():
            parse_att(output,
                      (str(attname), str(var.getncattr(attname))),
                      new_indent)

        output.write('''{}</{}>\n'''.format(indent, VARIABLE))


def parse_group(output, group, indent):

    output.write('''{indent}<{group} {name}="{groupname}">\n'''.format(
        indent=indent,
        group=GROUP,
        name=NAME,
        groupname=sanitize(str(group.path).split('/')[-1]),
    )
    )

    new_indent = indent + '  '

    for dim in list(group.dimensions.values()):
        parse_dim(output, dim, new_indent)

    for attname in group.ncattrs():
        parse_att(output, (attname, group.getncattr(attname)), new_indent)

    for var in list(group.variables.values()):
        parse_var(output, var, new_indent)

    output.write('''{}</{}>\n'''.format(indent, GROUP))


def dataset2ncml_buffer(dataset, output, url=None):

    if url is None:
        output.write('''{header}\n<{netcdf} {xmlns}="{namespace}">\n'''.format(
            header=HEADER,
            netcdf=NETCDF,
            xmlns=XMLNS,
            namespace=NAMESPACE,
            location=LOCATION,
            url=url
        )
        )
    else:
        output.write('''{header}\n<{netcdf} {xmlns}="{namespace}" {location}="{url}">\n'''.format(
            header=HEADER,
            netcdf=NETCDF,
            xmlns=XMLNS,
            namespace=NAMESPACE,
            location=LOCATION,
            url=url
        )
        )

    indent = '  '
    for dim in list(dataset.dimensions.values()):
        parse_dim(output, dim, indent)

    for attname in dataset.ncattrs():
        parse_att(output, (str(attname),
                           str(dataset.getncattr(attname))),
                  indent)

    for var in list(dataset.variables.values()):
        parse_var(output, var, indent)

    for group in list(dataset.groups.values()):
        parse_group(output, group, indent)

    output.write('''</{}>\n'''.format(NETCDF))


def dataset2ncml(dataset, url=None):
    retval = ''
    output = io.StringIO()
    try:
        dataset2ncml_buffer(dataset, output, url)
        retval = output.getvalue()
    finally:
        output.close()
    return retval
