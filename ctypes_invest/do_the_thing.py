import os
import platform

if "darwin" in platform.platform().lower() or "mac" in platform.platform().lower():
    libname = "libfib.dylib"
elif "win" in platform.platform().lower():
    libname = 'libfib.dll'
else:
    libname = "libfib.so"

fort_comp = "ifort"
c_comp = "gcc"

tags = ["dylib","so","a","dll","o","mod"]
del_files = [f for f in os.listdir(".") if f.split('.')[1] in tags]
for f in del_files:
    os.remove(f)

#os.system("{0} -c fib1.f90".format(fort_comp))
#os.system("{0} -fPIC -shared -o {1} fibby_int.c fib1.o".format(c_comp,libname))

os.system("{0} -shared -o {1} fib1.f90".format(fort_comp,libname))

from ctypes import CDLL, POINTER, c_int, c_double, byref
import numpy as np

fibby = CDLL(libname)
a = np.zeros(7)
b = a.copy() + 10
#fibby.c_fib.argtypes = [POINTER(c_double),POINTER(c_int)]
intvarptr = c_int(0)
out = np.zeros(7,dtype=np.int32)
fibby.c_fib(a.ctypes.data_as(POINTER(c_double)),c_int(7),byref(intvarptr),b.ctypes.data_as(POINTER(c_double)),out.ctypes.data_as(POINTER(c_int)))
print(out)
print(a,intvarptr.value)
print(b)



s1 = "stringy thing"
fibby.do_stringy_things(s1.encode(),a.ctypes.data_as(POINTER(c_double)))


