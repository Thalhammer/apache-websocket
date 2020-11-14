#! /usr/bin/env python
#
# Presents the results of an Autobahn TestSuite run in TAP format.
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

from distutils.version import StrictVersion
import json
import os.path
import sys
import textwrap
import yamlish

def filter_report(report):
    """Filters a test report dict down to only the interesting keys."""

    INTERESTING_KEYS = [
        'behavior',
        'behaviorClose',
        'expected',
        'received',
        'expectedClose',
        'remoteCloseCode'
    ]

    return { key: report[key] for key in INTERESTING_KEYS }

def prepare_description(report):
    """Constructs a description from a test report."""
    raw = report['description']

    # Wrap to at most 80 characters.
    wrapped = textwrap.wrap(raw, 80)
    description = wrapped[0]

    if len(wrapped) > 1:
        # If the text is longer than one line, add an ellipsis.
        description += '...'

    return description

#
# MAIN
#

# Read the index.
results_dir = 'test-results'
with open(os.path.join(results_dir, 'index.json'), 'r') as index_file:
    index = json.load(index_file)['AutobahnPython']

# Sort the tests by numeric ID so we print them in a sane order.
test_ids = list(index.keys())
test_ids.sort(key=StrictVersion)

# Print the TAP header.
print('TAP version 13')
print('1..{0!s}'.format(len(test_ids)))

count = 0
skipped_count = 0
failed_count = 0

for test_id in test_ids:
    count += 1
    passed = True
    skipped = False
    report = None

    result = index[test_id]

    # Try to get additional information from this test's report file.
    try:
        path = os.path.join(results_dir, result['reportfile'])
        with open(path, 'r') as f:
            report = json.load(f)

        description = prepare_description(report)

    except Exception as e:
        description = '[could not load report file: {0!s}]'.format(e)

    test_result = result['behavior']
    close_result = result['behaviorClose']

    # Interpret the result for this test.
    if test_result != 'OK' and test_result != 'INFORMATIONAL':
        if test_result == 'UNIMPLEMENTED':
            skipped = True
        else:
            passed = False
    elif close_result != 'OK' and close_result != 'INFORMATIONAL':
        passed = False

    # Print the TAP result.
    print(u'{0} {1} - [{2}] {3}{4}'.format('ok' if passed else 'not ok',
                                           count,
                                           test_id,
                                           description,
                                           ' # SKIP unimplemented' if skipped
                                                                   else ''))

    # Print a YAMLish diagnostic for failed tests.
    if report and not passed:
        output = filter_report(report)
        diagnostic = yamlish.dumps(output)
        for line in diagnostic.splitlines():
            print('  ' + line)

    if not passed:
        failed_count += 1
    if skipped:
        skipped_count += 1

# Print a final result.
print('# Autobahn|TestSuite {0}'.format('PASSED' if not failed_count else 'FAILED'))
print('# total {0}'.format(count))
print('# passed {0}'.format(count - failed_count - skipped_count))
print('# skipped {0}'.format(skipped_count))
print('# failed {0}'.format(failed_count))

exit(0 if not failed_count else 1)
