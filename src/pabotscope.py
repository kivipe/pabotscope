"""Libary for plotting pabot process usage"""

import argparse
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def downsample_to_width(parallel_counts, max_height, max_width):
    """
    Downsamples the input list of counts to a specified maximum width and
    scales the values to a maximum height.

    Parameters:
    parallel_counts (list): A list of counts to be downsampled and scaled.
    max_height (int): The maximum height for scaling the counts.
    max_width (int): The maximum width for downsampling the counts.

    Returns:
    list: A list of scaled counts.

    Raises:
    ValueError: If max_width is less than 1.
    """
    if len(parallel_counts) > max_width:
        indices = np.linspace(0, len(parallel_counts) - 1, max_width, dtype=int)
        data = [parallel_counts[i] for i in indices]
    else:
        data = parallel_counts

    max_value = max(data) or 1
    scaled = [int((count / max_value) * max_height) for count in data]
    return scaled


def draw_ascii_chart_horizontal(
    parallel_counts, max_height=10, max_width=80, block="▓"
):
    """
    Draws a horizontal ASCII chart based on the provided counts.

    Parameters:
    parallel_counts (list): A list of counts to visualize.
    max_height (int): The maximum height of the chart (default is 10).
    max_width (int): The maximum width of the chart (default is 80).
    block (str): The character used to represent the blocks in the chart (default is "▓").

    Returns:
    None

    Raises:
    ValueError: If parallel_counts is empty.
    """
    if not parallel_counts:
        print("No data.")
        return
    scaled = downsample_to_width(parallel_counts, max_height, max_width)

    lines = []
    for level in range(max_height, 0, -1):
        line = "".join(block if height >= level else " " for height in scaled)
        lines.append(line.rstrip())

    for line in lines:
        print(line)


def print_longest_tests(longest_tests):
    """
    Prints the top longest running tests with their durations.

    Parameters:
    longest_tests (list of tuples): A list containing tuples of test names and their durations.
    count (int): The number of longest tests to display (default is 10).

    Returns:
    None

    Exceptions:
    None
    """
    print("\nTop Longest Running Tests:")
    print("-" * 50)
    print(f"{'Test Name':<35} {'Duration (s)':>12}")
    print("-" * 50)
    for name, duration in longest_tests:
        print(f"{name:<35} {duration:>12.2f}")
    print("-" * 50)


def load_log_file(log_path):
    """
    Loads a log file specified as a command-line argument and returns its
    contents as a list of lines.

    Parameters:
    None

    Returns:
    list: A list of strings, each representing a line from the log file.

    Raises:
    SystemExit: If no log file is provided as an argument.
    """
    with open(log_path, "r", encoding="utf-8") as file:
        log_lines = file.readlines()
    return log_lines


def parse_log_lines(log_lines):
    """
    Parses log lines to extract timestamps and durations of executed tests.

    Parameters:
    log_lines (iterable): An iterable containing log lines as strings.

    Returns:
    tuple: A tuple containing three dictionaries - starts, ends, and durations of tests.

    Raises:
    ValueError: If the timestamp format in the log lines is incorrect.
    """
    executing_re = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+).*?EXECUTING (?P<test>.+)"
    )
    passed_re = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+).*?PASSED "
        r"(?P<test>.+?) in (?P<duration>[\d.]+) seconds"
    )

    starts = {}
    ends = {}
    durations = {}

    for line in log_lines:
        exec_match = executing_re.search(line)
        if exec_match:
            ts = datetime.strptime(exec_match["timestamp"], "%Y-%m-%d %H:%M:%S.%f")
            test = exec_match["test"]
            starts[test] = ts
            continue
        pass_match = passed_re.search(line)
        if pass_match:
            ts = datetime.strptime(pass_match["timestamp"], "%Y-%m-%d %H:%M:%S.%f")
            test = pass_match["test"]
            dur = float(pass_match["duration"])
            ends[test] = ts
            durations[test] = dur
    return starts, ends, durations


def parse_status_times(status):
    """
    Reads start time and duration from a Robot Framework status element.

    Parameters:
    status (Element): A <status> element from output.xml.

    Returns:
    tuple: A tuple containing start time (datetime) and duration in seconds (float),
    or (None, None) if the element has no timing information.

    Raises:
    ValueError: If the timestamp format is incorrect.
    """
    # Robot Framework 7+ format: start="2025-10-03T13:20:05.472000" elapsed="1.002000"
    if status.get("start") is not None:
        start = datetime.fromisoformat(status.get("start"))
        return start, float(status.get("elapsed", 0))
    # Robot Framework < 7 format: starttime="20251003 13:20:05.472" endtime="..."
    starttime = status.get("starttime")
    endtime = status.get("endtime")
    if starttime and starttime != "N/A" and endtime and endtime != "N/A":
        start = datetime.strptime(starttime, "%Y%m%d %H:%M:%S.%f")
        end = datetime.strptime(endtime, "%Y%m%d %H:%M:%S.%f")
        return start, (end - start).total_seconds()
    return None, None


