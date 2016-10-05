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
module: iperf
short_description: Execute the iPerf3 benchmark
description:
 - Use this module to run the iPerf3 benchmark
 - http://software.es.net/iperf/
version_added: "2.1"
options:
  chdir:
    description:
     - change working directory
    required: False
    default: null
  mode:
    description:
     - Determines if target is acting as server or client
    required: True
  bind:
    description:
     - Address of interface to bind to
    required: False
  executable:
    description:
     - path to iperf3 executable if running from source
    required: False
  dest:
    description:
     - absolute path of file to write stdout to
    required: False
  interval:
    description:
     - Number of seconds to pause between each bandwidth report.
    required: False
  port:
    description:
     - Set the port to listen on
    required: False
    default: 5201
  udp:
    description:
     - use UDP instead of TCP
    required: False
  server:
    description:
     - hostname or ip address of the iperf server to connect to
    required: True
  verbose:
    description:
     - give more detailed output
    required: False
  timeout:
    description:
     - Total time to run iperf3 for.
    required: False
requirements:
 - iperf3
author: "Hugh Ma <Hugh.Ma@flextronics.com>"
'''

EXAMPLES = '''
# Start server daemon on target host
- iperf: mode=server

# Run iperf3 tcp on target host as client
- iperf: mode=client server=ubuntu_14

# Run iperf3 udp on target host as client with verbose
- iperf: mode=client server=target1 udp=True verbose=True
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
  sample: "/usr/bin/iperf3 -s"
'''

import os
import re
import tempfile


def benchmark(module, result, bin, params):

    mode        = params['mode']
    timeout     = params['timeout']
    bind        = params['bind']
    dest        = params['dest']
    interval    = params['interval']
    port        = params['port']
    udp         = params['udp']
    server      = params['server']
    verbose     = params['verbose']
    parallel_threads    = params['parallel_threads']
    tcp_window_size     = params['tcp_window_size']
    output_format       = params['output_format']


    benchmark_command = None

    if mode == 'server':
        benchmark_command = "{} -s -D" \
            .format(bin)
    else:
        benchmark_command = "{} -c {} -t {}"\
            .format(bin, server, timeout)

        if udp:
            benchmark_command += " --udp"
        if output_format:
            benchmark_command += " --json"
        if dest:
            benchmark_command += " --logfile {}".format(dest)
        if parallel_threads:
            benchmark_command += " --parallel {}".format(parallel_threads)
        if tcp_window_size:
            benchmark_command += " --window {}".format(tcp_window_size)

    if interval:
        benchmark_command += " --interval {}".format(interval)
    if port:
        benchmark_command += " --port {}".format(port)
    if bind:
        benchmark_command += " --bind {}".format(bind)
    if verbose:
        benchmark_command += " --verbose"

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

    dest        = params['dest']

    if not os.path.exists(dest):
        module.fail_json(msg="{} does not exist".format(dest))

    result_file = open(dest, 'r')
    data = result_file.readlines()
    result_file.close()

    json_result = dict()

    for line in data:
        if "hogs" in line:
            match = re.search('(\d+)\s+cpu,\s+(\d+)\s+io,\s+(\d+)\s+vm,\s+(\d+)\s+hdd', line)
            if match:
                json_result['cpu_hogs'] = match.group(1)
                json_result['io_hogs'] = match.group(2)
                json_result['vm_hogs'] = match.group(3)
                json_result['hdd_hogs'] = match.group(4)
        elif "successful" in line:
            match = re.search('completed\s+in\s+(\d+)', line)
            if match:
                json_result['completion_time'] = match.group(1)
    if not json_result:
        module.fail_json(msg="Invalid result file at {}: {}".format(dest, line))

    result['changed'] = True
    result['results'] = json.dumps(json_result)


def main():

    module = AnsibleModule(
        argument_spec = dict(
            chdir=dict(required=False,
                       type='str'),
            mode=dict(required=False,
                      type='str',
                      default="client",
                      choices=['server', 'client']),
            bind=dict(type='str',
                      required=False),
            dest=dict(required=False,
                      type='str',
                      default=None),
            executable=dict(required=False,
                            type='str'),
            format=dict(required=False,
                        type='str',
                        default='k',
                        choices=['k', 'm', 'K', 'M']),
            interval=dict(required=False,
                          type='int'),
            port=dict(required=False,
                      type=int),
            state=dict(type='str',
                       default="benchmark",
                       choices=['benchmark', 'parse']),
            server=dict(type='str',
                        required=False),
            output_format=dict(type='str',
                               required=False,
                               choices=['standard', 'json']),
            timeout=dict(required=False,
                         type='int',
                         default=10),
            udp=dict(required=False,
                     type='bool',
                     default=False),
            verbose=dict(required=False,
                         type='bool',
                         default=False),
            tcp_window_size=dict(required=False,
                                 type='str'),
            parallel_threads=dict(required=False,
                          type='int'),
        ),
        supports_check_mode=False
    )

    iperf_bin = None
    result = {'changed': False, 'bench_config': dict()}

    if module.params['state'] == 'parse':
        if not module.params['dest']:
            module.fail_json(msg='dest= is required for state=parse')
        parse(module, result, module.params)

    if module.params['state'] == 'benchmark':
        missing_params = list()

        if module.params['mode'] == 'client':
            for param in ['server']:
                if not module.params[param]:
                    missing_params.append(param)
        if len(missing_params) > 0:
            module.fail_json(msg="missing required arguments: {}".format(missing_params))
        if module.params['executable']:
            iperf_bin = module.params['executable']
        else:
            iperf_bin = module.get_bin_path('iperf3', True, ['/usr/bin/local'])

        benchmark(module, result, iperf_bin, module.params)

    for param in ['timeout', 'udp']:
        result['bench_config'][param] = module.params[param]

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
main()
