from distutils.core import setup, Extension
import sys

extra_compile_args = []
if sys.platform.startswith('darwin'):
	extra_compile_args = ['-std=c++11', '-stdlib=libc++', '-mmacosx-version-min=10.9']
elif sys.platform.startswith('linux'):
	extra_compile_args = ['-std=c++11']

chromaprint_ext = Extension('chromaprint_compare_c',
                    sources = ['audiofp/chromaprint/chromaprint_compare.cpp', 'audiofp/chromaprint/include/fingerprint_matcher.cpp'],
                    include_dirs = ['audiofp/chromaprint/include'],
                    extra_compile_args=extra_compile_args)

setup (name = 'youtube_search',
       version = '0.0.1',
       description = 'Something',
       ext_modules = [chromaprint_ext])
