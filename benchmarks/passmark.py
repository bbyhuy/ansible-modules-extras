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
module: passmark
short_description: Execute the Passmark BurnInTest
description:
 - Use this module to run the Passmark BIT benchmark
 - http://www.passmark.com/products/bitlinux.htm
version_added: "2.1"
options:
  chdir:
    description:
     - change working directory
    required: false
    default: null
  cfg:
    description:
     - path to passmark burnintest cfg file
    required: true
  executable:
    description:
     - path to passmark burnintest executable if running from source
    required: false
  dest:
    description:
     - absolute path of file to write stdout to
    required: false
requirements:
 - passmark burnintest
author: "Hugh Ma <Hugh.Ma@flextronics.com>"
'''

EXAMPLES = '''
# Run Passmark BIT with the config.bitcfg file and write output to result.log
- passmark:
    cfg: /path/to/config.bitcfg
    executable: /path/to/bit_cmd_line_x64
    dest: /path/to/result.log
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
  sample: "/path/to/passmark ..."
'''

import os
import re
import tempfile


def benchmark(module, result, benchmark_bin, params):

    cfg         = params['cfg']
    chdir       = params['chdir']
    dest        = params['dest']


    if chdir:
        try:
            os.chdir(chdir)
            benchmark_bin = './bit_cmd_line_x64'
        except OSError as e:
            module.fail_json(msg=str(e))

    benchmark_command = None

    if dest:
        benchmark_command = "{} -C {} > {}"\
            .format(benchmark_bin, cfg, dest)
    else:
        benchmark_command = "{} -C {}"\
            .format(benchmark_bin, cfg)

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
    json_result['errors'] = list()

    reached = False
    serious = False
    errors = 0

    regex = re.compile('(\w+)')

    def pass_or_fail(dat):
        return "PASS" if "PASS" in dat else "FAIL"

    for line in data:
        if "RESULT SUMMARY" in line:
            reached = True
        if "SERIOUS ERROR SUMMARY" in line:
            serious = True
            reached = False
        if reached and "CPU" in line:
            splitted = re.findall(regex, line)
            json_result['cpu'] = (pass_or_fail(splitted))
        if reached and "Memory" in line:
            splitted = re.findall(regex, line)
            json_result['memory'] = (pass_or_fail(splitted))
        if reached and "Disk" in line:
            splitted = re.findall(regex, line)
            json_result['disk'] = (pass_or_fail(splitted))
        if reached and "Network" in line:
            splitted = re.findall(regex, line)
            json_result['network'] = (pass_or_fail(splitted))
        if serious and "SERIOUS:" in line:
            errors += 1
            json_result['errors'].append(line)

    if not json_result:
        module.fail_json(msg="Invalid result file at {}".format(dest))
    json_result['total_errors'] = errors

    result['changed'] = True
    result['results'] = json.dumps(json_result)


def main():

    module = AnsibleModule(
        argument_spec = dict(
            chdir=dict(required=False,
                       type='str'),
            cfg=dict(required=False,
                     type='str'),
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

    benchmark_bin = None
    result = {'changed': False}

    if module.params['state'] == 'parse':
        if not module.params['dest']:
            module.fail_json(msg='dest= is required for state=parse')
        parse(module, result, module.params)

    if module.params['state'] == 'benchmark':
        missing_params = list()
        for param in ['cfg']:
            if not module.params[param]:
                missing_params.append(param)
        if len(missing_params) > 0:
            module.fail_json(msg="missing required arguments: {}".format(missing_params))
        if module.params['executable']:
            benchmark_bin = module.get_bin_path('bit_cmd_line_x64', False, [module.params['executable']])
        else: 
            benchmark_bin = module.get_bin_path('bit_cmd_line_x64', False, ['/usr/bin/local'])

        benchmark(module, result, benchmark_bin, module.params)

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
main()
