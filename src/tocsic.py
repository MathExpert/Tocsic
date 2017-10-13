#!/usr/bin/env python3

import re
import os
import argparse
from enum import Enum
from tocsic_utils import static_vars


class Tocsic:
    toc_marker = '# Table of Contents'

    head_regex = re.compile(r'(#+)\s*(\S+(?:\s+\S+)*)')
    keyword_regex = re.compile(r'\s*<a +id="([\w-]+)"></a>')

    class BodyState(Enum):
        BODY = 1
        FOUND_LINK = 2
        FOUND_HEADER = 3
        IN_CODE_BLOCK = 4

    def __init__(self):
        self.args = None

        self.input_file = None
        self.output_file = None
        self.is_overwrite = False

        self.make_arguments()
        self.check_arguments()

        self.toc_info = []
        self.toc = Tocsic.toc_marker + '\n'
        self.body = ''

        self.header_dict = dict()

        try:
            self.file = open(self.input_file, 'r')
        except IOError:
            raise TocsicException('Failed to open file ' + self.input_file)

        self.is_valid = True

    def make_arguments(self):
        arg_parser = argparse.ArgumentParser()
        arg_parser.add_argument('filename', type=str, help='path to Markdown document')
        arg_parser.add_argument('-c', '--clean', help='remove table of contents if present')
        arg_parser.add_argument('-o', '--output', type=str, help='output file', default=None)
        # TODO: add an option for handling empty header names
        # TODO: add an option for handling other keyword formats
        # TODO: add an option for disabling keyword processing
        self.args = arg_parser.parse_args()

    def check_arguments(self):
        md_path = self.args.filename
        if not os.path.exists(md_path) or not os.path.isfile(md_path):
            raise TocsicException('{} does not exist or is not a file'.format(md_path))

        self.input_file = md_path

        if self.args.output is not None:
            self.output_file = self.args.output
            if self.output_file == self.input_file:
                self.is_overwrite = True
                if not is_user_sure('Output file is the same as input file, rewrite? [y/n]'):
                    self.is_valid = False
                    return
        else:
            self.output_file = self.make_output_name(self.input_file)

    @staticmethod
    def make_output_name(filename):
        if '.' not in filename:
            return filename + '_toc'

        return '.cot_'.join(filename[::-1].split('.', 1))[::-1]

    def add_toc(self):
        if not self.is_valid:
            return

        line_gen = FileReader(self.file)
        if self.process_start(line_gen):
            self.process_toc(line_gen)
        self.process_body(line_gen)
        self.file.close()
        # TODO: add toc error-checking and maybe some postprocessing

        self.make_toc()
        self.generate_md()

    @staticmethod
    def process_start(line_gen):
        try:
            line = next(line_gen).strip()
            while not line:
                line = next(line_gen).strip()

            line_gen.back()
            if line == Tocsic.toc_marker:
                return True
            else:
                return False
        except StopIteration:
            pass

    @staticmethod
    def process_toc(line_gen):
        try:
            line = next(line_gen).strip()
            while line:
                line = next(line_gen).strip()

            line_gen.back()
        except StopIteration:
            pass

    def process_body(self, line_gen):
        body_state = Tocsic.BodyState.BODY
        link_line = ''

        try:
            while True:
                if body_state == Tocsic.BodyState.BODY:
                    line = next(line_gen)
                    if line.startswith('<a'):
                        link_line = line
                        body_state = Tocsic.BodyState.FOUND_LINK
                    elif line.startswith('#'):
                        # TODO: add support for === and --- style headers
                        self.make_toc_entry(line, line_gen.line_num, None)
                        self.body += '<a id="{}"></a>\n'.format(self.toc_info[-1][2])
                        self.body += line
                    elif line.startswith('```'):
                        body_state = Tocsic.BodyState.IN_CODE_BLOCK
                        self.body += line
                    else:
                        self.body += line
                elif body_state == Tocsic.BodyState.IN_CODE_BLOCK:
                    line = next(line_gen)
                    if line.startswith('```'):
                        body_state = Tocsic.BodyState.BODY
                    self.body += line
                elif body_state == Tocsic.BodyState.FOUND_LINK:
                    line = next(line_gen)
                    if line.startswith('<a'):
                        link_line = line
                    elif line.startswith('#'):
                        body_state = Tocsic.BodyState.BODY
                        self.make_toc_entry(line, line_gen.line_num, link_line)
                        self.body += '<a id="{}"></a>\n'.format(self.toc_info[-1][2])
                    elif line.strip() != '':
                        print('ERROR: There is something between <a> and a header')
                    self.body += line
        except StopIteration:
            pass

    @static_vars(to_underscore_regex=re.compile(r'[ -/]+'))
    def header_to_link(self, header):
        # TODO: generate correct link name if header contains characters that don't work in links
        link = re.sub(self.header_to_link.to_underscore_regex, '_', header.lower()).strip('_')
        link = ''.join(filter(lambda s: str.isalnum(s) or s == '_', link))

        header_cnt = self.header_dict.get(link, 0)
        if header_cnt == 0:
            self.header_dict[link] = 1
            return link
        else:
            self.header_dict[link] += 1
            return link + '_' + str(header_cnt)

    def make_toc_entry(self, line, line_num, keyword_line=None):
        search_res = re.search(Tocsic.head_regex, line)
        if not search_res:
            raise TocsicException('Line {} starts with "#" but is not a header'.format(line_num))

        header = search_res.groups()
        level = len(header[0]) - 1
        header_name = header[1]
        link = ''

        if keyword_line:
            search_res = re.search(Tocsic.keyword_regex, keyword_line)
            if search_res:
                link = search_res.groups()[0]
        else:
            link = self.header_to_link(header_name)

        self.toc_info.append((level, header_name, link))

    def make_toc(self):
        for toc_entry in self.toc_info:
            self.toc += '{}1. [{}](#{})\n'.format('    ' * toc_entry[0], toc_entry[1], toc_entry[2])

    def generate_md(self):
        with open(self.output_file, 'w') as f:
            f.write(self.toc)
            f.write('\n')
            f.write(self.body)


class TocsicException(Exception):
    pass


class FileReader:
    def __init__(self, f):
        self.repeat = False
        self.last_line = None
        self.iter = iter(f)
        self.line_num = 0

    def __iter__(self):
        return self

    def back(self):
        self.repeat = True

    def __next__(self):
        if self.repeat:
            self.repeat = False
            return self.last_line
        else:
            self.last_line = next(self.iter)
            self.line_num += 1
            return self.last_line


def is_user_sure(message):
    print(message)
    while True:
        answer = input()
        if answer.lower() in ('y', 'yes'):
            return True
        elif answer.lower() in ('n', 'no'):
            return False
        else:
            print('Please type "y" or "n"')


if __name__ == '__main__':
    md = Tocsic()
    md.add_toc()
