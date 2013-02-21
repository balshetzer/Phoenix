#!/usr/bin/python
#-----------------------------------------------------------------------------
#  WAF script for building and installing the wxPython extension modules.
#
# Author:      Robin Dunn
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#-----------------------------------------------------------------------------

import sys
import os

import buildtools.config
cfg = buildtools.config.Config(True)

#-----------------------------------------------------------------------------
# Options and configuration

APPNAME = 'wxPython'
VERSION = cfg.VERSION

isWindows = sys.platform.startswith('win')
isDarwin = sys.platform == "darwin"

top = '.'
out = 'build_waf'


def options(opt):
    if isWindows:
        opt.load('msvc')
    else:
        opt.load('compiler_cc compiler_cxx')
    opt.load('python')

    opt.add_option('--debug', dest='debug', action='store_true', default=False,
                   help='Turn on debug compile options.')        
    opt.add_option('--python', dest='python', default='', action='store',
                   help='Full path to the Python executrable to use.')
    opt.add_option('--wx_config', dest='wx_config', default='wx-config', action='store',
                   help='Full path to the wx-config script to be used for this build.')
    opt.add_option('--mac_arch', dest='mac_arch', default='', action='store',
                   help='One or more comma separated architecture names to be used for '
                   'the Mac builds. Should be at least a subset of the architectures '
                   'used by wxWidgets and Python')
    opt.add_option('--msvc_arch', dest='msvc_arch', default='x86', action='store',
                   help='The architecture to target for MSVC builds. Supported values '
                   'are: "x86" or "x64"')
    #opt.add_option('--msvc_ver', dest='msvc_ver', default='9.0', action='store',
    #               help='The MSVC version to use for the build, if multiple versions are '
    #               'installed. Currently supported values are: "9.0" or "10.0"')

    # TODO: The waf msvc tool has --msvc_version and --msvc_target options
    # already. We should just switch to those instead of adding our own
    # option names...


