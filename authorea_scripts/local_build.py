#!/usr/bin/env python

from __future__ import division, print_function

"""
This script generates a file to use for building authorea papers, and then runs
latex on them.

Requires python >= 2.6 (3.x should work, too)

The key assumptions are:
* ``layout.md`` exists in the article (I think it always does in Authorea)
* ``preamble.tex`` and/or``header.tex``, ``title.tex``, and
  ``bibliobgraphy/biblio.bib`` exist (I think these are created normally in a
    new Authorea article)
* ``posttitle.tex`` exists.  This one you'll have to create, containing
  everything you want after the title but before the beginning of the document.
  If it doesn't exist that's ok too, it'll just be ignored.
* Figures are in the ``figures`` directory (where authorea puts them), and in
  the correct place in the ``layout.md`` file.  A file named 'latexfigopts.json'
  can specify a dictionary for additional figure options (see the
  `FIGURE_DEFAULTS` below for what options that can be replaced).
  If pdf or eps figures exist alongside referenced raster image files, they will
  be favored over the raster format.

"""

import os
import sys
import shutil
import subprocess

from pypandoc import convert_file

#lots of dobule-{}'s are here because we use it as a formatting template below
MAIN_TEMPLATE = r"""
% Options for packages loaded elsewhere
\PassOptionsToPackage{{unicode}}{{hyperref}}
\PassOptionsToPackage{{hyphens}}{{url}}
\documentclass[12pt]{{article}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\usepackage{{natbib}}
\usepackage{{latexml}}
\usepackage{{setspace}}

% From pandoc
\usepackage{{lmodern}}
\usepackage{{amssymb,amsmath}}
\usepackage{{ifxetex,ifluatex}}
\ifnum 0\ifxetex 1\fi\ifluatex 1\fi=0 % if pdftex
  \usepackage[T1]{{fontenc}}
  \usepackage[utf8]{{inputenc}}
  \usepackage{{textcomp}} % provide euro and other symbols
\else % if luatex or xetex
  \usepackage{{unicode-math}}
  \defaultfontfeatures{{Scale=MatchLowercase}}
  \defaultfontfeatures[\rmfamily]{{Ligatures=TeX,Scale=1}}
\fi
% Use upquote if available, for straight quotes in verbatim environments
\IfFileExists{{upquote.sty}}{{\usepackage{{upquote}}}}{{}}
\IfFileExists{{microtype.sty}}{{% use microtype if available
  \usepackage[]{{microtype}}
  \UseMicrotypeSet[protrusion]{{basicmath}} % disable protrusion for tt fonts
}}{{}}
{parskip}
\usepackage{{xcolor}}
\IfFileExists{{xurl.sty}}{{\usepackage{{xurl}}}}{{}} % add URL line breaks if available
\IfFileExists{{bookmark.sty}}{{\usepackage{{bookmark}}}}{{\usepackage{{hyperref}}}}
\hypersetup{{
  hidelinks,
  pdfcreator={{LaTeX via pandoc}}}}
\urlstyle{{same}} % disable monospaced font for URLs
\setlength{{\emergencystretch}}{{3em}} % prevent overfull lines
\providecommand{{\tightlist}}{{%
  \setlength{{\itemsep}}{{0pt}}\setlength{{\parskip}}{{0pt}}}}
\setcounter{{secnumdepth}}{{-\maxdimen}} % remove section numbering

\date{{}}

{preamblein}

{headerin}

{titlecontent}

\begin{{document}}

{spacing}

{sectioninputs}

\bibliographystyle{{{bibstyle}}}
\bibliography{{{bibloc}}}{{}}

\end{{document}}
"""

FIGURE_TEMPLATE = r"""
\begin{<figure_env>}[<placement>]
\begin{center}
\includegraphics[width=<width>]{<figfn>}
<caption>
\end{center}
\end{<figure_env>}
""".replace('{', '{{').replace('}', '}}').replace('<', '{').replace('>', '}')

FIGURE_DEFAULTS = {'placement': '', 'width': '1\columnwidth', 'figure_env': 'figure', 'caption': ''}


def get_input_string(filename, localdir, quotepath=True, flatten=False):
    if flatten:
        filepath = os.path.join(localdir, filename)
        if not os.path.exists(filepath):
            filepath = filepath + '.tex'

        with open(filepath, 'r') as f:
            return f.read()
    else:
        if filename.endswith('.tex'):
            filename = filename[:-4]
        if quotepath:
            quote_chr = '"'
        else:
            quote_chr = ''
        return r'\input{' + os.path.join(localdir, filename) + '}'


