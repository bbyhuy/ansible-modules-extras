#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2016, Hugh Ma <Hugh.Ma@flextronics.com>
# Kwanho Ryu <Kwanho.Ryu@flextronics.com>
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
module: unixbench
short_description: Execute the Unixbench benchmark
description:
 - Use this module to run the Unixbench benchmark
options:
  delay:
    description:
     - piggybacks off the at module as a action plugin to run benchmark at a schedule time
    required: False
  state:
    description:
     - specify whether to run benchmark or parse output
    required: False
  executable:
    description:
     - path to unixbench executable if running from source 
    required: False
  count:
    description:
     - number of copies of each test in parallel
    required: True
  dest:
    description:
     - absolute path of file to write stdout to
    required: False
requirements:
 - unixbench
author: "Hugh Ma <Hugh.Ma@flextronics.com>"
        "Kwanho Ryu <Kwanho.Ryu@flextronics.com>"
'''

EXAMPLES = '''
# Run unixbench in the given absolute path with count 1 and write stdout to the dest.
- unixbench:
    state: benchmark
    executable: /tmp/test/byte-unixbench-master/UnixBench/
    count: 1
    dest: /tmp/test/ansible_Unixbench.out

# Schedule parsing the file in the given path to execute in 10 minutes
    state: parse
    dest: /tmp/test/ansible_Unixbench.out
    delay: 10
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
  sample: "/path/to/unixbench ..."
'''

import os
import re
import tempfile
from commands import *
import fcntl, struct, sys


def benchmark(module, result, bin, params):

    count   = params['count']
    dest    = params['dest']

    # Changing directory to the one containing executable benchmark
    [path, bin] = bin.rsplit('/', 1)
    os.chdir(path)

    if dest:
        benchmark_command = "./{} -c {} > {}".format(bin, count, dest)
    else:
        benchmark_command = "./{} -c {}".format(bin, count)

    rc, out, err = module.run_command(benchmark_command,
                                      use_unsafe_shell=True,
                                      check_rc=True)

    if dest:
        out += "; Output located on targeted hosts at: {}".format(dest)

    result['changed'] 	= True
    result['exec_cmd']  = benchmark_command
    result['stdout'] 	= out.rstrip("\r\n")
    result['stderr'] 	= err.rstrip("\r\n")
    result['rc'] 	= rc


def parse(module, result, params):
    dest = params['dest']

    if not os.path.exists(dest):
        module.fail_json(msg="{} does not exist".format(dest))

    result_file = open(dest, 'r')
    data = result_file.read()
    data = data.strip()
    data = data.splitlines()
    result_file.close()

    json_result = dict()

    for line in data:
        if 'BASELINE' in line:
            idx = data.index(line)
    data = data[(idx + 1):]
    data = [x for x in data if '========' not in x]

    json_result = dict()
    for x in data:
        rez = x.split(' ')
        rez = filter(None, rez)
        index = rez.pop()
        if 'Index Score' not in x:
            rez.pop()
            rez.pop()
        json_result[' '.join(rez)] = index

    if not json_result:
        module.fail_json(msg="Invalid result file at {}: {}".format(dest, line))

    result['changed'] = True
    result['results'] = json.dumps(json_result)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            chdir=dict(required=False,
                       default=None,
                       type='str'),
            state=dict(required=False,
                       choices=['benchmark', 'parse'],
                       default="benchmark",
                       type='str'),
            executable=dict(required=False,
                            type='str'),
            count=dict(required=True,
                       type='str'),
            dest=dict(required=False,
                      type='str'),
        ),
        supports_check_mode=False
    )

    benchmark_bin = None
    result = {'changed': False}

    if module.params['state'] == 'parse':
        if not module.params['dest']:
            module.fail_json(msg='dest= is required for state=parse')
        parse(module, result, module.params)

    if module.params['state'] == 'benchmark':
        missing_params = list()
        for param in ['count']:
            if not module.params[param]:
                missing_params.append(param)
        if len(missing_params) > 0:
            module.fail_json(msg="missing required arguments: {}".format(missing_params))
        if module.params['executable']:
            benchmark_bin = module.get_bin_path('Run', True, [module.params['executable']])
        else:
            benchmark_bin = module.get_bin_path('Run', True, ['/usr/bin/local'])

        benchmark(module, result, benchmark_bin, module.params)

    module.exit_json(**result)


# import module snippets
from ansible.module_utils.basic import *

main()