def parse_output_xml(xml_path):
    """
    Parses Robot Framework output.xml to extract start times, end times and
    durations of the suites executed by pabot. Pabot runs each lowest level
    suite in its own process, so only suites without child suites are
    included.

    Parameters:
    xml_path (str): Path to output.xml file.

    Returns:
    tuple: A tuple containing three dictionaries - starts, ends, and durations of suites.

    Raises:
    xml.etree.ElementTree.ParseError: If the file is not valid XML.
    """
    root = ET.parse(xml_path).getroot()

    starts = {}
    ends = {}
    durations = {}

    def visit(suite, parent_name):
        name = suite.get("name")
        full_name = f"{parent_name}.{name}" if parent_name else name
        children = suite.findall("suite")
        if children:
            for child in children:
                visit(child, full_name)
            return
        status = suite.find("status")
        if status is None:
            return
        start, duration = parse_status_times(status)
        if start is None:
            return
        starts[full_name] = start
        ends[full_name] = start + timedelta(seconds=duration)
        durations[full_name] = duration

    for suite in root.findall("suite"):
        visit(suite, "")
    return starts, ends, durations


def build_timeline(starts, ends, durations):
    """
    Constructs a timeline of test events based on their start and end times.

    Parameters:
    starts (dict): A dictionary mapping test names to their start times.
    ends (dict): A dictionary mapping test names to their end times.
    durations (dict): A dictionary mapping test names to their durations in seconds.

    Returns:
    list: A sorted list of tuples containing (time, event_type, test_name).

    Raises:
    KeyError: If a test name is not found in the starts, ends, or durations dictionaries.
    """
    timeline = []
    for test, start_time in starts.items():
        end_time = ends.get(
            test, start_time + timedelta(seconds=durations.get(test, 0))
        )
        timeline.append((start_time, "start", test))
        timeline.append((end_time, "end", test))
    timeline.sort()
    return timeline


def parse_args():
    """
    Parse command line arguments.

    Parameters:

    Returns:
    args: dictionary of command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Plot pabot process usage and show longest tests"
    )
    parser.add_argument(
        "-c", "--count", help="Number of longest tests to display", type=int, default=0
    )

    parser.add_argument(
        "-t",
        "--text",
        help="Read pabot text output instead of output.xml",
        action="store_true",
    )

    parser.add_argument(
        "logfile",
        help="Path to output.xml (default: output.xml) or pabot text output when --text is used",
        nargs="?",
        default="output.xml",
    )

    args = parser.parse_args()
    return args


def load_results(arguments):
    """
    Loads test start times, end times and durations from the input file.

    Parameters:
    arguments (Namespace): Parsed command line arguments.

    Returns:
    tuple: A tuple containing three dictionaries - starts, ends, and durations of tests.
    """
    if arguments.text:
        log_lines = load_log_file(arguments.logfile)
        return parse_log_lines(log_lines)
    return parse_output_xml(arguments.logfile)


def count_parallel_tests(timeline, starts, ends, durations):
    """
    Counts how many tests are running in parallel at one second intervals.

    Parameters:
    timeline (list): A sorted list of tuples containing (time, event_type, test_name).
    starts (dict): A dictionary mapping test names to their start times.
    ends (dict): A dictionary mapping test names to their end times.
    durations (dict): A dictionary mapping test names to their durations in seconds.

    Returns:
    list: A list of parallel test counts, one per second.
    """
    time_cursor = timeline[0][0]
    end_time = timeline[-1][0]
    interval = timedelta(seconds=1)
    parallel_counts = []

    while time_cursor <= end_time:
        active = 0
        for test, s_time in starts.items():
            e_time = ends.get(test, s_time + timedelta(seconds=durations.get(test, 0)))
            if s_time <= time_cursor < e_time:
                active += 1
        parallel_counts.append((time_cursor, active))
        time_cursor += interval

    parallel_df = pd.DataFrame(parallel_counts, columns=["Timestamp", "ParallelTests"])
    return parallel_df["ParallelTests"].tolist()


def get_longest_tests(durations, count):
    """
    Returns tests sorted by duration, longest first.

    Parameters:
    durations (dict): A dictionary mapping test names to their durations in seconds.
    count (int): The number of tests to return, 0 for all.

    Returns:
    list: A list of (test_name, duration) tuples.
    """
    longest_tests = sorted(durations.items(), key=lambda x: -x[1])
    if count != 0:
        longest_tests = longest_tests[:count]
    return longest_tests


def main():
    """main function"""
    arguments = parse_args()
    starts, ends, durations = load_results(arguments)
    timeline = build_timeline(starts, ends, durations)

    if timeline:
        draw_ascii_chart_horizontal(
            count_parallel_tests(timeline, starts, ends, durations)
        )
        print_longest_tests(get_longest_tests(durations, arguments.count))


if __name__ == "__main__":
    main()
