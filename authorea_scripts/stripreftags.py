#!/usr/bin/env python
"""
Pandoc filter to strip tags from references and citations and write plain
text.
"""
import re
import panflute as pf

pattern = re.compile('\\\\(cite[tp]?|ref)\{(.*)\}')


def striptags(elem, doc):
    try:
        if elem.format == 'html':
            return[]
    except AttributeError:
        pass


def destring(elem, doc):
    if isinstance(elem, pf.Str):
        pf.debug(elem.text)
        pf.debug(pattern.match(elem.text))
        return pf.RawInline(re.sub(pattern, r'\\\1{\2}', elem.text),
                            format='latex')
    else:
        return elem


def labels(elem, doc):
    try:
        if 'label' in elem.attributes.keys():
            return (pf.Plain(
                pf.RawInline('\\caption{' + '\\label{'
                             + elem.attributes['label'] + '}',
                             format='latex'),
                *elem.content[0].content,
                pf.Str('}')
                ))
    except AttributeError:
        pass


def main(doc=None):
    return pf.run_filters((labels, striptags, destring), doc=doc)


if __name__ == '__main__':
    main()
