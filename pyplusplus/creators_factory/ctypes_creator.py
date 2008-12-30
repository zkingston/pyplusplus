# Copyright 2004-2008 Roman Yakovenko.
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)

import sort_algorithms
import dependencies_manager
from pygccxml import msvc
from pyplusplus import _logging_
from pygccxml import declarations
from pyplusplus import decl_wrappers
from pyplusplus import code_creators
from pyplusplus import code_repository

ACCESS_TYPES = declarations.ACCESS_TYPES
VIRTUALITY_TYPES = declarations.VIRTUALITY_TYPES

class ctypes_creator_t( declarations.decl_visitor_t ):
    def __init__( self
                  , global_ns
                  , library_path
                  , exported_symbols
                  , doc_extractor=None ):
        declarations.decl_visitor_t.__init__(self)
        self.logger = _logging_.loggers.module_builder
        self.decl_logger = _logging_.loggers.declarations

        self.global_ns = global_ns

        self.__library_path = library_path
        self.__exported_symbols = exported_symbols
        self.module = code_creators.ctypes_module_t( global_ns )
        self.__dependencies_manager = dependencies_manager.manager_t(self.decl_logger)

        #bookmark for class introductions
        self.__class_ccs = code_creators.bookmark_t()
        #bookmark for class deinitions
        self.__class_defs_ccs = code_creators.bookmark_t()

        #~ prepared_decls = self.__prepare_decls( global_ns, doc_extractor )
        #~ self.__decls = sort_algorithms.sort( prepared_decls )
        self.curr_decl = global_ns
        self.curr_code_creator = self.module
        #mapping between class declaration and class introduction code creator
        self.__class2introduction = {}
        #mapping between classs and its methods definition dictionary
        self.__class2methods_def = {}
        #mapping between namespace and its code creator
        self.__namespace2pyclass = {}
        #set of all included namespaces
        #~ self.__included_nss = set()
        #~ for decl in self.global_ns

    def __print_readme( self, decl ):
        readme = decl.readme()
        if not readme:
            return

        if not decl.exportable:
            reason = readme[0]
            readme = readme[1:]
            self.decl_logger.warn( "%s;%s" % ( decl, reason ) )

        for msg in readme:
            self.decl_logger.warn( "%s;%s" % ( decl, msg ) )

    def __should_generate_code( self, decl ):
        if decl.ignore or decl.already_exposed:
            return False
        return True


    #~ def __prepare_decls( self, global_ns, doc_extractor ):
        #~ to_be_exposed = []
        #~ for decl in declarations.make_flatten( global_ns ):
            #~ if decl.ignore:
                #~ continue

            #~ if not decl.exportable:
                #~ #leave only decls that user wants to export and that could be exported
                #~ self.__print_readme( decl )
                #~ continue

            #~ if decl.already_exposed:
                #~ #check wether this is already exposed in other module
                #~ continue

            #~ if isinstance( decl.parent, declarations.namespace_t ):
                #~ #leave only declarations defined under namespace, but remove namespaces
                #~ to_be_exposed.append( decl )

            #~ if doc_extractor:
                #~ decl.documentation = doc_extractor( decl )

            #~ self.__print_readme( decl )

        #~ return to_be_exposed

    def __contains_exported( self, decl ):
        return bool( decl.decls( self.__should_generate_code, recursive=True, allow_empty=True ) )

    # - implement better 0(n) algorithm
    def __add_class_introductions( self, cc, class_ ):
        ci_creator = code_creators.class_introduction_t( class_ )
        self.__class2introduction[ class_ ] = ci_creator
        cc.adopt_creator( ci_creator )
        classes = class_.classes( recursive=False, allow_empty=True)
        classes = sort_algorithms.sort_classes( classes )
        for internal_class in classes:
            if self.__contains_exported( internal_class ):
                self.__add_class_introductions( ci_creator, internal_class )

    def create(self ):
        """Create and return the module for the extension.

        @returns: Returns the root of the code creators tree
        @rtype: L{module_t<code_creators.module_t>}
        """
        # Invoke the appropriate visit_*() method on all decls
        ccc = self.curr_code_creator
        ccc.adopt_creator( code_creators.import_t( 'ctypes' ) )
        ccc.adopt_creator( code_creators.import_t( code_repository.ctypes_utils.file_name  ) )

        ccc.adopt_creator( code_creators.separator_t() )

        ccc.adopt_creator( code_creators.library_reference_t( self.__library_path ) )
        ccc.adopt_creator( code_creators.name_mappings_t( self.__exported_symbols ) )

        ccc.adopt_creator( code_creators.separator_t() )
        #adding namespaces
        global_ns_cc = code_creators.bookmark_t()
        ccc.adopt_creator( global_ns_cc )
        ccc.adopt_creator( self.__class_ccs )
        self.__namespace2pyclass[ self.global_ns ] = global_ns_cc
        #adding class introductions - special case because of hierarchy
        f = lambda cls: self.__should_generate_code( cls ) \
                        and isinstance( cls.parent, declarations.namespace_t )
        ns_classes = self.global_ns.classes( f, recursive=True, allow_empty=True)
        ns_classes = sort_algorithms.sort_classes( ns_classes )
        for class_ in ns_classes:
            if self.__contains_exported( class_ ):
                self.__add_class_introductions( self.__class_ccs, class_ )

        ccc.adopt_creator( self.__class_defs_ccs )

        declarations.apply_visitor( self, self.curr_decl )

        self.__dependencies_manager.inform_user()

        return self.module

    def visit_member_function( self ):
        self.__dependencies_manager.add_exported( self.curr_decl )
        md_cc = self.__class2methods_def[ self.curr_decl.parent ]
        cls_intro_cc = self.__class2introduction[ self.curr_decl.parent ]
        mem_fun_def_cc = code_creators.mem_fun_definition_t( self.curr_decl )
        #TODO: calculate only exported functions
        if 0 == len( self.curr_decl.overloads):
            #this is the first and the last and the only class constructor
            md_cc.adopt_creator( mem_fun_def_cc )
            cls_intro_cc.adopt_creator( code_creators.mem_fun_introduction_t(self.curr_decl) )
        else:
            has_introduction = cls_intro_cc.find_by_creator_class( code_creators.mem_fun_introduction_t, unique=False )
            has_introduction = filter( lambda cc: cc.alias == mem_fun_def_cc.alias, has_introduction )
            if not has_introduction:
                cls_intro_cc.adopt_creator( code_creators.mem_fun_introduction_t(self.curr_decl) )

            multi_method_def = md_cc.find_mutli_method( mem_fun_def_cc.alias )
            if not multi_method_def:
                multi_method_def = code_creators.multi_method_definition_t ()
                md_cc.adopt_creator( multi_method_def )
            multi_method_def.adopt_creator( mem_fun_def_cc )

        #~ if self.curr_decl.virtuality == VIRTUALITY_TYPES.NOT_VIRTUAL:
            #~ cls_intro_cc.adopt_creator( code_creators.mem_fun_introduction_t( self.curr_decl ) )
        #~ elif self.curr_decl.virtuality == VIRTUALITY_TYPES.VIRTUAL:
            #~ cls_intro_cc.adopt_creator( code_creators.vmem_fun_introduction_t( self.curr_decl ) )
        #~ else:
            #~ pass

    def visit_constructor( self ):
        self.__dependencies_manager.add_exported( self.curr_decl )
        md_cc = self.__class2methods_def[ self.curr_decl.parent ]
        cls_intro_cc = self.__class2introduction[ self.curr_decl.parent ]
        init_def_cc = code_creators.init_definition_t( self.curr_decl )
        #TODO: calculate only exported constructors
        if 0 == len( self.curr_decl.overloads):
            #this is the first and the last and the only class constructor
            md_cc.adopt_creator( init_def_cc )
            cls_intro_cc.adopt_creator( code_creators.init_introduction_t(self.curr_decl) )
        else:
            has_constructor = cls_intro_cc.find_by_creator_class( code_creators.init_introduction_t )
            if not has_constructor:
                cls_intro_cc.adopt_creator( code_creators.init_introduction_t(self.curr_decl) )

            multi_method_def = md_cc.find_mutli_method( init_def_cc.alias )
            if not multi_method_def:
                multi_method_def = code_creators.multi_method_definition_t ()
                md_cc.adopt_creator( multi_method_def )
            multi_method_def.adopt_creator( init_def_cc )

    def visit_destructor( self ):
        self.__dependencies_manager.add_exported( self.curr_decl )
        cls_intro_cc = self.__class2introduction[ self.curr_decl.parent ]
        cls_intro_cc.adopt_creator( code_creators.del_introduction_t( self.curr_decl ) )

        md_cc = self.__class2methods_def[ self.curr_decl.parent ]
        md_cc.adopt_creator( code_creators.del_definition_t( self.curr_decl ) )

    def visit_member_operator( self ):
        self.__dependencies_manager.add_exported( self.curr_decl )

    def visit_casting_operator( self ):
        self.__dependencies_manager.add_exported( self.curr_decl )

    def visit_free_function( self ):
        self.__dependencies_manager.add_exported( self.curr_decl )
        if self.curr_decl.name in self.__exported_symbols \
           and self.curr_decl.name == self.__exported_symbols[ self.curr_decl.name ]:
            return #it is notpossible to call C function from CPPDLL
        else:
            self.curr_code_creator.adopt_creator( code_creators.function_definition_t( self.curr_decl ) )

    def visit_free_operator( self ):
        self.__dependencies_manager.add_exported( self.curr_decl )

    def visit_class_declaration(self ):
        self.__dependencies_manager.add_exported( self.curr_decl )
        ci_creator = code_creators.class_declaration_introduction_t( self.curr_decl )
        self.__class_ccs.adopt_creator( ci_creator )

    def visit_class(self):
        self.__dependencies_manager.add_exported( self.curr_decl )
        #fields definition should be recursive using the visitor
        self.__class_defs_ccs.adopt_creator( code_creators.fields_definition_t( self.curr_decl ) )
        md_cc = code_creators.methods_definition_t( self.curr_decl )
        self.__class2methods_def[ self.curr_decl ] = md_cc
        self.__class_defs_ccs.adopt_creator( md_cc )
        class_ = self.curr_decl
        for decl in self.curr_decl.decls( recursive=False, allow_empty=True ):
            if self.__should_generate_code( decl ):
                self.curr_decl = decl
                declarations.apply_visitor( self, decl )
        self.curr_decl = class_

    def visit_enumeration(self):
        self.__dependencies_manager.add_exported( self.curr_decl )

    def visit_typedef(self):
        self.__dependencies_manager.add_exported( self.curr_decl )

    def visit_variable(self):
        self.__dependencies_manager.add_exported( self.curr_decl )

    def visit_namespace(self ):
        if not self.__contains_exported( self.curr_decl ):
            return
        if self.global_ns is not self.curr_decl:
            ns_creator = code_creators.namespace_as_pyclass_t( self.curr_decl )
            self.__namespace2pyclass[ self.curr_decl ] = ns_creator
            self.__namespace2pyclass[ self.curr_decl.parent ].adopt_creator( ns_creator )

        ns = self.curr_decl
        for decl in self.curr_decl.decls( recursive=False, allow_empty=True ):
            if isinstance( decl, declarations.namespace_t) or self.__should_generate_code( decl ):
                self.curr_decl = decl
                declarations.apply_visitor( self, decl )
        self.curr_decl = ns


