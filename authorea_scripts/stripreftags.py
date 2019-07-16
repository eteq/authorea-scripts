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
    if (       isinstance(elem, pf.Header)
            or isinstance(elem, pf.Div)):
        try:
            if 'label' in elem.attributes:
                elem.identifier = label = elem.attributes['label']
                mytext = (r'\caption{\hypertarget{'
                          + label
                          + r'}{\label{'
                          + label
                          + r'}}')
                first_child = elem.content[0]
                first_child.content.insert(0, pf.RawInline(mytext, format='latex'))
                first_child.content.append(pf.RawInline(r'}', format='latex'))
                return (elem if isinstance(elem, pf.Header)
                        else pf.Div(first_child))
        except AttributeError:
            pass
        # Extra section headers with not content can cause an IndexError.
        except IndexError:
            pass
        except KeyError:
            pass


def main(doc=None):
    replacements = {'\\\\(cite[tp]?|ref)\{(.*)\}': r'\\\1{\2}',
                    '$': r'\$'}
    return pf.run_filters((labels, striptags, destring),
                          doc=doc, replacements=replacements)


if __name__ == '__main__':
    main()