def configure(conf):    
    #import waflib.Logs
    #waflib.Logs.init_log()

    if isWindows:
        msvc_version = '9.0' #conf.options.msvc_ver
        if conf.options.python and '33' in conf.options.python:
            msvc_version = '10.0'

        conf.env['MSVC_VERSIONS'] = ['msvc ' + msvc_version]
        conf.env['MSVC_TARGETS'] = [conf.options.msvc_arch]
        conf.load('msvc')
    else:
        conf.load('compiler_cc compiler_cxx')

    if conf.options.python:
        conf.env.PYTHON = conf.options.python
    conf.load('python')
    conf.check_python_version(minver=(2,7,0))

    if isWindows:
        # WAF seems to occasionally have troubles building the test programs
        # correctly on Windows, and so it ends up thinking that the Python
        # lib and/or Python.h files do not exist. So instead of using the
        # check_python_headers function we will just manually fill in the
        # values for Windows based on what we already know that the function
        # would normally have done , but without running the test programs.

        v = 'prefix SO INCLUDEPY'.split()
        try:
            lst = conf.get_python_variables(["get_config_var('%s') or ''" % x for x in v])
        except RuntimeError:
            conf.fatal("Python development headers not found (-v for details).")
        dct = dict(zip(v, lst))

        conf.env['pyext_PATTERN'] = '%s' + dct['SO'] # not a mistake

        libname = 'python' + conf.env['PYTHON_VERSION'].replace('.', '')
        # TODO: libpath will be incorrect in virtualenv's.  Fix this...
        libpath = [os.path.join(dct['prefix'], "libs")]       
        
        conf.env['LIBPATH_PYEMBED'] = libpath
        conf.env.append_value('LIB_PYEMBED', [libname])
        conf.env['LIBPATH_PYEXT'] = conf.env['LIBPATH_PYEMBED']
        conf.env['LIB_PYEXT'] = conf.env['LIB_PYEMBED']

        conf.env['INCLUDES_PYEXT'] = [dct['INCLUDEPY']]
        conf.env['INCLUDES_PYEMBED'] = [dct['INCLUDEPY']]

        from distutils.msvccompiler import MSVCCompiler
        dist_compiler = MSVCCompiler()
        dist_compiler.initialize()
        conf.env.append_value('CFLAGS_PYEXT', dist_compiler.compile_options)
        conf.env.append_value('CXXFLAGS_PYEXT', dist_compiler.compile_options)
        conf.env.append_value('LINKFLAGS_PYEXT', dist_compiler.ldflags_shared)

    else:
        # If not Windows then let WAF take care of it all.
        conf.check_python_headers()


    # fetch and save the debug option
    conf.env.debug = conf.options.debug

    # Ensure that the headers in siplib and Phoenix's src dir can be found
    conf.env.INCLUDES_WXPY = ['sip/siplib', 'src']

    if isWindows:
        # Windows/MSVC specific stuff

        cfg.finishSetup(debug=conf.env.debug)

        conf.env.INCLUDES_WX = cfg.includes
        conf.env.DEFINES_WX = cfg.wafDefines
        conf.env.CFLAGS_WX = cfg.cflags
        conf.env.CXXFLAGS_WX = cfg.cflags
        conf.env.LIBPATH_WX = cfg.libdirs
        conf.env.LIB_WX = cfg.libs
        conf.env.LIBFLAGS_WX = cfg.lflags

        _copyEnvGroup(conf.env, '_WX', '_WXADV')
        conf.env.LIB_WXADV += cfg.makeLibName('adv')

        _copyEnvGroup(conf.env, '_WX', '_WXSTC')
        conf.env.LIB_WXSTC += cfg.makeLibName('stc')

        _copyEnvGroup(conf.env, '_WX', '_WXHTML')
        conf.env.LIB_WXHTML += cfg.makeLibName('html')

        _copyEnvGroup(conf.env, '_WX', '_WXGL')
        conf.env.LIB_WXGL += cfg.makeLibName('gl')

        _copyEnvGroup(conf.env, '_WX', '_WXWEBVIEW')
        conf.env.LIB_WXWEBVIEW += cfg.makeLibName('webview')

        _copyEnvGroup(conf.env, '_WX', '_WXXML')
        conf.env.LIB_WXXML += cfg.makeLibName('xml', isMSWBase=True)

        _copyEnvGroup(conf.env, '_WX', '_WXXRC')
        conf.env.LIB_WXXRC += cfg.makeLibName('xrc')




        # tweak the PYEXT compile and link flags if making a --debug build
        if conf.env.debug:
            for listname in ['CFLAGS_PYEXT', 'CXXFLAGS_PYEXT']:
                lst = conf.env[listname]
                for opt in '/Ox /MD /DNDEBUG'.split():
                    try:
                        lst.remove(opt)
                    except ValueError:
                        pass
                lst[1:1] = '/Od /MDd /Z7 /D_DEBUG'.split()

            conf.env['LINKFLAGS_PYEXT'].append('/DEBUG')
            conf.env['LIB_PYEXT'][0] += '_d'

    else: 
        # Configuration stuff for non-Windows ports using wx-config
        conf.env.CFLAGS_WX   = list()
        conf.env.CXXFLAGS_WX = list()
        conf.env.CFLAGS_WXPY   = list()
        conf.env.CXXFLAGS_WXPY = list()

        # finish configuring the Config object
        conf.env.wx_config = conf.options.wx_config
        cfg.finishSetup(conf.env.wx_config, conf.env.debug)

        # Check wx-config exists and fetch some values from it
        conf.check_cfg(path=conf.options.wx_config, package='', 
                       args='--cxxflags --libs core,net', 
                       uselib_store='WX', mandatory=True)

        # Run it again with different libs options to get different
        # sets of flags stored to use with varous extension modules below.
        conf.check_cfg(path=conf.options.wx_config, package='', 
                       args='--cxxflags --libs adv,core,net', 
                       uselib_store='WXADV', mandatory=True)

        libname = '' if cfg.MONOLITHIC else 'stc,' # workaround bug in wx-config
        conf.check_cfg(path=conf.options.wx_config, package='', 
                       args='--cxxflags --libs %score,net' % libname, 
                       uselib_store='WXSTC', mandatory=True)

        conf.check_cfg(path=conf.options.wx_config, package='', 
                       args='--cxxflags --libs html,core,net', 
                       uselib_store='WXHTML', mandatory=True)

        conf.check_cfg(path=conf.options.wx_config, package='', 
                       args='--cxxflags --libs gl,core,net', 
                       uselib_store='WXGL', mandatory=True)

        conf.check_cfg(path=conf.options.wx_config, package='', 
                       args='--cxxflags --libs webview,core,net', 
                       uselib_store='WXWEBVIEW', mandatory=True)

        conf.check_cfg(path=conf.options.wx_config, package='', 
                       args='--cxxflags --libs xml,core,net', 
                       uselib_store='WXXML', mandatory=True)

        conf.check_cfg(path=conf.options.wx_config, package='', 
                       args='--cxxflags --libs xrc,xml,core,net', 
                       uselib_store='WXXRC', mandatory=True)



        # NOTE: This assumes that if the platform is not win32 (from
        # the test above) and not darwin then we must be using the
        # GTK2 port of wxWidgets.  If we ever support other ports then
        # this code will need to be adjusted.
        if not isDarwin:
            gtkflags = os.popen('pkg-config gtk+-2.0 --cflags', 'r').read()[:-1]
            conf.env.CFLAGS_WX   += gtkflags.split()
            conf.env.CXXFLAGS_WX += gtkflags.split()

        # clear out Python's default NDEBUG and make sure it is undef'd too just in case
        if 'NDEBUG' in conf.env.DEFINES_PYEXT:
            conf.env.DEFINES_PYEXT.remove('NDEBUG')
        conf.env.CFLAGS_WXPY.append('-UNDEBUG')
        conf.env.CXXFLAGS_WXPY.append('-UNDEBUG')

        # Add basic debug info for all builds
        conf.env.CFLAGS_WXPY.append('-g')
        conf.env.CXXFLAGS_WXPY.append('-g')

        # And if --debug is set turn on more detailed debug info and turn off optimization
        if conf.env.debug:
            conf.env.CFLAGS_WXPY.extend(['-ggdb', '-O0'])
            conf.env.CXXFLAGS_WXPY.extend(['-ggdb', '-O0'])

        # Remove some compile flags we don't care about, ones that we may be
        # replacing ourselves anyway, or ones which may have duplicates.
        flags = ['CFLAGS_PYEXT',    'CXXFLAGS_PYEXT',    'LINKFLAGS_PYEXT',
                 'CFLAGS_cshlib',   'CXXFLAGS_cshlib',   'LINKFLAGS_cshlib',
                 'CFLAGS_cxxshlib', 'CXXFLAGS_cxxshlib', 'LINKFLAGS_cxxshlib']
        for key in flags:
            _cleanFlags(conf, key)


        # Use the same compilers that wxWidgets used
        if cfg.CC:
            conf.env.CC = cfg.CC.split()
        if cfg.CXX:
            conf.env.CXX = cfg.CXX.split()


        # Some Mac-specific stuff
        if isDarwin:
            conf.env.MACOSX_DEPLOYMENT_TARGET = "10.5"  

            if conf.options.mac_arch:
                conf.env.ARCH_WXPY = conf.options.mac_arch.split(',')        

    #import pprint
    #pprint.pprint( [(k, conf.env[k]) for k in conf.env.keys()] )


