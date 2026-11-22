import subprocess

script = """
import os, glob
print("Current dir:", os.getcwd())
for r, d, f in os.walk('/home/ubuntu/smc-ai-agent'):
    for file in f:
        if file.endswith('.db') or file.endswith('.json') or file.endswith('.log'):
            fp = os.path.join(r, file)
            print(fp, os.path.getsize(fp))
"""

cmd = [
    'ssh',
    '-i', r'C:\Users\power\.ssh\id_rsa_oracle',
    '-o', 'StrictHostKeyChecking=no',
    'ubuntu@130.210.4.45',
    'python3 -'
]
res = subprocess.run(cmd, input=script, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
