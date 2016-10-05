#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2016, Hugh Ma <Hugh.Ma@flextronics.com>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: fio
short_description: Execute the fio benchmark
description:
 - Use this module to run the FlexibleI/O benchmark
 - https://github.com/axboe/fio
version_added: "2.1"
options:
  chdir:
    description:
     - change working directory
    required: false
    default: null
  bs:
    description:
     - block size
    required: true
  delay:
    description:
     - piggybacks off the at module as a action plugin to run benchmark at a schedule time
    required: false
  executable:
    description:
     - path to fio executable if running from source
    required: false
  dest:
    description:
     - absolute path of file to write stdout to
    required: false
  direct:
    description:
     - If true, use non-buffered I/O
    required: False
  iodepth:
    description:
     - Number of I/O units to keep in flight against file
    required: False
  ioengine:
    description:
     - Defined how the job issues I/O
    required: False
  name:
    description:
     - Used as Job Name and to specify start of a new job.
    required: True
  numjobs:
    description:
     - Number of threads/processes performing the same workload
    required: False
    default: 1
  rw:
    description:
     - Type of I/O pattern to perform
    required: True
  size:
    description:
     - Total size of I/O for job. Can give specific size or percentage of drive
    required: True
  offset:
    description:
     - Offset in the file to start I/O. Data before the offset will not be touched.
    required: False
  sync:
    description:
     - Use synchronous I/O for buffered writes.
    required: False
  time_based:
    description:
     - Run jobs (even if repeated) until specified time is reached.
    required: False
  ramp_time:
    description:
     - Time to run specified workload before start of logging.
    required: False
  runtime:
    description:
     - Total time to run specified workload.
    required: False
  rwmixread:
    description:
     - Percentage of mixed workload that should be reads.
    required: False
  rwmixwrite:
    description:
     - Percentage of mixed workload that should be writes.
    required: False
  output_format:
    description:
     - Format in which the job results should be displayed.
    required: False
  group_reporting:
    description:
     - If set, display per-group reports instead of per-job when numjobs is specified.
    required: True
requirements:
 - fio
author: "Hugh Ma <Hugh.Ma@flextronics.com>"
'''

EXAMPLES = '''
# Run fio read job in 4k blocks up to 512M
- fio: name=read rw=read bs=4k size=512M

# Run fio read job in 4k blocks up to 512M and output to /tmp/fio.out
- fio: name=read rw=read bs=4k size=512M dest=/tmp/fio.out

# Run fio readwrite job in 4k blocks up to 512M using libaio engine with iodepth of 1
- fio: name=rw rw=rw bs=4k size=512M ioengine=libaio iodepth=1'
'''

RETURN = '''
changed:
  description: response to whether or not the benchmark completed successfully
  returned: always
  type: boolean
  sample: true

stdout:
  description: the set of responses from the commands
  returned: always
  type: list
  sample: ['...', '...']

stdout_lines:
  description: the value of stdout split into a list
  returned: always
  type: list
  sample: [['...', '...'], ['...'], ['...']]

exec_cmd:
  description: Exact command executed to launch the benchmark with parameters
  returned: success
  type: string
  sample: "/usr/bin/fio --name=..."
