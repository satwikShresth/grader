import subprocess
from pathlib import Path
from ansi2html import Ansi2HTMLConverter
import pygments
from pygments import formatters, lexers
from pygments.util import ClassNotFound
import logging

logger = logging.getLogger('uvicorn.error')


class TestRunner:
    def __init__(self, submission_folder, files):
        self.submission_folder = Path(submission_folder, "submission")
        self.files = files
        self.conv = Ansi2HTMLConverter(inline=True)
        self.tabs = []

    def run_script(self, script_name, *args):
        command = ['python3', str(
            self.submission_folder / script_name)] + list(args)
        logger.info(f"Executing command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        return result.stdout, result.stderr

    def truncate_output(self, output, num_lines=100):
        lines = output.splitlines()
        if len(lines) > num_lines:
            return '\n'.join(lines[-num_lines:])
        return output

    def get_formatted_code(self, filepath):
        try:
            with open(filepath, 'r') as file:
                code = file.read()
            lexer = lexers.get_lexer_by_name("python")
            formatter = formatters.HtmlFormatter(
                style='monokai',
                noclasses=True,
                cssstyles='font-size: 16px; line-height: 1.5em;'
            )
            return pygments.highlight(code, lexer, formatter)
        except (FileNotFoundError, ClassNotFound):
            return f"<p>File {filepath} not found or could not be processed.</p>"

    def generate_tabs(self, test_cases):
        def process_test_cases(command_args, test_cases, expected_output=None):
            if isinstance(test_cases, dict):
                for key, value in test_cases.items():
                    if isinstance(value, (list, dict)):
                        new_command_args = command_args + [key]
                        process_test_cases(new_command_args, value)
                    elif isinstance(value, str):
                        new_command_args = command_args + [key]
                        expected = value
                        script_name = new_command_args[0]
                        args = new_command_args[1:]

                        # Extract file_name, function_name, and test_case
                        file_name = script_name
                        function_name = args[0] if len(args) > 0 else ''
                        test_case = args[1] if len(args) > 1 else ''

                        logger.info(f"Running script: {
                                    script_name} with args: {args}")
                        stdout, stderr = self.run_script(script_name, *args)
                        stdout_truncated = self.truncate_output(stdout)
                        stderr_truncated = self.truncate_output(stderr)

                        # Construct a valid HTML ID
                        tab_id = f"tab_{script_name}_{'_'.join(args)}".replace(
                            '/', '_').replace(' ', '_')

                        tab = {
                            'id': tab_id,
                            'title': f"{script_name} {' '.join(args)}",
                            'content': self.conv.convert(stdout_truncated, full=False),
                            'error': stderr_truncated if stderr else None,
                            'expected': expected,
                            'command': ' '.join(['python3', script_name] + args),
                            'type': 'output',
                            'file_name': file_name,
                            'function_name': function_name,
                            'test_case': test_case
                        }
                        self.tabs.append(tab)
            else:
                logger.warning(f"Unexpected test case format: {test_cases}")

        self.tabs = []
        for file, arguments in test_cases.items():
            logger.info(f"Processing test cases for file: {file}")
            process_test_cases([file], arguments)

        for file in self.files:
            self.tabs.append({
                'id': f'code_{file}',
                'title': file,
                'content': self.get_formatted_code(self.submission_folder / file),
                'type': 'code'
            })

        return self.tabs

