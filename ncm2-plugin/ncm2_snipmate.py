# -*- coding: utf-8 -*-


def wrap():
    def snipmate_text(txt):
        txt = txt.replace('\\', '\\\\')
        txt = txt.replace('$', r'\$')
        txt = txt.replace('{', r'\{')
        txt = txt.replace('}', r'\}')
        txt = txt.replace(':', r'\:')
        txt = txt.replace('`', r'\`')
        return txt

    def snipmate_placeholder(num, txt=''):
        if txt:
            # : doesn't work in placeholder
            txt = snipmate_text(txt)
            return '${%s:%s}'  % (num, txt)
        else:
            return '${%s}'  % (num)

    def to_snipmate(ast):
        txt = ''
        for t, ele in ast:
            if t == 'text':
                txt += snipmate_text(ele)
            elif t == 'tabstop':
                txt += "${%s}" % ele
            elif t == 'placeholder':
                tab, ph = ele
                txt += "${%s:%s}" % (tab, to_snipmate(ph))
            elif t == 'choice':
                # snipmate doesn't support choices, replace it with placeholder
                tab, opts = ele
                txt += "${%s:%s}" % (tab, snipmate_text(opts[0]))
        return txt

    from ncm2_core import ncm2_core
    from ncm2 import getLogger
    import vim
    from ncm2_lsp_snippet.parser import Parser
    import ncm2_lsp_snippet.utils as lsp_utils
    import re
    import json

    logger = getLogger(__name__)

    vim.command('call ncm2_snipmate#init()')

    old_formalize = ncm2_core.match_formalize
    old_decorate = ncm2_core.matches_decorate

    parser = Parser()

    # convert lsp snippet into snipmate snippet
    def formalize(ctx, item):
        item = old_formalize(ctx, item)
        item = lsp_utils.match_formalize(ctx, item)
        ud = item['user_data']
        if not ud['is_snippet']:
            return item
        try:
            ast = parser.get_ast(ud['snippet'])
            snipmate = to_snipmate(ast)
            if snipmate:
                ud['snipmate_snippet'] = snipmate
                ud['is_snippet'] = 1
            else:
                ud['is_snippet'] = 0
        except:
            ud['is_snippet'] = 0
            logger.exception("ncm2_lsp_snippet failed parsing item %s", item)
        return item

    # add [+] mark for snippets
    def decorate(data, matches):
        matches = old_decorate(data, matches)

        has_snippet = False

        for m in matches:
            ud = m['user_data']
            if not ud.get('is_snippet', False):
                continue
            has_snippet = True

        if not has_snippet:
            return matches

        for m in matches:
            ud = m['user_data']
            if ud.get('is_snippet', False):
                # [+] sign indicates that this completion item is
                # expandable
                if ud.get('ncm2_snipmate_auto', False):
                    m['menu'] = '(+) ' + m['menu']
                else:
                    m['menu'] = '[+] ' + m['menu']
            else:
                m['menu'] = '[ ] ' + m['menu']

        return matches

    ncm2_core.matches_decorate = decorate
    ncm2_core.match_formalize = formalize


wrap()
