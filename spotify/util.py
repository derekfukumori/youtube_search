import sys
import os
import contextlib

@contextlib.contextmanager
def nostdout():
	with open(os.devnull, 'w') as devnull:
		old_stdout = sys.stdout
		sys.stdout = devnull
		try: 
			yield
		finally:
			sys.stdout = old_stdout