#-----------------------------------------------------------------------------
# Build command

def build(bld):
    # Ensure that the directory containing this script is on the python
    # path for spawned commands so the builder and phoenix packages can be
    # found.
    thisdir = os.path.abspath(".")
    sys.path.insert(0, thisdir)

    from distutils.file_util import copy_file
    from distutils.dir_util  import mkpath
    from distutils.dep_util  import newer, newer_group
    from buildtools.config   import opj, loadETG, getEtgSipCppFiles

    cfg.finishSetup(bld.env.wx_config)

    # update the license files
    mkpath('license')
    for filename in ['preamble.txt', 'licence.txt', 'licendoc.txt', 'lgpl.txt']:
        copy_file(opj(cfg.WXDIR, 'docs', filename), opj('license',filename), update=1, verbose=1)

    # create the package's __version__ module
    open(opj(cfg.PKGDIR, '__version__.py'), 'w').write(
        "# This file was generated by Phoenix's wscript.\n\n"
        "VERSION_STRING    = '%(VERSION)s'\n"
        "MAJOR_VERSION     = %(VER_MAJOR)s\n"
        "MINOR_VERSION     = %(VER_MINOR)s\n"
        "RELEASE_NUMBER    = %(VER_RELEASE)s\n"
        "SUBRELEASE_NUMBER = %(VER_SUBREL)s\n\n"
        "VERSION = (MAJOR_VERSION, MINOR_VERSION, RELEASE_NUMBER, SUBRELEASE_NUMBER, '%(VER_FLAGS)s')\n"
        % cfg.__dict__)

    # copy the wx locale message catalogs to the package dir
    if isWindows or isDarwin:
        cfg.build_locale_dir(opj(cfg.PKGDIR, 'locale'))

    # copy __init__.py
    copy_file('src/__init__.py', cfg.PKGDIR, update=1, verbose=1)


    # Create the build tasks for each of our extension modules.
    siplib = bld(
        features = 'c cxx cshlib cxxshlib pyext',
        target   = makeTargetName(bld, 'siplib'),
        source   = ['sip/siplib/apiversions.c',
                    'sip/siplib/bool.cpp',
                    'sip/siplib/descriptors.c',
                    'sip/siplib/objmap.c',
                    'sip/siplib/qtlib.c',
                    'sip/siplib/siplib.c',
                    'sip/siplib/threads.c',
                    'sip/siplib/voidptr.c',
                    ],
        uselib   = 'WX WXPY',
    )  
    makeExtCopyRule(bld, 'siplib')


    etg = loadETG('etg/_core.py')
    rc = ['src/wxc.rc'] if isWindows else []
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_core'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WX WXPY',
        )
    makeExtCopyRule(bld, '_core')


    etg = loadETG('etg/_adv.py')
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_adv'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WXADV WXPY',
        )
    makeExtCopyRule(bld, '_adv')


    etg = loadETG('etg/_dataview.py')
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_dataview'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WXADV WXPY',    # dataview classes are also in the adv library
        )
    makeExtCopyRule(bld, '_dataview')


    etg = loadETG('etg/_grid.py')
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_grid'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WXADV WXPY',    # grid classes are also in the adv library
        )
    makeExtCopyRule(bld, '_grid')


    etg = loadETG('etg/_stc.py')
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_stc'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WXSTC WXPY',
        )
    makeExtCopyRule(bld, '_stc')


    etg = loadETG('etg/_html.py')
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_html'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WXHTML WXPY',
        )
    makeExtCopyRule(bld, '_html')


    etg = loadETG('etg/_glcanvas.py')
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_glcanvas'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WXGL WXPY',
        )
    makeExtCopyRule(bld, '_glcanvas')


    etg = loadETG('etg/_html2.py')
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_html2'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WXWEBVIEW WXPY',
        )
    makeExtCopyRule(bld, '_html2')


    etg = loadETG('etg/_xml.py')
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_xml'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WXXML WXPY',
        )
    makeExtCopyRule(bld, '_xml')


    etg = loadETG('etg/_xrc.py')
    bld(features = 'c cxx cxxshlib pyext',
        target   = makeTargetName(bld, '_xrc'),
        source   = getEtgSipCppFiles(etg) + rc,
        uselib   = 'WXXRC WXPY',
        )
    makeExtCopyRule(bld, '_xrc')



