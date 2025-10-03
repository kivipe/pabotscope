"""Libary for plotting pabot process usage"""
import re
import sys
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


def print_longest_tests(longest_tests, count=10):
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
    for name, duration in longest_tests[:count]:
        print(f"{name:<35} {duration:>12.2f}")
    print("-" * 50)


def load_log_file():
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
    if len(sys.argv) < 2:
        print("Usage: python yourscript.py <logfile>")
        sys.exit(1)

    log_path = sys.argv[1]
    with open(log_path, "r", encoding='utf-8') as file:
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


def main():
    """main function"""
    log_lines = load_log_file()
    starts, ends, durations = parse_log_lines(log_lines)
    timeline = build_timeline(starts, ends, durations)

    if timeline:
        time_cursor = timeline[0][0]
        end_time = timeline[-1][0]
        interval = timedelta(seconds=1)
        parallel_counts = []

        while time_cursor <= end_time:
            active = 0
            for test, s_time in starts.items():
                e_time = ends.get(
                    test, s_time + timedelta(seconds=durations.get(test, 0))
                )
                if s_time <= time_cursor < e_time:
                    active += 1
            parallel_counts.append((time_cursor, active))
            time_cursor += interval

        longest_tests = sorted(durations.items(), key=lambda x: -x[1])[:10]
        parallel_df = pd.DataFrame(
            parallel_counts, columns=["Timestamp", "ParallelTests"]
        )

        draw_ascii_chart_horizontal(parallel_df["ParallelTests"].tolist())
        print_longest_tests(longest_tests)


if __name__ == "__main__":
    main()
