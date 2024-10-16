import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ansi2html import Ansi2HTMLConverter
import pygments
from pygments import formatters, lexers
from pygments.util import ClassNotFound


class TestRunner:
    def __init__(self, submission_folder, exec_file="search.py", files=["search.py", "agent.py"]):
        self.submission_folder = Path(submission_folder) / "submission"
        self.files = files
        self.exec_file = exec_file
        self.conv = Ansi2HTMLConverter(inline=True)
        self.tabs = []

    def run_search(self, cmdline, state=None):
        command = ['python3', self.submission_folder / self.exec_file, cmdline]
        if state:
            command.append(state)

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

    def generate_tabs(self, commands):
        for i, (algo, state) in enumerate(commands):
            stdout, stderr = self.run_search(algo, state)
            stdout_truncated = self.truncate_output(stdout)
            stderr_truncated = self.truncate_output(stderr)

            tab = {
                'id': f'tab{i}',
                'title': f'{algo} {state if state else ""}'.strip(),
                'content': self.conv.convert(stdout_truncated, full=False),
                'error': stderr_truncated if stderr else None,
                'type': 'output'
            }
            self.tabs.append(tab)

        # Add tabs for code display
        for file in self.files:
            self.tabs.append({
                'id': f'code_{file}',
                'title': file,
                'content': self.get_formatted_code(self.submission_folder / file),
                'type': 'code'
            })

        return self.tabs


if __name__ == '__main__':
    submission_folder = './submission/search.py'
    agent_file_path = './submission/agent.py'

    commands = [
        ('bfs', None),
        ('dfs', '-|--|-OO|O--O|-OOOO'),
        ('a_star', 'O|OO|OOO|OOOO|OOOOO'),
        ('random', None)
    ]

    runner = TestRunner(submission_folder, agent_file_path)
    runner.generate_html_report(commands)
