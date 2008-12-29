# Copyright 2004-2008 Roman Yakovenko.
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)

import os
import compound
import declaration_based
from pygccxml import declarations

class methods_definition_t(compound.compound_t, declaration_based.declaration_based_t):
    def __init__( self, class_ ):
        compound.compound_t.__init__(self)
        declaration_based.declaration_based_t.__init__( self, class_ )

    @property
    def mem_fun_factory_var_name(self):
        return "mfcreator"

    def _create_impl(self):
        result = []
        scope = declarations.algorithm.declaration_path( self.declaration )
        del scope[0] #del :: from the global namespace
        del scope[-1] #del self from the list

        result.append( '%(mem_fun_factory_var_name)s = ctypes_utils.mem_fun_factory( %(library_var_name)s, %(complete_py_name)s, "%(class_name)s", "%(ns)s" )'
                       % dict( mem_fun_factory_var_name=self.mem_fun_factory_var_name
                               , library_var_name=self.top_parent.library_var_name
                               , complete_py_name=self.complete_py_name
                               , class_name=self.declaration.name
                               , ns='::'.join(scope) ) )
        result.append( '%(complete_py_name)s._methods_ = { #class non-virtual member functions definition list'
                       % dict( complete_py_name=self.complete_py_name ) )
        result.append( compound.compound_t.create_internal_code( self.creators ) )
        result.append( '}' )
        result.append( 'del %s' % self.mem_fun_factory_var_name )
        return os.linesep.join( result )

    def _get_system_headers_impl( self ):
        return []