def get_figure_string(filename, localdir, inputdir, flatten=False, copyto=False):
    import json

    figdir, figname = os.path.split(filename)

    fignamebase = os.path.splitext(figname)[0]
    figfn = os.path.join(inputdir, filename)
    pngfn = os.path.join(localdir, figdir, fignamebase, fignamebase + '.png')
    pdffn = os.path.join(localdir, figdir, fignamebase, fignamebase + '.pdf')
    epsfn = os.path.join(localdir, figdir, fignamebase, fignamebase + '.eps')

    if copyto:
        figpath = os.path.join(localdir, filename)
        if os.path.exists(pdffn):
            figpath = pdffn
            figfn = fignamebase
        elif os.path.exists(epsfn):
            figpath = epsfn
            figfn = fignamebase
        elif os.path.exists(pngfn):
            figpath = pngfn
            figfn = fignamebase
        elif os.path.exists(figpath):
            figfn = figname
        else:
            raise IOError('Could not find figure file {}'.format(figpath))
        shutil.copy(figpath, os.path.join(copyto, os.path.split(figpath)[1]))
    else:
        if (   os.path.exists(pdffn) 
            or os.path.exists(epsfn)
            or os.path.exists(pngfn)
           ):
            figfn = os.path.join(inputdir, figdir, fignamebase, fignamebase)

    if os.path.exists(os.path.join(localdir, figdir, 'caption.tex')):
        capinput = get_input_string('caption', os.path.join(inputdir, figdir), False, flatten=flatten)
        caption = r'\caption{ \protect' + capinput.strip() + '}'
    elif os.path.exists(
        os.path.join(localdir, figdir, 'caption.html')
        ):
        caption = convert_file(
            os.path.join(localdir, figdir, 'caption.html'),
            'latex', format='html+tex_math_dollars', filters=['stripreftags'], 
            )
    else:
        caption = ''

    optsfn = os.path.join(localdir, figdir, 'latexfigopts.json')
    figopts = FIGURE_DEFAULTS.copy()
    if os.path.exists(optsfn):
        with open(optsfn) as f:
            optsjson = json.load(f)
        if not isinstance(optsjson, dict):
            raise ValueError('File "{0}" does not have a top-level dict'.format(optsfn))
        for k in FIGURE_DEFAULTS.keys():
            v = optsjson.pop(k, None)
            if v is not None:
                figopts[k] = v
        if len(optsjson) != 0:
            raise ValueError('Entries in "{0}" that were not understood: {1}'.format(optsfn, optsjson))
    figopts['caption'] = caption

    figopts.update(locals())
    return FIGURE_TEMPLATE.format(**figopts)


# if builddir and local dir are the same set the paths used for input/include in
# the output tex file to be relative paths (this helps if sharing the created
# tex file with collaborator who don't use this script) otherwise use absolute
# paths. Alternatively, use the user defined option for whether relative or
# absolute paths are used.
def get_in_path(localdir, builddir, pathtype=None):
    """
    Figure out the path for a file in ``localdir`` relative to ``builddir``, or
    just use an absolute path dependeing on whether ``pathtype`` is 'rel' or
    'abs'. Or if it is None, pick relative only if ``localdir`` is the same as
    ``builddir``.
    """
    if pathtype == 'rel':
        return os.path.relpath(localdir, builddir)
    elif pathtype == 'abs':
        return os.path.abspath(localdir)
    elif pathtype is None:
        if builddir == localdir:
            return os.path.relpath(localdir, builddir)
        else:
            return os.path.abspath(localdir)
    else:
        raise ValueError('Invalid pathtype: "{0}"'.format(pathtype))


