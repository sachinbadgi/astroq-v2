import subprocess
try:
    output = subprocess.check_output(['git', 'log', '--all', '--name-status', '--diff-filter=D'], text=True)
    for line in output.split('\n'):
        if line.startswith('D\t'):
            print(line)
except Exception as e:
    print(e)
