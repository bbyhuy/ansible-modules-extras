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
module: multichase
short_description: Execute the Multichase benchmark
description:
 - Use this module to run the Multichase benchmark
options:
  delay:
    description:
     - piggybacks off the at module as a action plugin to run benchmark at a schedule time
    required: False
  state:
    description:
     - specify whether to run benchmark or parse output
    required: False
    default: benchmark
    choices: ["benchmark", "parse"]
  benchmark:
    description:
     - benchmark to run
    required: False
    choices: ["multichase", "pingpong", "fairness"]
    default: multichase
  memory:
    description:
     - used only for multichase, size of array that a pointer chase will be performed through
    required: False
  stride:
    description:
     - used only for multichase, size of stride that a pointer chase will be run with
    required: False
  threads:
    description:
     - used only for multichase, number of threads that we run the benchmark on
    required: False
  samples:
    description:
     - used only for multichase, number of 0.5 second samples
    required: False
  dest:
    description:
     - absolute path of file to write stdout to or where the output file to be parsed is
    required: False
  delay:
    description:
     - piggybacks off the at module as a action plugin to run benchmark at a schedule time
    required: False
requirements:
 - multichase
author: "Hugh Ma <Hugh.Ma@flextronics.com>"
        "Kwanho Ryu <Kwanho.Ryu@flextronics.com>"
'''

EXAMPLES = '''
# Run multichase that will perform a pointer chase through an array size of 200000 bytes
  with a stride size of 128 bytes on 1 thread where the number of 0.5 second samples is 3
  and write stdout to the absolute path specified in dest option.
- multichase:
    state: benchmark
    benchmark: multichase
    executable: /tmp/test/
    memory: 200000
    stride: 128
    threads: 1
    samples: 3
    dest: /tmp/test/multichase.out

# parse the output file stored in the path given in dest
- multichase:
    state: parse
    dest: /tmp/test/multichase.out

# Schedule fairness benchmark to execute in 10 minutes
- multichase:
    state: benchmark
    benchmark: fairness
    executable: /tmp/test/
    dest: /tmp/test/fairness.out
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
  sample: "/path/to/multichase ..."
'''


import os
import re
import tempfile
from commands import *
import fcntl, struct, sys


def benchmark(module, result, bin, params):

    benchmark   = params['benchmark']
    memory      = params['memory']
    stride      = params['stride']
    threads     = params['threads']
    samples     = params['samples']
    dest        = params['dest']

    # Changing directory to the one containing executable benchmark
    [path, bin] = bin.rsplit('/', 1)
    os.chdir(path)

    benchmark_command = "./{}".format(benchmark)

    if benchmark == "multichase":
        if memory:
            benchmark_command += " -m {}".format(memory)
        if stride:
            benchmark_command += " -s {}".format(stride)
        if threads:
            benchmark_command += " -t {}".format(threads)
        if samples:
            benchmark_command += " -n {}".format(samples)
        benchmark_command += " -v"
    elif benchmark == "pingpong":
        benchmark_command += " -u"

    if dest:
        benchmark_command += " > {}".format(dest)

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

# Parse only supports multichase benchmark
def parse(module, result, params):
    dest	= params['dest']

    if not os.path.exists(dest):
        module.fail_json(msg="{} does not exist".format(dest))

    f = open(dest, 'r')

    json_result = dict()

    counter = 0
    prev_line = ""
    curr_line = ""
    while True:
        prev_line = curr_line
        curr_line = f.readline()
        counter += 1
        if not curr_line:
            break
    json_result["Best Latency Time"]=prev_line

    if not json_result:
        module.fail_json(msg="Invalid result file at {}".format(dest))

    result['changed'] = True
    result['results'] = json.dumps(json_result)


def main():

    module = AnsibleModule(
        argument_spec = dict(
            chdir=dict(required=False,
                       default=None,
                       type='str'),
            state=dict(required=False,
                       choices=['benchmark', 'parse'],
                       default="benchmark",
                       type='str'),
            benchmark=dict(required=False,
                           choices=['multichase', 'pingpong', 'fairness'],
                           default='multichase',
                           type='str'),
            executable=dict(required=False,
                            type='str'),
            memory=dict(required=False,
                        type='str'),
            stride=dict(required=False,
                        type='str'),
            threads=dict(required=False,
                         type='str'),
            samples=dict(required=False,
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
        if module.params['executable']:
            benchmark_bin = module.get_bin_path(module.params['benchmark'], True, [module.params['executable']])
        else:
            benchmark_bin = module.get_bin_path(module.params['benchmark'], True, ['/usr/bin/local'])

        benchmark(module, result, benchmark_bin, module.params)

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
main()