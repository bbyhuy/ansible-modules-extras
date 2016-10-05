#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2016, Hugh Ma <Hugh.Ma@flextronics.com>
# Shanthini Velan <Shanthini.Velan@flextronics.com>
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
module: scimark2
short_description: Execute the Scimark 2.0 benchmark
description:
 - Use this module to run the Scimark 2.0 benchmark
 - http://math.nist.gov/scimark2
version_added: "2.1"
options:
  chdir:
    description:
     - change working directory
    required: false
    default: null
  delay:
    description:
     - piggybacks off the at module as a action plugin to run benchmark at a schedule time
    required: false
  executable:
    description:
     - path to scimark2 executable if running from source
    required: true
  dest:
    description:
     - absolute path of file to write stdout to
    required: false
  state:
    description:
     - specify whether to run benchmark or parse output
    required: false
requirements:
 - scimark2
author: "Hugh Ma <Hugh.Ma@flextronics.com>"
'''

EXAMPLES = '''
# Run scimark2 executable located at /home/scimark
- scimark: executable=/home/scimark

# Run scimark2 executable located at /home/scimark and output results to /tmp/scimark2.out
- scimark2: executable=/home/scimark dest=/tmp/scimark2.out

# Schedule scimark2 to execute in 10 minutes
- scimark2: executable=/home/scimark delay=10
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
  sample: "/path/to/scimark2 ..."
'''

import os
import re
import tempfile


def benchmark(module, result, bin, params):

    dest        = params['dest']

    # Changing directory to the one containing executable benchmark
    os.chdir(params['executable'])

    benchmark_command = None

    if dest:
        benchmark_command = "{} > {}"\
            .format(bin, dest)
    else:
        benchmark_command = "{} "\
            .format(bin)

    rc, out, err = module.run_command(benchmark_command,
                                      use_unsafe_shell=True,
                                      check_rc=True)

    if dest:
        out += "; Output located on targeted hosts at: {}".format(dest)

    result['changed']   = True
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
        if "Mflops" in line:
            match = re.search('Mflops:\s+(\d+)', line)
            if match:
                if "FFT" in line:
                    json_result['FFT'] = match.group(1)
                elif "SOR" in line:
                    json_result['SOR'] = match.group(1)
                elif "MonteCarlo" in line:
                    json_result['MonteCarlo'] = match.group(1)
                elif "Sparse"in line:
                    json_result['Sparse_Matrix_Mult'] = match.group(1)
                elif "LU" in line:
                    json_result['Dense_LU'] = match.group(1)
        elif "Composite" in line:
            match = re.search('Score:\s+(\d+)', line)
            if match:
                json_result['composite_score'] = match.group(1)
    if not json_result:
        module.fail_json(msg="Invalid result file at {}: {}".format(dest, line))

    result['changed'] = True
    result['results'] = json.dumps(json_result)


def main():

    module = AnsibleModule(
        argument_spec = dict(
            chdir=dict(required=False,
                       type='str'),
            delay=dict(required=False,
                       type='int'),
            dest=dict(required=False,
                      type='str',
                      default=None),
            executable=dict(required=False,
                            type='str'),
            state=dict(type='str',
                       default="benchmark",
                       choices=['benchmark', 'parse']),

        ),
        supports_check_mode=False
    )

    result = {'changed': False}
    benchmark_bin=None

    if module.params['state'] == 'parse':
        if not module.params['dest']:
            module.fail_json(msg='dest= is required for state=parse')
        parse(module, result, module.params)
    
    if module.params['state'] == 'benchmark':
        if not module.params['executable']:
            module.fail_json(msg='executable= is required for state=benchmark')
            benchmark(module, result, benchmark_bin, module.params)
        else:
            benchmark_bin = module.get_bin_path('scimark2', True, [module.params['executable']])
            benchmark(module, result, benchmark_bin, module.params)

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
main()