def build_authorea_latex(localdir, builddir, latex_exec, bibtex_exec, outname,
                         usetitle, dobibtex, npostbibcalls, openwith, titleinput,
                         dobuild, pathtype, flatten, copy_figs, bibstyle,
                         citecommand, spacing, noparskip):

    if noparskip:
        parskip = ''
    else:
        parskip = r''' 
        \makeatletter
        \@ifundefined{{KOMAClassName}}{{% if non-KOMA class
          \IfFileExists{{parskip.sty}}{{%
            \usepackage{{parskip}}
          }}{{% else
            \setlength{{\parindent}}{{0pt}}
            \setlength{{\parskip}}{{6pt plus 2pt minus 1pt}}}}
        }}{{% if KOMA class
          \KOMAoptions{{parskip=half}}}}
        \makeatother
        '''

    if spacing == 'single':
        spacing = ''
    elif spacing == 'half':
        spacing = r'\onehalfspacing'
    elif spacing == 'double':
        spacing = r'\doublespacing'
    else:
        raise ValueError('spacing must be "single, half, or double"')

    if not os.path.exists(builddir):
        os.mkdir(builddir)

    if not os.path.isdir(builddir):
        raise IOError('Requested build directory {0} is a file, not a '
                      'directory'.format(builddir))

    # generate the main tex file as a string
    if os.path.exists(os.path.join(localdir, 'preamble.tex')):
        preamblein = get_input_string('preamble', get_in_path(localdir, builddir, pathtype), flatten=flatten)
    else:
        preamblein = ''
    if os.path.exists(os.path.join(localdir, 'header.tex')):
        headerin = get_input_string('header', get_in_path(localdir, builddir, pathtype), flatten=flatten)
    else:
        headerin = ''

    if not headerin and not preamblein:
        print("Neither preable nor header found!  Proceeding, but that's rather weird")


    if copy_figs:
        bibloc_abs = os.path.join(get_in_path(localdir, builddir, 'abs'), 'bibliography', 'biblio') + '.bib'
        shutil.copy(bibloc_abs, os.path.join(builddir, os.path.split(bibloc_abs)[1]))
        bibloc = 'biblio'
    else:
        bibloc = os.path.join(get_in_path(localdir, builddir, pathtype), 'bibliography', 'biblio') + '.bib'

    titlecontent = []
    sectioninputs = []
    if usetitle:
        if titleinput:
            titlestr = get_input_string('title', get_in_path(localdir, builddir, pathtype), flatten=flatten)
        else:
            with open(os.path.join(get_in_path(localdir, builddir, 'abs'), 'title.tex')) as f:
                titlestr = f.read()
        titlecontent.append(r'\title{' + titlestr.strip('\n') + '}')
        sectioninputs.append('\maketitle\n')

    with open(os.path.join(localdir, 'layout.md')) as f:
        for l in f:
            ls = l.strip()
            if ls == '':
                pass
            elif ls in ('posttitle.tex', 'title.tex', 'preamble.tex', 'header.tex'):
                pass # skip any that have been processed above
            elif ls in ('abstract.tex'):
                # add abstract to title content
                titlein = get_input_string('abstract', get_in_path(localdir, builddir, pathtype), flatten=flatten)
                titlecontent.append(r'\begin{abstract}' + titlein  + '\end{abstract}')
            elif ls.endswith('.html') or ls.endswith('.htm'):
                html_to_tex = convert_file(
                    os.path.join(localdir, ls),
                    'latex', format='html+tex_math_dollars', filters=['stripreftags'])
                sectioninputs.append(html_to_tex)
            elif ls.startswith('figures'):
                ls = ls + ls.lstrip('figures')
                inpath = get_in_path(localdir, builddir, pathtype)
                sectioninputs.append(get_figure_string(ls, localdir, inpath, flatten=flatten,
                                                       copyto=builddir if copy_figs else False))
            else:
                sectioninputs.append(get_input_string(ls, get_in_path(localdir, builddir, pathtype), flatten=flatten))
    sectioninputs = '\n'.join(sectioninputs)

    if os.path.exists(os.path.join(localdir, 'posttitle.tex')):
        titlecontent.append(get_input_string('posttitle', get_in_path(localdir, builddir, pathtype), flatten=flatten))
        # swap this to before the abstract
        if r'\begin{abstract}' in titlecontent[-2]: # check second to last value and swap position
            titlecontent[-1], titlecontent[-2] = titlecontent[-2], titlecontent[-1]
    titlecontent = '\n'.join(titlecontent)

    maintexstr = MAIN_TEMPLATE.format(**locals())

    #now save that string out as a file
    outname = outname if outname.endswith('.tex') else (outname + '.tex')
    outtexpath = os.path.join(builddir, outname)
    with open(outtexpath, 'w') as f:
        f.write(maintexstr)

    if outname.endswith('.tex'):
        outname = outname[:-4]

    if dobuild:
        #now actually run latex/bibtex
        buildargs = [latex_exec, outname + '.tex']
        print('\n\RUNNING THIS COMMAND: "{0}"\n'.format(' '.join([latex_exec, outname + '.tex'])))
        subprocess.check_call(buildargs, cwd=builddir)
        if dobibtex:
            buildargs = [bibtex_exec, outname]
            print('\n\RUNNING THIS COMMAND: "{0}"\n'.format(' '.join([latex_exec, outname + '.tex'])))
            subprocess.check_call(buildargs, cwd=builddir)
        for _ in range(npostbibcalls):
            buildargs = [latex_exec, outname + '.tex']
            print('\n\RUNNING THIS COMMAND: "{0}"\n'.format(' '.join([latex_exec, outname + '.tex'])))
            subprocess.check_call(buildargs, cwd=builddir)

        #launch the result if necessary
        resultfn = outtexpath[:-4] + ('.pdf' if 'pdf' in latex_exec else '.dvi')
        if openwith:
            buildargs = openwith.split(' ')
            buildargs.append(resultfn)
            print('\nLaunching as:' + str(buildargs), '\n')
            subprocess.check_call(buildargs)
        else:
            msg = '\nBuild completed.  You can see the result in "{0}": "{1}"'
            print(msg.format(builddir, resultfn), '\n')
    else:
        msg = 'Preprocessing done but skipping build.  Main file:"{0}.tex"'
        print(msg.format(os.path.join(builddir, outname)))


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Local builder for authorea papers.')

    parser.add_argument('localdir', nargs='?', default='.',
                        help='The directory to actually search for the authorea'
                             ' files in. Default to the current directory.')
    parser.add_argument('--build-dir', '-d', default='authorea_build',
                        help='the directory to build the paper in')
    parser.add_argument('--latex', '-l', default='pdflatex',
                        help='The executable to use for the latex build step.')
    parser.add_argument('--bibtex', '-b', default='bibtex',
                        help='The executable to use for the bibtex build step.')
    parser.add_argument('--filename', '-f', default='authorea_paper',
                        help='The name to use for the output tex file.')
    parser.add_argument('--no-bibtex', action='store_false', dest='usebibtex',
                        help='Provide this to not run bibtex.')
    parser.add_argument('--no-title', action='store_false', dest='usetitle',
                        help='Provide this to skip the title command.')
    parser.add_argument('--title-input', action='store_true', dest='titleinput',
                        help='Provide this to have the title included via the '
                             '\\input command instead of directly in the '
                             'generated tex file. This is useful because \\input'
                             'sometimes prevents the title from being cased '
                             'correctly.', default=False)
    parser.add_argument('--n-runs-after-bibtex', '-n', type=int, default=3,
                        help='The number of times to call latex after bibtex.')
    parser.add_argument('--open-with', '-o', default=None,
                        help='An executable to launch the output file with. '
                             'Default is to not do anything with it.')
    parser.add_argument('--no-build', action='store_false', dest='dobuild',
                        help='Only do preprocessing and skip all the build/open steps')
    parser.add_argument('--relative-links', action='store_true', dest='rellinks',
                        help='Always make links (to input files and figures) within '
                             'the .tex file relative. Default is to do this if '
                             'localdir and buildir are the same.')
    parser.add_argument('--absolute-links', action='store_true', dest='abslinks',
                        help='Always make links (to input files and figures) within '
                             'the .tex file absolute. Default is to do this if '
                             'localdir and buildir are different.')
    parser.add_argument('--flatten', '-t', action='store_true',
                        help=r'Directly includes the content from tex files '
                             r'instead of using \input.')
    parser.add_argument('--copy-figs', '-c', action='store_true',
                        help='Copy figures and any bib files into the build '
                             'directory and set includes to point to those copies.')
    parser.add_argument('--bibstyle', nargs='?', default='apa',
                        help='The bibliography style to use')
    parser.add_argument('--citecommand', nargs='?', default='citep',
                        help='The primary natbib citation command to use.'
                             ' Omit leading backslash.')
    parser.add_argument('--spacing', nargs='?', default='half',
                        help='Spacing to use for the document. "single", "half", or "double"'
                             ' "half" is one and one-half')
    parser.add_argument('--noparskip', action='store_true',
                        help='Suppresses loading parskip class for normal'
                             ' indentation rules.')

    args = parser.parse_args()

    pathtype = None

    convert_file(os.path.join(args.localdir, 'title.html'),
                 'latex', format='html+tex_math_dollars', outputfile=os.path.join(args.localdir, 'title.tex'))

    if args.flatten and (args.rellinks or args.abslinks):
        print('You cannot use both "--flatten" and either "--relative-links" '
              'or "--absolute-links".')
        sys.exit(1)

    if args.rellinks and args.abslinks:
        print('You must use either "--relative-links", "--absolute-links", or '
              'neither, but not both.')
        sys.exit(1)
    else:
        if args.rellinks:
            pathtype = 'rel'
        if args.abslinks:
            pathtype = 'abs'

    build_authorea_latex(args.localdir, args.build_dir, args.latex, args.bibtex,
                         args.filename, args.usetitle, args.usebibtex,
                         args.n_runs_after_bibtex, args.open_with,
                         args.titleinput, args.dobuild, pathtype, args.flatten,
                         args.copy_figs, args.bibstyle, args.citecommand,
                         args.spacing, args.noparskip)


if __name__ == "__main__":
    main()
