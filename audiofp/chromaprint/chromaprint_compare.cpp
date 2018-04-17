#include <Python.h>
#include "fingerprint_matcher.h"

static PyObject *
chromaprint_compare_fingerprints(PyObject *self, PyObject *args) {
	PyObject *fp1_py_list, *fp2_py_list;
	Py_ssize_t fp1_size = 0, fp2_size = 0;

	if(!PyArg_ParseTuple(args, "OO", &fp1_py_list, &fp2_py_list))
	 	return NULL;

	 if ((fp1_size = PyList_Size(fp1_py_list)) <= 0 || (fp2_size = PyList_Size(fp2_py_list)) <= 0)
	 	return NULL; //TODO: Error


	std::vector<uint32_t> fp1_data(fp1_size);
	std::vector<uint32_t> fp2_data(fp2_size);


	auto fpm = new chromaprint::FingerprintMatcher();

	// uint32_t *fp1_data = new uint32_t[fp1_size];
	for (int i = 0; i < fp1_size; ++i) {
	 	fp1_data[i] = uint32_t(PyLong_AsUnsignedLong(PyList_GetItem(fp1_py_list, i)));
	}

	// uint32_t *fp2_data = new uint32_t[fp2_size];
	for (int i = 0; i < fp2_size; ++i) {
	 	fp2_data[i] = uint32_t(PyLong_AsUnsignedLong(PyList_GetItem(fp2_py_list, i)));
	}


	fpm->Match(fp1_data, fp2_data);

	PyObject *segment_list_py = PyList_New(0);

	for (chromaprint::Segment s : fpm->segments()) {
		PyObject *segment_dict_py = PyDict_New();

		PyDict_SetItemString(segment_dict_py, "duration", PyLong_FromUnsignedLong(s.duration));
		PyDict_SetItemString(segment_dict_py, "score", PyLong_FromLong(s.public_score()));

		PyList_Append(segment_list_py, segment_dict_py);
	}

	return segment_list_py;
}

static PyMethodDef module_methods[] = {
   	{"compare_fingerprints", chromaprint_compare_fingerprints, METH_VARARGS, "Compare two Chromaprint fingerprints."},
    {NULL, NULL, 0, NULL} 
};

static struct PyModuleDef chromaprint_compare = {
    PyModuleDef_HEAD_INIT,
    "chromaprint_compare",   /* name of module */
    NULL, /* module documentation, may be NULL */
    -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
    module_methods
};

PyMODINIT_FUNC PyInit_chromaprint_compare_c(void)
{
    return PyModule_Create(&chromaprint_compare);
}