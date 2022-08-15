import types

noglobals = lambda fct: types.FunctionType(fct.__code__,
                                          {},
                                          argdefs=fct.__defaults__)