'''

import os
import re
import tempfile


def benchmark(module, result, bin, params):

    name        = params['name']
    bs          = params['bs']
    dest        = params['dest']
    direct      = params['direct']
    iodepth     = params['iodepth']
    ioengine    = params['ioengine']
    numjobs     = params['numjobs']
    rw          = params['rw']
    size        = params['size']
    offset      = params['offset']
    sync        = params['sync']
    time_based  = params['time_based']
    ramp_time   = params['ramp_time']
    runtime    = params['runtime']
    rwmixread   = params['rwmixread']
    rwmixwrite  = params['rwmixwrite']
    output_format   = params['output_format']
    group_reporting = params['group_reporting']

    benchmark_command = None

    if dest:
        benchmark_command = "{} --name={} --bs={} " \
                            "--rw={} --size={} --output={}"\
            .format(bin, name, bs, rw, size, dest)
    else:
        benchmark_command = "{} --name={} --bs={} " \
                            "--rw={} --size={}"\
            .format(bin, name, bs, rw, size)

    if direct: benchmark_command += " --direct=1"
    if iodepth: benchmark_command += " --iodepth={}".format(iodepth)
    if ioengine: benchmark_command += " --ioengine={}".format(ioengine)
    if numjobs: benchmark_command += " --numjobs={}".format(numjobs)
    if offset: benchmark_command += " --offset={}".format(offset)
    if output_format: benchmark_command += " --output_format={}".format(output_format)
    if sync: benchmark_command += " --sync=1"
    if ramp_time: benchmark_command += " --ramp_time={}".format(ramp_time)
    if runtime: benchmark_command += " --runtime={}".format(runtime)
    if rwmixread: benchmark_command += " --rwmixread={}".format(rwmixread)
    if rwmixwrite: benchmark_command += " --rwmixwrite={}".format(rwmixwrite)
    if time_based: benchmark_command += " --time_based"
    if group_reporting: benchmark_command += " --group_reporting"

    rc, out, err = module.run_command(benchmark_command,
                                      use_unsafe_shell=True,
                                      check_rc=True)

    if dest:
        out += "; Output located on targeted hosts at: {}".format(dest)

    result['changed']   = True
    result['exec_cmd']  = benchmark_command
    result['stdout']    = out.rstrip("\r\n")
    result['stderr']    = err.rstrip("\r\n")
    result['rc']        = rc


def parse(module, result, params):
    # Doesn't need one, since fio output has both original and JSON formats
    pass


def main():

    module = AnsibleModule(
        argument_spec = dict(
            bs=dict(required=True,
                    type='str'),
            chdir=dict(required=False,
                       type='str'),
            dest=dict(required=False,
                      type='str',
                      default=None),
            direct=dict(required=False,
                        type='int',
                        default=1,
                        choices=[0, 1]),
            executable=dict(required=False,
                            type='str'),
            name=dict(required=True,
                      type='str'),
            rw=dict(required=True,
                    type='str',
                    choices=['read', 'write', 'randread', 'randwrite',
                             'rw', 'readwrite', 'randrw']),
            size=dict(required=True,
                      type='str'),
            state=dict(type='str',
                       default="benchmark",
                       choices=['benchmark', 'parse']),
            timeout=dict(required=False,
                         type='int'),
            group_reporting=dict(required=False,
                                 type='bool',
                                 default=False),
            iodepth=dict(required=False,
                         type='int'),
            ioengine=dict(required=False,
                          type='str',
                          choices=['sync', 'psync', 'vsync', 'libaio',
                                   'posixaio', 'solarisaio', 'windowsaio',
                                   'mmap', 'splice', 'syslet-rw', 'sg',
                                   'null', 'net', 'netsplice', 'cpuio',
                                   'guasi', 'rdma', 'external', 'falloc',
                                   'e4defrag']),
            numjobs=dict(required=False,
                         type='int',
                         default=1),
            offset=dict(required=False,
                        type='int'),
            output_format=dict(required=False,
                               type='str',
                               choices=['terse', 'json', 'json+', 'normal']),
            sync=dict(required=False,
                      type='bool',
                      default=False),
            time_based=dict(required=False,
                            type='bool',
                            default=False),
            ramp_time=dict(required=False,
                           type='int'),
            runtime=dict(required=False,
                         type='int'),
            rwmixread=dict(required=False,
                           type='int'),
            rwmixwrite=dict(required=False,
                            type='int'),

        ),
        supports_check_mode=False
    )

    benchmark_bin = None
    result = {'changed': False}

    if module.params['state'] == 'benchmark':
        missing_params = list()
        for param in ['name', 'rw', 'bs', 'size']:
            if not module.params[param]:
                missing_params.append(param)
        if len(missing_params) > 0:
            module.fail_json(msg="missing required arguments: {}".format(missing_params))
        if module.params['executable']:
            benchmark_bin = module.get_bin_path('fio', True, [module.params['executable']])
        else:
            benchmark_bin = module.get_bin_path('fio', True, ['/usr/bin/local'])

        benchmark(module, result, benchmark_bin, module.params)
        
    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
main()
