#! /usr/bin/env python
#
# Aggregates a series of TAP streams into a single stream using tap.py.
#
# Copyright 2015 Jacob Champion
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import subprocess
import sys
import tap.line
import tap.parser
import yamlish

TEST_SPEC = 'tests.yaml'

has_failures = False

def warn(msg):
    print("WARNING: {0}".format(msg), file=sys.stderr)

def error(msg):
    global has_failures
    print("ERROR: {0}".format(msg), file=sys.stderr)
    has_failures = True

#
# MAIN
#

# Open up the test specification. This contains the commands we should run.
with open(TEST_SPEC, 'r') as spec_file:
    spec = yamlish.load(spec_file)

print("TAP version 13")

parser = tap.parser.Parser()
test_number = 0

for cmd in spec['commands']:
    # Run each command in the shell and capture the output. Standard error is
    # piped directly to this script's stderr descriptor.
    p = subprocess.Popen(cmd,
                         shell=True,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=None)
    p.stdin.close()

    print("# << Begin stream for command `{0}`".format(cmd))

    stream_end = False
    stream_expected_tests = None
    stream_test_number = 0

    for line in p.stdout:
        # Parse each line of TAP.
        line = line.decode('utf-8').rstrip("\r\n")
        tap_line = parser.parse_line(line)
        category = tap_line.category

        if stream_end and category != 'diagnostic':
            error("Unexpected output found past the final test plan; bailing on the stream")
            break

        if category == 'test':
            # Test result.
            test_number += 1
            stream_test_number += 1

            # Check the test number.
            if (tap_line.number is not None) and (tap_line.number != stream_test_number):
                error("Expected test number {0} but stream is at test {1}".format(
                          stream_test_number,
                          tap_line.number
                      ))

            # Strip dashes and spaces from the beginning of the test
            # description; Result will add a dash separator on its own.
            description = tap_line.description.lstrip(" -")

            # Unfortunately lines without directives are given a non-None
            # Directive object by the Parser. Fix that here.
            directive = tap_line.directive
            directive = directive if directive.text else None

            # Print the result.
            result = tap.line.Result(tap_line.ok,
                                     number=test_number,
                                     description=description,
                                     directive=directive)
            print(result)

            # Keep track of failures.
            if not tap_line.ok and not tap_line.todo:
                has_failures = True

        elif category == 'version':
            if tap_line.version != 13:
                warn("stream declares TAP version other than 13; we might not process it correctly")

        elif category == 'bail':
            # Bail out!
            print(line)
            has_failures = True
            break

        elif category == 'plan':
            if stream_expected_tests is not None:
                error("Stream contains multiple test plans")

            stream_expected_tests = tap_line.expected_tests

            if not stream_test_number:
                # Test plan at the beginning of the file.
                if tap_line.skip or not stream_expected_tests:
                    print('# Skipping stream due to empty test plan')
                    break
            else:
                # Test plan at the end of the file.
                stream_end = True

        else:
            print(line)

    # Check that our plan matches the actual results.
    if stream_test_number != stream_expected_tests:
        error("stream expected {0} tests but we found {1}".format(
                  stream_expected_tests,
                  stream_test_number
              ))

    # Wait for the command to finish.
    p.wait()

    print("# >> End stream for command `{0}`".format(cmd))

# Print results and exit.
print("1..{0!s}".format(test_number))
print("#")
print("# test suite {0}".format('FAILED' if has_failures else 'PASSED'))
print("#")

exit(1 if has_failures else 0)
