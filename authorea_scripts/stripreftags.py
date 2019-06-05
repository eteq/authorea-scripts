#!/usr/bin/env python
"""
Pandoc filter to strip tags from references and citations and write plain
text.
"""
import re
import panflute as pf



def multireplace(string, replacements):
    """
    Given a string and a replacement map, it returns the replaced string.
    :param str string: string to execute replacements on
    :param dict replacements: replacement dictionary {value to find: value to replace}
    :rtype: str
    """
    # Place longer ones first to keep shorter substrings from matching where the longer ones should take place
    # For instance given the replacements {'ab': 'AB', 'abc': 'ABC'} against the string 'hey abc', it should produce
    # 'hey ABC' and not 'hey ABc'
    substrs = sorted(replacements, key=len, reverse=True)

    # Create a big OR regex that matches any of the substrings to replace
    regexp = re.compile('|'.join(map(re.escape, substrs)))

    # For each match, look up the new string in the replacements
    return regexp.sub(lambda match: replacements[match.group(0)], string)


def striptags(elem, doc, replacements):
    try:
        if elem.format == 'html':
            return[]
    except AttributeError:
        pass


def destring(elem, doc, replacements):
    if isinstance(elem, pf.Str):
        return pf.RawInline(multireplace(elem.text, replacements),
                            format='latex')
    else:
        return elem


def labels(elem, doc, replacements):
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
    # Extra section headers with not content can cause an IndexError.
    except IndexError:
        pass


def main(doc=None):
    replacements = {'\\\\(cite[tp]?|ref)\{(.*)\}': r'\\\1{\2}',
                    '$': r'\$'}
    return pf.run_filters((labels, striptags, destring),
                          doc=doc, replacements=replacements)


if __name__ == '__main__':
    main()
