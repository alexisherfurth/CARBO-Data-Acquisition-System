import subprocess
import os

# Access some information about the git repo this file is inside of

def _check_output(cmd):
	try:
		cwd = os.path.dirname(os.path.realpath(__file__))
		x = subprocess.check_output(cmd, cwd=cwd, shell=True, 
			timeout=0.1, stderr=subprocess.DEVNULL)
		x = x.decode().strip()
		assert 'fatal' not in x
	except:
		return 'Unknown'
	return x
	
def git_branch():
	return _check_output('git rev-parse --abbrev-ref HEAD')
	
def git_date():
	#~ return _check_output('git log -1 --pretty=format:%cI')
	return _check_output('git log -1 --pretty=format:%ci')
	
def git_commit():
	return _check_output('git rev-parse HEAD')
	#~ return _check_output('git rev-parse --short HEAD')

# Store the values at boot in case they change so we know the values
# for the code that is running
BOOT_GIT_BRANCH = git_branch()
BOOT_GIT_DATE = git_date()
BOOT_GIT_COMMIT = git_commit()

if __name__ == '__main__':
	input("Press enter to continue")
	print("--- Live Values ---")
	print("git branch: " + git_branch())
	print("git date: " + git_date())
	print("git commit: " + git_commit())
	print("--- Boot Values ---")
	print("git branch: " + BOOT_GIT_BRANCH)
	print("git date: " + BOOT_GIT_DATE)
	print("git commit: " + BOOT_GIT_COMMIT)
