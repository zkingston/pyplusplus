# Copyright 2004 Roman Yakovenko.
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)

import os
import types
import algorithm 
import code_creator
import declaration_based
from pygccxml import declarations

class indexing_suite1_t( declaration_based.declaration_based_t ):
    def __init__(self, container, parent=None ):        
        declaration_based.declaration_based_t.__init__( self, declaration=container, parent=parent )
            
    def _get_configuration( self ):
        return self.declaration.indexing_suite
    configuration = property( _get_configuration )

    def _get_container( self ):
        return self.declaration 
    container = property( _get_container )

    def guess_suite_name( self ):
        if self.container.name.startswith( 'vector' ):
            return 'boost::python::vector_indexing_suite'
        else:
            return 'boost::python::map_indexing_suite'

    def _create_suite_declaration( self ):
        suite_identifier = algorithm.create_identifier( self, self.guess_suite_name() )
        args = [ self.container.decl_string ]
        if self.configuration.derived_policies:
            if self.configuration.no_proxy:
                args.append( 'true' )
            else:
                args.append( 'false' )
            args.append( self.configuration.derived_policies )
        else:
            if self.configuration.no_proxy:
                args.append( 'true' )        
        return declarations.templates.join( suite_identifier, args )        

    def _create_impl(self):
        return "def( %s() )" %  self._create_suite_declaration()
    

class indexing_suite2_t( declaration_based.declaration_based_t ):
    def __init__(self, container, parent=None ):        
        declaration_based.declaration_based_t.__init__( self, declaration=container, parent=parent )
        self.__method_mask_var_name = "methods_mask"
        self.works_on_instance = not self.does_user_disable_methods()
        
    def does_user_disable_methods( self ):
        return bool( self.declaration.indexing_suite.disabled_methods_groups ) \
               or bool( self.declaration.indexing_suite.disable_methods )

    def generate_algorithm_mask( self ):
        indexing = algorithm.create_identifier(self, "::boost::python::indexing" )
        disable = []
        for group in self.declaration.indexing_suite.disabled_methods_groups:
            group_id = algorithm.create_identifier(self, "::boost::python::indexing::%s_methods" % group )
            disable.append( group_id )
        for method in self.declaration.indexing_suite.disable_methods:
            method_id = algorithm.create_identifier(self, "::boost::python::indexing::method_" + method )
            disable.append( method_id )
        answer = [ 'unsigned long const %s = ' % self.__method_mask_var_name ]
        answer.append( algorithm.create_identifier(self, "::boost::python::indexing::all_methods" ) )
        answer.append( ' & ~' )
        if 1 == len ( disable ):
            answer.append( disable[0] )
        else:
            answer.append( '( ' )
            answer.append( ' |  '.join( disable ) )
            answer.append( ' ) ' )
        answer.append( ';' )
        return ''.join( answer )
        
    def _create_impl( self ):
        answer = []
        if self.does_user_disable_methods():
            answer.append( self.generate_algorithm_mask() )
            answer.append( os.linesep )
        if not self.works_on_instance:
            answer.append( '%s.def( ' % self.parent.class_var_name)
        else:
            answer.append( 'def( ' )
        answer.append( algorithm.create_identifier(self, "::boost::python::indexing::container_suite" ) )
        answer.append( '< ' )
        answer.append( self.decl_identifier )
        if self.does_user_disable_methods():
            answer.append( self.PARAM_SEPARATOR )
            answer.append( self.__method_mask_var_name )
        answer.append( ' >' )
        if self.declaration.indexing_suite.call_policies:
            answer.append( '::with_policies(%s)' 
                           % self.declaration.indexing_suite.call_policies.create( self )  )
        else:
            answer.append( '()' )
        answer.append( ' )' )
        if not self.works_on_instance:
            answer.append( ';' )
        return ''.join( answer )

class value_traits_t( declaration_based.declaration_based_t ):
    def __init__( self, value_class, parent=None ):
        declaration_based.declaration_based_t.__init__( self, declaration=value_class, parent=parent )

    def generate_value_traits( self ):
        tmpl = os.linesep.join([
              "namespace boost { namespace python { namespace indexing {"
            , ""
            , "template<>"
            , "struct value_traits<%(value_class)s>{"
            , ""
            , self.indent( "static bool const equality_comparable = %(has_equal)s;" )
            , self.indent( "static bool const less_than_comparable = %(has_lessthan)s;" )
            , ""
            , self.indent( "template<typename PythonClass, typename Policy>" )
            , self.indent( "static void visit_container_class(PythonClass &, Policy const &){" )    
            , self.indent( "%(visitor_helper_body)s", 2 )
            , self.indent( "}" )
            , ""
            , "};"
            , ""
            , "}/*indexing*/ } /*python*/ } /*boost*/"
        ])

        return tmpl % { 'value_class' : self.decl_identifier
                        , 'has_equal' : str( bool( self.declaration.equality_comparable ) ) .lower()
                        , 'has_lessthan' : str( bool( self.declaration.less_than_comparable ) ).lower()
                        , 'visitor_helper_body' : '' }

    def generate_value_class_fwd_declaration( self ):
        pass # for inner class this code will generate error :-((((
    
    def _create_impl( self ):
        return self.generate_value_traits()














