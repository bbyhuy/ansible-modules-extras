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
module: mprime
short_description: Execute the mPrime torture benchmark
description:
 - Use this module to run the mPrime benchmark
 - http://www.mersenne.org/download/
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
     - path to mprime executable if running from source
    required: false
  dest:
    description:
     - absolute path of file to write stdout to
    required: false
  timeout:
    description:
     - Total time to run mprime for.
    required: true
  unit:
    description:
     - Unit of time for timeout(s = seconds, m = minutes, h = hours, d = day)
    required: false
    default: s
requirements:
 - mprime
author: "Hugh Ma <Hugh.Ma@flextronics.com>"
'''

EXAMPLES = '''
# Run mprime for 60 seconds
- mprime: timeout=60 unit=s

# Run mprime for 60 seconds output results to /tmp/mprime.out
- mprime: timeout=60 unit=s dest=/tmp/mprime.out

# Parse mprime result from file
- mprime: state=parse dest=/tmp/mprime.out
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
  sample: "/path/to/mprime ..."
'''

import os
import re
import tempfile


def benchmark(module, result, bin, params):

    timeout     = params['timeout']
    unit        = params['unit']
    dest        = params['dest']

    benchmark_command = None

    if dest:
        benchmark_command = "timeout --preserve-status -s SIGINT {1}{2} {0} -t > {3}"\
            .format(bin, timeout, unit, dest)
    else:
        benchmark_command = "timeout --preserve-status -s SIGINT {1}{2} {0} -t"\
            .format(bin, timeout, unit)

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
    data = result_file.read()
    result_file.close()

    json_result = dict()

    regex = re.compile('\w* completed (\d*) .*? - (\d*) \w*, (\d*) \w*')
    data = re.findall(regex, data)

    json_result['total_tests'] = 0
    json_result['total_errors'] = 0
    json_result['total_warnings'] = 0

    for tup in data:
        json_result['total_tests'] += int(tup[0])
        json_result['total_errors'] += int(tup[1])
        json_result['total_warnings'] += int(tup[2])

    if not json_result:
        module.fail_json(msg="Invalid result file at {}".format(dest))

    result['changed'] = True
    result['results'] = json.dumps(json_result)


def main():

    module = AnsibleModule(
        argument_spec = dict(
            chdir=dict(required=False,
                       type='str'),
            dest=dict(required=False,
                      type='str',
                      default=None),
            executable=dict(required=False,
                            type='str'),
            state=dict(type='str',
                       default="benchmark",
                       choices=['benchmark', 'parse']),
            timeout=dict(required=False,
                         type='int'),
            unit=dict(required=False,
                      type='str',
                      default='s',
                      choices=['s', 'm', 'h', 'd']),

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
        for param in ['timeout']:
            if not module.params[param]:
                missing_params.append(param)
        if len(missing_params) > 0:
            module.fail_json(msg="missing required arguments: {}".format(missing_params))
        if module.params['executable']:
            benchmark_bin = module.get_bin_path('mprime', True, [module.params['executable']])
        else:
            benchmark_bin = module.get_bin_path('mprime', True, ['/usr/bin/local'])

        benchmark(module, result, benchmark_bin, module.params)

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
main()