#-----------------------------------------------------------------------------
# helpers

# Remove some unwanted flags from the given key in the context's environment
def _cleanFlags(ctx, key):
    cleaned = list()
    skipnext = False
    for idx, flag in enumerate(ctx.env[key]):
        if flag in ['-arch', '-isysroot', '-compatibility_version', '-current_version']:
            skipnext = True  # implicitly skips this one too
        elif not skipnext:
            cleaned.append(flag)
        else:
            skipnext = False
    ctx.env[key] = cleaned


def makeTargetName(bld, name):
    if isWindows and bld.env.debug:
        name += '_d'
    return name


# Make a rule that will copy a built extension module to the in-place package
# dir so we can test locally without doing an install.
def makeExtCopyRule(bld, name):
    name = makeTargetName(bld, name)
    src = bld.env.pyext_PATTERN % name
    tgt = 'pkg.%s' % name  # just a name to be touched to serve as a timestamp of the copy
    bld(rule=copyFileToPkg, source=src, target=tgt, after=name)


# This is the task function to be called by the above rule.
def copyFileToPkg(task): 
    from distutils.file_util import copy_file
    from buildtools.config   import opj
    src = task.inputs[0].abspath() 
    tgt = task.outputs[0].abspath() 
    task.exec_command('touch %s' % tgt)
    tgt = opj(cfg.PKGDIR, os.path.basename(src))
    copy_file(src, tgt, verbose=1)
    return 0


# Copy all the items in env with a matching postfix to a similarly
# named item with the dest postfix.
def _copyEnvGroup(env, srcPostfix, destPostfix):
    import copy
    for key in env.keys():
        if key.endswith(srcPostfix):
            newKey = key[:-len(srcPostfix)] + destPostfix
            env[newKey] = copy.copy(env[key])

#-----------------------------------------------------------------------------