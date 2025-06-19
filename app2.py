from flask import Flask, render_template, request, jsonify
import os
import re
from collections import defaultdict

app = Flask(__name__)

LOG_DIR = 'logs'  # Directory containing .log files

# Parses updated log format and extracts durations
def parse_log(log_content, log_filename):
    step_times = defaultdict(list)
    step_names = {}  # Dictionary to map step numbers to step names
    errors = []  # List to store error messages

    # Patterns to match different log entries
    step_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) - STEP (\d+): (.+)")
    starting_pattern = re.compile(r"Starting: (.+)")
    duration_pattern = re.compile(r"Completed in (\d+) seconds")
    error_pattern = re.compile(r"FAILED: (.+)")

    lines = log_content.splitlines()
    for line in lines:
        step_match = step_pattern.search(line)
        if step_match:
            date = step_match.group(1)
            time = step_match.group(2)
            step_number = step_match.group(3)
            details = step_match.group(4)

            # Extract step name from "Starting:" lines
            starting_match = starting_pattern.search(details)
            if starting_match:
                step_name = starting_match.group(1).strip()
                step_names[f"STEP {step_number}"] = step_name

            # Check if the line contains a duration
            duration_match = duration_pattern.search(details)
            if duration_match:
                duration = int(duration_match.group(1))
                step_times[f"STEP {step_number}"].append(duration)

            # Check if the line contains an error
            error_match = error_pattern.search(details)
            if error_match:
                error_message = error_match.group(1).strip()
                errors.append(f"{log_filename}|{step_number}|{error_message}|{date}|{time}")

    return step_times, step_names, errors

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/get_chart_data', methods=['POST'])
def get_chart_data():
    chart_type = request.json.get('chart_type')
    all_step_times = defaultdict(list)
    all_step_names = {}  # Collect step names from all logs
    all_errors = []  # Collect errors from all logs

    try:
        for filename in os.listdir(LOG_DIR):
            if filename.endswith('.log'):
                with open(os.path.join(LOG_DIR, filename), 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    step_times, step_names, errors = parse_log(log_content, filename)

                    for step, durations in step_times.items():
                        all_step_times[step].extend(durations)

                    all_step_names.update(step_names)
                    all_errors.extend(errors)

        if not all_step_times:
            return jsonify({
                'labels': [],
                'values': [],
                'errors': all_errors,  # Include errors even if no step data is found
                'chart_type': chart_type,
                'message': 'No valid step data found in the logs.'
            })

        # Compute average durations and match the label order
        steps = list(all_step_times.keys())
        avg_durations = [sum(all_step_times[step]) / len(all_step_times[step]) for step in steps]
        step_labels = [all_step_names.get(step, step) for step in steps]  # Use step names for labels

        return jsonify({
            'labels': step_labels,  # Use step names for the x-axis
            'values': avg_durations,
            'errors': all_errors,  # Include errors in the response
            'chart_type': chart_type,
            'message': 'Success'
        })

    except Exception as e:
        return jsonify({
            'labels': [],
            'values': [],
            'errors': [],
            'chart_type': chart_type,
            'message': f'Error reading logs: {str(e)}'
        })

if __name__ == '__main__':
    os.makedirs(LOG_DIR, exist_ok=True)
    app.run(debug=True)
