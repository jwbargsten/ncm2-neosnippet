# -*- coding: utf-8 -*-


def wrap():
    def snipmate_text(txt):
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
    import re

    logger = getLogger(__name__)

    vim.command('call ncm2_snipmate#init()')

    old_formalize = ncm2_core.match_formalize
    old_decorate = ncm2_core.matches_decorate

    parser = Parser()

    # convert lsp snippet into snipmate snippet
    def formalize(ctx, item):
        item = old_formalize(ctx, item)
        ud = item['user_data']

        if 'is_snippet' in item and 'is_snippet' not in ud:
            ud['is_snippet'] = item['is_snippet']
        if 'snippet' in item and 'snippet' not in ud:
            ud['snippet'] = item['snippet']
        if 'is_snippet' not in ud:
            ud['is_snippet'] = 0
        if 'snippet' not in ud:
            ud['snippet'] = ''
        if 'snippet_word' not in ud:
            ud['snippet_word'] = item['word']

        # fix data return from LanguageClient
        if ud['is_snippet'] and item['word'] == ud['snippet']:
            item['word'] = item['abbr']

        if not ud['is_snippet'] or not ud['snippet']:

            if ud.get('is_snippet', None):
                return item

            w = item['word']
            m = re.search(re.escape(w) + r'\s*\((.*)\)', item['menu'])
            if not m:
                return item

            if not ctx.get('menu_snippet', False):
                return item

            # hacky
            # convert it into snippet
            args = m.group(1)
            snippet = snipmate_text(w + '(')
            for idx, arg in enumerate(args.split(',')):
                if idx > 0:
                    snippet += snipmate_text(', ')

                snippet += snipmate_placeholder(idx+1, arg)
            snippet += snipmate_text(')') + snipmate_placeholder(0)
            ud['snipmate_snippet'] = snippet
            ud['is_snippet'] = 1
            ud['ncm2_snipmate_auto'] = 1
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
                    m['menu'] = '|+| ' + m['menu']
                else:
                    m['menu'] = '[+] ' + m['menu']
            else:
                m['menu'] = '[ ] ' + m['menu']

        return matches

    ncm2_core.matches_decorate = decorate
    ncm2_core.match_formalize = formalize


wrap()
